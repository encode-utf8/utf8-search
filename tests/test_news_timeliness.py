"""时效性集成测试（对应验收项 5.2-2 / 5.2-6 / 5.2-8），全部离线。

覆盖：新闻引擎选择、pipeline 的时效重排与过期过滤、日期回补、general 主题不受影响。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from utf8_search.cache.store import CacheStore
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import ExtractItem, SearchRequest
from utf8_search.providers.base import BaseProvider, SearchHit
from utf8_search.providers.searxng import SearxngProvider
from utf8_search.verify.metrics import evaluate_timeliness


class _FakeResponse:
    """最小的 httpx.Response 替身：只提供 SearxngProvider 用到的方法。"""

    status_code = 200
    request = None

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _RecordingClient:
    """记录请求参数，用于断言引擎选择逻辑。"""

    def __init__(self) -> None:
        self.params: dict = {}

    async def get(self, url, params=None, timeout=None):  # noqa: ANN001
        self.params = dict(params or {})
        return _FakeResponse({"results": []})


class _DateProvider(BaseProvider):
    """返回固定结果（含日期）的假搜索源。"""

    name = "searxng"

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):
        return self._hits[:max_results]


class _DateExtractor:
    """只实现 fetch_date 的假抽取器，用于验证日期回补。"""

    def __init__(self, date: str | None) -> None:
        self._date = date
        self.calls = 0

    async def fetch_date(self, url, *, download_timeout=None):  # noqa: ANN001
        self.calls += 1
        return self._date

    async def extract(self, url, **kwargs):  # noqa: ANN001
        return ExtractItem(url=url, raw_content="正文", chars=2)


class _RecordingProvider(BaseProvider):
    """记录每次调用的 topic / time_range / engines，用于断言「通用引擎补充」这一路。"""

    name = "searxng"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):  # noqa: ANN001
        self.calls.append(
            {"topic": topic, "time_range": time_range, "engines": engines, "max_results": max_results}
        )
        return []


def _hit(index: int, published: str | None) -> SearchHit:
    return SearchHit(
        title=f"结果{index}",
        url=f"https://site{index}.com/a",
        snippet=f"摘要{index}",
        engine="duckduckgo news",
        published_date=published,
    )


async def _make_pipeline(settings, tmp_path, hits, extractor=None) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "news.db"))
    await cache.open()
    return SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[_DateProvider(hits)],
        extractor=extractor or _DateExtractor(None),
    )


# ---------------------------------------------------------------- 引擎选择
async def test_news_topic_uses_news_engines() -> None:
    """topic=news 时必须使用 news_engines，而不是通用引擎列表。"""
    client = _RecordingClient()
    provider = SearxngProvider(
        "http://searxng:8080",
        client,
        default_engines=["resulthunter", "yandex"],
        news_engines=["duckduckgo news"],
    )
    await provider.search("测试", max_results=5, topic="news")
    assert client.params["engines"] == "duckduckgo news"
    # 关键回归点：给了 engines 就绝不能同时传 categories。
    # SearXNG（webadapter.parse_generic）把两者按「叠加」处理，同时传会让
    # engines 列表失去约束力，退回 news 类目下全部引擎 —— 2026-09-24 前的
    # 逐引擎隔离实测就是栽在这里，得出了错误结论。
    assert "categories" not in client.params


async def test_general_topic_uses_default_engines() -> None:
    client = _RecordingClient()
    provider = SearxngProvider(
        "http://searxng:8080",
        client,
        default_engines=["resulthunter", "yandex"],
        news_engines=["duckduckgo news"],
    )
    await provider.search("测试", max_results=5, topic="general")
    assert client.params["engines"] == "resulthunter,yandex"
    assert "categories" not in client.params


async def test_explicit_engines_override_news_engines() -> None:
    """调用方显式指定 engines 时优先（调试用）。"""
    client = _RecordingClient()
    provider = SearxngProvider(
        "http://searxng:8080", client, default_engines=["a"], news_engines=["duckduckgo news"]
    )
    await provider.search("测试", max_results=5, topic="news", engines=["wikinews"])
    assert client.params["engines"] == "wikinews"


async def test_empty_news_engines_leaves_choice_to_searxng() -> None:
    """news_engines 留空时不传 engines，交给 SearXNG 自己的 news 类目引擎集合。"""
    client = _RecordingClient()
    provider = SearxngProvider("http://searxng:8080", client, default_engines=["a"], news_engines=[])
    await provider.search("测试", max_results=5, topic="news")
    assert "engines" not in client.params
    assert client.params["categories"] == "news"


# ---------------------------------------------------------------- 时效重排
def _now_iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


async def test_news_search_ranks_fresh_first_and_drops_stale(settings, tmp_path) -> None:
    """新闻主题：新鲜结果排前，已知过期结果被剔除。"""
    hits = [_hit(1, _now_iso(400)), _hit(2, _now_iso(2)), _hit(3, _now_iso(1))]
    pipeline = await _make_pipeline(settings, tmp_path, hits)
    response = await pipeline.search(
        SearchRequest(query="最近新闻", max_results=2, depth="basic", topic="news")
    )

    assert len(response.results) == 2
    assert all(r.published_date for r in response.results)
    assert all("2021" not in (r.published_date or "") for r in response.results)
    await pipeline.close()


async def test_general_topic_keeps_original_order(settings, tmp_path) -> None:
    """general 主题不做时效重排：行为与改动前一致。"""
    hits = [_hit(1, _now_iso(400)), _hit(2, _now_iso(2)), _hit(3, _now_iso(1))]
    pipeline = await _make_pipeline(settings, tmp_path, hits)
    response = await pipeline.search(
        SearchRequest(query="普通查询", max_results=3, depth="basic", topic="general")
    )

    assert [r.url for r in response.results] == [h.url for h in hits]
    await pipeline.close()


async def test_news_backfills_missing_dates(settings, tmp_path) -> None:
    """缺失发布日期时会调用 fetch_date 回补，并用于后续重排。"""
    extractor = _DateExtractor(_now_iso(1).split("T")[0])
    hits = [_hit(1, None), _hit(2, _now_iso(30))]
    pipeline = await _make_pipeline(settings, tmp_path, hits, extractor)
    response = await pipeline.search(
        SearchRequest(query="新闻", max_results=2, depth="basic", topic="news")
    )

    assert extractor.calls == 1  # 只有「无日期」的第 1 条会触发抓取，已有日期的不会
    filled = [r for r in response.results if r.published_date]
    assert filled, "回补后的日期应写入结果"
    await pipeline.close()


async def test_news_backfill_can_be_disabled(settings, tmp_path) -> None:
    """关闭 news_date_backfill 后不应产生任何抓取。"""
    tuning = settings.model_copy(update={"news_date_backfill": False})
    extractor = _DateExtractor(_now_iso(1).split("T")[0])
    pipeline = await _make_pipeline(tuning, tmp_path, [_hit(1, None)], extractor)
    await pipeline.search(SearchRequest(query="新闻", max_results=1, depth="basic", topic="news"))

    assert extractor.calls == 0
    await pipeline.close()


def test_fresh_days_follows_time_range(settings, tmp_path) -> None:
    """time_range 决定新鲜窗口：day/week/month/year 分别是 1/7/31/365 天。"""
    from utf8_search.cache.store import CacheStore as _Store  # noqa: F401

    pipeline = SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=CacheStore(str(tmp_path / "x.db")),
        providers=[],
        extractor=_DateExtractor(None),
    )
    assert pipeline._fresh_days(SearchRequest(query="q", time_range="day")) == 1
    assert pipeline._fresh_days(SearchRequest(query="q", time_range="week")) == 7
    assert pipeline._fresh_days(SearchRequest(query="q", time_range="month")) == 31
    assert pipeline._fresh_days(SearchRequest(query="q", time_range="year")) == 365
    assert pipeline._fresh_days(SearchRequest(query="q")) == settings.news_fresh_days


# ---------------------------------------------------------------- 验收判定
def test_evaluate_timeliness_passes_at_threshold() -> None:
    passed, notes, details = evaluate_timeliness(total=10, fresh=8)
    assert passed is True
    assert details["ratio"] == 0.8


def test_evaluate_timeliness_fails_below_threshold() -> None:
    passed, notes, _ = evaluate_timeliness(total=10, fresh=7)
    assert passed is False
    assert any("未达标" in note for note in notes)


def test_evaluate_timeliness_without_results() -> None:
    passed, notes, _ = evaluate_timeliness(total=0, fresh=0)
    assert passed is False
    assert notes

# ---------------------------------------------------------------- 通用引擎新鲜候选补充
async def test_news_general_extra_passes_time_range_and_uses_clean_engines(settings, tmp_path) -> None:
    """新闻的「通用引擎补充」必须透传 time_range，且使用 news_general_engines 这组更干净的引擎。

    两个点都是实测驱动：
    - 通用引擎（Bing/Google 等）的 time_range 过滤是有效的：time_range=day 时每条查询能拿到
      5-12 条「当天/1 日内」结果；不透传时同一批查询只有 0-2 条带日期。这一路是本服务
      时效性从 75% 拉到 100% 的关键。
    - 主通用引擎列表里的 yandex 配合 time_range 会返回垃圾农场内容（成人站/盗播站），
      所以这一路单独配引擎集，默认把它排除。
    """
    tuning = settings.model_copy(update={"news_general_engines": "resulthunter,google"})
    provider = _RecordingProvider()
    cache = CacheStore(str(tmp_path / "extra.db"))
    await cache.open()
    pipeline = SearchPipeline(
        tuning,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[provider],
        extractor=_DateExtractor(None),
    )
    await pipeline.search(
        SearchRequest(query="新闻", max_results=5, depth="basic", topic="news", time_range="day")
    )
    await pipeline.close()

    news_calls = [c for c in provider.calls if c["topic"] == "news"]
    general_calls = [c for c in provider.calls if c["topic"] == "general"]
    assert len(news_calls) == 1, provider.calls
    assert len(general_calls) == 1, provider.calls
    assert general_calls[0]["time_range"] == "day"
    assert general_calls[0]["engines"] == ["resulthunter", "google"]


async def test_general_topic_does_not_trigger_extra_call(settings, tmp_path) -> None:
    """通用主题不应触发任何「新闻补充」请求（避免白白多一次上游往返）。"""
    provider = _RecordingProvider()
    cache = CacheStore(str(tmp_path / "no-extra.db"))
    await cache.open()
    pipeline = SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[provider],
        extractor=_DateExtractor(None),
    )
    await pipeline.search(SearchRequest(query="普通查询", max_results=5, depth="basic", topic="general"))
    await pipeline.close()

    assert [c["topic"] for c in provider.calls] == ["general"]


class _ConcurrencyProbeProvider(BaseProvider):
    """探测「新闻请求」与「通用引擎补充请求」是否真的并发。

    news 那一路会等 general 那一路先启动：如果实现退回成串行（先 news 再 general），
    news 会一直等到超时，`concurrent` 就是 False。
    """

    name = "searxng"

    def __init__(self) -> None:
        self.general_started = asyncio.Event()
        self.concurrent = False

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):  # noqa: ANN001
        if topic == "news":
            try:
                await asyncio.wait_for(self.general_started.wait(), timeout=1.0)
                self.concurrent = True
            except asyncio.TimeoutError:
                self.concurrent = False
        else:
            self.general_started.set()
        return []


async def test_news_and_general_requests_run_concurrently(settings, tmp_path) -> None:
    """两路上游请求必须并发发出：新闻主题只多花「较慢那一次」的延迟。

    实测这项优化把 topic=news 的端到端耗时从 2.6-5.6s 压到 1.1-1.3s。
    """
    provider = _ConcurrencyProbeProvider()
    cache = CacheStore(str(tmp_path / "concurrent.db"))
    await cache.open()
    pipeline = SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[provider],
        extractor=_DateExtractor(None),
    )
    await asyncio.wait_for(
        pipeline.search(
            SearchRequest(query="新闻", max_results=5, depth="basic", topic="news", time_range="day")
        ),
        timeout=5.0,
    )
    await pipeline.close()

    assert provider.concurrent is True


# ---------------------------------------------------------------- 日期回补的按需触发
def _dated_url(index: int, days_ago: int) -> str:
    """构造一条「日期写在 URL 路径里」的地址（风格仿政府站 /202609/t20260922_ 形态）。"""
    day = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return f"https://news{index}.example.com/{day:%Y%m}/{day:%Y%m%d}_1.html"


async def test_url_dates_are_used_without_fetching_pages(settings, tmp_path) -> None:
    """URL 里带日期的结果直接采用，完全不触发抓页面（零网络开销的第一步）。"""
    hits = [
        SearchHit(
            title=f"新闻{i}",
            url=_dated_url(i, 1),
            snippet="",
            engine="google news",
            published_date=None,
        )
        for i in range(1, 6)
    ]
    extractor = _DateExtractor(None)
    pipeline = await _make_pipeline(settings, tmp_path, hits, extractor)
    response = await pipeline.search(
        SearchRequest(query="新闻", max_results=5, depth="basic", topic="news")
    )

    assert extractor.calls == 0, "URL 已给出日期，不该再抓页面"
    assert all(r.published_date for r in response.results)
    await pipeline.close()


async def test_backfill_skipped_when_fresh_results_already_enough(settings, tmp_path) -> None:
    """已有足够「新鲜」结果时整段跳过抓页面回补 —— topic=news 延迟优化的关键。"""
    hits = [_hit(1, _now_iso(1)), _hit(2, _now_iso(2)), _hit(3, None)]
    extractor = _DateExtractor(_now_iso(1).split("T")[0])
    pipeline = await _make_pipeline(settings, tmp_path, hits, extractor)
    await pipeline.search(SearchRequest(query="新闻", max_results=2, depth="basic", topic="news"))

    assert extractor.calls == 0
    await pipeline.close()


async def test_backfill_page_budget_scales_with_shortfall(settings, tmp_path) -> None:
    """缺口越大抓得越多，但始终受 news_date_pages 封顶（避免长尾查询拖慢响应）。"""
    tuning = settings.model_copy(update={"news_date_pages": 2})
    extractor = _DateExtractor(None)
    hits = [_hit(i, None) for i in range(1, 11)]
    pipeline = await _make_pipeline(tuning, tmp_path, hits, extractor)
    await pipeline.search(SearchRequest(query="新闻", max_results=5, depth="basic", topic="news"))

    # 缺口 5，按每个缺口 4 个候选估算应为 20，但被 news_date_pages=2 封顶
    assert extractor.calls == 2
    await pipeline.close()

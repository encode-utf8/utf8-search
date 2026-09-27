"""流水线测试：深度模式、抓取预算、缓存与降级（全部离线，使用假 Provider）。"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

from utf8_search.cache.store import CacheStore
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import ExtractItem, ExtractRequest, SearchRequest
from utf8_search.providers.base import BaseProvider, SearchHit


class FakeProvider(BaseProvider):
    """返回固定结果的假搜索源。"""

    def __init__(self, name: str, hits: list[SearchHit], *, delay: float = 0.0, fail: bool = False) -> None:
        self.name = name
        self._hits = hits
        self._delay = delay
        self._fail = fail
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        non_blocking=False,
    ):
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._fail:
            raise RuntimeError("模拟上游故障")
        return self._hits[:max_results]


class FakeExtractor:
    """返回固定正文的假抽取器（可注入延迟，用于验证总预算）。"""

    def __init__(self, *, delay: float = 0.0) -> None:
        self._delay = delay
        self.calls = 0

    async def extract(
        self,
        url,
        *,
        fmt="markdown",
        max_chars=None,
        query="",
        use_cache=True,
        allow_jina=True,
        download_timeout=None,
        need_title=True,
    ):
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        text = f"{url} 的正文内容，包含 GPT-6 与价格信息。" * 2
        return ExtractItem(url=url, raw_content=text[: max_chars or len(text)], chars=len(text))


def _hits(count: int, engine: str = "brave") -> list[SearchHit]:
    return [
        SearchHit(title=f"结果{i}", url=f"https://site{i}.com/a", snippet=f"摘要{i}", engine=engine)
        for i in range(1, count + 1)
    ]


async def _make_pipeline(settings, tmp_path, providers, extractor) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    client = httpx.AsyncClient()
    return SearchPipeline(settings, client=client, cache=cache, providers=providers, extractor=extractor)


async def test_basic_mode_does_not_fetch_pages(settings, tmp_path) -> None:
    """basic 模式只搜索，不抓取正文。"""
    extractor = FakeExtractor()
    pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", _hits(5))], extractor)
    response = await pipeline.search(SearchRequest(query="GPT-6", max_results=3, depth="basic"))

    assert len(response.results) == 3
    assert response.pages_read == 0
    assert extractor.calls == 0
    await pipeline.close()


async def test_advanced_mode_reads_pages(settings, tmp_path) -> None:
    """advanced 模式会抓取正文，并计入 pages_read。"""
    extractor = FakeExtractor()
    pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", _hits(5))], extractor)
    response = await pipeline.search(SearchRequest(query="GPT-6", max_results=3, depth="advanced"))

    assert response.pages_read >= 1
    assert "正文内容" in response.results[0].content
    await pipeline.close()


async def test_second_identical_request_is_cached(settings, tmp_path) -> None:
    """同参数第二次请求应命中结果缓存。"""
    provider = FakeProvider("searxng", _hits(5))
    pipeline = await _make_pipeline(settings, tmp_path, [provider], FakeExtractor())
    request = SearchRequest(query="缓存测试", max_results=3, depth="basic")

    first = await pipeline.search(request)
    provider.calls = 0
    second = await pipeline.search(request)

    assert second.cached is True
    assert provider.calls == 0
    assert first.query == second.query
    await pipeline.close()


async def test_fetch_budget_cuts_slow_pages(settings, tmp_path) -> None:
    """慢页面会被总预算截断：整体耗时接近预算，而不是被最慢页面拖住。"""
    extractor = FakeExtractor(delay=5.0)
    pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", _hits(5))], extractor)

    started = time.perf_counter()
    response = await pipeline.search(SearchRequest(query="慢站点", max_results=3, depth="advanced"))
    elapsed = time.perf_counter() - started

    assert elapsed < 3.0  # 预算 0.6s，远小于单页 5s
    assert response.pages_read == 0
    await pipeline.close()


async def test_fallback_provider_used_when_primary_fails(settings, tmp_path) -> None:
    """主源失败时使用兜底源，并记录失败引擎。"""
    failing = FakeProvider("searxng", _hits(5), fail=True)
    fallback = FakeProvider("bing", _hits(3, engine="bing"))
    pipeline = await _make_pipeline(settings, tmp_path, [failing, fallback], FakeExtractor())

    response = await pipeline.search(SearchRequest(query="降级测试", max_results=2, depth="basic"))

    assert response.engines_used == ["bing"]
    assert "searxng" in response.failed_engines
    assert len(response.results) == 2
    await pipeline.close()


async def test_extract_batch_reports_failures(settings, tmp_path) -> None:
    """批量抽取：成功与失败分别返回，结构与请求对应。"""
    pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", _hits(2))], FakeExtractor())
    response = await pipeline.extract(ExtractRequest(urls=["https://a.com/1"], max_chars=500))

    assert len(response.results) == 1
    assert response.results[0].url == "https://a.com/1"
    assert response.failed_results == []
    await pipeline.close()

def test_build_http_mounts_bypasses_proxy_for_given_hosts() -> None:
    """回环与容器主机名应被配置为绕过代理（避免 Windows 系统代理导致的 502）。"""
    from utf8_search.core.pipeline import build_http_mounts

    mounts = build_http_mounts(["127.0.0.1", "searxng"])
    assert mounts == {"all://127.0.0.1": None, "all://searxng": None}
    assert build_http_mounts([]) is None

class RecordingProvider(FakeProvider):
    """记录每次向上游索取的条数，用于验证候选池。"""

    def __init__(self, hits: list[SearchHit]) -> None:
        super().__init__("searxng", hits)
        self.requested: list[int] = []

    async def search(self, query, *, max_results, **kwargs):
        self.requested.append(max_results)
        return await super().search(query, max_results=max_results, **kwargs)


def _article(index: int, title: str) -> SearchHit:
    return SearchHit(
        title=title, url=f"https://news{index}.com/2026/09/24/article-{index}.html", engine="brave"
    )


async def test_general_topic_asks_for_candidate_pool(settings, tmp_path) -> None:
    """通用主题也要向上游索取候选池（M5-5.3）：候选等于结果数时质量过滤会被全部补回、等于失效。"""
    provider = RecordingProvider(_hits(30))
    pipeline = await _make_pipeline(settings, tmp_path, [provider], FakeExtractor())

    await pipeline.search(SearchRequest(query="候选池测试", max_results=5, depth="basic"))

    assert provider.requested[0] >= settings.rank_candidate_pool
    await pipeline.close()


async def test_rank_filters_drop_aggregator_when_candidates_enough(settings, tmp_path) -> None:
    """候选充足时聚合页被剔除；关掉过滤（改动前口径）时它仍在结果里。"""
    hits = [
        SearchHit(title="GPT-6 价格 参数 官网首页", url="https://agg.com/", engine="brave"),
        *[_article(i, f"GPT-6 价格与参数详解（第{i}篇）") for i in range(1, 7)],
    ]
    legacy_settings = settings.model_copy(
        update={
            "rank_drop_aggregator_pages": False,
            "rank_min_query_coverage": 0.0,
            "rank_max_per_host": 0,
        }
    )
    legacy_pipeline = await _make_pipeline(legacy_settings, tmp_path, [FakeProvider("searxng", hits)], FakeExtractor())
    new_pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", hits)], FakeExtractor())
    request = SearchRequest(query="GPT-6 价格 参数", max_results=5, depth="basic")

    legacy_top = (await legacy_pipeline._rank_hits(list(hits), request))[:5]
    new_top = (await new_pipeline._rank_hits(list(hits), request))[:5]

    assert any("agg.com" in r.url for r in legacy_top)          # 改动前：聚合页留在结果里
    assert all("agg.com" not in r.url for r in new_top)         # 改动后：被剔除
    assert len(new_top) == 5                                    # 且没有把结果掏空
    await legacy_pipeline.close()
    await new_pipeline.close()


async def test_rank_filters_never_empty_results(settings, tmp_path) -> None:
    """候选不足时按原排序补回：质量过滤绝不把结果掏空（M5-5.3 稳健性要求）。"""
    hits = [
        SearchHit(title=f"某站{i}_官网首页", url=f"https://agg{i}.com/", engine="brave")
        for i in range(1, 4)
    ] + [_article(1, "GPT-6 价格与参数详解")]
    pipeline = await _make_pipeline(settings, tmp_path, [FakeProvider("searxng", hits)], FakeExtractor())

    top = await pipeline._rank_hits(list(hits), SearchRequest(query="GPT-6 价格", max_results=5, depth="basic"))

    assert len(top) == 4  # 全部候选都在，没有被过滤掏空
    await pipeline.close()

async def test_news_topic_keeps_aggregator_pages_general_drops_them(settings, tmp_path) -> None:
    """新闻主题只做结构性过滤（同站/脚本），通用主题才剔除聚合页。

    依据：配对 A/B（`news_check.py --ab`）实测，通用主题的聚合页/覆盖度判据套到新闻路径上，
    会把各站点「当天更新的日报/栏目页」连同日期一起剔除，时效性 39/40 → 32/40。
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hits = [
        # 标题含「首页」且是站点首页 → 通用主题必判聚合页；这里刻意让它的查询词匹配度最高
        SearchHit(
            title="最近一周 AI 行业动态 太平洋科技 首页",
            url="https://www.pconline.com.cn/",
            engine="brave",
            published_date=today,
        ),
        *[
            SearchHit(
                title=f"最近一周 AI 行业动态（第{i}期）",
                url=f"https://post.smzdm.com/p/{i}",
                engine="brave",
                published_date=today,
            )
            for i in range(1, 7)
        ],
    ]
    news_settings = settings.model_copy(update={"news_date_backfill": False})
    pipeline = await _make_pipeline(news_settings, tmp_path, [FakeProvider("searxng", hits)], FakeExtractor())
    query = "最近一周 AI 行业动态"

    general_top = (
        await pipeline._rank_hits(
            list(hits), SearchRequest(query=query, max_results=5, depth="basic")
        )
    )[:5]
    news_top = (
        await pipeline._rank_hits(
            list(hits), SearchRequest(query=query, max_results=5, depth="basic", topic="news")
        )
    )[:5]

    assert len(general_top) == 5 and len(news_top) == 5
    assert all("pconline.com.cn" not in r.url for r in general_top)   # 通用主题：聚合页被剔除
    assert any("pconline.com.cn" in r.url for r in news_top)          # 新闻主题：保留（不挤掉日期）
    # 两种口径下同站限流都生效：同一域名最多 2 条（其余靠补回机制兜底，不会掏空结果）
    assert sum(1 for r in news_top if "smzdm.com" in r.url) <= 4
    await pipeline.close()

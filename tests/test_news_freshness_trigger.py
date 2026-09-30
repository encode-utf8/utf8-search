"""news 时效收口（2026-09-30）：新鲜度触发判据 + Bing 让位。全部离线。

两条改动：
1. `_needs_general_extra` 的判据从「主源结果数 < max_results」改成
   「**窗口内带日期的新鲜结果数** < max_results」—— 无日期结果不计入分子，但也不丢弃；
2. 新闻 + time_range 场景下，兜底源（Bing）**让位**到「日期回补」之后：
   顺序为 主源 → 日期回补 → Bing，避免 Bing 的无日期结果先把 max_results 填满、
   把日期回补路整条旁路掉（实测中文组 0/25 就是这个原因）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from utf8_search.cache.store import CacheStore
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import ExtractItem, SearchRequest
from utf8_search.providers.base import BaseProvider, SearchHit


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit(
    index: int, published: str | None, engine: str = "chinaso news", title: str | None = None
) -> SearchHit:
    return SearchHit(
        title=title or f"结果{index}",
        url=f"https://site{index}.com/a",
        snippet=f"摘要{index}",
        engine=engine,
        published_date=published,
    )


class _Extractor:
    async def fetch_date(self, url, *, download_timeout=None):  # noqa: ANN001
        return None

    async def extract(self, url, **kwargs):  # noqa: ANN001
        return ExtractItem(url=url, raw_content="正文", chars=2)


class _ScriptedSearxng(BaseProvider):
    """按 topic 返回不同结果，并记录调用顺序。"""

    name = "searxng"

    def __init__(self, news_hits: list[SearchHit], general_hits: list[SearchHit] | None = None) -> None:
        self.news_hits = news_hits
        self.general_hits = general_hits or []
        self.calls: list[str] = []
        self.unresponsive_engines: list[str] = []

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):  # noqa: ANN001
        self.calls.append(topic)
        return list(self.news_hits if topic == "news" else self.general_hits)[:max_results]


class _RecordingBing(BaseProvider):
    name = "bing"

    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):  # noqa: ANN001
        self.calls += 1
        return list(self.hits)[:max_results]


async def _pipeline(settings, tmp_path, providers) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "news-freshness.db"))
    await cache.open()
    return SearchPipeline(
        settings, client=httpx.AsyncClient(), cache=cache, providers=providers, extractor=_Extractor()
    )


# ---------------------------------------------------------------- 判据：三档输入
async def test_needs_extra_false_when_all_dated_and_fresh(settings, tmp_path) -> None:
    pipeline = await _pipeline(settings, tmp_path, [])
    hits = [_hit(i, _iso(0.5)) for i in range(5)]
    assert pipeline._needs_general_extra(hits, SearchRequest(query="q", topic="news", time_range="day")) is False


async def test_needs_extra_true_when_all_undated(settings, tmp_path) -> None:
    """无日期结果不计入分子（无法证明新鲜），但也不丢弃 —— 判据要求补一路新鲜候选。"""
    pipeline = await _pipeline(settings, tmp_path, [])
    hits = [_hit(i, None) for i in range(5)]
    assert pipeline._needs_general_extra(hits, SearchRequest(query="q", topic="news", time_range="day")) is True
    assert pipeline._fresh_count(hits, SearchRequest(query="q", topic="news", time_range="day")) == 0


async def test_needs_extra_mixed_counts_only_fresh(settings, tmp_path) -> None:
    """混合输入：只有「带日期且窗口内」的才算数；过期与无日期都不算。"""
    pipeline = await _pipeline(settings, tmp_path, [])
    request = SearchRequest(query="q", topic="news", time_range="day")
    mixed = [_hit(1, _iso(0.2)), _hit(2, _iso(0.8)), _hit(3, _iso(40)), _hit(4, None), _hit(5, None)]
    assert pipeline._fresh_count(mixed, request) == 2
    assert pipeline._needs_general_extra(mixed, request) is True
    # 凑够 5 条新鲜的就不再补（即使还有过期/无日期的在池子里）
    enough = [_hit(i, _iso(0.3)) for i in range(5)] + [_hit(9, _iso(99)), _hit(10, None)]
    assert pipeline._needs_general_extra(enough, request) is False


async def test_needs_extra_ignores_general_topic(settings, tmp_path) -> None:
    pipeline = await _pipeline(settings, tmp_path, [])
    hits = [_hit(i, None) for i in range(5)]
    assert pipeline._needs_general_extra(hits, SearchRequest(query="q", topic="general")) is False


# ---------------------------------------------------------------- Bing 让位
async def test_bing_defers_until_after_date_backfill(settings, tmp_path) -> None:
    """新闻 + time_range：主源→日期回补→Bing；Bing 结果仍入池。"""
    stale_news = [_hit(i, _iso(60), engine="chinaso news") for i in range(5)]
    fresh_extra = [_hit(100 + i, _iso(0.4), engine="naver") for i in range(5)]
    # 兜底结果要与查询相关（2026-09-30 起兜底源入池前过覆盖率闸门）
    bing_hits = [_hit(200 + i, None, engine="bing", title=f"中文新闻 兜底 {i}") for i in range(5)]
    searxng = _ScriptedSearxng(stale_news, fresh_extra)
    bing = _RecordingBing(bing_hits)
    pipeline = await _pipeline(settings, tmp_path, [searxng, bing])

    hits, engines_used, _failed, _degraded = await pipeline._collect_hits(
        SearchRequest(query="中文新闻", topic="news", time_range="day", max_results=5)
    )

    # 顺序：先 news 主源，再 general 日期回补，最后才轮到 Bing
    assert searxng.calls == ["news", "general"]
    assert bing.calls == 0, "日期回补已经凑够新鲜候选，没必要再打兜底源"
    assert engines_used == ["searxng", "searxng:general"]
    # 日期回补已凑够 5 条新鲜 → Bing 不该再被打
    assert pipeline._fresh_count(hits, SearchRequest(query="q", topic="news", time_range="day")) >= 5
    assert all(hit.engine != "bing" for hit in hits), "日期回补已够，Bing 不该被调用"


async def test_bing_still_fills_when_backfill_not_enough(settings, tmp_path) -> None:
    """主源条数本身不足、日期回补也没补上时，让位后的 Bing 仍然兜住（不返回空/残缺结果）。"""
    stale_news = [_hit(i, _iso(60)) for i in range(2)]  # 只有 2 条 → 数量不足
    # 兜底结果要与查询相关（2026-09-30 起兜底源入池前过覆盖率闸门）
    bing_hits = [_hit(200 + i, None, engine="bing", title=f"中文新闻 兜底 {i}") for i in range(5)]
    searxng = _ScriptedSearxng(stale_news, general_hits=[])
    bing = _RecordingBing(bing_hits)
    pipeline = await _pipeline(settings, tmp_path, [searxng, bing])

    hits, engines_used, _failed, _degraded = await pipeline._collect_hits(
        SearchRequest(query="中文新闻", topic="news", time_range="day", max_results=5)
    )

    assert searxng.calls == ["news", "general"]
    assert bing.calls == 1
    # 补充路没拿到任何候选，所以不会记 "searxng:general"；Bing 兜住
    assert engines_used == ["searxng", "bing"]
    assert any(hit.engine == "bing" for hit in hits)
    assert len(hits) >= 5


async def test_bing_not_deferred_without_time_range(settings, tmp_path) -> None:
    """没有 time_range 时不启用让位逻辑：Bing 仍然按老顺序（主源够 5 条就不打）。

    注意：新的新鲜度判据对「无 time_range 的新闻查询」同样生效 —— 5 条结果全都**没有发布日期**
    时会触发日期回补路（这正是本次改动的目的），所以 searxng 会被调用两次（news + general）。
    """
    news_hits = [_hit(i, None) for i in range(5)]
    searxng = _ScriptedSearxng(news_hits, general_hits=[])
    bing = _RecordingBing([_hit(200, None, engine="bing", title="中文新闻 兜底")])
    pipeline = await _pipeline(settings, tmp_path, [searxng, bing])

    await pipeline._collect_hits(SearchRequest(query="中文新闻", topic="news", max_results=5))

    assert bing.calls == 0
    assert searxng.calls == ["news", "general"]

"""时效降级信号 `freshness_unverified`（2026-09-30，离线）。

规则：查询带 `time_range` 时，如果**可信日期源**（`news_trusted_date_engines` 白名单）里
窗口内的结果数 < `max_results`，就置 `degraded=true` + `degraded_reason="freshness_unverified"`。
背景：yandex 会把**索引日期**当发布日期上报（2017 年旧文标成当天），只看"7 日内比例"会被骗；
所以"能验证的时效"必须来自**抽检过日期可信**的引擎。

覆盖三层：pipeline 判据、REST 通道字段、MCP 通道字段。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient

from utf8_search.cache.store import CacheStore
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import ExtractItem, SearchRequest, SearchResponse
from utf8_search.providers.base import BaseProvider, SearchHit
from utf8_search.server import http_api, mcp_server


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit(index: int, engine: str, days_ago: float | None = None) -> SearchHit:
    return SearchHit(
        title=f"结果{index}",
        url=f"https://site{index}.com/a",
        snippet=f"摘要{index}",
        engine=engine,
        published_date=None if days_ago is None else _iso(days_ago),
    )


class _Provider(BaseProvider):
    name = "searxng"

    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.unresponsive_engines: list[str] = []

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):  # noqa: ANN001
        return list(self.hits)[:max_results]


class _Extractor:
    async def fetch_date(self, url, *, download_timeout=None):  # noqa: ANN001
        return None

    async def extract(self, url, **kwargs):  # noqa: ANN001
        return ExtractItem(url=url, raw_content="正文", chars=2)


async def _pipeline(settings, tmp_path, hits) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "degraded.db"))
    await cache.open()
    return SearchPipeline(
        settings, client=httpx.AsyncClient(), cache=cache, providers=[_Provider(hits)], extractor=_Extractor()
    )


# ---------------------------------------------------------------- pipeline 判据
async def test_trusted_fresh_results_not_degraded(settings, tmp_path) -> None:
    """可信源给了 5 条窗口内结果 → 不降级。"""
    hits = [_hit(i, "duckduckgo news", 0.3) for i in range(5)]
    pipeline = await _pipeline(settings, tmp_path, hits)
    response = await pipeline.search(
        SearchRequest(query="q", topic="news", time_range="day", max_results=5)
    )
    assert response.degraded is False
    assert response.degraded_reason is None
    await pipeline.close()


async def test_untrusted_dates_mark_degraded(settings, tmp_path) -> None:
    """只有「仅索引日期」的源（yandex）→ 标降级，即便条数与日期看着都够。"""
    hits = [_hit(i, "yandex", 0.1) for i in range(5)]
    pipeline = await _pipeline(settings, tmp_path, hits)
    response = await pipeline.search(
        SearchRequest(query="q", topic="news", time_range="day", max_results=5)
    )
    assert response.degraded is True
    assert response.degraded_reason == "freshness_unverified"
    await pipeline.close()


async def test_untrusted_engine_without_dates_marks_degraded(settings, tmp_path) -> None:
    """无日期结果（naver/yahoo/…）同样算「时效无法验证」。"""
    hits = [_hit(i, "naver") for i in range(5)]
    pipeline = await _pipeline(settings, tmp_path, hits)
    response = await pipeline.search(
        SearchRequest(query="q", topic="news", time_range="week", max_results=5)
    )
    assert response.degraded is True
    assert response.degraded_reason == "freshness_unverified"
    await pipeline.close()


async def test_no_time_range_never_marks_freshness_degraded(settings, tmp_path) -> None:
    """没指定 time_range 时不产生时效降级（普通新闻查询不该被标 degraded）。"""
    hits = [_hit(i, "naver") for i in range(5)]
    pipeline = await _pipeline(settings, tmp_path, hits)
    response = await pipeline.search(SearchRequest(query="q", topic="news", max_results=5))
    assert response.degraded is False
    await pipeline.close()


# ---------------------------------------------------------------- REST / MCP 通道
def _degraded_response() -> SearchResponse:
    return SearchResponse(
        query="中文新闻",
        results=[],
        degraded=True,
        degraded_reason="freshness_unverified",
        request_id="req-degraded",
    )


def test_rest_exposes_freshness_degraded(monkeypatch) -> None:
    """REST：degraded / degraded_reason 出现在响应体里（不动 Tavily 标准字段语义）。"""

    class _Stub:
        async def search(self, request):
            return _degraded_response()

    async def fake_get_pipeline(settings=None):
        return _Stub()

    monkeypatch.setattr(http_api, "get_pipeline", fake_get_pipeline)
    client = TestClient(http_api.app)
    payload = client.post("/v1/search", json={"query": "中文新闻", "topic": "news", "days": 1}).json()
    assert payload["degraded"] is True
    assert payload["degraded_reason"] == "freshness_unverified"


async def test_mcp_exposes_freshness_degraded(monkeypatch) -> None:
    """MCP：同一套字段，客户端能读到 degraded 与原因。"""

    class _Stub:
        async def search(self, request):
            return _degraded_response()

    async def fake_get_pipeline(settings=None):
        return _Stub()

    monkeypatch.setattr(mcp_server, "get_pipeline", fake_get_pipeline)
    payload = await mcp_server.web_search(query="中文新闻", topic="news", time_range="day")
    assert payload["degraded"] is True
    assert payload["degraded_reason"] == "freshness_unverified"

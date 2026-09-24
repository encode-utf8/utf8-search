"""流水线测试：深度模式、抓取预算、缓存与降级（全部离线，使用假 Provider）。"""

from __future__ import annotations

import asyncio
import time

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

    async def search(self, query, *, max_results, topic="general", time_range=None, engines=None, language="all"):
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
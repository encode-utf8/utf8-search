"""联网冒烟测试：需要真实的 SearXNG 与公网出口。

运行方式：先 `docker compose up -d searxng`，再 `pytest -m net -v`
"""

from __future__ import annotations

import time

import pytest

from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import ExtractRequest, SearchRequest

pytestmark = pytest.mark.net


@pytest.fixture
async def pipeline(settings):
    """使用真实配置（读取环境变量/默认值）的流水线。"""
    from utf8_search.config import Settings

    real = Settings(cache_enabled=False, enable_jina_fallback=True)
    instance = await SearchPipeline.create(real)
    yield instance
    await instance.close()


async def test_searxng_is_reachable(pipeline) -> None:
    """SearXNG 健康检查应通过（验证代理绕过配置正确）。"""
    searxng = next(p for p in pipeline.providers if p.name == "searxng")
    assert await searxng.health() is True


async def test_basic_search_returns_results_quickly(pipeline) -> None:
    """basic 搜索应返回结果，且引擎为 SearXNG（而不是兜底的 Bing）。"""
    started = time.perf_counter()
    response = await pipeline.search(SearchRequest(query="2026年 人工智能 政策", max_results=5, depth="basic"))
    elapsed = time.perf_counter() - started

    assert len(response.results) >= 3
    assert all(result.url.startswith("http") for result in response.results)
    assert "searxng" in response.engines_used, f"实际引擎: {response.engines_used}"
    assert elapsed < 6.0, f"basic 模式耗时 {elapsed:.2f}s"


async def test_advanced_search_reads_pages(pipeline) -> None:
    """advanced 模式应真正读到若干网页正文。"""
    response = await pipeline.search(
        SearchRequest(query="MCP protocol specification", max_results=5, depth="advanced", max_pages=5)
    )
    assert response.pages_read >= 1, "未读到任何页面正文"
    assert any(len(result.content) > 200 for result in response.results)


async def test_fetch_specific_url(pipeline) -> None:
    """web_fetch 能读取指定 URL 的正文。"""
    response = await pipeline.extract(ExtractRequest(urls=["https://example.com"], max_chars=2000))
    assert len(response.results) == 1
    assert "example" in response.results[0].raw_content.lower()
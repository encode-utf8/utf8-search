"""HTTP 接口测试：Tavily 兼容的 /search、/extract 与 /health（用桩流水线，离线运行）。

注意：这里刻意不使用 TestClient 的上下文管理器，因为进入 lifespan 会启动 MCP 会话管理器，
而它每个实例只能启动一次（MCP 传输层本身由 test_mcp_* 覆盖）。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from utf8_search.models import ExtractItem, ExtractResponse, SearchResponse, SearchResult
from utf8_search.server import http_api


class StubProvider:
    """占位搜索源，仅用于 /health 检查。"""

    name = "searxng"

    async def health(self) -> bool:
        return True


class StubCache:
    """占位缓存，返回固定条目数。"""

    async def count(self) -> int:
        return 7


class StubPipeline:
    """记录调用参数的假流水线。"""

    def __init__(self) -> None:
        self.providers = [StubProvider()]
        self.cache = StubCache()
        self.last_search = None
        self.last_extract = None

    async def search(self, request) -> SearchResponse:
        self.last_search = request
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    title="示例", url="https://example.com", content="摘要内容", score=0.5, engine="brave"
                )
            ],
            response_time=0.42,
            request_id="req-1",
            depth=request.depth,
        )

    async def extract(self, request) -> ExtractResponse:
        self.last_extract = request
        return ExtractResponse(
            results=[ExtractItem(url=request.urls[0], raw_content="# 正文", chars=4)],
            failed_results=[],
            response_time=0.1,
            request_id="req-2",
        )


def _client(monkeypatch) -> tuple[TestClient, StubPipeline]:
    """构造带桩流水线的测试客户端。"""
    stub = StubPipeline()

    async def fake_get_pipeline(settings=None):
        return stub

    monkeypatch.setattr(http_api, "get_pipeline", fake_get_pipeline)
    return TestClient(http_api.app), stub


def test_search_endpoint_is_tavily_compatible(monkeypatch) -> None:
    """Tavily 风格请求应返回 Tavily 风格响应。"""
    client, stub = _client(monkeypatch)
    response = client.post("/search", json={"query": "GPT-6", "max_results": 1, "search_depth": "advanced"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "GPT-6"
    assert payload["results"][0]["url"] == "https://example.com"
    assert payload["results"][0]["score"] == 0.5
    assert "response_time" in payload and "request_id" in payload
    # 未请求 images / answer 时不应出现在响应里（与 Tavily 默认行为一致）
    assert "images" not in payload and "answer" not in payload
    assert stub.last_search.depth == "advanced"


def test_v1_search_alias_and_optional_fields(monkeypatch) -> None:
    """ /v1/search 别名可用；显式请求时可返回 answer/images 字段。"""
    client, _ = _client(monkeypatch)
    response = client.post(
        "/v1/search",
        json={"query": "缓存", "include_answer": True, "include_images": True, "days": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] is None and payload["images"] == []


def test_days_maps_to_time_range(monkeypatch) -> None:
    """Tavily 的 days 参数应映射到内部 time_range。"""
    client, stub = _client(monkeypatch)
    client.post("/search", json={"query": "新闻", "days": 2})
    assert stub.last_search.time_range == "week"


def test_extract_endpoint(monkeypatch) -> None:
    """抽取接口返回 Tavily 结构。"""
    client, _ = _client(monkeypatch)
    response = client.post("/extract", json={"urls": ["https://example.com"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["raw_content"] == "# 正文"
    assert payload["failed_results"] == []


def test_health_endpoint(monkeypatch) -> None:
    """健康检查应报告 SearXNG 与缓存状态。"""
    client, _ = _client(monkeypatch)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["cache_entries"] == 7
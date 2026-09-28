"""Tavily 兼容性回归（M6）。

对照依据不是记忆，而是归档在 `docs/reports/` 里的官方文档摘录：

- `docs/reports/tavily-official-search-20260928.md`：官方 `/search` 的请求/响应/错误字段清单
  （从官方 OpenAPI schema 逐字提取）＋官方 Python SDK 的错误解析代码；
- `docs/reports/tavily-search-response-example-20260928.json`：官方示例响应（本测试的 fixture）。

覆盖三件事：
1. 官方示例响应能被我们的模型**直接解析**（我们的 schema 是 Tavily 的超集）；
2. 我们的真实响应**包含官方示例里的每一个字段路径**（标准 Tavily 客户端按字段取值不会 KeyError），
   且 REST 与 MCP 两条通道字段集一致；
3. 错误语义：用官方 SDK 的解析写法解析我们的错误体，分类正确、429 带 `Retry-After`、消息可读。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from utf8_search.models import ExtractItem, ExtractResponse, SearchResponse, SearchResult
from utf8_search.server import http_api, mcp_server

EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reports"
    / "tavily-search-response-example-20260928.json"
)


class _StubPipeline:
    """最小桩流水线：返回带 Tavily 兼容字段的响应。"""

    async def search(self, request) -> SearchResponse:
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
            auto_parameters={"topic": request.topic, "search_depth": request.depth},
            usage={"credits": 0} if request.include_usage else None,
        )

    async def extract(self, request) -> ExtractResponse:
        return ExtractResponse(
            results=[ExtractItem(url=request.urls[0], raw_content="# 正文", chars=4)],
            failed_results=[{"url": "https://gone.example", "error": "Failed to retrieve content"}],
            response_time=0.1,
            request_id="req-2",
        )

    def render_metrics(self) -> str:
        return ""


def _official_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _paths(node: object, prefix: str = "") -> list[str]:
    """把示例响应展开成字段路径列表（数组取第 0 个元素做代表）。"""
    paths: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.append(path)
            paths.extend(_paths(value, path))
    elif isinstance(node, list) and node:
        paths.extend(_paths(node[0], f"{prefix}[]"))
    return paths


def _lookup(payload: object, path: str) -> object:
    """按 `a.b[].c` 形式的路径取值（数组取第 0 个元素）；任一步缺失即抛 AssertionError。"""
    node = payload
    for raw in path.split("."):
        part, is_list = raw.replace("[]", ""), raw.endswith("[]")
        assert isinstance(node, dict), f"路径 {path} 在 {part!r} 处不是对象"
        assert part in node, f"缺少字段 {path}"
        node = node[part]
        if is_list:
            assert isinstance(node, list), f"路径 {path} 不是数组"
            if not node:
                # 空数组也算「字段存在」：我们不做图片搜索，results[].images 恒为空，
                # 元素内部结构无从校验（Tavily 在 include_images=false 时同样可能为空）。
                return node
            node = node[0]
    return node


# ---------------------------------------------------------------- 1) fixture 可解析
def test_official_example_parses_into_our_models() -> None:
    """官方示例响应能被我们的模型直接解析 —— 说明我们的 schema 覆盖 Tavily 的响应结构。"""
    official = _official_example()

    parsed = SearchResponse.model_validate(official)

    assert parsed.query == "Who is Leo Messi?"
    assert parsed.request_id == "123e4567-e89b-12d3-a456-426614174111"
    # 官方 schema 里 response_time 是 number，示例里写成字符串 "1.67"：两种都要能吃下
    assert parsed.response_time == pytest.approx(1.67)
    assert parsed.results[0].favicon == "https://britannica.com/favicon.png"
    assert parsed.results[0].images[0].url == "<string>"
    assert parsed.results[0].id == "a3f9c2-04"
    assert parsed.auto_parameters == {"topic": "general", "search_depth": "basic"}
    assert parsed.usage == {"credits": 1}


def test_official_extract_example_shapes() -> None:
    """官方 /extract 的示例结构（results[].images / failed_results[].{url,error}）能被我们表达。"""
    response = ExtractResponse(
        results=[ExtractItem(url="https://example.com/article", raw_content="Example extracted article content.")],
        failed_results=[{"url": "https://example.com/unavailable", "error": "Failed to retrieve content"}],
        response_time=0.5,
        request_id="123e4567-e89b-12d3-a456-426614174111",
    )
    payload = response.model_dump(mode="json")

    assert payload["results"][0]["images"] == []
    assert payload["failed_results"][0] == {
        "url": "https://example.com/unavailable",
        "error": "Failed to retrieve content",
    }


# ---------------------------------------------------------------- 2) 我们的响应覆盖官方字段
def test_rest_response_covers_every_official_field(monkeypatch) -> None:
    """REST 响应必须覆盖官方示例里的每个字段路径（标准客户端按字段取值不会 KeyError）。"""
    async def fake_get_pipeline(settings=None):
        return _StubPipeline()

    monkeypatch.setattr(http_api, "get_pipeline", fake_get_pipeline)
    client = TestClient(http_api.app)
    response = client.post(
        "/v1/search",
        json={"query": "Leo Messi", "include_answer": True, "include_images": True, "include_usage": True},
    )
    payload = response.json()

    assert response.status_code == 200
    for path in _paths(_official_example()):
        _lookup(payload, path)

    # 结果级 Tavily 字段（官方 results[] 的三项）逐个确认
    result = payload["results"][0]
    assert set(("favicon", "images", "id")) <= set(result)
    assert result["images"] == [] and result["favicon"] is None
    # 注：桩流水线不盖章 id（真实 pipeline 会写成 `request_id-序号`，见文件末尾的真实流水线用例）


async def test_mcp_web_search_exposes_the_same_field_set(monkeypatch) -> None:
    """MCP 工具输出与 REST 响应保持同一套字段（含本轮补齐的 Tavily 兼容字段）。"""
    async def fake_get_pipeline(settings=None):
        return _StubPipeline()

    monkeypatch.setattr(mcp_server, "get_pipeline", fake_get_pipeline)
    payload = await mcp_server.web_search(query="Leo Messi", include_usage=True)

    for path in _paths(_official_example()):
        _lookup(payload, path)
    assert set(("favicon", "images", "id")) <= set(payload["results"][0])
    assert payload["usage"] == {"credits": 0}


# ---------------------------------------------------------------- 3) 错误与限流语义
def _sdk_error_branch(body: object, status_code: int) -> tuple[str, str]:
    """复刻官方 SDK `_handle_error_response` 的逻辑，返回 (异常类别, 消息)。"""
    detail = ""
    if isinstance(body, dict):
        try:
            detail = body.get("detail", {}).get("error", None) or ""
        except Exception:
            detail = ""
    if status_code == 429:
        return "UsageLimitExceededError", detail
    if status_code in (403, 432, 433):
        return "ForbiddenError", detail
    if status_code == 401:
        return "InvalidAPIKeyError", detail
    if status_code == 400:
        return "BadRequestError", detail
    return "HTTPError", detail


def _guard_with_keys(keys: set[str], rpm: int = 60):
    from utf8_search.auth import AccessGuard
    from utf8_search.config import Settings

    settings = Settings(api_keys=",".join(sorted(keys)), rate_limit_rpm=rpm)
    return AccessGuard(settings)


def test_error_bodies_are_parseable_by_standard_tavily_client(monkeypatch) -> None:
    """401 用官方 SDK 的写法解析：不抛、分类正确，且消息可读（顶层 `error`）。"""
    guard = _guard_with_keys({"k1"})
    monkeypatch.setattr(http_api, "get_guard", lambda settings=None: guard)
    client = TestClient(http_api.app)

    bad_key = client.post("/v1/search", json={"query": "x"})
    assert bad_key.status_code == 401
    body = bad_key.json()
    # Tavily 的写法吃到字符串 detail 会走 try/except 兜底（消息为空串），但**不崩**；
    # 我们额外给的顶层 `error` 让消息可读。
    category, detail = _sdk_error_branch(body, 401)
    assert category == "InvalidAPIKeyError"
    assert detail == ""
    assert body["error"] and isinstance(body["error"], str)


def test_rate_limit_429_shape_and_retry_after(monkeypatch) -> None:
    """限流 429：Tavily 风格的 `detail.error` 缺失时 SDK 也能分类，我们额外给 `Retry-After`。"""
    guard = _guard_with_keys({"k1"}, rpm=1)
    monkeypatch.setattr(http_api, "get_guard", lambda settings=None: guard)
    client = TestClient(http_api.app)
    headers = {"x-api-key": "k1"}

    assert client.post("/v1/search", json={"query": "x"}, headers=headers).status_code == 200
    limited = client.post("/v1/search", json={"query": "x"}, headers=headers)

    assert limited.status_code == 429
    assert limited.headers.get("Retry-After")
    body = limited.json()
    assert _sdk_error_branch(body, 429)[0] == "UsageLimitExceededError"
    assert body["error"]


def test_validation_error_is_400_bad_request_like_tavily(monkeypatch) -> None:
    """请求体校验失败 → **400 + `BadRequestError`**（对齐 Tavily；FastAPI 默认 422 会走错 SDK 分支）。"""
    async def fake_get_pipeline(settings=None):
        return _StubPipeline()

    monkeypatch.setattr(http_api, "get_pipeline", fake_get_pipeline)
    client = TestClient(http_api.app)
    response = client.post("/v1/search", json={"query": []})

    assert response.status_code == 400
    # body 形态保持既有约定：detail 仍是 FastAPI 风格的错误列表
    assert isinstance(response.json()["detail"], list)
    # 官方 SDK 的分支必须落到 BadRequestError（而不是 422 的 raise_for_status 通用分支）
    category, detail = _sdk_error_branch(response.json(), 400)
    assert category == "BadRequestError"
    # 我们补的顶层 error 给出可读汇总（Tavily 的 detail.error 取法在列表场景同样取不到，只能靠它）
    assert response.json()["error"] and isinstance(response.json()["error"], str)


def test_validation_error_message_summarises_the_first_errors(monkeypatch) -> None:
    """`error` 是可读汇总：至少包含出错字段路径与原因，便于按 Tavily 习惯直接展示。"""
    async def fake_get_pipeline(settings=None):
        return _StubPipeline()

    monkeypatch.setattr(http_api, "get_pipeline", fake_get_pipeline)
    client = TestClient(http_api.app)
    response = client.post("/v1/search", json={"query": "ok", "topic": "sports"})

    assert response.status_code == 400
    message = response.json()["error"]
    assert "topic" in message


# ---------------------------------------------------------------- 4) 真实 pipeline 会盖章
async def test_real_pipeline_stamps_ids_and_auto_parameters(tmp_path) -> None:
    """真实 pipeline 会给结果盖 `request_id-序号` 的 id，并回显 auto_parameters/usage。"""
    import httpx

    from utf8_search.cache.store import CacheStore
    from utf8_search.config import Settings
    from utf8_search.core.pipeline import SearchPipeline
    from utf8_search.models import SearchRequest
    from utf8_search.providers.base import BaseProvider, SearchHit

    class _Provider(BaseProvider):
        name = "searxng"

        async def search(self, query, *, max_results, topic="general", time_range=None, engines=None, language="all", optional_wait=None):
            return [
                SearchHit(title=f"r{i}", url=f"https://s{i}.example/a", snippet="x", engine="brave")
                for i in range(max_results)
            ]

    class _Extractor:
        async def extract(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("basic 模式不应抓页")

    cache = CacheStore(str(tmp_path / "tavily.db"))
    await cache.open()
    pipeline = SearchPipeline(
        Settings(searxng_url="http://searxng-test:8080", api_keys=""),
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[_Provider()],
        extractor=_Extractor(),
    )
    response = await pipeline.search(
        SearchRequest(query="盖章测试", max_results=3, depth="basic", include_usage=True)
    )
    await pipeline.close()

    assert [item.id for item in response.results] == [
        f"{response.request_id}-0",
        f"{response.request_id}-1",
        f"{response.request_id}-2",
    ]
    assert response.auto_parameters == {"topic": "general", "search_depth": "basic"}
    assert response.usage == {"credits": 0}

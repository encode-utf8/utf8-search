"""HTTP 接入层：Tavily 兼容的 REST 接口 + MCP Streamable HTTP（同一端口）。

- POST /search  (等同 /v1/search)  ：Tavily /search 兼容，可直接替换现有客户端
- POST /extract (等同 /v1/extract) ：Tavily /extract 兼容
- GET  /health                     ：健康检查（含 SearXNG 与缓存状态）
- /mcp                             ：MCP Streamable HTTP 端点
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from .. import __version__
from ..auth import get_guard
from ..config import Settings, get_settings
from ..core.runtime import get_pipeline, shutdown_pipeline
from ..models import ExtractRequest, SearchRequest
from .mcp_server import mcp

logger = logging.getLogger(__name__)


def _transport_security(settings: Settings) -> TransportSecuritySettings | None:
    """构造 MCP HTTP 的 Host 白名单；未配置时返回 None（使用 SDK 默认的本机限制）。"""
    hosts = settings.allowed_host_list
    if not hosts:
        return None
    # 始终保留本机访问能力，避免本地调试被 421 拒绝
    hosts = list(dict.fromkeys(hosts + ["127.0.0.1:*", "localhost:*", "[::1]:*"]))
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


settings = get_settings()
# 注意：必须在模块导入期创建，mcp.session_manager 才会存在
mcp_asgi_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=settings.mcp_json_response,
    transport_security=_transport_security(settings),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时预热流水线（消除首次请求的初始化耗时），关闭时释放连接。"""
    await get_pipeline()
    async with mcp.session_manager.run():
        yield
    await shutdown_pipeline()


app = FastAPI(
    title="utf8-search",
    description="面向 LLM 的免费高速联网搜索服务（Tavily 兼容 REST + MCP）",
    version=__version__,
    lifespan=lifespan,
)


# ---------------------------------------------------------------- 请求/响应模型
class TavilySearchBody(BaseModel):
    """Tavily /search 兼容请求体。"""

    model_config = ConfigDict(extra="ignore")

    api_key: str | None = Field(default=None, description="兼容 Tavily 的 body 传 Key 方式")
    query: str = Field(..., min_length=1)
    search_depth: Literal["basic", "advanced", "deep"] = "basic"
    topic: Literal["general", "news"] = "general"
    days: int | None = Field(default=None, ge=1, le=3650, description="兼容 Tavily：最近 N 天")
    time_range: Literal["day", "week", "month", "year"] | None = None
    max_results: int = Field(default=5, ge=1, le=20)
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    include_answer: bool = Field(default=False, description="本服务不自带 LLM，该项恒为空")
    include_raw_content: bool = False
    include_images: bool = False
    engines: list[str] | None = None
    max_pages: int | None = Field(default=None, ge=0, le=60, description="覆盖深度模式抓取页数")

    def to_search_request(self) -> SearchRequest:
        """转换为内部请求模型（含 days -> time_range 的兼容映射）。"""
        time_range = self.time_range
        if time_range is None and self.days is not None:
            if self.days <= 1:
                time_range = "day"
            elif self.days <= 7:
                time_range = "week"
            elif self.days <= 31:
                time_range = "month"
            else:
                time_range = "year"
        return SearchRequest(
            query=self.query,
            max_results=self.max_results,
            depth=self.search_depth,
            topic=self.topic,
            time_range=time_range,
            include_domains=self.include_domains,
            exclude_domains=self.exclude_domains,
            include_raw_content=self.include_raw_content,
            engines=self.engines,
            max_pages=self.max_pages,
        )


class TavilyExtractBody(BaseModel):
    """Tavily /extract 兼容请求体。"""

    model_config = ConfigDict(extra="ignore")

    api_key: str | None = None
    urls: list[str] = Field(..., min_length=1, max_length=10)
    format: Literal["markdown", "text"] = "markdown"
    max_chars: int = Field(default=20000, gt=0, le=200000)


# ---------------------------------------------------------------- 中间件
@app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    """对 /mcp 端点同样施加 Key 校验（stdio 方式不经过这里，属于本机可信通道）。"""
    guard = get_guard()
    if guard.enabled and request.url.path.startswith("/mcp"):
        try:
            await guard.authorize(
                request.headers.get("authorization"),
                request.headers.get("x-api-key"),
            )
        except HTTPException as exc:
            return JSONResponse(
                {"error": exc.detail},
                status_code=exc.status_code,
                headers=getattr(exc, "headers", None) or {},
            )
    return await call_next(request)


async def _authorize(request: Request, body_api_key: str | None = None) -> str:
    """统一鉴权入口，供各端点复用。"""
    guard = get_guard()
    return await guard.authorize(
        request.headers.get("authorization"),
        request.headers.get("x-api-key"),
        body_api_key,
    )


# ---------------------------------------------------------------- 路由
@app.get("/", include_in_schema=False)
async def root() -> dict[str, Any]:
    """服务信息。"""
    return {
        "name": "utf8-search",
        "version": __version__,
        "endpoints": ["/search", "/v1/search", "/extract", "/v1/extract", "/health", "/mcp"],
        "auth_enabled": get_guard().enabled,
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """健康检查：报告 SearXNG 可达性、缓存条目数与引擎健康快照。"""
    pipeline = await get_pipeline()
    searxng_ok = False
    engine_health: dict[str, Any] | None = None
    for provider in pipeline.providers:
        if provider.name == "searxng":
            searxng_ok = await provider.health()
            # 引擎健康快照（M5-5.1）：上游引擎被限流/封锁是常态，把「哪些引擎正在冷却、
            # 什么原因、还有多久解冻」暴露出来，运维才能发现「上游策略变了」而不是只看延迟。
            snapshot = getattr(provider, "engine_health_snapshot", None)
            if callable(snapshot):
                engine_health = snapshot()
            break
    payload: dict[str, Any] = {
        "status": "ok" if searxng_ok else "degraded",
        "version": __version__,
        "searxng": "ok" if searxng_ok else "unreachable",
        "cache_entries": await pipeline.cache.count(),
        "auth_enabled": get_guard().enabled,
    }
    if engine_health is not None:
        payload["engines"] = engine_health
    return payload


@app.post("/search")
@app.post("/v1/search")
async def search_endpoint(body: TavilySearchBody, request: Request) -> dict[str, Any]:
    """联网搜索（Tavily 兼容）。"""
    await _authorize(request, body.api_key)
    pipeline = await get_pipeline()
    response = await pipeline.search(body.to_search_request())
    payload = response.model_dump(mode="json")
    if not body.include_images:
        payload.pop("images", None)
    if not body.include_answer:
        payload.pop("answer", None)
    return payload


@app.post("/extract")
@app.post("/v1/extract")
async def extract_endpoint(body: TavilyExtractBody, request: Request) -> dict[str, Any]:
    """网页正文抽取（Tavily 兼容）。"""
    await _authorize(request, body.api_key)
    pipeline = await get_pipeline()
    response = await pipeline.extract(
        ExtractRequest(urls=body.urls, format=body.format, max_chars=body.max_chars)
    )
    return response.model_dump(mode="json")


# MCP Streamable HTTP 端点挂载在最后：前面已注册的路由优先匹配
app.mount("/", mcp_asgi_app)
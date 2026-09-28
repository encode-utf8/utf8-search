"""对外数据模型：MCP 工具返回、REST 响应（含 Tavily 兼容字段）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Depth = Literal["basic", "advanced", "deep"]
Topic = Literal["general", "news"]
TimeRange = Literal["day", "week", "month", "year"]


class SearchRequest(BaseModel):
    """一次搜索请求的规范化参数。"""

    query: str = Field(..., min_length=1, description="查询词")
    max_results: int = Field(default=5, ge=1, le=20, description="返回结果条数")
    depth: Depth = Field(default="basic", description="basic 只搜索；advanced/deep 额外抓取正文")
    topic: Topic = Field(default="general", description="general 通用；news 新闻（时效性优先）")
    time_range: TimeRange | None = Field(default=None, description="时间范围过滤")
    include_domains: list[str] | None = Field(default=None, description="仅保留这些域名")
    exclude_domains: list[str] | None = Field(default=None, description="排除这些域名")
    include_raw_content: bool = Field(default=False, description="是否附带完整正文")
    include_usage: bool = Field(
        default=False,
        description="Tavily 兼容：为 true 时在响应里附带 usage（本服务免费，credits 恒 0）",
    )
    engines: list[str] | None = Field(default=None, description="指定搜索引擎（调试用）")
    max_pages: int | None = Field(default=None, ge=0, le=60, description="覆盖深度模式的抓取页数")


class ResultImage(BaseModel):
    """结果内嵌图片（Tavily 兼容：`results[].images[] = {url, description}`）。"""

    url: str = ""
    description: str | None = None


class SearchResult(BaseModel):
    """单条搜索结果。"""

    title: str = ""
    url: str = ""
    content: str = Field(default="", description="给 LLM 阅读的摘要或正文片段")
    raw_content: str | None = Field(default=None, description="完整正文（可选）")
    score: float = 0.0
    engine: str = ""
    published_date: str | None = None
    # ---- Tavily 兼容字段（M6）：官方 results[] 还含这三项；我们只做加法，不改既有字段语义 ----
    favicon: str | None = Field(
        default=None, description="Tavily 兼容：结果站点图标。本服务不采集 favicon，恒为 null"
    )
    images: list[ResultImage] = Field(
        default_factory=list, description="Tavily 兼容：结果内嵌图片。本服务不做图片搜索，恒为空数组"
    )
    id: str = Field(default="", description="Tavily 兼容：结果唯一 id（= request_id-序号）")


class SearchResponse(BaseModel):
    """搜索响应（字段名与 Tavily 对齐，便于直接替换）。"""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    response_time: float = 0.0
    request_id: str = ""
    cached: bool = False
    depth: Depth = "basic"
    pages_read: int = Field(default=0, description="深度模式下实际读到的页面数")
    engines_used: list[str] = Field(default_factory=list)
    failed_engines: list[str] = Field(default_factory=list)
    # 上游过载降级标记（M5 并发保护）：为 true 时结果可能不完整（例如 news 的第二路上游被闸门拒绝），
    # 但仍有可用结果，因此按 200 返回并带上该标记，而不是 429。
    degraded: bool = Field(default=False, description="上游过载导致的降级返回（结果可能不完整）")
    degraded_reason: str | None = Field(default=None, description="降级原因，如 upstream_overloaded")

    # ---- Tavily 兼容字段（本服务不自带 LLM，恒为空）----
    answer: str | None = None
    follow_up_questions: list[str] | None = None
    images: list[str] = Field(default_factory=list)
    # ---- Tavily 兼容字段（M6 补齐）----
    auto_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Tavily 兼容：实际生效的关键参数（我们不做自动推断，这里回显 topic/search_depth）",
    )
    usage: dict[str, Any] | None = Field(
        default=None, description="Tavily 兼容：仅 include_usage=true 时给出；本服务免费，credits 恒 0"
    )


class ExtractRequest(BaseModel):
    """正文抽取请求。"""

    urls: list[str] = Field(..., min_length=1, max_length=10)
    format: Literal["markdown", "text"] = "markdown"
    max_chars: int = Field(default=20000, gt=0, le=200000)


class ExtractItem(BaseModel):
    """单页抽取结果。"""

    url: str
    raw_content: str
    title: str | None = None
    chars: int = 0
    # Tavily 兼容（M6）：官方 /extract 的 results[] 含 images
    images: list[ResultImage] = Field(
        default_factory=list, description="Tavily 兼容：本服务不做图片提取，恒为空数组"
    )


class ExtractResponse(BaseModel):
    """抽取响应（Tavily /extract 兼容）。"""

    results: list[ExtractItem] = Field(default_factory=list)
    failed_results: list[dict[str, Any]] = Field(default_factory=list)
    response_time: float = 0.0
    request_id: str = ""
    cached: bool = False

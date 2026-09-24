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
    engines: list[str] | None = Field(default=None, description="指定搜索引擎（调试用）")
    max_pages: int | None = Field(default=None, ge=0, le=60, description="覆盖深度模式的抓取页数")


class SearchResult(BaseModel):
    """单条搜索结果。"""

    title: str = ""
    url: str = ""
    content: str = Field(default="", description="给 LLM 阅读的摘要或正文片段")
    raw_content: str | None = Field(default=None, description="完整正文（可选）")
    score: float = 0.0
    engine: str = ""
    published_date: str | None = None


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

    # ---- Tavily 兼容字段（本服务不自带 LLM，恒为空）----
    answer: str | None = None
    follow_up_questions: list[str] | None = None
    images: list[str] = Field(default_factory=list)


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


class ExtractResponse(BaseModel):
    """抽取响应（Tavily /extract 兼容）。"""

    results: list[ExtractItem] = Field(default_factory=list)
    failed_results: list[dict[str, Any]] = Field(default_factory=list)
    response_time: float = 0.0
    request_id: str = ""
    cached: bool = False
"""MCP 服务：暴露 web_search / web_fetch 两个工具，供 Claude Desktop、Codex、Cursor 等客户端调用。"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from pydantic import Field

from .. import __version__
from ..core.runtime import get_pipeline
from ..models import ExtractRequest, SearchRequest

logger = logging.getLogger(__name__)

mcp = MCPServer(
    "utf8-search",
    title="utf8-search 联网搜索",
    version=__version__,
    instructions=(
        "面向 LLM 的免费联网搜索服务。"
        "需要实时信息（新闻、价格、最新文档、版本号）时调用 web_search；"
        "已知具体网址需要读正文时调用 web_fetch。"
        "search_depth=basic 最快（只返回搜索摘要）；advanced 会读若干网页正文；"
        "deep 会读取数十个网页正文，适合需要综合多来源的任务。"
    ),
)


@mcp.tool()
async def web_search(
    query: Annotated[str, Field(description="搜索关键词，尽量具体；中文、英文均可")],
    max_results: Annotated[int, Field(description="返回结果条数，1-20", ge=1, le=20)] = 5,
    search_depth: Annotated[
        Literal["basic", "advanced", "deep"],
        Field(description="basic=仅搜索(最快)；advanced=抓取少量网页正文；deep=读取数十个网页，适合综述型任务"),
    ] = "basic",
    topic: Annotated[Literal["general", "news"], Field(description="general=通用；news=新闻（时效性优先）")] = "general",
    time_range: Annotated[
        Literal["day", "week", "month", "year"] | None,
        Field(description="只返回该时间范围内的结果"),
    ] = None,
    include_domains: Annotated[list[str] | None, Field(description="仅保留这些域名，如 ['gov.cn']")] = None,
    exclude_domains: Annotated[list[str] | None, Field(description="排除这些域名")] = None,
    include_raw_content: Annotated[bool, Field(description="是否额外返回完整正文（token 消耗更大）")] = False,
) -> dict[str, Any]:
    """联网搜索：返回带标题、URL、摘要（深度模式附带正文）的结果列表，可直接作为引用来源。"""
    pipeline = await get_pipeline()
    request = SearchRequest(
        query=query,
        max_results=max_results,
        depth=search_depth,
        topic=topic,
        time_range=time_range,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        include_raw_content=include_raw_content,
    )
    response = await pipeline.search(request)
    return response.model_dump(mode="json")


@mcp.tool()
async def web_fetch(
    urls: Annotated[list[str], Field(description="待读取的网页地址列表（最多 10 条）", max_length=10)],
    format: Annotated[Literal["markdown", "text"], Field(description="输出格式")] = "markdown",
    max_chars: Annotated[int, Field(description="单页返回的最大字符数", ge=100, le=200000)] = 20000,
) -> dict[str, Any]:
    """读取指定网页的正文内容（已去除导航广告等噪声），返回 Markdown 或纯文本。"""
    pipeline = await get_pipeline()
    request = ExtractRequest(urls=urls, format=format, max_chars=max_chars)
    response = await pipeline.extract(request)
    return response.model_dump(mode="json")
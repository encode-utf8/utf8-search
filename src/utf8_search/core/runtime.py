"""运行时单例：MCP 工具与 REST 接口共享同一套流水线实例。"""

from __future__ import annotations

import asyncio
import logging

from ..config import Settings, get_settings
from .pipeline import SearchPipeline

logger = logging.getLogger(__name__)

_pipeline: SearchPipeline | None = None
_lock = asyncio.Lock()


async def get_pipeline(settings: Settings | None = None) -> SearchPipeline:
    """获取（懒加载）全局流水线实例。"""
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    async with _lock:
        if _pipeline is None:
            resolved = settings or get_settings()
            logger.info("初始化搜索流水线：SearXNG=%s", resolved.searxng_url)
            _pipeline = await SearchPipeline.create(resolved)
    return _pipeline


async def shutdown_pipeline() -> None:
    """关闭全局流水线并释放连接。"""
    global _pipeline
    if _pipeline is not None:
        await _pipeline.close()
        _pipeline = None
        logger.info("搜索流水线已关闭")
"""Jina Reader Provider：免费的网页转 Markdown 兜底通道（r.jina.ai）。"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class JinaReader:
    """当本地抽取失败时，用 r.jina.ai 获取正文 Markdown。"""

    def __init__(self, client: httpx.AsyncClient, *, prefix: str = "https://r.jina.ai/") -> None:
        self.client = client
        self.prefix = prefix

    async def fetch(self, url: str) -> str | None:
        """返回 Markdown 正文，失败返回 None。"""
        try:
            response = await self.client.get(f"{self.prefix}{url}")
            response.raise_for_status()
            text = response.text
        except Exception as exc:
            logger.debug("Jina Reader 兜底失败 url=%s: %s", url, exc)
            return None
        # 去掉 Jina 的元信息头，只保留正文部分
        marker = "Markdown Content:"
        if marker in text:
            text = text.split(marker, 1)[1]
        text = text.strip()
        return text or None
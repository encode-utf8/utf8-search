"""Bing HTML Provider：SearXNG 不可用时的兜底搜索源（实测 700ms 级、可解析）。

注意：这是对公开搜索结果页的解析，仅作为降级方案，调用频率由上层并发与缓存控制。
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import httpx
from lxml import html as lxml_html

from .base import BaseProvider, SearchHit

logger = logging.getLogger(__name__)


class BingHtmlProvider(BaseProvider):
    """解析 Bing 搜索结果页（b_algo 结果块）。"""

    name = "bing"

    def __init__(self, client: httpx.AsyncClient, *, endpoint: str = "https://www.bing.com/search") -> None:
        self.client = client
        self.endpoint = endpoint

    async def search(
        self,
        query: str,
        *,
        max_results: int,
        topic: str = "general",
        time_range: str | None = None,
        engines: list[str] | None = None,
        language: str = "all",
    ) -> list[SearchHit]:
        """抓取并解析 Bing 结果页。"""
        params = {"q": query, "count": str(max(max_results, 10))}
        if language and language.lower().startswith("zh"):
            params["setlang"] = "zh-hans"
            params["mkt"] = "zh-CN"
        else:
            params["setlang"] = "en"
        # Bing 的时间过滤通过 qft 参数表达
        if time_range == "day":
            params["filters"] = 'ex1:"ez1"'
        elif time_range == "week":
            params["filters"] = 'ex1:"ez2"'
        elif time_range == "month":
            params["filters"] = 'ex1:"ez3"'

        response = await self.client.get(self.endpoint, params=params)
        response.raise_for_status()
        return self.parse(response.text, max_results=max_results)

    @staticmethod
    def parse(page_html: str, *, max_results: int = 10) -> list[SearchHit]:
        """从 HTML 中解析结果；独立成静态方法便于离线单测。"""
        document = lxml_html.fromstring(page_html)
        hits: list[SearchHit] = []
        for node in document.xpath("//li[contains(@class, 'b_algo')]"):
            link_nodes = node.xpath(".//h2//a[@href]")
            if not link_nodes:
                continue
            link = link_nodes[0]
            url = (link.get("href") or "").strip()
            if not url or url.startswith("/"):
                continue
            title = " ".join(link.itertext()).strip()
            snippet_nodes = node.xpath(".//p//text()") or node.xpath(".//div[contains(@class,'b_caption')]//text()")
            snippet = " ".join(t.strip() for t in snippet_nodes if t.strip())
            hits.append(
                SearchHit(
                    title=title,
                    url=_unwrap_bing_redirect(url),
                    snippet=snippet,
                    engine="bing",
                )
            )
            if len(hits) >= max_results:
                break
        return hits


def _unwrap_bing_redirect(url: str) -> str:
    """解析 Bing 的跳转链接（/ck/a?...&u=a1aHR0c...）为真实地址。"""
    if "bing.com/ck/a" not in url:
        return url
    try:
        query = parse_qs(urlparse(url).query)
        raw = (query.get("u") or [""])[0]
        if raw.startswith("a1"):
            import base64

            padding = "=" * (-len(raw[2:]) % 4)
            decoded = base64.urlsafe_b64decode(raw[2:] + padding).decode("utf-8", "ignore")
            if decoded.startswith("http"):
                return decoded
    except Exception as exc:  # 解码失败时退回原始链接即可
        logger.debug("Bing 跳转链接解码失败: %s", exc)
    return url
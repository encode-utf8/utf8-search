"""网页抓取与正文抽取。

设计要点（均为实测结论驱动）：
1. 流式读取并限制单页字节数，避免大页面拖慢整体延迟；
2. 以 bytes 交给 trafilatura，让它自行探测编码（对 GBK 中文站点更稳）；
3. httpx 的超时是「每次读超时」，对慢速站点几乎无效，因此下载用 wait_for 做整段硬超时；
4. 正文解析是 CPU 密集型，放进独立线程池（默认 32 线程），避免拖住整体吞吐；
5. 抽取为空或抓取失败时，按配置回退到 Jina Reader（仅 deep 模式默认启用）。
"""

from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import trafilatura

from ..cache.store import CacheStore
from ..config import Settings
from ..models import ExtractItem
from ..providers.jina_reader import JinaReader
from ..rank.fusion import normalize_url, tokenize

logger = logging.getLogger(__name__)

# 单页最大下载字节数（超出即截断，防止大页面拖慢请求与解析）
MAX_HTML_BYTES = 500_000
# 视为可抽取文本的 Content-Type
HTML_TYPES = ("text/html", "application/xhtml", "text/plain", "text/xml", "application/xml")


class PageExtractor:
    """负责「URL -> 正文」的抓取与抽取。"""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: CacheStore,
        jina: JinaReader | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.cache = cache
        self.jina = jina
        # 正文解析线程池：CPU 密集，独立于事件循环，容量可配（默认 32）
        self._executor = ThreadPoolExecutor(
            max_workers=max(4, settings.extract_workers), thread_name_prefix="utf8-extract"
        )

    async def extract(
        self,
        url: str,
        *,
        fmt: str = "markdown",
        max_chars: int | None = None,
        query: str = "",
        use_cache: bool = True,
        allow_jina: bool = True,
        download_timeout: float | None = None,
        need_title: bool = True,
    ) -> ExtractItem | None:
        """抓取并抽取单个 URL；失败返回 None。"""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return None
        limit = max_chars or self.settings.raw_content_max_chars
        cache_key = f"page:{fmt}:{normalize_url(url)}"

        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                text = self._shape(cached.get("text", ""), query, limit)
                return ExtractItem(url=url, raw_content=text, title=cached.get("title"), chars=len(text))

        text: str | None = None
        title: str | None = None

        # 1) 本地抓取（硬超时）+ trafilatura 抽取
        # 下载上限：优先用调用方传入的（deep 模式会放宽），否则取配置的较小值
        download_cap = download_timeout or min(self.settings.fetch_timeout, self.settings.page_total_timeout)
        try:
            html_bytes = await asyncio.wait_for(self._download(url, download_cap), timeout=download_cap)
        except (asyncio.TimeoutError, TimeoutError):
            logger.debug("下载超时（%.1fs）: %s", download_cap, url)
            html_bytes = None

        if html_bytes:
            loop = asyncio.get_running_loop()
            text, title = await loop.run_in_executor(
                self._executor, self._extract_from_bytes, html_bytes, fmt, need_title
            )

        # 2) 兜底：Jina Reader（免费、免密钥），仅在允许的深度模式下启用
        if not text and allow_jina and self.settings.enable_jina_fallback and self.jina is not None:
            try:
                text = await asyncio.wait_for(self.jina.fetch(url), timeout=self.settings.jina_timeout)
            except (asyncio.TimeoutError, TimeoutError):
                logger.debug("Jina Reader 兜底超时: %s", url)
                text = None
            if text:
                logger.debug("使用 Jina Reader 兜底成功: %s", url)

        if not text:
            logger.debug("正文抽取失败: %s", url)
            return None

        if use_cache:
            await self.cache.set(
                cache_key,
                {"url": url, "title": title, "text": text},
                self.settings.cache_page_ttl,
            )

        shaped = self._shape(text, query, limit)
        return ExtractItem(url=url, raw_content=shaped, title=title, chars=len(shaped))

    async def _download(self, url: str, timeout: float | None = None) -> bytes | None:
        """流式下载页面，超过字节上限即停止。"""
        try:
            async with self.client.stream(
                "GET", url, timeout=timeout or self.settings.fetch_timeout
            ) as response:
                if response.status_code >= 400:
                    return None
                content_type = (response.headers.get("content-type") or "").lower()
                if content_type and not any(t in content_type for t in HTML_TYPES):
                    return None
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size >= MAX_HTML_BYTES:
                        break
                return b"".join(chunks) if chunks else None
        except Exception as exc:
            logger.debug("下载失败 url=%s: %s", url, exc)
            return None

    @staticmethod
    def _extract_from_bytes(
        html_bytes: bytes, fmt: str, need_title: bool = True
    ) -> tuple[str | None, str | None]:
        """用 trafilatura 抽取正文（在线程池中执行）。

        favor_precision=True 比 favor_recall 更快、噪声更少，实测中文站点抽取质量同样可用。
        """
        output_format = "markdown" if fmt == "markdown" else "txt"
        try:
            # 先按高精度抽取（快、噪声少）
            text = trafilatura.extract(
                html_bytes,
                output_format=output_format,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
            )
            if not text:
                # 失败再按高召回重试一次：部分「正文被算法低估」的页面能被救回来
                text = trafilatura.extract(
                    html_bytes,
                    output_format=output_format,
                    include_comments=False,
                    include_tables=True,
                    favor_recall=True,
                )
        except Exception as exc:
            logger.debug("trafilatura 抽取异常: %s", exc)
            return None, None
        if not text:
            return None, None
        # extract_metadata 是又一次完整解析（成本与正文抽取相当），只有当调用方
        # 确实需要标题时才执行：搜索结果本身已带标题，deep/advanced 抓取无需重复解析。
        title = None
        if need_title:
            try:
                meta = trafilatura.extract_metadata(html_bytes)
                title = getattr(meta, "title", None) if meta else None
            except Exception:
                title = None
        return text.strip(), title

    def _shape(self, text: str, query: str, limit: int) -> str:
        """按查询相关性压缩正文，并做长度裁剪。"""
        if len(text) <= limit:
            return text
        return condense_text(text, query, limit)


def condense_text(text: str, query: str, max_chars: int) -> str:
    """从长文中挑选与查询最相关的句子，拼接到不超过 max_chars 的片段。

    思路：按句切分 -> 句子与查询词重叠度打分 -> 取分数最高的句子 -> 按原文顺序还原，
    保证语义连贯且信息密度高（LLM 读起来更省 token）。
    """
    query_terms = set(tokenize(query))
    sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;\n])", text) if len(s.strip()) >= 8]
    if not sentences:
        return text[:max_chars]

    scored: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        tokens = tokenize(sentence)
        if query_terms:
            overlap = len(query_terms & set(tokens))
            density = overlap / (len(tokens) ** 0.5 + 1)
        else:
            density = 0.0
        # 位置加权：开头段落通常更概括
        position_bonus = 0.15 if index < 3 else 0.0
        scored.append((density + position_bonus, index, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)
    picked: list[tuple[int, str]] = []
    total = 0
    for _, index, sentence in scored:
        if total + len(sentence) > max_chars and picked:
            continue
        picked.append((index, sentence))
        total += len(sentence)
        if total >= max_chars:
            break
    picked.sort(key=lambda item: item[0])
    return "".join(sentence for _, sentence in picked)[:max_chars]
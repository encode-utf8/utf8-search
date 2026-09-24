"""SearXNG Provider：主力搜索源（聚合 Mojeek / Google CSE / Startpage / Presearch / Yahoo 等引擎）。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .base import BaseProvider, SearchHit

logger = logging.getLogger(__name__)

# 视为「瞬时故障」、值得重试一次的状态码
RETRYABLE_STATUS = (502, 503, 504)


class SearxngProvider(BaseProvider):
    """通过 SearXNG 的 JSON 接口进行聚合搜索。"""

    name = "searxng"

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient,
        *,
        default_engines: list[str] | None = None,
        timeout_limit: float | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client
        self.default_engines = default_engines or []
        # 聚合搜索时间上限（SearXNG 的 timeout_limit 参数）：到点即返回已有结果，
        # 避免个别慢引擎拖垮整体延迟。
        self.timeout_limit = timeout_limit
        self.unresponsive_engines: list[str] = []

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
        """调用 /search?format=json，返回归一化后的结果。"""
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "language": language or "all",
            "categories": "news" if topic == "news" else "general",
            "pageno": 1,
        }
        if time_range:
            params["time_range"] = time_range
        if self.timeout_limit:
            params["timeout_limit"] = self.timeout_limit
        engine_names = engines if engines else self.default_engines
        if engine_names:
            params["engines"] = ",".join(engine_names)

        payload = await self._request(params)

        # 记录不可用引擎，供上层判断是否需要降级到兜底源
        self.unresponsive_engines = [
            str(item[0]) if isinstance(item, (list, tuple)) and item else str(item)
            for item in (payload.get("unresponsive_engines") or [])
        ]
        if self.unresponsive_engines:
            logger.debug("SearXNG 不可用引擎: %s", ", ".join(self.unresponsive_engines))

        hits: list[SearchHit] = []
        for item in payload.get("results") or []:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            hits.append(
                SearchHit(
                    title=(item.get("title") or "").strip(),
                    url=url,
                    snippet=(item.get("content") or "").strip(),
                    engine=(item.get("engine") or "searxng").strip(),
                    published_date=item.get("publishedDate") or item.get("published_date"),
                    raw_score=float(item.get("score") or 0.0),
                )
            )
            if len(hits) >= max_results:
                break
        return hits

    @property
    def request_timeout(self) -> float:
        """搜索请求的 HTTP 超时：比聚合上限略宽，留给网络与序列化开销。"""
        return (self.timeout_limit or 6.0) + 3.0

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """请求 SearXNG，并对瞬时错误重试一次。

        SearXNG 在引擎超时后可能重启 worker，短暂返回 502/503/504；
        重试时会去掉 engines 定制，改用它的默认引擎集合，提高成功率。
        """
        last_error: Exception | None = None
        for attempt in range(2):
            current = dict(params)
            if attempt == 1:
                current.pop("engines", None)
            try:
                response = await self.client.get(
                    f"{self.base_url}/search", params=current, timeout=self.request_timeout
                )
                if response.status_code in RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(
                        f"SearXNG 瞬时错误 {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status not in RETRYABLE_STATUS:
                    raise
                if attempt == 0:
                    logger.warning("SearXNG 返回 %s，0.4s 后重试一次", status)
                    await asyncio.sleep(0.4)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning("SearXNG 连接异常，0.4s 后重试一次: %s", exc)
                    await asyncio.sleep(0.4)
        raise last_error if last_error is not None else RuntimeError("SearXNG 请求失败")

    async def health(self) -> bool:
        """通过 /healthz 判断 SearXNG 是否可用。"""
        try:
            response = await self.client.get(f"{self.base_url}/healthz", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False
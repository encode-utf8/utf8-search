"""全链路编排：查询规划 -> 多源搜索 -> 融合去重 -> 并发抓取 -> 正文压缩 -> 结果打包。

延迟控制是这里的核心目标，关键手段：
1. 多源并发（SearXNG 主力 + Bing 兜底），不串行等待；
2. 页面抓取使用「总预算 + 单页硬超时」，超过预算即返回已就绪的部分；
3. 命中缓存直接返回（查询缓存 + 页面缓存 + 结果包缓存三级）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Any

import httpx

from ..cache.store import CacheStore
from ..config import Settings
from ..extract.extractor import PageExtractor
from ..models import (
    ExtractItem,
    ExtractRequest,
    ExtractResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from ..providers.base import BaseProvider, SearchHit
from ..providers.bing_html import BingHtmlProvider
from ..providers.jina_reader import JinaReader
from ..providers.searxng import SearxngProvider
from ..rank.fusion import filter_domains, fuse, rerank

logger = logging.getLogger(__name__)

# 各深度模式默认抓取的页面数
DEPTH_PAGE_DEFAULTS = {"basic": 0, "advanced": 8, "deep": 30}


def build_http_mounts(hosts: list[str]) -> dict[str, Any] | None:
    """为指定主机名构造「直连、绕过代理」的 httpx transport 映射。

    背景：Windows 系统代理（本地 Clash/V2Ray 等）会让 httpx 把回环请求也走代理，
    表现为访问 http://127.0.0.1:8888 时收到 502；用 mounts 显式把这些主机指向默认
    transport（None）即可绕过，而对外网请求仍然正常使用代理。
    """
    if not hosts:
        return None
    return {f"all://{host}": None for host in hosts}

def _group_hits(hits: list[SearchHit]) -> list[list[SearchHit]]:
    """按来源引擎分组，供 RRF 融合使用（同源结果保持原有顺序即排名）。"""
    groups: dict[str, list[SearchHit]] = {}
    for hit in hits:
        groups.setdefault(hit.engine or "unknown", []).append(hit)
    return list(groups.values())


class SearchPipeline:
    """搜索与抽取的统一入口，被 MCP 工具与 REST 接口共用。"""

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient,
        cache: CacheStore,
        providers: list[BaseProvider],
        extractor: PageExtractor,
    ) -> None:
        self.settings = settings
        self.client = client
        self.cache = cache
        self.providers = providers
        self.extractor = extractor
        self._semaphore = asyncio.Semaphore(settings.max_fetch_concurrency)

    # ------------------------------------------------------------------ 构建
    @classmethod
    async def create(cls, settings: Settings) -> "SearchPipeline":
        """按配置组装全部依赖。"""
        limits = httpx.Limits(
            max_connections=max(32, settings.max_fetch_concurrency * 2),
            max_keepalive_connections=max(16, settings.max_fetch_concurrency),
        )
        # 关键：本机 SearXNG 必须绕过系统代理，否则 httpx 会把回环请求也发给代理并收到 502
        # （curl / urllib 默认绕过 localhost，httpx 不会，这是本项目在 Windows 上的实测坑）
        mounts = build_http_mounts(settings.bypass_proxy_host_list)
        if mounts:
            logger.debug("以下主机将绕过系统代理直连: %s", ", ".join(settings.bypass_proxy_host_list))
        client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(settings.request_timeout, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": settings.user_agent,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            proxy=settings.http_proxy or None,
            mounts=mounts,
            trust_env=settings.trust_env,
        )
        cache = CacheStore(
            settings.cache_path,
            enabled=settings.cache_enabled,
            memory_size=settings.cache_memory_size,
        )
        await cache.open()

        providers: list[BaseProvider] = [
            SearxngProvider(
                settings.searxng_url,
                client,
                default_engines=settings.engine_list,
                timeout_limit=settings.search_timeout_limit,
            ),
            BingHtmlProvider(client),
        ]
        jina = JinaReader(client, prefix=settings.jina_prefix) if settings.enable_jina_fallback else None
        extractor = PageExtractor(settings, client, cache, jina=jina)
        return cls(settings, client=client, cache=cache, providers=providers, extractor=extractor)

    async def close(self) -> None:
        """释放资源。"""
        await self.client.aclose()
        await self.cache.close()

    # ------------------------------------------------------------------ 搜索
    async def search(self, request: SearchRequest) -> SearchResponse:
        """执行一次完整搜索。"""
        started = time.perf_counter()
        request_id = uuid.uuid4().hex[:16]
        result_key = self._result_cache_key(request)

        cached_payload = await self.cache.get(result_key)
        if cached_payload:
            response = SearchResponse.model_validate(cached_payload)
            response.cached = True
            response.request_id = request_id
            response.response_time = round(time.perf_counter() - started, 3)
            return response

        # 1) 取原始结果（多源并发 + 兜底）
        hits, engines_used, failed_engines = await self._collect_hits(request)

        # 2) 融合、去重、重排、过滤
        merged = fuse(_group_hits(hits)) if hits else []
        merged = filter_domains(
            merged,
            include_domains=request.include_domains,
            exclude_domains=request.exclude_domains,
        )
        merged = rerank(merged, request.query)

        # 3) 深度模式：并发抓取正文（受总预算约束）
        pages_read = 0
        if request.depth in ("advanced", "deep"):
            merged, pages_read = await self._enrich_with_content(request, merged)

        results = merged[: request.max_results]
        response = SearchResponse(
            query=request.query,
            results=results,
            response_time=round(time.perf_counter() - started, 3),
            request_id=request_id,
            cached=False,
            depth=request.depth,
            pages_read=pages_read,
            engines_used=engines_used,
            failed_engines=failed_engines,
        )
        await self.cache.set(result_key, response.model_dump(mode="json"), self.settings.cache_result_ttl)
        return response

    async def _collect_hits(self, request: SearchRequest) -> tuple[list[SearchHit], list[str], list[str]]:
        """从各 Provider 收集原始结果，主源不足时自动兜底。"""
        pages_cap = self._page_budget(request)
        want = max(request.max_results, pages_cap)
        query_key = self._query_cache_key(request, want)

        cached_hits = await self.cache.get(query_key)
        if cached_hits is not None:
            return [SearchHit(**item) for item in cached_hits], ["cache"], []

        engines_used: list[str] = []
        failed_engines: list[str] = []
        hits: list[SearchHit] = []

        # 主源：SearXNG；仅在「结果拿不满用户需要的条数」或主源失败时才启用兜底源，
        # 避免深度模式下为了凑够抓取页数而白白多打一次外部请求。
        for index, provider in enumerate(self.providers):
            if index > 0 and len(hits) >= request.max_results:
                break
            try:
                provider_hits = await provider.search(
                    request.query,
                    max_results=want,
                    topic=request.topic,
                    time_range=request.time_range,
                    engines=request.engines,
                    language=self.settings.language,
                )
            except Exception as exc:
                logger.warning("Provider %s 搜索失败: %s", provider.name, exc)
                failed_engines.append(provider.name)
                continue

            if provider.name == "searxng":
                unresponsive = getattr(provider, "unresponsive_engines", [])
                failed_engines.extend(unresponsive)

            if provider_hits:
                hits.extend(provider_hits)
                engines_used.append(provider.name)
                # 结果已够用则立即返回，不再触发兜底源（S1/S4：能快就快）
                if len(hits) >= want:
                    break
                if len(hits) >= request.max_results and index == 0:
                    break

        if hits:
            await self.cache.set(query_key, [h.to_dict() for h in hits], self.settings.cache_query_ttl)
        return hits, engines_used, failed_engines

    async def _enrich_with_content(
        self, request: SearchRequest, results: list[SearchResult]
    ) -> tuple[list[SearchResult], int]:
        """为结果并发抓取正文（deep/advanced 模式）。

        返回时机取三者中最先到者：
          1. 已成功读到「够用」的页面数（fetch_early_stop_ratio，最少 fetch_min_pages）；
          2. 所有目标页面都已处理完；
          3. 达到总时间预算（fetch_total_budget）。
        这样既保证信息量（对标「快速阅读几十个网页」），又不会被个别慢站点拖住。
        """
        pages_cap = self._page_budget(request)
        if pages_cap <= 0:
            return results, 0
        targets = results[:pages_cap]
        if not targets:
            return results, 0

        ratio = self._early_stop_ratio(request)
        needed = min(
            len(targets),
            max(self.settings.fetch_min_pages, int(len(targets) * ratio)),
        )

        # advanced 走纯本地抓取（更快）；deep 才允许 Jina 兜底（更全）
        allow_jina = request.depth in self.settings.jina_depth_list
        page_timeout = (
            self.settings.deep_page_timeout if request.depth == "deep" else self.settings.page_total_timeout
        )

        async def fetch_one(result: SearchResult) -> tuple[SearchResult, ExtractItem | None]:
            async with self._semaphore:
                try:
                    # 单页总时长硬上限：即使下载被取消后解析仍卡住，也能按时归还
                    item = await asyncio.wait_for(
                        self.extractor.extract(
                            result.url,
                            fmt="markdown",
                            max_chars=self.settings.page_max_chars,
                            query=request.query,
                            allow_jina=allow_jina,
                            download_timeout=(
                                self.settings.deep_download_timeout
                                if request.depth == "deep"
                                else None
                            ),
                            need_title=False,
                        ),
                        timeout=page_timeout,
                    )
                except (asyncio.TimeoutError, TimeoutError):
                    logger.debug("单页超时（%.1fs）: %s", page_timeout, result.url)
                    item = None
            return result, item

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._time_budget(request)
        tasks = [asyncio.create_task(fetch_one(result)) for result in targets]
        pending: set[asyncio.Task[Any]] = set(tasks)
        finished: list[tuple[SearchResult, ExtractItem | None]] = []
        success = 0

        while pending:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            done, pending = await asyncio.wait(
                pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED
            )
            if not done:
                break
            for task in done:
                try:
                    result, item = task.result()
                except Exception as exc:
                    logger.debug("抓取任务失败: %s", exc)
                    continue
                finished.append((result, item))
                if item is not None and item.raw_content:
                    success += 1
            if success >= needed:
                break

        for task in pending:
            task.cancel()

        pages_read = 0
        matched = set()
        for result, item in finished:
            if item is None or not item.raw_content:
                continue
            pages_read += 1
            matched.add(id(result))
            result.content = item.raw_content
            if request.include_raw_content:
                raw = await self.extractor.extract(
                    result.url,
                    fmt="markdown",
                    max_chars=self.settings.raw_content_max_chars,
                    query=request.query,
                    allow_jina=allow_jina,
                )
                result.raw_content = raw.raw_content if raw else item.raw_content
        # 读到正文的结果优先排在前面
        results.sort(key=lambda r: (0 if id(r) in matched else 1, -r.score))
        return results, pages_read
    # ------------------------------------------------------------------ 抽取
    async def extract(self, request: ExtractRequest) -> ExtractResponse:
        """批量抓取并抽取正文。"""
        started = time.perf_counter()
        request_id = uuid.uuid4().hex[:16]

        async def fetch_one(url: str) -> ExtractItem | None:
            async with self._semaphore:
                return await self.extractor.extract(url, fmt=request.format, max_chars=request.max_chars)

        tasks = [fetch_one(url) for url in request.urls]
        finished = await self._run_with_budget(tasks, self.settings.extract_budget)

        results: list[ExtractItem] = []
        failed: list[dict[str, Any]] = []
        for url, item in zip(request.urls, finished):
            if item is None:
                failed.append({"url": url, "error": "抽取失败或超时"})
            else:
                results.append(item)

        # 未能完成（被总预算取消）的 URL 也记为失败，保证返回结构与请求一一对应
        for url in request.urls[len(finished):]:
            failed.append({"url": url, "error": "超出抓取总预算"})

        return ExtractResponse(
            results=results,
            failed_results=failed,
            response_time=round(time.perf_counter() - started, 3),
            request_id=request_id,
        )

    # ------------------------------------------------------------------ 内部工具
    async def _run_with_budget(self, coros: list[Any], budget: float) -> list[Any]:
        """并行执行协程，最多等待 budget 秒；返回已完成任务的结果（顺序与输入一致）。"""
        if not coros:
            return []
        tasks = [asyncio.create_task(coro) for coro in coros]
        try:
            await asyncio.wait(tasks, timeout=budget)
        finally:
            pass
        results: list[Any] = []
        for task in tasks:
            if task.done() and not task.cancelled():
                try:
                    results.append(task.result())
                except Exception as exc:
                    logger.debug("任务执行失败: %s", exc)
                    results.append(None)
            else:
                task.cancel()
        return results

    def _early_stop_ratio(self, request: SearchRequest) -> float:
        """提前返回阈值：deep 以覆盖为先（读更多页面才停），advanced 以速度为先。"""
        if request.depth == "deep":
            return self.settings.deep_early_stop_ratio
        return self.settings.fetch_early_stop_ratio

    def _time_budget(self, request: SearchRequest) -> float:
        """按深度返回抓取阶段的时间预算：advanced 追求速度，deep 追求覆盖。"""
        return self.settings.deep_budget if request.depth == "deep" else self.settings.advanced_budget

    def _page_budget(self, request: SearchRequest) -> int:
        """计算本次请求允许抓取的页面数。"""
        if request.depth == "basic":
            return 0
        if request.max_pages is not None:
            return request.max_pages
        default = self.settings.advanced_pages if request.depth == "advanced" else self.settings.deep_pages
        return max(0, default)

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        """把请求参数变成稳定的短哈希，作为缓存 key。"""
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:20]

    def _query_cache_key(self, request: SearchRequest, want: int) -> str:
        """原始结果缓存 key：只与查询本身有关，可被不同深度模式复用。"""
        return "hits:" + self._fingerprint(
            {
                "q": request.query,
                "want": want,
                "topic": request.topic,
                "time_range": request.time_range,
                "engines": sorted(request.engines) if request.engines else None,
                "language": self.settings.language,
            }
        )

    def _result_cache_key(self, request: SearchRequest) -> str:
        """最终结果包缓存 key。"""
        return "res:" + self._fingerprint(request.model_dump(mode="json"))
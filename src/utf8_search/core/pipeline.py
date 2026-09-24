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
from datetime import datetime, timezone
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
from ..providers.engine_health import EngineHealthTracker
from ..providers.searxng import SearxngProvider
from ..rank.fusion import filter_domains, filter_low_quality, fuse, rerank
from ..rank.recency import age_days, apply_recency, date_from_url

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
                news_engines=settings.news_engine_list,
                news_pass_time_range=settings.news_pass_time_range,
                # 引擎健康度自适应（M5-5.1）：开关关闭时 from_settings 返回 None，
                # provider 会完全跳过自适应逻辑，等价于旧行为
                engine_health=EngineHealthTracker.from_settings(settings),
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
        # 剔除客观低质结果（无标题 / 标题是裸域名）：这类结果在「按时间过滤」的通用引擎
        # 结果里占比不低，留着会挤掉真正切题的新闻
        merged = filter_low_quality(merged)
        merged = filter_domains(
            merged,
            include_domains=request.include_domains,
            exclude_domains=request.exclude_domains,
        )
        merged = rerank(merged, request.query)

        # 2.5) 时效性（M5-5.2）：新闻主题下补齐发布日期并按新鲜度重排，必要时剔除已知过期结果
        if request.topic == "news":
            merged = await self._apply_news_recency(request, merged)

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
        if request.topic == "news":
            # 新闻主题必须拿候选池：只取 top-N 的话，融合后已无「更接近现在」的结果可挑，
            # 时效排序与过期过滤就失去意义。
            want = max(want, self.settings.news_candidate_pool)
        query_key = self._query_cache_key(request, want)

        cached_hits = await self.cache.get(query_key)
        if cached_hits is not None:
            return [SearchHit(**item) for item in cached_hits], ["cache"], []

        engines_used: list[str] = []
        failed_engines: list[str] = []
        hits: list[SearchHit] = []

        # 新闻主题：通用引擎兜底请求与主源的新闻请求互不依赖，先并发发出去，
        # 拿到主源结果后再汇合。这样新闻主题只多花「较慢的那一次」的延迟。
        general_task: asyncio.Task | None = None
        if request.topic == "news" and self.settings.news_include_general:
            general_task = asyncio.create_task(self._collect_general_extra(request, want))

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

        # 汇合并发的通用兜底结果（新闻源对中文长尾覆盖差，用通用结果补齐候选；
        # 融合阶段会按 URL 去重）
        if general_task is not None:
            try:
                extras, extra_engines, extra_failed = await general_task
            except Exception as exc:  # noqa: BLE001 - 兜底检索失败不应影响新闻主流程
                logger.warning("新闻补充检索（通用引擎）失败: %s", exc)
                failed_engines.append("searxng:general")
            else:
                hits.extend(extras)
                engines_used.extend(extra_engines)
                failed_engines.extend(extra_failed)

        if hits:
            await self.cache.set(query_key, [h.to_dict() for h in hits], self.settings.cache_query_ttl)
        return hits, engines_used, failed_engines

    async def _collect_general_extra(
        self, request: SearchRequest, want: int
    ) -> tuple[list[SearchHit], list[str], list[str]]:
        """新闻主题下再打一次通用引擎，补充新闻源拿不到的候选。

        免费新闻源对中文长尾查询覆盖很差（实测 8 条查询里有 3 条直接返回 0 条），
        只靠新闻引擎会导致整轮结果退化成兜底源的无日期结果。补充失败不影响主流程。

        这里**必须把 time_range 透传给通用引擎**：通用引擎（Bing/Google 等）的日期过滤
        是真的有效的，实测 time_range=day 时每条查询都能拿到 5-12 条「当天/1 日内」结果，
        且延迟不增（1.0-2.3s）；不透传时同一批查询只有 0-2 条带日期。
        注意这与新闻类目引擎相反：新闻引擎带 time_range 一律返回 0 条
        （见 config.news_pass_time_range）。
        """
        extras: list[SearchHit] = []
        engines_used: list[str] = []
        failed_engines: list[str] = []
        # 用一组独立的引擎（见 news_general_engines）：主通用引擎列表里的 yandex
        # 配合 time_range 会返回大量垃圾农场内容（实测出现成人站、综艺盗播站），
        # 而这一路只用来补「最新的候选」，用更干净的引擎集更划算。
        extra_engines = self.settings.news_general_engine_list or None
        for provider in self.providers:
            if provider.name != "searxng":
                continue
            try:
                provider_hits = await provider.search(
                    request.query,
                    max_results=want,
                    topic="general",
                    time_range=request.time_range,
                    engines=extra_engines,
                    language=self.settings.language,
                )
            except Exception as exc:  # noqa: BLE001 - 补充检索失败不应影响新闻主流程
                logger.warning("新闻补充检索（通用引擎）失败: %s", exc)
                failed_engines.append("searxng:general")
                continue
            if provider_hits:
                extras.extend(provider_hits)
                engines_used.append("searxng:general")
        return extras, engines_used, failed_engines

    # -------------------------------------------------------------- 时效性（M5-5.2）
    def _fresh_days(self, request: SearchRequest) -> int:
        """新闻结果的「新鲜」排序窗口：显式 time_range 优先，否则用配置默认值。"""
        window = {"day": 1, "week": 7, "month": 31, "year": 365}.get(request.time_range or "")
        return window or self.settings.news_fresh_days

    def _drop_after_days(self, request: SearchRequest) -> int:
        """丢弃阈值：不低于配置的新闻新鲜窗口。

        不能直接沿用 `time_range=day` 的 1 天：免费源给不出足够的当天结果，
        用 1 天当阈值会把 2-7 天的近期新闻丢掉、拿无日期结果补位，实测会显著拉低时效性。
        """
        return max(self._fresh_days(request), self.settings.news_fresh_days)

    async def _apply_news_recency(
        self, request: SearchRequest, results: list[SearchResult]
    ) -> list[SearchResult]:
        """新闻主题的时效处理：先回补缺失日期，再按新鲜度重排。"""
        fresh_days = self._fresh_days(request)
        # 先用 URL 里的日期线索做零成本补全，再决定要不要抓页面
        self._fill_dates_from_urls(results)
        shortfall = self._fresh_shortfall(results, fresh_days=fresh_days, max_results=request.max_results)
        if shortfall > 0:
            await self._backfill_published_dates(results, shortfall=shortfall)
        return apply_recency(
            results,
            fresh_days=fresh_days,
            max_results=request.max_results,
            drop_stale=self.settings.news_drop_stale,
            drop_after_days=self._drop_after_days(request),
        )

    def _fresh_shortfall(
        self, results: list[SearchResult], *, fresh_days: int, max_results: int
    ) -> int:
        """还差几条「新鲜」结果才能填满 max_results；已够则为 0。

        用于决定要不要花时间去抓页面回补日期：免费源里抓页面补日期的成功率约 1/3，
        且补出来的经常是旧日期，所以在「已经有足够新鲜结果」时完全跳过这一步，
        是 topic=news 延迟优化的关键（实测能把新闻查询的端到端耗时压回 1-2s 量级）。
        """
        now = datetime.now(timezone.utc)
        fresh = 0
        for result in results:
            days = age_days(result.published_date, now=now)
            if days is not None and days <= fresh_days:
                fresh += 1
                if fresh >= max_results:
                    return 0
        return max_results - fresh

    def _fill_dates_from_urls(self, results: list[SearchResult]) -> int:
        """用 URL 路径里内嵌的日期补全缺失的 `published_date`（纯本地计算，零网络开销）。

        很多结果（通用引擎兜底、google news 等不给日期的引擎）其实把日期写在了 URL 里，
        例如 `/202609/t20260922_12028748.htm`、`/2026/08/01/ARTI...`。
        先做这一步，后面的抓页面回补只需处理「连 URL 都没有日期线索」的结果，
        实测能明显提高日期覆盖率，同时减少抓取请求、降低延迟。

        只补空值，不覆盖引擎已经给出的日期（引擎给的是权威值）。
        """
        filled = 0
        for result in results:
            if result.published_date:
                continue
            found = date_from_url(result.url)
            if found:
                result.published_date = found
                filled += 1
        if filled:
            logger.debug("新闻日期回补（URL）：%d 条", filled)
        return filled

    async def _backfill_published_dates(self, results: list[SearchResult], *, shortfall: int) -> None:
        """为缺少发布日期的新闻结果抓页面推断日期（原地修改，受页数与时间预算约束）。

        `shortfall` 是「还差几条新鲜结果」，由 `_fresh_shortfall` 算出，为 0 时调用方
        根本不会进来。据此反推要抓的页数：免费源抓页面补日期的成功率约 1/3、且补出来的
        常常是旧日期，所以按每个缺口试 4 个候选来估算，再受 `news_date_pages` 与
        `news_date_budget` 双重封顶。这样「结果已经够新鲜」的查询完全不产生抓取请求。
        """
        if not self.settings.news_date_backfill or self.settings.news_date_pages <= 0:
            return
        page_cap = min(self.settings.news_date_pages, max(1, shortfall) * 4)
        now = datetime.now(timezone.utc)
        targets = [
            result
            for result in results[:page_cap]
            if age_days(result.published_date, now=now) is None
        ]
        if not targets:
            return

        page_timeout = min(self.settings.fetch_timeout, self.settings.page_total_timeout)

        async def fetch_one(result: SearchResult) -> tuple[SearchResult, str | None]:
            async with self._semaphore:
                try:
                    date = await asyncio.wait_for(
                        self.extractor.fetch_date(result.url), timeout=page_timeout
                    )
                except (asyncio.TimeoutError, TimeoutError):
                    logger.debug("回补日期超时（%.1fs）: %s", page_timeout, result.url)
                    date = None
                return result, date

        finished = await self._run_with_budget(
            [fetch_one(result) for result in targets], self.settings.news_date_budget
        )
        filled = 0
        for item in finished:
            if not item:
                continue
            result, date = item
            if date and not result.published_date:
                result.published_date = date
                filled += 1
        if filled:
            logger.debug("新闻日期回补：%d/%d 条补齐成功", filled, len(targets))

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
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
from ..rank.diversity import (
    apply_form_penalty,
    apply_rank_filters,
    query_coverage,
    registrable_domain,
)
from ..rank.fusion import filter_domains, filter_low_quality, fuse, rerank
from ..rank.recency import (
    age_days,
    apply_recency,
    date_from_url,
    has_recency_intent,
    mark_stale_by_title_year,
    parse_published,
)
from ..verify.expansion import ExpansionMetrics, expansion_needed
from .upstream_gate import UpstreamGate, UpstreamOverloaded

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
        gate: UpstreamGate | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.cache = cache
        self.providers = providers
        self.extractor = extractor
        self._semaphore = asyncio.Semaphore(settings.max_fetch_concurrency)
        # 上游并发闸门：与 provider 共享同一个实例，/metrics 也从这里取
        self.gate = gate if gate is not None else UpstreamGate.from_settings(settings)
        # 查询扩展埋点（M6 阶段 1）：只记录分布，不改变任何行为、不增加上游调用
        self.expansion_metrics = ExpansionMetrics()

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

        # 闸门必须先于 provider 构造：SearxngProvider 直接持有它（重试也算同一个槽位）
        gate = UpstreamGate.from_settings(settings)
        providers: list[BaseProvider] = [
            SearxngProvider(
                settings.searxng_url,
                client,
                default_engines=settings.engine_list,
                timeout_limit=settings.search_timeout_limit,
                news_engines=settings.news_engine_list,
                news_pass_time_range=settings.news_pass_time_range,
                # 新闻主题下按引擎白名单透传 time_range（见 config.news_time_range_engines）：
                # sina 靠它给 7 日内结果，duckduckgo news 带它返回 0 条 —— 一个全局开关服务不了两者。
                news_time_range_engines=settings.news_time_range_engine_set,
                # 引擎健康度自适应（M5-5.1）：开关关闭时 from_settings 返回 None，
                # provider 会完全跳过自适应逻辑，等价于旧行为
                engine_health=EngineHealthTracker.from_settings(settings),
                # 上游并发闸门（M5 并发保护）：包住整次 search（含重试），过载抛 UpstreamOverloaded
                gate=gate,
            ),
            BingHtmlProvider(client),
        ]
        jina = JinaReader(client, prefix=settings.jina_prefix) if settings.enable_jina_fallback else None
        extractor = PageExtractor(settings, client, cache, jina=jina)
        return cls(
            settings, client=client, cache=cache, providers=providers, extractor=extractor, gate=gate
        )

    async def close(self) -> None:
        """释放资源。"""
        await self.client.aclose()
        await self.cache.close()

    def render_metrics(self) -> str:
        """渲染 Prometheus 文本指标（上游闸门 + M6 阶段 1 的扩展埋点）。"""
        return self.gate.render_metrics() + self.expansion_metrics.render()

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
            # Tavily 兼容（M6）：结果级 id 跟着本次 request_id 重新盖章，避免缓存复用后 id 与 request_id 不一致
            for index, item in enumerate(response.results):
                item.id = f"{request_id}-{index}"
            response.auto_parameters = {"topic": request.topic, "search_depth": request.depth}
            response.usage = {"credits": 0} if request.include_usage else None
            return response

        # 1) 取原始结果（多源并发 + 兜底）。
        # 上游过载且**一条结果都没有**时，_collect_hits 会向上抛 UpstreamOverloaded（→ 429），
        # 而不是返回空列表把「过载」伪装成「没搜到」。
        hits, engines_used, failed_engines, degraded_reason = await self._collect_hits(request)

        # 2) 融合、去重、重排、过滤、时效分层（不含正文抓取）
        merged = await self._rank_hits(hits, request)
        # 规格不匹配被"补回"（候选不足，只能降权保留）时，明确告诉调用方：结果里含规格不符项
        rank_stats = getattr(self, "last_rank_stats", {}) or {}
        if rank_stats.get("spec_mismatch_refilled"):
            degraded_reason = ",".join(
                dict.fromkeys([*(degraded_reason.split(",") if degraded_reason else []), "spec_unverified"])
            )

        # 3) 深度模式：并发抓取正文（受总预算约束）
        pages_read = 0
        if request.depth in ("advanced", "deep"):
            merged, pages_read = await self._enrich_with_content(request, merged)

        results = merged[: request.max_results]
        # M6 阶段 1 埋点（零额外上游调用、零行为改变）：记录候选/覆盖率/独立站点/候选不足判定
        self._record_expansion_sample(request, hits, results)
        # Tavily 兼容（M6）：补结果级 id 与 auto_parameters/usage（只加字段，不改已有字段语义）
        for index, item in enumerate(results):
            item.id = f"{request_id}-{index}"
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
            degraded=degraded_reason is not None,
            degraded_reason=degraded_reason,
            auto_parameters={"topic": request.topic, "search_depth": request.depth},
            usage={"credits": 0} if request.include_usage else None,
        )
        await self.cache.set(result_key, response.model_dump(mode="json"), self.settings.cache_result_ttl)
        return response

    async def _rank_hits(
        self, hits: list[SearchHit], request: SearchRequest
    ) -> list[SearchResult]:
        """把原始结果重组成最终排序（融合 → 过滤 → 重排 → 质量过滤 → 时效分层）。

        单独抽出来有两个目的：
        1. 正文抓取（深度模式）与排序解耦，basic 深度下这一步纯本地计算、零网络开销；
        2. 允许用**同一批候选**离线复算「改动前 / 改动后」的排序结果（见 scripts/rank_ab.py）。
           上游免费引擎每次返回的候选集差异很大，只有固定候选才能分清
           「排序改动带来的差异」与「上游漂移带来的差异」。
        """
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

        # 2.5) 新闻主题（M5-5.2 在前，质量过滤在后）：先按新鲜度分层，再在同一顺序上过滤。
        # 顺序是实测定的 —— 配对 A/B（scripts/news_check.py --ab，逐条交替两种口径）：
        # 先过滤会把「新鲜且有日期」的结果（多为各站当天更新的日报/栏目页）挤掉、换成更陈旧的候选，
        # 7 日内日期 39/40 → 32/40；反过来先分层再过滤（剔除只删不改顺序），复测得 40/40 vs 40/40。
        if request.topic == "news":
            merged = await self._apply_news_recency(request, merged)
            return self._apply_quality_filters(merged, request, structural_only=True)

        # 2.2) 质量与多样性过滤（M5-5.3）：通用主题下先清垃圾，再谈新鲜度。
        # 所有过滤都会在结果不足时按原排序补回，因此不会让结果变少。
        merged = self._apply_quality_filters(merged, request)

        # 2.6) 时效意图（M5-5.3）：通用主题命中「最新/最近/latest」这类词时也按新鲜度分层重排。
        # 只用零网络开销的日期线索（URL 内嵌日期 + 标题里的跨年年份），不抓页面、不丢弃结果，
        # 因此不影响 basic 的速度。
        # `stale_last=True`：通用主题下「无日期」多是实时页面（台风实时路径、官网专题），
        # 把「已知跨年旧闻」排在它们后面才对。依据：2-9 的 #4「台风 最新消息 路径」
        # 曾在通用主题下把 2021 年旧闻排到第 1 位。
        if self.settings.general_recency_intent and has_recency_intent(request.query):
            self._fill_dates_from_urls(merged)
            mark_stale_by_title_year(merged)
            merged = apply_recency(
                merged,
                fresh_days=self.settings.news_fresh_days,
                # 2026-09-30（P5）：命中时间意图时**硬过滤已知陈旧**结果（够新鲜/无日期的仍保留）。
                # 依据：docs/04 §8 遗留 3-①（英文 latest/update 类查询没有硬过滤，Q3#4/Q15#4 的旧文照排）。
                # `drop_stale=True` 只在"剩余结果仍够 max_results"时生效，不会掏空结果集。
                drop_stale=True,
                stale_last=True,
                max_results=request.max_results,
            )

        # 2.7) 形态轻降权（2026-09-30，P1）：含实质内容的首页/栏目页 ×0.95，让独立文章略靠前。
        # 与过滤层共用 `looks_like_column` 判据；日报/汇总类文章只降权、不剔除。
        merged = apply_form_penalty(merged)
        return merged

    def _apply_quality_filters(
        self, results: list[SearchResult], request: SearchRequest, *, structural_only: bool = False
    ) -> list[SearchResult]:
        """质量与多样性过滤（M5-5.3）：候选充足时剔除聚合页 / 非中文脚本 / 低覆盖 / 同站冗余。

        只做删除、不重排；候选不足 `max_results` 时会按「缺陷轻重」补回被剔除的结果
        （见 `rank.diversity.apply_rank_filters`），因此这一步永远不会把结果掏空。

        `structural_only=True`（新闻主题）只保留「同站冗余 / 脚本不匹配」这两项结构性判据，
        关掉聚合页与覆盖度过滤 —— 依据是配对 A/B（`news_check.py --ab`，逐条交替两种口径）：
        news 主题 + time_range=day 下，「带日期」的候选本就很稀缺，而聚合页/覆盖度判据剔除的
        恰恰是各站点的「日报 / 栏目」页（它们带日期且当天更新），换上来的是更陈旧的候选，
        实测时效性 39/40 → 32/40。新闻路径已有自己的质量机制（日期回补、过期丢弃、新鲜优先分层），
        5.3 的这两项判据是在通用主题的候选集上验证的，不应顺手套到新闻路径上。
        """
        filtered, hygiene = apply_rank_filters(
            results,
            query=request.query,
            max_results=request.max_results,
            max_per_host=self.settings.rank_max_per_host,
            min_query_coverage=(
                0.0 if structural_only else self.settings.rank_min_query_coverage
            ),
            drop_aggregator_pages=(
                False if structural_only else self.settings.rank_drop_aggregator_pages
            ),
            drop_script_mismatch=self.settings.rank_drop_script_mismatch,
        )
        if any(hygiene.values()):
            logger.debug("质量过滤：%s", hygiene)
        # 记下本轮过滤统计：`search()` 用它决定是否标 degraded（如规格不匹配被补回）
        self.last_rank_stats = hygiene
        return filtered

    def _candidate_target(self, request: SearchRequest) -> int:
        """本次向主源索取的**候选池目标值**（`want`）。

        与 `_collect_hits` 用的是同一套口径，抽出来是为了让 M6 阶段 1 的埋点能在**不改变行为**的前提下
        读到「目标候选数」，并据此判断「候选不足」。
        """
        pages_cap = self._page_budget(request)
        want = max(request.max_results, pages_cap)
        if request.topic == "news":
            # 新闻主题必须拿候选池：只取 top-N 的话，融合后已无「更接近现在」的结果可挑，
            # 时效排序与过期过滤就失去意义。
            want = max(want, self.settings.news_candidate_pool)
        else:
            # 通用主题同样要候选池（M5-5.3）。SearXNG 一次就把整批结果返回给本地，
            # 多留候选不增加任何上游请求；但候选数等于结果数时，质量过滤必然因为
            # 「不足 max_results」被全部补回 —— 过滤形同虚设（实测 2-9 的聚合页就是这么漏出来的）。
            want = max(want, self.settings.rank_candidate_pool)
        return want

    def _record_expansion_sample(
        self, request: SearchRequest, hits: list[SearchHit], results: list[SearchResult]
    ) -> None:
        """M6 阶段 1 埋点：记录候选数 / 覆盖率 / 独立站点数与「候选不足」判定。

        **零额外上游调用、零行为改变**：全部数值都来自本次已经拿到的候选与最终结果。
        覆盖率分母固定为**用户原始查询词**（`query_coverage(request.query, ...)`），
        扩展/改写词不参与计算 —— 这是 2026-09-28 拍板的约束。
        """
        target = self._candidate_target(request)
        coverage: float | None = None
        if results:
            coverage = sum(query_coverage(request.query, item) for item in results) / len(results)
        hosts = {registrable_domain(item.url) for item in results}
        hosts.discard("")
        reason = expansion_needed(len(hits), target, coverage)
        # SearXNG 原始返回条数（未截断）：用于判断「候选池上限是不是约束」（M6 阶段 2a）。
        # 与 unresponsive_engines 同一模式：provider 上的「最近一次请求」状态，单并发下准确。
        raw_candidates: int | None = None
        for provider in self.providers:
            if provider.name == "searxng":
                raw_candidates = getattr(provider, "raw_result_count", None)
                break
        self.expansion_metrics.observe(
            candidates=len(hits),
            raw_candidates=raw_candidates,
            target=target,
            coverage_mean=coverage,
            distinct_hosts=len(hosts),
            reason=reason,
        )
        logger.debug(
            "扩展埋点：候选 %d/%d（原始 %s）（%s） 覆盖率 %s 独立站点 %d",
            len(hits),
            target,
            raw_candidates,
            reason or "充足",
            f"{coverage:.2f}" if coverage is not None else "n/a",
            len(hosts),
        )

    async def _collect_hits(
        self, request: SearchRequest
    ) -> tuple[list[SearchHit], list[str], list[str], str | None]:
        """从各 Provider 收集原始结果，主源不足时自动兜底。

        返回 `(hits, engines_used, failed_engines, degraded_reason)`。上游过载（`UpstreamOverloaded`）：

        - **绝不被 `except Exception` 吞成「返回 0 条」**——一条结果都没有时直接向上抛，由接口层映射成
          429 / MCP 可读错误；
        - **主源过载时绝不降级到兜底源**（Bing 等）——过载是全局保护，把压力转嫁给更脆弱的抓取源只会扩大故障面；
        - **按「跳过是否会导致返回空结果」区分两类调用**：
          * **兜底型**（Bing 兜底、news 的通用引擎补充）：只在主源凑不满 `max_results` 时触发，
            跳过就会把空/残缺结果交给用户 → **不许静默跳过**，按 `upstream_optional_wait` 有限等待取容量，
            拿不到直接 429（`fallback_no_capacity` / `no_capacity`）；
          * **锦上添花型**（少几条候选无妨）：可跳过并记 `degraded_reason`（当前产品路径没有这种调用，
            因此正常情况下 `degraded` 为 false）。
        """
        want = self._candidate_target(request)
        query_key = self._query_cache_key(request, want)

        cached_hits = await self.cache.get(query_key)
        if cached_hits is not None:
            return [SearchHit(**item) for item in cached_hits], ["cache"], [], None

        engines_used: list[str] = []
        failed_engines: list[str] = []
        hits: list[SearchHit] = []
        overloaded: UpstreamOverloaded | None = None
        degraded_reasons: list[str] = []

        # 主源：SearXNG；仅在「结果拿不满用户需要的条数」或主源失败时才启用兜底源，
        # 避免深度模式下为了凑够抓取页数而白白多打一次外部请求。
        #
        # 2026-09-30（Bing 让位）：新闻 + time_range 场景下，兜底源**不能抢在日期回补路前面** ——
        # Bing 结果通常没有发布日期，一旦它先把 max_results 填满，`_needs_general_extra` 就永远不会触发，
        # 「按 time_range 拿新鲜候选」的整条路等于被旁路（实测中文组 0/25 就是这个原因）。
        # 因此这里把兜底源**延后**到日期回补之后：主源 → 日期回补 → Bing（Bing 仍可入池，只是让位）。
        defer_fallback = request.topic == "news" and bool(request.time_range)
        deferred_providers: list[BaseProvider] = []
        for index, provider in enumerate(self.providers):
            if index > 0 and len(hits) >= request.max_results:
                break
            if index > 0 and defer_fallback:
                deferred_providers.append(provider)
                continue
            # 兜底源（index>0）属于**兜底型**调用：它只在「主源凑不满 max_results」时才会走到这里，
            # 跳过它就可能让用户拿到空/残缺结果，所以**不许静默跳过**——按 `upstream_optional_wait`
            # 有限等待取容量，等不到直接抛 `UpstreamOverloaded`（→ 429），绝不返回空结果。
            provider_hits, provider_error, provider_overloaded = await self._call_provider(
                provider, request, want, optional=index > 0
            )
            if provider_error is not None:
                failed_engines.append(provider_error)
                continue
            if provider_overloaded is not None:
                # 过载是全局保护：不降级到兜底源、也不吞成空结果，直接中止本轮上游收集。
                overloaded = provider_overloaded
                break

            if provider.name == "searxng":
                unresponsive = getattr(provider, "unresponsive_engines", [])
                failed_engines.extend(unresponsive)
            elif provider_hits:
                # 兜底源入池前先过相关性闸门（不合格的直接不注入）
                provider_hits, dropped = self._filter_fallback_hits(provider, provider_hits, request)
                if dropped:
                    logger.info("兜底源 %s 有 %d 条未过相关性闸门，已丢弃", provider.name, dropped)
                    if not provider_hits:
                        degraded_reasons.append("fallback_low_relevance")

            if provider_hits:
                hits.extend(provider_hits)
                engines_used.append(provider.name)
                # 结果已够用则立即返回，不再触发兜底源（S1/S4：能快就快）
                if len(hits) >= want:
                    break
                if len(hits) >= request.max_results and index == 0:
                    break

        # 主源过载且一条结果都没有 → 直接 429；不再去试补充路，避免在同一个饱和的上游上继续排队。
        if overloaded is not None and not hits:
            raise overloaded

        # 新闻主题：**新鲜候选不足时才补**（2026-09-30 起判据是「窗口内带日期条数 < max_results」，
        # 不再是「主源结果数 < max_results」—— 见 _needs_general_extra 的说明）。
        # 这条补充路是**兜底型**：拿不到容量就直接 429，不允许静默跳过并把空/过期结果交给用户。
        if self._needs_general_extra(hits, request):
            try:
                extras, extra_engines, extra_failed = await self._collect_general_extra(request, want)
            except UpstreamOverloaded as exc:
                # 兜底型调用拿不到容量 → 直接 429（不返回空/残缺结果）
                raise exc from None
            except Exception as exc:  # noqa: BLE001 - 兜底检索失败不应影响新闻主流程
                logger.warning("新闻补充检索（通用引擎）失败: %s", exc)
                failed_engines.append("searxng:general")
            else:
                hits.extend(extras)
                engines_used.extend(extra_engines)
                failed_engines.extend(extra_failed)

        # 让位的兜底源：日期回补之后仍不够 max_results 才启用（仍是兜底型：拿不到容量直接 429）
        if overloaded is None:
            for provider in deferred_providers:
                if len(hits) >= request.max_results:
                    break
                provider_hits, provider_error, provider_overloaded = await self._call_provider(
                    provider, request, want, optional=True
                )
                if provider_overloaded is not None:
                    overloaded = provider_overloaded
                    break
                if provider_error is not None:
                    failed_engines.append(provider_error)
                    continue
                if provider_hits:
                    provider_hits, dropped = self._filter_fallback_hits(provider, provider_hits, request)
                    if dropped and not provider_hits:
                        degraded_reasons.append("fallback_low_relevance")
                if provider_hits:
                    hits.extend(provider_hits)
                    engines_used.append(provider.name)

        if overloaded is not None and hits:
            # 主源过载但仍有结果 → 降级返回（保留可用结果）
            degraded_reasons.append("upstream_overloaded")
        if overloaded is not None and not hits:
            # 一条结果都没有、且原因是上游过载 —— 必须让调用方看到明确信号，不能返回空列表。
            raise overloaded

        # 时效降级信号（2026-09-30）：调用方指定了 time_range，但我们**数不出足够的「可信日期」结果**时，
        # 必须明说「时效无法验证」，而不是让它以为这 5 条就是「最近一天/一周」的结果。
        # 「可信」= 结果来自 news_trusted_date_engines 白名单里的引擎（抽检过：上报日期与内容时间线索一致）。
        # 典型场景：中文新闻查询受限于上游（chinaso 索引旧 / 其它源不给日期），命中该信号；
        # 英文查询由 duckduckgo news 稳定提供可信日期，一般不触发。
        if request.time_range and self._trusted_fresh_count(hits, request) < request.max_results:
            degraded_reasons.append("freshness_unverified")

        if hits:
            await self.cache.set(query_key, [h.to_dict() for h in hits], self.settings.cache_query_ttl)
        return hits, engines_used, failed_engines, (",".join(dict.fromkeys(degraded_reasons)) or None)

    async def _call_provider(
        self,
        provider: BaseProvider,
        request: SearchRequest,
        want: int,
        *,
        optional: bool,
    ) -> tuple[list[SearchHit] | None, str | None, UpstreamOverloaded | None]:
        """调用一个 provider；返回 `(hits, 失败的 provider 名, 过载异常)`。

        `optional=True`（兜底源）走「有限等待取闸门容量」：拿不到就返回
        `UpstreamOverloaded(reason="fallback_no_capacity")`，由调用方决定是上抛 429 还是记降级。
        抽成方法是为了让「主源循环」与「让位后的兜底源」共用同一套闸门与异常语义。
        """
        acquired_optional = False
        if optional:
            acquired_optional = await self.gate.try_acquire(
                timeout=self.settings.upstream_optional_wait
            )
            if not acquired_optional:
                self.gate.metrics.record_rejected("fallback_no_capacity")
                return None, None, UpstreamOverloaded(
                    reason="fallback_no_capacity", retry_after=self.gate.retry_after
                )
        try:
            provider_hits = await provider.search(
                request.query,
                max_results=want,
                topic=request.topic,
                time_range=request.time_range,
                engines=request.engines,
                language=self.settings.language,
            )
        except UpstreamOverloaded as exc:
            return None, None, exc
        except Exception as exc:  # noqa: BLE001 - 单个 provider 失败不应中断整轮
            logger.warning("Provider %s 搜索失败: %s", provider.name, exc)
            return None, provider.name, None
        finally:
            if optional and acquired_optional:
                self.gate.release()
        return provider_hits, None, None

    def _filter_fallback_hits(
        self, provider: BaseProvider, hits: list[SearchHit], request: SearchRequest
    ) -> tuple[list[SearchHit], int]:
        """兜底源（Bing）的相关性闸门（2026-09-30）。

        兜底源的问题在 2-9 里出现过两次：查询「最近一周 AI 行业动态」时它返回
        **沃尔玛滤水器页 / 世界杯日历 / 动漫站**（字面无关、且没有发布日期），
        一旦入池就会挤掉真正相关的结果（Q2 的 1/5 就是这么来的）。

        判据复用 5.3 的**查询词覆盖率**（阈值 = `rank_min_query_coverage`，默认 0.34）：
        不达标的兜底结果**不入池**；若全部被挡下，返回空列表 + 由调用方记 degraded
        （宁可少几条，也不把无关结果当"兜底"给用户）。
        """
        if provider.name != "bing" or not hits:
            return hits, 0
        threshold = self.settings.rank_min_query_coverage
        if threshold <= 0:
            return hits, 0
        kept: list[SearchHit] = []
        for hit in hits:
            result = SearchResult(
                title=hit.title or "", url=hit.url or "", content=hit.snippet or ""
            )
            if query_coverage(request.query, result) >= threshold:
                kept.append(hit)
        return kept, len(hits) - len(kept)

    def _needs_general_extra(self, hits: list[SearchHit], request: SearchRequest) -> bool:
        """news 主题下是否需要再补一路通用引擎（**兜底型**判据）。

        2026-09-30 改动：判据从「**主源结果数** < max_results」改成
        「**窗口内带发布日期的新鲜结果数** < max_results」。

        旧判据的漏洞（实测证据）：主源返回 5-10 条「过期但字面匹配」的结果时，数量够了就不再补充，
        而本地时效排序只能在这堆过期结果里排 —— 中文组 5/5 查询因此拿到 0 条 7 日内结果，
        而真正带日期的候选（若在补充路上）根本没被调用。

        口径细节：
        * **无日期的结果不计入分子**（无法证明它新鲜），但**不会被丢弃** —— 它们照常进候选池，
          只是在时效排序里靠后（见 `rank.recency`）；
        * 判据仍属**兜底型**：拿不到容量直接 429，不静默跳过。
        """
        if request.topic != "news" or not self.settings.news_include_general:
            return False
        return self._fresh_count(hits, request) < request.max_results

    def _fresh_count(self, hits: list[SearchHit], request: SearchRequest) -> int:
        """候选里「窗口内且带发布日期」的条数（补充路判据的分子，也用于诊断）。"""
        window = self._fresh_days(request)
        now = datetime.now(timezone.utc)
        count = 0
        for hit in hits:
            published = parse_published(hit.published_date)
            if published is None:
                continue
            if (now - published).total_seconds() <= window * 86400:
                count += 1
        return count

    def _trusted_fresh_count(self, hits: list[SearchHit], request: SearchRequest) -> int:
        """窗口内、且来源引擎属于「日期可信白名单」的条数（时效降级信号的判据）。"""
        window = self._fresh_days(request)
        now = datetime.now(timezone.utc)
        trusted = self.settings.news_trusted_date_engine_set
        count = 0
        for hit in hits:
            if trusted and hit.engine not in trusted:
                continue
            published = parse_published(hit.published_date)
            if published is None:
                continue
            if (now - published).total_seconds() <= window * 86400:
                count += 1
        return count

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
                    # 可选补充路：**有限等待**取容量，拿不到就跳过（由 _collect_hits 记 degraded）。
                    # 这条路的唯一理由就是补中文长尾的 0 结果，所以给 0.5s 等待换更低的降级率。
                    optional_wait=self.settings.upstream_optional_wait,
                )
            except UpstreamOverloaded:
                # 过载必须穿透到 _collect_hits 决定「降级返回」还是「上抛 429」，
                # 不能被这里的 except Exception 吞成「补充检索失败」。
                raise
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

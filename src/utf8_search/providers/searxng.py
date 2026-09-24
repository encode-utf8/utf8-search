"""SearXNG Provider：主力搜索源（聚合 Mojeek / Google CSE / Startpage / Presearch / Yahoo 等引擎）。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .base import BaseProvider, SearchHit
from .engine_health import EngineHealthTracker

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
        news_engines: list[str] | None = None,
        news_pass_time_range: bool = False,
        engine_health: EngineHealthTracker | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client
        self.default_engines = default_engines or []
        # 新闻类目引擎（topic=news 时优先使用）：免费源的 news 类目与 general 差异很大，
        # 用一组独立的引擎列表才能拿到带发布日期的时效性结果。
        self.news_engines = news_engines or []
        # 新闻主题是否把 time_range 透传上游：免费新闻引擎对该过滤支持很差
        # （实测 duckduckgo news + time_range=day 直接返回 0 条），默认不透传，本地过滤。
        self.news_pass_time_range = news_pass_time_range
        # 聚合搜索时间上限（SearXNG 的 timeout_limit 参数）：到点即返回已有结果，
        # 避免个别慢引擎拖垮整体延迟。
        self.timeout_limit = timeout_limit
        # 引擎健康度自适应（M5-5.1，见 engine_health.py）：None 表示关闭，行为与旧版一致
        self.engine_health = engine_health
        # 上一次查询里不可用的引擎，供上层判断是否需要降级到兜底源（保留旧接口）
        self.unresponsive_engines: list[str] = []
        # 引擎名 -> 失败原因：旧实现只取了名字、把原因丢掉了，而原因正是分级退避的依据
        self.unresponsive_reasons: dict[str, str] = {}

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
            "pageno": 1,
        }
        # 新闻主题默认不透传 time_range：免费引擎会因此返回空结果（见配置说明），
        # 时效性改由 pipeline 按 published_date 在本地处理。
        if time_range and (topic != "news" or self.news_pass_time_range):
            params["time_range"] = time_range
        if self.timeout_limit:
            params["timeout_limit"] = self.timeout_limit

        engine_names = self._planned_engines(engines, topic)
        if engine_names:
            params["engines"] = ",".join(engine_names)
        else:
            # 只在「没有显式引擎列表」时才传 categories。
            # SearXNG 的 webadapter.parse_generic 里 engines 与 categories 是「叠加」关系：
            # 一旦同时传，就会把该 categories 下的全部引擎追加进查询，显式 engines 列表
            # 因此失去约束力（实测 categories=news + engines="google news" 会返回 news
            # 类目全部引擎的结果，导致「按引擎隔离实测」得出的结论全部不可信）。
            params["categories"] = "news" if topic == "news" else "general"

        payload, used_engines = await self._request(
            params, retry_engines=self._retry_engines(engine_names)
        )

        # 记录不可用引擎（含原因），供上层降级判断与健康度统计使用
        unresponsive = self._parse_unresponsive(payload.get("unresponsive_engines"))
        self.unresponsive_engines = [name for name, _ in unresponsive]
        self.unresponsive_reasons = dict(unresponsive)
        if unresponsive:
            logger.debug(
                "SearXNG 不可用引擎: %s",
                ", ".join(f"{name}({reason})" if reason else name for name, reason in unresponsive),
            )
        if self.engine_health is not None:
            self.engine_health.observe(used_engines, unresponsive)

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

    # ------------------------------------------------------------------ 引擎选择
    def _planned_engines(self, explicit: list[str] | None, topic: str) -> list[str]:
        """确定本次查询的显式引擎列表。

        调用方显式指定（调试用）优先；否则新闻主题用 news_engines、其余用 default_engines。
        开启自适应时再按健康度收敛：冷却中的引擎不参与（除非命中覆盖率下限或探测名额）。
        """
        if explicit:
            base = list(explicit)
        elif topic == "news":
            # 未配置新闻引擎时留空，让 SearXNG 用它自己的 news 类目引擎集合
            base = list(self.news_engines)
        else:
            base = list(self.default_engines)
        if not base or self.engine_health is None:
            return base
        return self.engine_health.select(base)

    def _retry_engines(self, engine_names: list[str]) -> list[str] | None:
        """瞬时错误（502/503/504）重试时用的引擎集合。

        关键点（M5-5.1）：**重试不能抛弃 `engines` 参数**。旧实现在重试时去掉 engines，
        等于把引擎集合换成 SearXNG 的默认集合 —— 返回内容不再受本服务控制
        （实测会混入垃圾农场内容），这是典型的「防御性降级」反例。
        这里改为「剔除冷却中的引擎后重试」：约束保持显式，同时避开最可能再次触发
        5xx 的引擎（实测 `resulthunter` 会引发 SearXNG 的 `add_unresponsive_engine after close`）。
        """
        if not engine_names:
            return None
        if self.engine_health is None:
            return list(engine_names)
        # probe_slots=0：重试是「求稳」的一次机会，不带仍在冷却期的引擎
        retry = self.engine_health.select(engine_names, probe_slots=0)
        return retry or list(engine_names)

    def engine_health_snapshot(self) -> dict[str, Any] | None:
        """引擎健康快照（供 `/health`）；未开启自适应时返回 None。"""
        if self.engine_health is None:
            return None
        candidates = list(dict.fromkeys([*self.default_engines, *self.news_engines]))
        return self.engine_health.snapshot(candidates=candidates or None)

    @staticmethod
    def _parse_unresponsive(raw: Any) -> list[tuple[str, str]]:
        """解析响应里的 `unresponsive_engines`。

        形态是 `[[引擎名, 原因], ...]`（个别版本可能是纯字符串），两种都吃下。
        原因（`Suspended: CAPTCHA` / `access denied` / `too many requests`）是分级退避的依据。
        """
        pairs: list[tuple[str, str]] = []
        for item in raw or []:
            if isinstance(item, (list, tuple)):
                name = str(item[0]) if item else ""
                reason = str(item[1]) if len(item) > 1 else ""
            else:
                name, reason = str(item), ""
            if name:
                pairs.append((name, reason))
        return pairs

    @staticmethod
    def _engines_of(params: dict[str, Any]) -> list[str]:
        """从实际发出的请求参数里还原引擎列表（重试后可能与初始计划不同）。"""
        raw = params.get("engines")
        if not raw:
            return []
        return [name.strip() for name in str(raw).split(",") if name.strip()]

    @property
    def request_timeout(self) -> float:
        """搜索请求的 HTTP 超时：比聚合上限略宽，留给网络与序列化开销。"""
        return (self.timeout_limit or 6.0) + 3.0

    # ------------------------------------------------------------------ 请求
    async def _request(
        self, params: dict[str, Any], *, retry_engines: list[str] | None = None
    ) -> tuple[dict[str, Any], list[str]]:
        """请求 SearXNG，并对瞬时错误重试一次。

        SearXNG 在引擎超时后可能重启 worker，短暂返回 502/503/504。
        重试时保持显式 `engines` 约束（只剔除仍在冷却期的引擎），而不是退回默认引擎集合。

        返回 `(响应 JSON, 本次实际使用的引擎列表)`：引擎列表要跟着实际请求走，
        否则重试后的结果会被记到错误的引擎集合上。
        """
        last_error: Exception | None = None
        current = dict(params)
        for attempt in range(2):
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
                return response.json(), self._engines_of(current)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status not in RETRYABLE_STATUS:
                    raise
                if attempt == 0:
                    current = self._retry_params(params, retry_engines)
                    logger.warning("SearXNG 返回 %s，0.4s 后重试一次", status)
                    await asyncio.sleep(0.4)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt == 0:
                    current = self._retry_params(params, retry_engines)
                    logger.warning("SearXNG 连接异常，0.4s 后重试一次: %s", exc)
                    await asyncio.sleep(0.4)
        raise last_error if last_error is not None else RuntimeError("SearXNG 请求失败")

    @staticmethod
    def _retry_params(params: dict[str, Any], retry_engines: list[str] | None) -> dict[str, Any]:
        """构造重试参数：保留显式引擎约束，只做「剔除冷却中引擎」的收紧。"""
        current = dict(params)
        if "engines" not in current:
            # 走 categories 的分支本来就没有显式列表，重试参数不变
            return current
        if not retry_engines:
            # 理论上不会到这里（select 会保证有引擎可选）；留一条明确告警的兜底路径，
            # 避免传空 engines 被 SearXNG 当成「零引擎」而稳定返回 0 条。
            logger.warning("重试时显式引擎集合为空，退回 SearXNG 默认引擎集合")
            current.pop("engines", None)
            return current
        current["engines"] = ",".join(retry_engines)
        return current

    async def health(self) -> bool:
        """通过 /healthz 判断 SearXNG 是否可用。"""
        try:
            response = await self.client.get(f"{self.base_url}/healthz", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False
"""上游并发闸门：限制同时打到 SearXNG 的聚合请求数，过载时**快速失败**。

动机（`docs/04` §4.4 实测）：并发 1-3 时 P50 ≈ 1.3s，并发 10 冷查询劣化到 ~12s；直连 SearXNG 的
独立探测显示上游聚合吞吐仅 1.3-2.0 req/s —— 瓶颈在上游聚合，不在本服务。没有闸门时，10 个请求
会同时压垮上游：上游开始返回瞬时错误，而本地 `_request()` 的「重试一次」又撞在同一批被打爆的
上游上，最坏 ≈ 5.5s × 2 ≈ 11s（正是 §4.4 那组 12s 级数字）。

设计取舍是「**宁可快速失败，不要一起慢**」：

- `limit`：同时打到上游的请求数上限（超出安全并发的部分不给上游，避免雪崩）；
- `queue_limit`：最多允许多少请求排队，队列满 → 立即拒绝；
- `max_wait`：排队等待上限，超过 → 立即拒绝（默认 ≈ 单次上游预算，等超过一个预算说明上游已过载）。

闸门只包住「上游聚合调用」这一段，不改搜索语义、融合、时效与引擎健康逻辑；并发 1 时零排队，
只增加一次计数与一次 `perf_counter`。
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型检查，避免运行时循环导入
    from ..config import Settings

# Prometheus 直方图默认桶（秒）：排队时长与上游调用时长共用一组
DEFAULT_BUCKETS: tuple[float, ...] = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)


class UpstreamOverloaded(RuntimeError):
    """上游过载：闸门队列满或排队超时。

    调用方必须把它转成「明确信号」（REST 429 + Retry-After / MCP isError），
    **不能**当成「没有搜到」吞成空结果，也不能降级到更脆弱的兜底源。
    """

    def __init__(self, reason: str, retry_after: float) -> None:
        super().__init__(f"上游搜索过载（{reason}）；请 {retry_after:.0f} 秒后重试")
        self.reason = reason
        self.retry_after = float(retry_after)


class Histogram:
    """极简 Prometheus 直方图（累计桶），不引第三方依赖。"""

    def __init__(self, buckets: tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        self.buckets = tuple(sorted(buckets))
        self.counts = [0] * len(self.buckets)  # 累计计数：value <= upper 的观测数
        self.count = 0
        self.total = 0.0

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        for index, upper in enumerate(self.buckets):
            if value <= upper:
                self.counts[index] += 1


class GateMetrics:
    """闸门指标（最小集）。"""

    def __init__(self, buckets: tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        self.rejected_total = 0
        self.rejected_by_reason: dict[str, int] = {}
        self.acquire_seconds = Histogram(buckets)  # 排队等待时长
        self.request_seconds = Histogram(buckets)  # 上游调用时长
        self.requests_total: dict[str, int] = {}  # result -> 次数

    def record_rejected(self, reason: str) -> None:
        self.rejected_total += 1
        self.rejected_by_reason[reason] = self.rejected_by_reason.get(reason, 0) + 1

    def record_request(self, seconds: float, result: str) -> None:
        self.request_seconds.observe(seconds)
        self.requests_total[result] = self.requests_total.get(result, 0) + 1


class UpstreamGate:
    """有界队列 + 等待上限的上游并发闸门。"""

    def __init__(
        self,
        *,
        limit: int = 3,
        queue_limit: int = 6,
        max_wait: float = 2.5,
        buckets: tuple[float, ...] = DEFAULT_BUCKETS,
    ) -> None:
        self.limit = max(0, int(limit))
        self.queue_limit = max(0, int(queue_limit))
        self.max_wait = max(0.0, float(max_wait))
        self.metrics = GateMetrics(buckets)
        self._active = 0
        self._waiters: deque[asyncio.Event] = deque()

    @classmethod
    def from_settings(cls, settings: "Settings") -> "UpstreamGate":
        """按配置构造闸门；`upstream_max_concurrency=0` 表示关闭闸门（但仍统计指标）。"""
        return cls(
            limit=settings.upstream_max_concurrency,
            queue_limit=settings.upstream_queue_limit,
            max_wait=settings.upstream_max_wait,
        )

    # ------------------------------------------------------------------ 状态
    @property
    def active(self) -> int:
        """当前占用槽位（正在打上游）的请求数。"""
        return self._active

    @property
    def waiting(self) -> int:
        """当前排队等待的请求数。"""
        return len(self._waiters)

    @property
    def retry_after(self) -> float:
        """过载时给客户端的 Retry-After 建议值（秒）。"""
        return max(1.0, self.max_wait)

    # ------------------------------------------------------------------ 闸门
    async def acquire(self) -> None:
        """获取一个槽位；队列满或等待超时抛 `UpstreamOverloaded`。"""
        if self.limit <= 0:  # 闸门关闭
            return
        if self._active < self.limit:
            self._active += 1
            return
        if len(self._waiters) >= self.queue_limit:
            self._reject("queue_full")

        event = asyncio.Event()
        self._waiters.append(event)
        started = time.perf_counter()
        try:
            await asyncio.wait_for(event.wait(), timeout=self.max_wait)
        except (asyncio.TimeoutError, TimeoutError):
            try:
                self._waiters.remove(event)
            except ValueError:
                # 到点的同时 release() 已把槽位转交给我们 —— 视为成功，不拒绝
                pass
            else:
                self._reject("timeout")
        # 走到这里说明拿到了槽位（release() 转交，_active 不变）
        self.metrics.acquire_seconds.observe(time.perf_counter() - started)

    async def try_acquire(self, timeout: float = 0.0) -> bool:
        """获取槽位但**不进入主源的排队额度**；拿不到返回 False。

        - `timeout=0`：纯非阻塞，拿不到立即 False，不排队、不写排队直方图；
        - `timeout>0`：有限等待 —— 先试一次，没容量最多等 `timeout` 秒；等到的计入排队直方图
          （它确实排了队），超时仍拿不到则返回 False。

        用途：给**兜底型**调用（Bing 兜底、news 的通用引擎补充）一个「有限等待」的取容量入口 ——
        它们不占用主源的排队额度，但也**不允许静默跳过**（跳过会返回空结果），所以等不到容量时
        调用方要直接 429，而不是降级返回。闸门关闭（limit<=0）时恒为 True。
        """
        if self.limit <= 0:
            return True
        if self._active < self.limit:
            self._active += 1
            return True
        if timeout <= 0:
            return False

        event = asyncio.Event()
        self._waiters.append(event)
        started = time.perf_counter()
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            try:
                self._waiters.remove(event)
            except ValueError:
                pass  # 到点同时被 release() 转交 → 视为成功
            else:
                self.metrics.acquire_seconds.observe(time.perf_counter() - started)
                return False
        self.metrics.acquire_seconds.observe(time.perf_counter() - started)
        return True

    def release(self) -> None:
        """释放槽位；若有排队者，把槽位直接转交给队首（_active 不变）。"""
        if self.limit <= 0:
            return
        while self._waiters:
            event = self._waiters.popleft()
            if not event.is_set():
                event.set()
                return
        self._active = max(0, self._active - 1)

    def _reject(self, reason: str) -> NoReturn:
        self.metrics.record_rejected(reason)
        raise UpstreamOverloaded(reason=reason, retry_after=self.retry_after)

    @asynccontextmanager
    async def slot(self):
        """只占用槽位、不记录上游时长（测试与特殊路径用）。"""
        await self.acquire()
        try:
            yield
        finally:
            self.release()

    @asynccontextmanager
    async def track(self, *, optional_wait: float | None = None):
        """占用槽位并记录「上游调用时长 + 结果」，供 `SearxngProvider` 使用。

        - `optional_wait=None`（默认）→ **主源路径**：阻塞取容量（排队优先）；
        - `optional_wait=<秒>` → **可选调用路径**：最多等这么久（`try_acquire(timeout=...)`），
          拿不到就抛 `UpstreamOverloaded(reason="no_capacity")`，不占用主源的排队额度。
        """
        if optional_wait is None:
            await self.acquire()
        elif not await self.try_acquire(timeout=optional_wait):
            # 可选调用的「没容量」：计入带标签的拒绝序列（reason=no_capacity），
            # 便于与真正返回给客户端的 429（queue_full / timeout）区分开。
            self._reject("no_capacity")
        started = time.perf_counter()
        result = "ok"
        try:
            yield
        except BaseException:
            result = "error"
            raise
        finally:
            self.release()
            self.metrics.record_request(time.perf_counter() - started, result)

    # ------------------------------------------------------------------ 指标
    def render_metrics(self) -> str:
        """渲染 Prometheus 文本格式（`text/plain; version=0.0.4`）。"""
        m = self.metrics
        lines: list[str] = []

        def emit(name: str, help_text: str, mtype: str, samples: list[str]) -> None:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
            lines.extend(samples)

        emit(
            "utf8search_upstream_active",
            "当前正在执行的上游聚合请求数",
            "gauge",
            [f"utf8search_upstream_active {self.active}"],
        )
        emit(
            "utf8search_upstream_waiting",
            "当前在上游闸门排队等待的请求数",
            "gauge",
            [f"utf8search_upstream_waiting {self.waiting}"],
        )
        # 只保留带 reason 标签的序列：无标签聚合线在 sum() 时会与带标签的重复计数。
        rejected = [
            f'utf8search_upstream_rejected_total{{reason="{reason}"}} {count}'
            for reason, count in sorted(m.rejected_by_reason.items())
        ]
        emit(
            "utf8search_upstream_rejected_total",
            "被闸门拒绝的请求数（reason=queue_full / timeout / no_capacity，按原因分标签）",
            "counter",
            rejected,
        )

        requests = [
            f'utf8search_upstream_requests_total{{result="{result}"}} {count}'
            for result, count in sorted(m.requests_total.items())
        ]
        emit("utf8search_upstream_requests_total", "实际打到上游的聚合请求数（按结果）", "counter", requests)

        for metric, hist, help_text in (
            ("utf8search_upstream_acquire_seconds", m.acquire_seconds, "在闸门排队等待的时长（秒）"),
            ("utf8search_upstream_request_seconds", m.request_seconds, "上游聚合调用的时长（秒）"),
        ):
            samples = [
                f'{metric}_bucket{{le="{upper:g}"}} {hist.counts[index]}'
                for index, upper in enumerate(hist.buckets)
            ]
            samples.append(f'{metric}_bucket{{le="+Inf"}} {hist.count}')
            samples.append(f"{metric}_sum {hist.total}")
            samples.append(f"{metric}_count {hist.count}")
            emit(metric, help_text, "histogram", samples)

        return "\n".join(lines) + "\n"

"""引擎健康度自适应（M5-5.1）：按失败原因分级冷却 + 租约式自愈。

设计取舍全部由 2026-09-24 的实测决定（数据见 `checklist.md` 第 11 节）：

1. **不追求延迟收益**。SearXNG 对处于惩罚期（suspended）的引擎是*快速失败*：
   实测单引擎探测 0.03-0.19s 返回 0 条，且 `request_count_total` 不增长（根本没往上流发请求）。
   既然不占用聚合等待时间，剔除它们就省不下时间（A/B 实测 P50 0.99s vs 0.98s）。
   本模块的价值是**让引擎集合随上游健康状态自动收敛与恢复**，避免静态名单过期带来的覆盖率损失。
2. **租约而非封杀**。每个引擎的失效态都带到期时间，到期自动回到候选集；
   任一次成功即清零失败计数。绝不永久剔除，避免「一次限流后永远少一个源」。
3. **分级退避**。CAPTCHA / access denied 这类硬封锁退避长，限流 / 超时较短；
   连续失败按指数增长并封顶，避免高频重试被上游当成滥用。
4. **覆盖率下限**。可用引擎不足时按「最早解冻优先」补足，引擎集合不会萎缩到搜不出东西。
5. **空结果不算失败**。只有 SearXNG 明确列进 `unresponsive_engines` 的引擎才计失败：
   实测 `zapmeta` / `reloado` 对纯中文长尾会返回 0 条但完全健康，把「空」当失败会误杀好引擎。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # 仅为类型标注，运行时不导入，避免 providers 反向依赖 config
    from ..config import Settings

logger = logging.getLogger(__name__)

# 失败原因分类常量（也是冷却档位名）
CLASS_CAPTCHA = "captcha"
CLASS_DENIED = "denied"
CLASS_RATE_LIMIT = "rate_limit"
CLASS_TIMEOUT = "timeout"
CLASS_OTHER = "other"

# 指数退避的最大翻倍次数：2**8 = 256 倍，足够触到 cooldown_max，同时避免指数溢出
_MAX_BACKOFF_DOUBLINGS = 8


@dataclass
class _EngineState:
    """单个引擎的健康状态（进程内、按引擎名）。"""

    consecutive_failures: int = 0
    cooldown_until: float = 0.0  # 绝对值（单调时钟），到期即重新参与
    last_reason: str = ""
    last_class: str = ""
    last_failure_at: float = 0.0
    last_success_at: float = 0.0
    successes: int = 0
    failures: int = 0

    def is_cooling(self, now: float) -> bool:
        """是否仍在冷却期内。"""
        return self.cooldown_until > now


class EngineHealthTracker:
    """维护每个引擎的滑动健康状态，并据此生成每次查询的引擎集合。"""

    def __init__(
        self,
        *,
        enabled: bool = True,
        min_active: int = 6,
        probe_slots: int = 0,
        cooldown_captcha: float = 1800.0,
        cooldown_denied: float = 900.0,
        cooldown_rate_limit: float = 180.0,
        cooldown_timeout: float = 90.0,
        cooldown_other: float = 120.0,
        cooldown_max: float = 3600.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.enabled = enabled
        # 覆盖率下限：候选里可用引擎少于该值时，补入冷却中的引擎（否则引擎集合会持续萎缩）
        self.min_active = max(1, int(min_active))
        # 主动探测名额：每次查询额外允许带入的冷却中引擎数（默认 0，只靠租约到期回归，零额外浪费）
        self.probe_slots = max(0, int(probe_slots))
        self._cooldowns: dict[str, float] = {
            CLASS_CAPTCHA: float(cooldown_captcha),
            CLASS_DENIED: float(cooldown_denied),
            CLASS_RATE_LIMIT: float(cooldown_rate_limit),
            CLASS_TIMEOUT: float(cooldown_timeout),
            CLASS_OTHER: float(cooldown_other),
        }
        self.cooldown_max = max(float(cooldown_max), 0.001)
        # 时钟可注入，便于测试用假时间验证租约到期与指数退避
        self._clock: Callable[[], float] = clock or time.monotonic
        self._states: dict[str, _EngineState] = {}

    @classmethod
    def from_settings(cls, settings: "Settings") -> "EngineHealthTracker | None":
        """按配置构造；开关关闭时返回 None，调用方据此完全跳过自适应逻辑。"""
        if not settings.engine_health_enabled:
            return None
        return cls(
            enabled=True,
            min_active=settings.engine_health_min_active,
            probe_slots=settings.engine_health_probe_slots,
            cooldown_captcha=settings.engine_health_cooldown_captcha,
            cooldown_denied=settings.engine_health_cooldown_denied,
            cooldown_rate_limit=settings.engine_health_cooldown_rate_limit,
            cooldown_timeout=settings.engine_health_cooldown_timeout,
            cooldown_other=settings.engine_health_cooldown_other,
            cooldown_max=settings.engine_health_cooldown_max,
        )

    # ------------------------------------------------------------------ 观测
    @staticmethod
    def classify(reason: str) -> str:
        """把 SearXNG 的失败原因归类到冷却档位。

        **必须同时匹配中英文**：SearXNG 用 gettext 本地化这些文案，实际返回哪种语言取决于
        请求的 `Accept-Language`（本服务的 httpx 客户端带 `zh-CN`，实测同一实例返回的是
        「暂停服务: 请求过于频繁」而不是英文的 `Suspended: too many requests`）。
        2026-09-24 实测踩到过这个坑：只写英文规则时全部落进 `other` 档，
        CAPTCHA/access denied 这类硬封锁只被冷却 120s，等于反复去撞墙。

        无法穷举所有语言，因此未命中的文案落回 `other`；连续失败的指数退避会兜住这种情况
        （120s -> 240s -> 480s ... 封顶 cooldown_max），不会退化成高频重试。
        """
        text = (reason or "").lower()
        if "captcha" in text or "验证码" in text or "驗證碼" in text:
            return CLASS_CAPTCHA
        if "access denied" in text or "forbidden" in text or "403" in text or "拒绝访问" in text:
            return CLASS_DENIED
        if (
            "too many requests" in text
            or "rate limit" in text
            or "ratelimit" in text
            or "429" in text
            or "请求过于频繁" in text
            or "请求频率" in text
            or "频率限制" in text
        ):
            return CLASS_RATE_LIMIT
        # 超时判定要排在「无原因 Suspended」之前，否则「Suspended: timeout」会被粗判成限流
        if "timeout" in text or "timed out" in text or "超时" in text:
            return CLASS_TIMEOUT
        # 不带原因的 Suspended（中英文）按限流处理：SearXNG 惩罚盒默认就是「请求过多」语义
        if "suspended" in text or "暂停服务" in text:
            return CLASS_RATE_LIMIT
        return CLASS_OTHER

    def _delay(self, klass: str, consecutive_failures: int) -> float:
        """本次冷却时长 = 档位基数 * 2^(连续失败-1)，封顶 cooldown_max。"""
        base = self._cooldowns.get(klass, self._cooldowns[CLASS_OTHER])
        doublings = min(max(int(consecutive_failures) - 1, 0), _MAX_BACKOFF_DOUBLINGS)
        return min(base * (2**doublings), self.cooldown_max)

    def observe(self, sent: Iterable[str], unresponsive: Iterable[tuple[str, str]]) -> None:
        """记录一次查询的结果。

        - `sent`：本次显式传给 SearXNG 的引擎列表（「请求过且没报不可用」才算成功）；
        - `unresponsive`：(引擎名, 原因) 列表，来自响应的 `unresponsive_engines`。

        未被显式请求时（走 `categories` 分支）不判成功，但失败的引擎照样记：
        失败信息本身是真实的，没有理由丢弃。
        """
        now = self._clock()
        failed: dict[str, str] = {}
        for name, reason in unresponsive:
            if name:
                failed[name] = reason or ""
        sent_list = [name for name in sent if name]
        sent_set = set(sent_list)

        for name in sent_list:
            if name in failed:
                self._record_failure(name, failed[name], now)
            else:
                self._record_success(name, now)
        for name, reason in failed.items():
            if name not in sent_set:
                self._record_failure(name, reason, now)

    def _record_failure(self, name: str, reason: str, now: float) -> None:
        """记录一次失败：累加连续失败、按原因分级设置冷却（指数退避）。"""
        state = self._states.setdefault(name, _EngineState())
        previous_class = state.last_class
        state.consecutive_failures += 1
        state.failures += 1
        state.last_reason = reason
        state.last_class = self.classify(reason)
        state.last_failure_at = now
        delay = self._delay(state.last_class, state.consecutive_failures)
        state.cooldown_until = now + delay

        if state.consecutive_failures == 1:
            logger.info("引擎 %s 进入冷却 %.0fs（原因：%s）", name, delay, reason or "未提供")
        elif state.last_class != previous_class:
            logger.info(
                "引擎 %s 失败原因变为 %s，冷却延长至 %.0fs（原因：%s）",
                name,
                state.last_class,
                delay,
                reason or "未提供",
            )
        else:
            logger.debug("引擎 %s 连续第 %d 次失败，冷却 %.0fs", name, state.consecutive_failures, delay)

    def _record_success(self, name: str, now: float) -> None:
        """记录一次成功：解除冷却并清零连续失败（自愈）。"""
        state = self._states.get(name)
        if state is None:
            self._states[name] = _EngineState(successes=1, last_success_at=now)
            return
        if state.consecutive_failures:
            logger.info("引擎 %s 已恢复（此前连续失败 %d 次）", name, state.consecutive_failures)
        state.consecutive_failures = 0
        state.cooldown_until = 0.0
        state.last_reason = ""
        state.last_class = ""
        state.successes += 1
        state.last_success_at = now

    # ------------------------------------------------------------------ 选路
    def select(
        self, candidates: list[str], *, now: float | None = None, probe_slots: int | None = None
    ) -> list[str]:
        """生成本次查询要用的引擎集合。

        - 未冷却的引擎**全部保留**，并保持候选顺序（引擎顺序实测不影响延迟，
          保持原序只是为了让行为可预测、便于复现）；
        - 冷却中的引擎按「最早解冻优先」补足到 `min_active`，保证覆盖率不被击穿；
        - 额外允许 `probe_slots` 个冷却引擎参与，用于主动发现恢复（默认 0）。
        """
        if not candidates:
            return []
        if not self.enabled:
            return list(candidates)
        now = self._clock() if now is None else now
        slots_limit = self.probe_slots if probe_slots is None else max(0, int(probe_slots))

        healthy: list[str] = []
        cooling: list[tuple[float, str]] = []
        for name in candidates:
            state = self._states.get(name)
            if state is not None and state.is_cooling(now):
                cooling.append((state.cooldown_until, name))
            else:
                healthy.append(name)

        # 最早解冻的排前面：它们最可能已经恢复
        cooling.sort()
        needed = max(0, self.min_active - len(healthy))
        slots = min(len(cooling), max(needed, slots_limit))
        if slots <= 0:
            return healthy
        chosen = set(healthy) | {name for _, name in cooling[:slots]}
        # 按候选原顺序输出，保证健康引擎的相对顺序与传入一致
        return [name for name in candidates if name in chosen]

    # ------------------------------------------------------------------ 可观测
    def snapshot(
        self, *, now: float | None = None, candidates: Iterable[str] | None = None
    ) -> dict[str, Any]:
        """引擎健康快照，供 `/health` 与日志使用（只列冷却中的，避免刷屏）。"""
        now = self._clock() if now is None else now
        cooling = [
            {
                "engine": name,
                "reason": state.last_reason,
                "class": state.last_class,
                "retry_after": round(max(0.0, state.cooldown_until - now), 1),
                "consecutive_failures": state.consecutive_failures,
            }
            for name, state in self._states.items()
            if state.is_cooling(now)
        ]
        cooling.sort(key=lambda item: item["retry_after"])
        payload: dict[str, Any] = {
            "enabled": self.enabled,
            "tracked": len(self._states),
            "cooling": cooling,
        }
        if candidates is not None:
            names = list(candidates)
            payload["active"] = self.select(names, now=now)
        return payload
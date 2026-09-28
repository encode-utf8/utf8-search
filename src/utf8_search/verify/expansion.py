"""查询扩展（M6 阶段 1）的测量与判定逻辑：**纯函数 + 最小指标集**。

阶段 1 只做**埋点测量**，不增加任何上游调用：在每次搜索已经拿到候选与最终结果之后，记录

- 主源候选数（`candidates`）与目标候选池（`target`）；
- 查询词覆盖率（`coverage_mean`）——**分母固定为用户原始查询词**（扩展/改写词不参与计算）；
- 独立站点数（`distinct_hosts`）；
- 是否命中「候选不足」判据（`expansion_needed` 的返回值）。

阈值**由分布选点**（用户 2026-09-28 拍板），所以这里只提供带参数的纯函数，不在代码里写死数字；
具体取哪个门槛由阶段 1 的分布报告决定（见 `docs/reports/m5-6-query-expansion-plan-20260928.md` §0.1/§7）。
"""

from __future__ import annotations

from ..core.upstream_gate import Histogram, render_histogram

# 直方图分桶：按「候选数 / 目标 / 覆盖率 / 独立站点数」的实际量纲选，便于报告里直接视觉读分布
CANDIDATE_BUCKETS: tuple[float, ...] = (0, 4, 8, 12, 16, 24, 32, 48)
TARGET_BUCKETS: tuple[float, ...] = (0, 5, 12, 24, 30)
COVERAGE_BUCKETS: tuple[float, ...] = (0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
HOST_BUCKETS: tuple[float, ...] = (0, 1, 2, 3, 4, 5, 8)


def expansion_needed(
    candidates: int,
    target: int,
    coverage_mean: float | None = None,
    *,
    min_coverage: float | None = None,
) -> str | None:
    """这次查询是否命中「候选不足」判据；命中返回原因字符串，不命中返回 `None`。

    判据（阈值全部由调用方给，阶段 1 不写死）：

    - **占位判据 = 5.2 的原始口径**：`candidates < target` → `"candidates"`
      （target 就是本次向主源索取的候选池目标值，见 `SearchPipeline._candidate_target`）；
    - **可选补充判据**：给了 `min_coverage` 且覆盖率低于它 → `"coverage"`
      （覆盖率分母固定为**用户原始查询词**）；
    - 两者同时命中 → `"candidates,coverage"`；两者都不命中 → `None`。
    """
    reasons: list[str] = []
    if target > 0 and candidates < target:
        reasons.append("candidates")
    if min_coverage is not None and coverage_mean is not None and coverage_mean < min_coverage:
        reasons.append("coverage")
    return ",".join(reasons) or None


class ExpansionMetrics:
    """查询扩展的埋点指标（阶段 1：只记录，不改变任何行为）。"""

    def __init__(self) -> None:
        self.candidates = Histogram(CANDIDATE_BUCKETS)
        self.targets = Histogram(TARGET_BUCKETS)
        self.coverage = Histogram(COVERAGE_BUCKETS)
        self.distinct_hosts = Histogram(HOST_BUCKETS)
        self.samples = 0
        self.trigger_total = 0
        self.trigger_by_reason: dict[str, int] = {}

    def observe(
        self,
        *,
        candidates: int,
        target: int,
        coverage_mean: float | None,
        distinct_hosts: int,
        reason: str | None,
    ) -> None:
        self.samples += 1
        self.candidates.observe(float(candidates))
        self.targets.observe(float(target))
        if coverage_mean is not None:
            self.coverage.observe(float(coverage_mean))
        self.distinct_hosts.observe(float(distinct_hosts))
        if reason:
            self.trigger_total += 1
            for name in reason.split(","):
                self.trigger_by_reason[name] = self.trigger_by_reason.get(name, 0) + 1

    def render(self) -> str:
        """渲染成 Prometheus 文本（与闸门指标同风格，供 `/metrics` 追加输出）。"""
        lines: list[str] = []

        def emit(name: str, help_text: str, mtype: str, samples: list[str]) -> None:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
            lines.extend(samples)

        emit(
            "utf8search_expansion_samples_total",
            "已测量（未扩展）的查询数",
            "counter",
            [f"utf8search_expansion_samples_total {self.samples}"],
        )
        for metric, hist, help_text in (
            ("utf8search_expansion_candidates", self.candidates, "主源返回的候选数（扩展埋点）"),
            ("utf8search_expansion_target", self.targets, "本次向主源索取的候选池目标值"),
            ("utf8search_expansion_coverage", self.coverage, "查询词覆盖率（分母=用户原始查询词）"),
            ("utf8search_expansion_distinct_hosts", self.distinct_hosts, "最终结果的独立站点数"),
        ):
            emit(metric, help_text, "histogram", render_histogram(metric, hist))
        trigger_samples = [
            f'utf8search_expansion_trigger_total{{reason="{name}"}} {count}'
            for name, count in sorted(self.trigger_by_reason.items())
        ]
        emit(
            "utf8search_expansion_trigger_total",
            "命中「候选不足」判据的次数（占位判据：候选数 < 目标候选池；按原因分标签）",
            "counter",
            trigger_samples,
        )
        return "\n".join(lines) + "\n"

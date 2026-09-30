"""日期可信度判定（纯函数，供探针与单测复用）。

背景（2026-09-30）：news 时效门槛曾被「假绿」骗过 —— `yandex` 会把**索引日期**当成发布日期上报
（实测 2017 年的《天津2017年新能源汽车地补政策发布》被标成 `2026-09-29`），
于是"7 日内比例"看着很漂亮，内容却是几年前的旧文 + 成人短剧/垃圾站。

这里把「上报日期 vs 内容里的时间线索」做成可自动化的判据：

* `year_clues()`：从标题 / 摘要 / URL 里抽 4 位年份；
* `classify_date_trust()`：按「年份冲突比例」「同日扎堆」给引擎定性：
  - `可信`：有 ≥5 条带日期，年份冲突 ≤20%，且没有同日扎堆；
  - `仅索引日期`：年份冲突 ≥50%，或出现 ≥5 条**同一天**的"日期"（典型的抓取/索引日期）；
  - `无日期`：带日期的样本不足 5 条；
  - `待人工确认`：介于两者之间。
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

YEAR_RE = re.compile(r"(?:19|20)\d{2}")

DATE_TRUST_TRUSTED = "可信"
DATE_TRUST_INDEX_ONLY = "仅索引日期"
DATE_TRUST_NO_DATE = "无日期（样本不足）"
DATE_TRUST_UNKNOWN = "待人工确认"

MIN_DATED_SAMPLES = 5
SAME_DAY_CLUSTER = 5


def year_clues(*texts: str | None) -> set[int]:
    """从任意文本里抽出 4 位年份（1900-2099）。"""
    clues: set[int] = set()
    for text in texts:
        if not text:
            continue
        for match in YEAR_RE.findall(str(text)):
            clues.add(int(match))
    return clues


@dataclass
class DateTrustStats:
    """单个引擎的日期可信度统计。"""

    total: int = 0
    dated: int = 0
    year_conflict: int = 0
    same_day_max: int = 0
    detail: list[dict[str, object]] | None = None

    @property
    def conflict_ratio(self) -> float:
        return self.year_conflict / self.dated if self.dated else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "dated": self.dated,
            "year_conflict": self.year_conflict,
            "conflict_ratio": round(self.conflict_ratio, 3),
            "same_day_max": self.same_day_max,
            "detail": self.detail or [],
        }


def classify_date_trust(items: list[dict[str, object]]) -> tuple[str, DateTrustStats]:
    """按「上报日期 vs 内容年份线索」判定一个引擎的日期可信度。

    `items` 每项至少包含 `date`（ISO 字符串或 None）与 `text`（标题+摘要+URL 拼成的文本）。
    年份冲突的定义：**上报日期的年份比内容里出现的最大年份还新**（内容提到 2017、却上报 2026）。
    只看"更新"这一方向，因为索引日期污染永远表现为"上报得更新"。
    """
    stats = DateTrustStats(detail=[])
    days: Counter[str] = Counter()
    for item in items:
        stats.total += 1
        raw_date = item.get("date")
        text = str(item.get("text") or "")
        if not raw_date:
            continue
        stats.dated += 1
        day = str(raw_date)[:10]
        days[day] += 1
        reported_year = int(str(raw_date)[:4]) if str(raw_date)[:4].isdigit() else None
        clues = year_clues(text)
        conflict = bool(reported_year and clues and max(clues) < reported_year)
        if conflict:
            stats.year_conflict += 1
        stats.detail.append({
            "url": item.get("url"),
            "title": str(item.get("title") or "")[:80],
            "reported_date": str(raw_date)[:10],
            "content_years": sorted(clues),
            "year_conflict": conflict,
        })
    stats.same_day_max = max(days.values()) if days else 0

    if stats.dated < MIN_DATED_SAMPLES:
        verdict = DATE_TRUST_NO_DATE
    elif stats.conflict_ratio >= 0.5 or stats.same_day_max >= SAME_DAY_CLUSTER:
        verdict = DATE_TRUST_INDEX_ONLY
    elif stats.conflict_ratio <= 0.2:
        verdict = DATE_TRUST_TRUSTED
    else:
        verdict = DATE_TRUST_UNKNOWN
    return verdict, stats

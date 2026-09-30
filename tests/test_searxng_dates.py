"""日期可信度判定的纯函数测试（2026-09-30「假绿」加固）。"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from searxng_dates import (  # noqa: E402
    DATE_TRUST_INDEX_ONLY,
    DATE_TRUST_NO_DATE,
    DATE_TRUST_TRUSTED,
    classify_date_trust,
    year_clues,
)


def _item(day: str | None, text: str = "") -> dict[str, object]:
    return {"date": day, "text": text, "url": "https://example.com/x", "title": text[:40]}


def test_year_clues_extracts_years() -> None:
    assert year_clues("天津2017年新能源汽车地补政策", "https://x.com/2026/09/a") == {2017, 2026}
    assert year_clues(None, "") == set()


def test_trusted_when_dates_match_content() -> None:
    # 注意日期要**分散**：同一天扎堆 ≥5 条本身就会被判「索引日期」嫌疑
    items = [
        _item(f"2026-09-2{day}T10:00:00", f"2026年9月 台风最新路径 第{day}条") for day in range(1, 7)
    ]
    verdict, stats = classify_date_trust(items)
    assert verdict == DATE_TRUST_TRUSTED
    assert stats.dated == 6 and stats.year_conflict == 0


def test_index_only_when_same_day_cluster_and_year_conflict() -> None:
    """yandex 的典型形态：全是同一天 + 内容年份明显更早（2017 年旧文被标成当天）。"""
    items = [_item("2026-09-29T00:00:00", f"天津2017年新能源汽车地补政策发布 第{i}条") for i in range(5)]
    items += [_item("2026-09-29T00:00:00", "2026年9月 其它新闻")]
    verdict, stats = classify_date_trust(items)
    assert verdict == DATE_TRUST_INDEX_ONLY
    assert stats.same_day_max == 6
    assert stats.year_conflict == 5
    assert stats.conflict_ratio > 0.8


def test_no_date_when_too_few_dated_samples() -> None:
    items = [_item(None, "无日期结果") for _ in range(20)]
    items += [_item("2026-09-29T00:00:00", "只有一条带日期")]
    verdict, stats = classify_date_trust(items)
    assert verdict == DATE_TRUST_NO_DATE
    assert stats.total == 21 and stats.dated == 1

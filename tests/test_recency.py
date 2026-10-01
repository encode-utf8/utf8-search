"""时效性逻辑单元测试（对应验收项 5.2-3 / 5.2-4 / 5.2-5）。

全部离线：不依赖网络、不依赖 SearXNG。
"""

from __future__ import annotations

from datetime import datetime, timezone

from utf8_search.models import SearchResult
from utf8_search.rank.recency import (
    FRESH,
    STALE,
    UNDATED,
    age_days,
    apply_recency,
    date_from_url,
    freshness_rank,
    mark_stale_by_title_year,
    parse_published,
    timing_stats,
    year_from_title,
)

NOW = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)


def _result(title: str, published: str | None) -> SearchResult:
    return SearchResult(title=title, url=f"https://example.com/{title}", published_date=published)


# ---------------------------------------------------------------- 日期解析
def test_parse_iso_with_timezone() -> None:
    parsed = parse_published("2026-09-23T13:36:00+08:00")
    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 8 * 3600
    assert parsed.year == 2026 and parsed.month == 9 and parsed.day == 23


def test_parse_iso_utc_markers() -> None:
    """`Z` 结尾与显式 +00:00 都要能解析。"""
    assert parse_published("2026-09-23T13:36:00Z") == datetime(2026, 9, 23, 13, 36, tzinfo=timezone.utc)
    assert parse_published("2026-09-23T13:36:00+00:00") == datetime(2026, 9, 23, 13, 36, tzinfo=timezone.utc)


def test_parse_plain_and_localized_dates() -> None:
    assert parse_published("2026-09-23") == datetime(2026, 9, 23, tzinfo=timezone.utc)
    assert parse_published("2026/09/23") == datetime(2026, 9, 23, tzinfo=timezone.utc)
    assert parse_published("2026年9月23日") == datetime(2026, 9, 23, tzinfo=timezone.utc)
    assert parse_published("23 Sep 2026") == datetime(2026, 9, 23, tzinfo=timezone.utc)


def test_parse_unix_timestamps() -> None:
    """秒与毫秒时间戳都要支持（部分引擎直接给数字）。"""
    seconds = int(datetime(2026, 9, 23, tzinfo=timezone.utc).timestamp())
    assert parse_published(str(seconds)).date() == datetime(2026, 9, 23).date()
    assert parse_published(str(seconds * 1000)).date() == datetime(2026, 9, 23).date()


def test_parse_invalid_returns_none() -> None:
    """空值、乱码、非法日期一律安全返回 None，绝不抛异常。"""
    for value in (None, "", "   ", "unknown", "2026-13-45", "昨天", "0"):
        assert parse_published(value) is None


# ---------------------------------------------------------------- 年龄与分层
def test_age_days() -> None:
    assert age_days("2026-09-23T12:00:00Z", now=NOW) == 1.0
    assert age_days(None, now=NOW) is None
    assert age_days("not a date", now=NOW) is None


def test_age_days_future_is_negative() -> None:
    """未来日期返回负数（免费源偶有轻微超前），调用方按新鲜处理。"""
    assert age_days("2026-09-25T12:00:00Z", now=NOW) < 0


def test_freshness_rank() -> None:
    assert freshness_rank("2026-09-23T12:00:00Z", fresh_days=7, now=NOW) == FRESH
    assert freshness_rank("2026-01-01T00:00:00Z", fresh_days=7, now=NOW) == STALE
    assert freshness_rank(None, fresh_days=7, now=NOW) == UNDATED


# ---------------------------------------------------------------- 重排与过滤
def test_apply_recency_orders_fresh_before_stale_and_undated() -> None:
    results = [_result("old", "2021-01-01"), _result("fresh", "2026-09-23T10:00:00Z"), _result("none", None)]
    ordered = apply_recency(results, fresh_days=7, max_results=1, now=NOW, drop_stale=False)
    assert [r.title for r in ordered] == ["fresh", "old", "none"]


def test_apply_recency_is_stable_within_tier() -> None:
    """同一层内必须保持上游的相关性顺序，不能被时间排序打乱。"""
    results = [
        _result("a", "2026-09-23T10:00:00Z"),
        _result("b", "2026-09-24T10:00:00Z"),
        _result("c", "2026-09-22T10:00:00Z"),
    ]
    ordered = apply_recency(results, fresh_days=7, max_results=3, now=NOW)
    assert [r.title for r in ordered] == ["a", "b", "c"]


def test_apply_recency_drops_stale_when_enough_results() -> None:
    """新鲜/无日期结果够 max_results 时，直接丢弃已知过期结果。"""
    results = [
        _result("old", "2021-01-01"),
        _result("fresh1", "2026-09-23T10:00:00Z"),
        _result("fresh2", "2026-09-22T10:00:00Z"),
    ]
    ordered = apply_recency(results, fresh_days=7, max_results=2, now=NOW)
    assert [r.title for r in ordered] == ["fresh1", "fresh2"]


def test_apply_recency_keeps_stale_when_not_enough_results() -> None:
    """非过期结果不够时保留过期结果，宁可给旧闻也不返回空。"""
    results = [_result("old", "2021-01-01"), _result("fresh", "2026-09-23T10:00:00Z")]
    ordered = apply_recency(results, fresh_days=7, max_results=5, now=NOW)
    assert [r.title for r in ordered] == ["fresh", "old"]


def test_apply_recency_can_be_disabled() -> None:
    results = [_result("old", "2021-01-01"), _result("fresh", "2026-09-23T10:00:00Z")]
    ordered = apply_recency(results, fresh_days=7, max_results=1, now=NOW, drop_stale=False)
    assert len(ordered) == 2


def test_apply_recency_handles_empty() -> None:
    assert apply_recency([], fresh_days=7, max_results=5, now=NOW) == []


# ---------------------------------------------------------------- 统计
def test_timing_stats() -> None:
    results = [
        _result("f1", "2026-09-23T10:00:00Z"),
        _result("f2", "2026-09-24T10:00:00Z"),
        _result("s1", "2021-01-01"),
        _result("u1", None),
    ]
    stats = timing_stats(results, fresh_days=7, now=NOW)
    assert stats["total"] == 4
    assert stats["fresh"] == 2
    assert stats["stale"] == 1
    assert stats["undated"] == 1
    assert stats["dated"] == 3
    assert stats["fresh_ratio"] == 0.5


def test_timing_stats_empty() -> None:
    stats = timing_stats([], fresh_days=7, now=NOW)
    assert stats["total"] == 0
    assert stats["fresh_ratio"] == 0.0

# ---------------------------------------------------------------- URL 内嵌日期
def test_date_from_url_common_news_layouts() -> None:
    """新闻站把日期写进路径的几种常见写法都要能认出来。"""
    cases = {
        "https://mv.china-embassy.gov.cn/fyrth/202609/t20260922_12028748.htm": "2026-09-22",
        "https://news.cctv.com/2026/08/01/ARTIJyn04nsrlL2LyT0ZDhTd260801.shtml": "2026-08-01",
        "https://finance.sina.cn/2026-09-22/detail-inissyqx6846162.d.html?vt=4": "2026-09-22",
        "https://finance.eastmoney.com/a/202608033829764288.html": "2026-08-03",
        "https://epaper.qingdaonews.com/qdzb/resfile/2026-01-16/A07/a.pdf": "2026-01-16",
    }
    for url, expected in cases.items():
        assert date_from_url(url) == expected, url


def test_date_from_url_rejects_long_ids_and_bad_values() -> None:
    """长数字 ID / 不存在的日期不能误判成发布日期（否则会把旧闻顶到最前）。"""
    for url in (
        "https://www.52hrtt.com/sa/n/w/info/G1786949196102",
        "https://k.sina.com.cn/article_7879848900_1d5acf3c401902vvc6.html",
        "https://www.toutiao.com/article/7604391218893554214/",
        "http://www.mod.gov.cn/gfbw/qwfb/16486340.html",
        "https://www.cls.cn/detail/2490170",
        "https://auto.news18a.com/news/storys_225921.html",
        "https://example.com/99999999/",
    ):
        assert date_from_url(url) is None, url


def test_date_from_url_only_accepts_full_dates() -> None:
    """只有年月（如 /202510/）时保守返回 None：月份粒度会把日期估错。"""
    assert date_from_url("http://beijing.chinatax.gov.cn/bjswj/c104539/202510/8798cfc2") is None
    assert date_from_url(None) is None
    assert date_from_url("") is None

# ---------------------------------------------------------------- 标题年份陈旧信号（M5-5.3）
def test_year_from_title() -> None:
    """标题里的「YYYY年」要能取到；没有年份、或年份藏在长数字里则取不到。"""
    assert year_from_title("【台风康森】2021年第13号康森台风最新消息-天气网") == 2021
    assert year_from_title("2026年9月 国内外重大新闻") == 2026
    assert year_from_title("无年份的标题") is None
    assert year_from_title("iPhone 17 Pro 价格 参数") is None
    assert year_from_title("工单号 120210930 的处理结果") is None
    assert year_from_title("") is None


def test_mark_stale_by_title_year_rules() -> None:
    """只标记「严格早于今年」且没有日期的结果：同年不标记、已有日期不覆盖。"""
    old = _result("2021年第13号康森台风最新消息", None)
    same_year = _result("2026年9月时事汇总", None)
    dated = _result("2021年旧闻但有权威日期", "2026-09-23")
    future = _result("2030年远景规划", None)

    marked = mark_stale_by_title_year([old, same_year, dated, future], now=NOW)

    assert marked == 1
    assert old.published_date == "2021-07-01"
    assert same_year.published_date is None
    assert dated.published_date == "2026-09-23"
    assert future.published_date is None


def test_apply_recency_stale_last_moves_stale_after_undated() -> None:
    """stale_last=True（通用主题时效意图）：新鲜 > 无日期 > 已知过期。"""
    fresh = _result("fresh", "2026-09-23T12:00:00Z")
    stale = _result("stale", "2021-07-01")
    undated = _result("undated", None)

    ordered = apply_recency(
        [stale, undated, fresh], fresh_days=7, now=NOW, drop_stale=False, stale_last=True
    )
    assert [r.title for r in ordered] == ["fresh", "undated", "stale"]


def test_apply_recency_default_keeps_stale_before_undated() -> None:
    """默认口径（5.2 新闻主题）保持「新鲜 > 过期 > 无日期」，不被 5.3 改动影响。"""
    fresh = _result("fresh", "2026-09-23T12:00:00Z")
    stale = _result("stale", "2021-07-01")
    undated = _result("undated", None)

    ordered = apply_recency([stale, undated, fresh], fresh_days=7, now=NOW, drop_stale=False)
    assert [r.title for r in ordered] == ["fresh", "stale", "undated"]
def test_recency_intent_covers_english_time_words() -> None:
    """P5（2026-09-30）：英文侧时新意图与中文对齐（latest / update / recent / last week…）。"""
    from utf8_search.rank.recency import has_recency_intent

    for query in (
        "children privacy law COPPA update",
        "latest news semiconductor export controls",
        "recent AI regulation changes",
        "OpenAI latest news",
        "what happened last week in tech",
    ):
        assert has_recency_intent(query) is True, query
    # 反例：不含时间意图的查询不应被误判（避免把普通查询也硬过滤旧结果）
    for query in ("how does HTTP/3 QUIC work", "Rust async runtime tokio 原理", "iPhone 17 Pro 价格 参数"):
        assert has_recency_intent(query) is False, query

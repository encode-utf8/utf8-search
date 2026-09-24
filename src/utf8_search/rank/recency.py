"""时效性处理：发布日期解析、年龄计算、新闻结果的时效重排与过期过滤。

用途（对应 M5-5.2 时效性增强）：`topic=news` 时，各免费引擎给出的 `publishedDate`
格式五花八门、且经常缺失。本模块负责把它们统一解析成时间点，再让「新鲜」的结果排到前面、
把「已知过期」的结果剔除，避免 LLM 读到几年前的旧闻（验收 2-9 就在「台风路径」上踩过这个坑）。

设计要点：
- 日期一律按 UTC 归一到 `datetime`，无时区信息时视为 UTC（免费源基本都给 UTC）；
- 分层排序而不是纯时间排序：同层内保持上游（RRF + BM25）给出的相关性顺序，
  避免「只按时间排」把不切题的新闻顶到前面；
- 解析失败/缺失一律归为「无日期」层，不是「过期」层——未知不等于陈旧。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from ..models import SearchResult

# 常见日期格式（SearXNG 各引擎的 publishedDate 实测出现过这些形态）
_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %b %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%Y年%m月%d日",
)

# 新鲜度分层：数字越小越优先
FRESH = 0
STALE = 1
UNDATED = 2

# 时间戳下限（2000-01-01 UTC）：早于它的数字视为占位值而不是真实日期
_MIN_TIMESTAMP = 946_684_800

# 兜底正则：从「2026-09-23T13:36:00+08:00」这类字符串里抓出日期
_DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# URL 里内嵌的日期：新闻站（尤其是政府和门户站）经常只把日期写在路径里，
# 例如 `/202609/t20260922_12028748.htm`、`/2026/08/01/ARTI...`、`/2026-09-22/detail-xxx`。
# 从 URL 取日期是零网络开销的，优先于抓页面回补，能省掉大量抓取。
_URL_DELIMITED_DATE = re.compile(r"(?<!\d)(\d{4})[-_/](\d{2})[-_/](\d{2})")
_URL_COMPACT_DATE = re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})")

# 可接受的年份范围：下限防「ID 里凑出 1970」，上限防「未来日期」把旧闻顶到最前
_URL_YEAR_MIN = 2000
_URL_YEAR_MAX = 2100


def parse_published(value: str | None) -> datetime | None:
    """把发布日期字符串解析成带时区的 datetime；无法识别返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # 纯数字：Unix 时间戳（秒或毫秒）。下限取 2000-01-01：
    # 免费源偶尔返回 "0" 之类的占位值，直接当 1970 年会把结果误判成「过期」。
    if text.isdigit():
        seconds = int(text)
        if seconds > 10_000_000_000:  # 13 位按毫秒处理
            seconds //= 1000
        if seconds < _MIN_TIMESTAMP:
            return None
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    match = _DATE_PREFIX.match(text)
    if match:
        try:
            return datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc
            )
        except ValueError:
            return None
    return None


def _valid_ymd(year: int, month: int, day: int) -> bool:
    """校验三元组是不是一个真实存在的日期（并限制在合理年份区间内）。"""
    if not (_URL_YEAR_MIN <= year <= _URL_YEAR_MAX):
        return False
    try:
        datetime(year, month, day)
    except ValueError:
        return False
    return True


def date_from_url(url: str | None) -> str | None:
    """从 URL 路径里提取发布日期，返回 `YYYY-MM-DD`；提取不到返回 None。

    很多新闻站把日期编码进路径（`/2026/09/22/`、`/202609/t20260922_`、`/2026-09-22/`），
    但页面上并不声明日期，靠抓页面拿不到。这里用正则直接读 URL，零网络开销，
    是 `topic=news` 时效性最划算的一步。

    两道校验防止把长 ID 误读成日期：
    1. 数字串必须以非数字为界（`(?<!\d) ... (?<=\d)`），避免在长数字里截取；
    2. 年/月/日必须构成真实日期，且年份落在 2000-2100（实测能过滤掉绝大多数雪花 ID）。

    带分隔符的写法优先于紧凑写法：`-`/`/`/`_` 是明确的日期分隔符，
    而紧凑写法容易在 ID 里误匹配。
    """
    if not url:
        return None
    for pattern in (_URL_DELIMITED_DATE, _URL_COMPACT_DATE):
        for match in pattern.finditer(url):
            year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if _valid_ymd(year, month, day):
                return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def age_days(published: str | None, *, now: datetime | None = None) -> float | None:
    """返回发布日期距「现在」的天数；无日期或无法解析返回 None。

    负数表示日期在未来（免费源偶有轻微超前），调用方按「新鲜」处理即可。
    """
    parsed = parse_published(published)
    if parsed is None:
        return None
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return (reference - parsed).total_seconds() / 86400


def freshness_rank(published: str | None, *, fresh_days: int, now: datetime | None = None) -> int:
    """新鲜度分层：FRESH / STALE / UNDATED。"""
    days = age_days(published, now=now)
    if days is None:
        return UNDATED
    return FRESH if days <= fresh_days else STALE


def apply_recency(
    results: list[SearchResult],
    *,
    fresh_days: int = 7,
    max_results: int = 5,
    now: datetime | None = None,
    drop_stale: bool = True,
    drop_after_days: int | None = None,
) -> list[SearchResult]:
    """按新鲜度重排新闻结果，必要时丢弃已知过旧的结果。

    两个窗口是分开的，这是实测驱动的重要设计：

    - `fresh_days`：**排序**窗口。≤ 该天数的结果排最前（用户说 `time_range=day` 时就是 1 天）。
    - `drop_after_days`：**丢弃**阈值，默认等于 `fresh_days`。为什么不共用？
      因为免费源根本给不出足够多的「当天」结果，若拿 1 天当丢弃阈值，会把 2-7 天的近期新闻
      丢掉、再拿「无日期」的结果补位，实测反而把时效性从 20% 拉到 0%。
      所以调用方通常传一个更宽的丢弃阈值（如 7 天）。

    排序为分层稳定排序：新鲜 > 过期 > 无日期，同层保持传入顺序（即原有相关性顺序）。
    只有在「保留结果已够 max_results」时才执行丢弃，宁可给旧闻也不返回空结果。
    """
    if not results:
        return results

    threshold = fresh_days if drop_after_days is None else drop_after_days

    def rank_of(result: SearchResult) -> int:
        return freshness_rank(result.published_date, fresh_days=fresh_days, now=now)

    def too_old(result: SearchResult) -> bool:
        """只把「有日期且超过丢弃阈值」的结果视为过旧；无日期不算（未知不等于陈旧）。"""
        days = age_days(result.published_date, now=now)
        return days is not None and days > threshold

    ordered = sorted(results, key=rank_of)
    if not drop_stale:
        return ordered

    kept = [result for result in ordered if not too_old(result)]
    return kept if len(kept) >= max_results else ordered


def timing_stats(
    results: list[SearchResult], *, fresh_days: int = 7, now: datetime | None = None
) -> dict[str, float]:
    """统计结果的日期覆盖情况，供验收脚本量化（对应 5.2-7）。"""
    total = len(results)
    fresh = 0
    stale = 0
    undated = 0
    for result in results:
        rank = freshness_rank(result.published_date, fresh_days=fresh_days, now=now)
        if rank == FRESH:
            fresh += 1
        elif rank == STALE:
            stale += 1
        else:
            undated += 1
    return {
        "total": total,
        "fresh": fresh,
        "stale": stale,
        "undated": undated,
        "dated": fresh + stale,
        "fresh_ratio": (fresh / total) if total else 0.0,
    }
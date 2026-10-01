"""规格 token 匹配（2026-09-30，治 2-9 的 Q6/Q16 缺陷类）。

2-9 抽检暴露的两类失败，词面覆盖率都看不出来：

* **Q6**：查询 `Python 3.13 新特性` 却返回 `3.14` 的文章（词元 `Python`/`新特性` 都在，版本号错了）；
* **Q16**：查询 `iPhone 17 Pro 价格 参数` 却返回 `iPhone 8` 的京东参数页（`iPhone` 命中、型号完全不符）。

所以这里把「**规格 token**」单独抽出来做匹配：数字 / 版本号（3.13）/ 型号修饰词（Pro/Max/…）/
「品牌+数字」短语（RTX 5090）。匹配分三档：**完全 / 部分 / 不匹配**；
没有规格 token 的查询（如「最近一周 AI 行业动态」「2026年 新能源汽车 补贴政策」）返回空列表，
调用方必须保持原有行为不变。

刻意排除「年份 / 日期」类数字（2026、2026年、9月、9月30日）：
它们不是规格，按规格去要求命中会把大量正常结果误判成不匹配。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 版本号（含点）：3.13 / 2.0.1
_VERSION_RE = re.compile(r"(?<![\d.])(\d+\.\d+(?:\.\d+)*)(?![\d.])")
# 品牌+数字短语：RTX 5090（允许空格或连字符；品牌必须在数字紧邻之前）
_BRAND_NUM_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2,8})[\s-]?(\d{2,5})(?![A-Za-z0-9])")
# 连写型号：S4000 / MTT-S4000 / S90（字母数字连写）
_ATTACHED_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{1,8}\d{2,6})(?![A-Za-z0-9])")
# 独立数字（1-5 位，排除紧邻小数点的情况）
_NUMBER_RE = re.compile(r"(?<![\d.])(\d{1,5})(?![\d.])")
# 型号修饰词：iPhone 17 **Pro** / Pro Max / Plus / mini …
_MODIFIER_RE = re.compile(r"(?<![a-z0-9])(pro|max|plus|mini|ultra|air|se)(?![a-z0-9])", re.IGNORECASE)
# 日期表达：2026年 / 9月 / 30日 / 9号 —— 这些数字不算规格
_DATE_SUFFIX = ("年", "月", "日", "号")


def _is_year(text: str) -> bool:
    return len(text) == 4 and text.isdigit() and 1900 <= int(text) <= 2099


def _is_date_number(query: str, start: int, end: int) -> bool:
    """数字后面紧跟 年/月/日/号 时按日期处理（不算规格 token）。"""
    rest = query[end : end + 1]
    return rest in _DATE_SUFFIX


def extract_spec_tokens(query: str) -> list[str]:
    """抽取查询里的规格 token（保序去重）。没有规格 token 时返回空列表。"""
    text = query or ""
    tokens: list[str] = []

    def add(token: str) -> None:
        lowered = token.lower()
        if lowered and lowered not in tokens:
            tokens.append(lowered)

    consumed: list[tuple[int, int]] = []
    for match in _ATTACHED_RE.finditer(text):
        add(match.group(1))
        consumed.append(match.span(1))
    for match in _BRAND_NUM_RE.finditer(text):
        number = match.group(2)
        if any(s >= match.start(2) and e <= match.end(2) for s, e in consumed):
            continue  # 「S4000」这类连写型号已单独处理
        if _is_year(number) or _is_date_number(text, *match.span(2)):
            continue
        add(f"{match.group(1)} {number}")
        add(number)  # 品牌短语 + 裸数字都算 token（用户口径：「RTX 5090」「5090」都要认）
        consumed.append(match.span(2))
    for match in _VERSION_RE.finditer(text):
        add(match.group(1))
        consumed.append(match.span(1))
    for match in _NUMBER_RE.finditer(text):
        start, end = match.span(1)
        number = match.group(1)
        if any(start >= s and end <= e for s, e in consumed):
            continue  # 已作为品牌短语/版本号的一部分处理
        if _is_year(number) or _is_date_number(text, start, end):
            continue
        add(number)
    for match in _MODIFIER_RE.finditer(text):
        add(match.group(1))
    return tokens


@dataclass(frozen=True)
class SpecMatch:
    """一次规格匹配的结果。`level` 为 `full` / `partial` / `none` / `n/a`（查询本身没有规格 token）。"""

    level: str
    matched: tuple[str, ...] = field(default_factory=tuple)
    missing: tuple[str, ...] = field(default_factory=tuple)


def _pattern_for(token: str) -> re.Pattern[str]:
    if " " in token:  # 品牌短语：允许空格/连字符变化
        brand, number = token.split(" ", 1)
        return re.compile(rf"(?<![a-z0-9]){re.escape(brand)}[\s\-]?{re.escape(number)}(?![a-z0-9])")
    if re.fullmatch(r"\d+(?:\.\d+)*", token):
        # 前界挡住「3.130 里的 3.13」「3.17 里的 17」；后界只挡数字（允许 3.13.html / 5090。这种结尾）
        return re.compile(rf"(?<![\d.]){re.escape(token)}(?!\d)")
    if re.fullmatch(r"[a-z]+\d+", token):  # 连写型号：S4000
        return re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    # 修饰词：只要求前后不是 ASCII 字母/数字（中文紧邻时也算命中，如「17 Pro参数」）
    return re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")


def match_spec_tokens(tokens: list[str], *, title: str = "", content: str = "", url: str = "") -> SpecMatch:
    """在「标题 + 摘要 + 正文开头 + URL」里匹配规格 token。

    返回三档：`full`（全部命中）/ `partial`（命中一部分）/ `none`（一个都没命中）；
    `tokens` 为空时返回 `n/a`（调用方应完全保持原行为）。
    """
    if not tokens:
        return SpecMatch(level="n/a")
    # 统一小写后再匹配：token 已小写，且大小写对规格没有语义（RTX / rtx 等价）
    haystack = " ".join(part for part in (title, content, url) if part).lower()
    matched: list[str] = []
    missing: list[str] = []
    for token in tokens:
        (matched if _pattern_for(token).search(haystack) else missing).append(token)
    if not missing:
        level = "full"
    elif matched:
        level = "partial"
    else:
        level = "none"
    return SpecMatch(level=level, matched=tuple(matched), missing=tuple(missing))


def spec_level_for_result(tokens: list[str], result) -> str:  # noqa: ANN001 - SearchResult
    """便捷入口：按 `SearchResult` 的字段做匹配（正文只取开头 500 字，避免超长正文拖慢）。"""
    return match_spec_tokens(
        tokens,
        title=result.title or "",
        content=(result.content or "")[:500],
        url=result.url or "",
    ).level


# 修饰词精确匹配（2026-10-01 T5，治 Q16）：
# 查询 iPhone 17 **Pro** 时，结果 "Apple iPhone 17 Pro Max" 里的「pro」也命中了 —— 但那是**另一个机型**。
# 旧实现把修饰词当普通 token 做「出现即命中」（Pro Max 只算 partial → 仅降权），于是 Q16 线上 3 轮
# 恒有 1 条 Pro Max 混进 top5。新口径：**修饰词必须精确匹配** ——
#   * 「缺」（结果只有 iPhone 17，没有 Pro）→ 不匹配；
#   * 「多」（结果只有 Pro Max / Pro Plus 这类被其它修饰词延长的写法）→ 不匹配；
#   * 页面同时提到 17 Pro 与 17 Pro Max（如 Apple 发布会报道）→ 存在**独立出现**的 Pro → 匹配。
# 修饰词后面紧跟的字母串（跳过少量非字母分隔符，含空格/连字符/斜杠，以及 URL 里的 `+`、`%20`）：
# 实测 Spigen 的 Pro Max 页面 URL 写成 `…?filter.v.option.device=iPhone+17+Pro+Max`，
# 只认 `[\s\-–—/]` 会把 `+Max` 漏掉、误判为「独立出现的 Pro」。
_MODIFIER_FOLLOW_RE = re.compile(r"[^a-z]{0,4}([a-z]+)")


def modifier_exact_match(tokens: list[str], *, title: str = "", url: str = "") -> bool:
    """查询里的修饰词（pro/max/plus/mini/ultra/air/se）是否**精确出现**在结果里。

    只对「查询本身含修饰词」的情况生效；查询没有修饰词时恒为 True（行为完全不变）。
    判定方式：逐个修饰词扫描出现位置，只要存在一次「后面不紧跟其它修饰词」的出现即算命中；
    全部出现都被更长的型号写法延长（如 `17 Pro Max`）→ 判不匹配。

    **只看标题与 URL**（页面身份），不看正文：实测 Spigen 的
    「iPhone 17 Pro Max Case Collection」正文/页脚里偶然出现「iPhone 17 Pro」链接，
    若把正文算进 haystack 就会把 Pro Max 页面放进来（2026-10-01 T5 实测）。
    """
    modifiers = [token for token in tokens if _MODIFIER_RE.fullmatch(token)]
    if not modifiers:
        return True
    haystack = " ".join(part for part in (title, url) if part).lower()
    for token in modifiers:
        exact = False
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack):
            following = haystack[match.end() : match.end() + 16]
            nxt = _MODIFIER_FOLLOW_RE.match(following)
            if not (nxt and _MODIFIER_RE.fullmatch(nxt.group(1))):
                exact = True
                break
        if not exact:
            return False
    return True


# 混杂列表/回收页形态（2026-09-30，治 2-9 的 Q16）：
# 京东「苹果8x参数」这类**二手回收/型号大全**页，标题里同时列了 17/16/15/14/13/12/11/X 与 pro/max/mini，
# 于是「17」和「pro」都命中，规格 token 误判为匹配 —— 但它并不是 iPhone 17 Pro 的参数页。
_MIXED_KEYWORDS = ("回收", "二手", "以旧换新", "翻新", "大全", "全系", "系列", "对比表")
_MIXED_MIN_NUMBERS = 3


def distinct_model_numbers(text: str | None) -> set[str]:
    """文本里出现的**互不相同**的数字型号（排除年份与日期表达）。"""
    raw = str(text or "")
    numbers: set[str] = set()
    for match in _NUMBER_RE.finditer(raw):
        start, end = match.span(1)
        value = match.group(1)
        if _is_year(value) or _is_date_number(raw, start, end):
            continue
        numbers.add(value)
    return numbers


def is_mixed_model_page(title: str | None, content: str | None = None) -> bool:
    """判定「一页多型号 / 回收列表」形态。

    返回 True 表示：标题（或摘要）里同时出现**多个不同型号数字**，且带列表/回收类关键词；
    或标题里出现 ≥3 个不同型号数字（即便没有关键词，如「苹果17/16/15/14 系列」）。
    这类页面**不能**用来证明规格匹配（Q16 的京东回收页就是这样骗过 token 匹配的）。
    """
    text = f"{title or ''} {content or ''}"
    numbers = distinct_model_numbers(title) | distinct_model_numbers(content)
    has_keyword = any(word in text for word in _MIXED_KEYWORDS)
    if len(numbers) >= _MIXED_MIN_NUMBERS:
        return True
    return bool(has_keyword and len(numbers) >= 2)

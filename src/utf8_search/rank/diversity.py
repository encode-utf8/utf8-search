"""结果质量与多样性过滤（M5-5.3）：同站限流、脚本一致性、聚合页识别、查询词覆盖度。

2-9 抽检未达标的 5 条查询暴露的问题，都能用**客观信号**修掉，不需要维护站点黑名单：

- #4 台风：top5 里两条来自同一「台风路径」站点体系 → 同站限流；
- #16 iPhone：中文查询混入俄语开箱视频 → 脚本一致性；
- #11 新能源补贴 / #18 扫地机器人：混入展会页、栏目页、官网首页、乐高攻略、净水器
  → 聚合页识别 + 查询词覆盖度；
- #2 AI 行业动态：混入德语无关页与产品页 → 查询词覆盖度。

统一原则：**候选充足才过滤**。`apply_rank_filters` 在过滤后若结果不足 `max_results`，
会按原排序把被剔除的结果补回来 —— 质量过滤绝不能把结果掏空（与 5.1 的覆盖率下限同一思路）。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

from ..models import SearchResult
from .fusion import tokenize
from .spec_tokens import (
    extract_spec_tokens,
    is_mixed_model_page,
    modifier_exact_match,
    spec_level_for_result,
)

# ---------------------------------------------------------------- 域名
# 常见「二级后缀」：可注册域要多吃一段，否则 zj.gov.cn / weather.com.cn 会被误当成两个不同的域
_MULTI_LABEL_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn", "ac.cn", "mil.cn",
    "com.hk", "org.hk", "gov.hk", "edu.hk", "com.tw", "org.tw", "gov.tw",
    "co.uk", "org.uk", "ac.uk", "gov.uk", "co.jp", "or.jp", "ne.jp", "go.jp",
    "com.au", "net.au", "org.au", "gov.au", "com.sg", "com.br", "co.kr", "or.kr",
}


def registrable_domain(url: str) -> str:
    """取可注册域（用于同站判定）。

    刻意用「后缀表 + 末两段」而不是 tldextract / 公共后缀列表：只为了同站聚类，
    不需要完备性，且避免为一个聚类信号引入依赖与新数据源。
    """
    try:
        host = (urlsplit(url).hostname or "").lower().strip(".")
    except ValueError:
        return ""
    if not host or host.replace(".", "").isdigit():
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last_two = ".".join(parts[-2:])
    if last_two in _MULTI_LABEL_SUFFIX and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last_two


# ---------------------------------------------------------------- 脚本一致性
# 查询主体是中文时，西里尔/阿拉伯/泰文/韩文的结果对中文用户基本无用（实测 #16 混入俄语开箱）。
# 判定口径：**含「其他脚本」且不含任何汉字/假名** → 不匹配。
# 这样英文结果一定保留（用户明确需要外网英文信息），中文/日文结果一定保留，
# 而「俄语 + 少量拉丁字母」这种混排标题也能识别出来（#16 的标题正是这种形态：
# "ГОД С iPHONE 17 / PRO / AIR — YouTube"，若把拉丁字母也算作「可用脚本」就会漏判）。
_CJK_CHARS = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff]")
_OTHER_SCRIPTS = re.compile(
    r"[\u0400-\u04ff\u0530-\u058f\u0590-\u05ff\u0600-\u06ff\u0e00-\u0e7f"
    r"\u0900-\u097f\uac00-\ud7af\u10a0-\u10ff\u1c00-\u1c4f]"
)


def is_cjk_query(query: str) -> bool:
    """查询里是否出现汉字/假名（出现即启用脚本过滤）。

    刻意不用「汉字数 ≥ 拉丁字母数」这种比例判据：2-9 抽检里的中文查询大量是中英混排
    （`iPhone 17 Pro 价格 参数`、`RTX 5090 benchmark 价格`、`Python 3.13 新特性`），
    按比例判会把它们排除在过滤之外，#16 的俄语开箱正是这样漏掉的。
    只要查询里有汉字/假名，就说明受众要的是中文可读结果，此时纯西里尔/阿拉伯/韩文标题应剔除。
    """
    return bool(_CJK_CHARS.search(query or ""))


def has_script_mismatch(query: str, title: str) -> bool:
    """中文查询下，标题是否为「其他脚本」（西里尔/阿拉伯/泰文/韩文等）。"""
    if not is_cjk_query(query):
        return False
    text = (title or "").strip()
    if not text:
        return False
    return bool(_OTHER_SCRIPTS.search(text)) and not _CJK_CHARS.search(text)


# ---------------------------------------------------------------- 聚合页
# 首页 / 栏目页 / 频道页对 LLM 没有价值：它们只是一堆链接，正文会退化成导航文字。
# 判据全部来自 URL 结构与标题用词，不针对具体站点。
_AGGREGATOR_TITLE = re.compile(
    r"(首页|官网首页|官方网站|频道|栏目|分类|导航|站点地图|新闻中心|资讯中心|产品中心|新闻超市)"
)
_ARTICLE_SUFFIX = re.compile(r"\.(s?html?|php|aspx?|jsp|shtml)$", re.IGNORECASE)
# 频道 / 标签 / 专题页的通用 URL 形态（各站点约定俗成，不是针对某个站点的规则）：
# `/tags/xxx`、`/topic/123`、`/zhuanti/xxx`、`/category/xxx`，或以 `/news`、`/list`、`/index` 结尾。
# 只对「浅路径（≤2 段）且无文章后缀」生效，避免误伤 `/news/20260924/a.shtml` 这类真正的文章页。
_AGGREGATOR_PATH_HEAD = re.compile(
    # 注意：这里的 path 已去掉首尾斜杠，所以不能用 ^/ 开头
    r"^(tags?|topics?|zhuanti|category|categories|channel|columns?|zt)(/|$)", re.IGNORECASE
)
_AGGREGATOR_PATH_TAIL = re.compile(r"/(news|list|index|all)/?$", re.IGNORECASE)


def has_substantive_content(result: SearchResult) -> bool:
    """正文里是否有**实质内容**（而不是一串导航/链接/列表标题）。

    判据刻意保守（宁可不判）：
    * 长度 ≥200 字 → 实质；
    * 长度 ≥120 且至少 2 个句末标点 → 实质；
    * 长度 ≥60 且至少 3 个句末标点 → 实质。
    注：basic 模式下 `content` 是上游摘要（几十到几百字），deep 模式是正文开头，两者都适用。

    2026-10-01（T10）补**条目式分支**：短摘要里带 ≥2 类时间线索（日期 / 时刻 / 相对时间）的
    —— 典型是「日报」类页面（AIHOT：「4 weeks ago — AIHOT 每日 8:00 自动生成的过去 24 小时…」，53 字）
    —— 也算实质内容，否则会被 `is_aggregator_page` 误判成「无实质内容的聚合页」剔除。
    纯导航页通常只有 0-1 类时间线索（例如只有一枚日期），仍按聚合页剔除。
    """
    text = (result.content or "").strip()
    if not text:
        return False
    if len(text) >= 200:
        return True
    sentences = len(re.findall(r"[。！？!?；;]", text))
    if len(text) >= 120 and sentences >= 2:
        return True
    if len(text) >= 60 and sentences >= 3:
        return True
    return len(text) >= 30 and _distinct_time_signal_kinds(text) >= 2


# 「条目式」时间线索（T10）：三类信号各自独立，至少要**两类同时出现**才算条目式，
# 避免「首页导航里带一枚日期」这种页面被误判成实质内容。
_ITEM_TIME_PATTERNS = {
    "date": re.compile(r"(?:19|20)\d{2}\s*[-/年]\s*\d{1,2}(?:\s*[-/月]\s*\d{1,2})?"),
    "clock": re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)"),
    "relative": re.compile(
        r"\d+\s*(?:分钟|小时|天|周|个月)前|\b\d+\s*(?:minutes?|hours?|days?|weeks?|months?)\s+ago\b|\bago\b"
        r"|published|posted\b|updated\b|更新于",
        re.IGNORECASE,
    ),
}


def _distinct_time_signal_kinds(text: str) -> int:
    return sum(1 for pattern in _ITEM_TIME_PATTERNS.values() if pattern.search(text))


# 「条目感」判据（2026-10-01 T6，治 Q3 的 newsfilter.io）：
# newsfilter.io 是**站点首页**，正文是站点自我介绍（"We deliver real-time business and markets news to the world…"），
# 因为「有实质内容」被 `is_aggregator_page` 放行 —— 但首页/栏目页的实质内容应当是**条目**（带日期的标题、
# 多条快讯），而不是站点自述。收紧后：有实质内容 **且** 内容像条目，才豁免聚合页判据。
# 已按既有裁决核对：发改委首页（"2026年9月11日…"）、美国之音首页（"5 days ago —"）、外交部栏目页（"（2026-09-26）"）
# 都带日期 → 保持豁免；只有纯自我介绍式的首页会被判聚合页。
_ITEM_DATE_RE = re.compile(r"(?:19|20)\d{2}\s*[-/年]\s*\d{1,2}(?:\s*[-/月]\s*\d{1,2})?")
_ITEM_AGE_RE = re.compile(r"\b\d+\s*(?:分钟|小时|天|周|个月)前|ago\b|published|posted\b|updated\b|更新于", re.IGNORECASE)


def has_item_like_content(result: SearchResult) -> bool:
    """首页/栏目页的「实质内容」是否像**条目**（带日期/时间线的快讯列表）。"""
    text = result.content or ""
    if _ITEM_DATE_RE.search(text) or _ITEM_AGE_RE.search(text):
        return True
    # 多条快讯常用 `·` / `|` 分隔（≥3 个分隔符 ≈ 至少 4 段）
    return (text.count("·") + text.count("|")) >= 3


def looks_like_column(result: SearchResult) -> bool:
    """**形态**上像站点首页 / 栏目页 / 专题页 / 列表汇总页（不看内容）。"""
    try:
        path = urlsplit(result.url or "").path.strip("/")
    except ValueError:
        path = ""
    if not path:
        return True  # 站点首页
    segments = path.split("/")
    has_article_suffix = bool(_ARTICLE_SUFFIX.search(path))
    if len(segments) == 1 and len(path) <= 12 and not has_article_suffix:
        # 一层浅路径且看不出文章线索（如 /news、/channel、/auto）—— 栏目页特征
        return True
    if (
        len(segments) <= 2
        and not has_article_suffix
        and (_AGGREGATOR_PATH_HEAD.search(path) or _AGGREGATOR_PATH_TAIL.search(path))
    ):
        # 频道 / 标签 / 专题页（/tags/国产显卡、/topic/7552…、/315440/news）
        return True
    return bool(_AGGREGATOR_TITLE.search(result.title or ""))


def is_aggregator_page(result: SearchResult) -> bool:
    """判断结果是否为「只能当导航用」的聚合页（2026-09-30 与 2-9 判分口径对齐）。

    **口径来源**：2-9 的裁决原话是「聚合形态本身不等于不相关；站点首页/栏目页这类『只是导航』才判 0」。
    所以这里的判据从「形态像栏目页」改成「**形态像栏目页 且 正文没有实质内容**」：

    * 首页 / 栏目页 / 频道页 / 专题页 + 短短几行导航 → 判聚合页（剔除）；
    * 标题含「汇总 / 日报 / 周报 / 速览」但**正文有实质内容**（如每日新闻汇总、周报正文）→ **保留**。

    2026-10-01（T6）再收紧一格：实质内容还必须**像条目**（带日期/时间线，见 `has_item_like_content`）——
    站点首页的纯自我介绍（newsfilter.io 这类「We deliver …」的使命陈述）不再豁免（Q3 三轮都栽在它上面）。
    正文是文章的情况本来就不走这条分支（`looks_like_column` 为假）。

    旧实现只看 URL/标题形态，把后者也一并剔除了，与判分口径不一致（Q1 的每日新闻汇总就被误伤）。
    """
    if not looks_like_column(result):
        return False
    return not (has_substantive_content(result) and has_item_like_content(result))


# ------------------------------------------------------------------ 内容农场/成人视频站（2026-10-01 T6，治 Q2）
# 2-9 的 Q2（最近一周 AI 行业动态）反复被「短剧/漫剧免费在线观看」这类内容农场站占据 top5
# （随机子域 + .cc 域名 + 标题带站点名，如「高三爱情故事 - 短剧视频在线观看 | 黄果短剧」）。
# 它们属于**站点形态**问题（不是主题匹配）：页面本身是盗版/成人视频聚合站，正文是色情文案，
# 对任何非该类查询都不该出现。判据 = 「站点标记 + 视频站尾部」双命中，且**查询本身不是这类内容**；
# 命中即**硬剔除**（不参与"候选不足补回"——垃圾站不该因为池子空就被放回来）。
_FARM_MARKERS = ("短剧", "漫剧", "擦边", "成人视频", "色情", "艳情", "福利视频")
_FARM_VIDEO_TAILS = ("在线观看", "免费观看", "在线播放", "免费在线", "全集")


def is_content_farm(result: SearchResult, query: str) -> bool:
    """内容农场/成人视频站形态（查询本身不是这类内容时生效）。"""
    if any(marker in (query or "") for marker in _FARM_MARKERS):
        return False
    text = f"{result.title or ''} {result.url or ''}"
    return any(marker in text for marker in _FARM_MARKERS) and any(tail in text for tail in _FARM_VIDEO_TAILS)


# ---------------------------------------------------------------- 主题相关性闸门（2026-10-01 T10）
# 目标（治 Q2「最近一周 AI 行业动态」）：**池内没有切题候选时如实降级**，
# 而不是用「候选不足就补回」的机制把无关结果硬凑成 5 条。
# 判据是**纯词面覆盖率代理**（`query_coverage` 已有实现）：
#   * 覆盖率 ≥ `TOPIC_COVERAGE_FLOOR` 的候选数为 **0** ⇒ 判「池内无切题候选」。
# 刻意保守（宁漏报、不误报）：只要池子里有 1 条覆盖率达标的候选，就不打降级标记。
# 阈值来源（2026-10-01 固定池实测）：Q2 的**无料抽样**里全池最高覆盖率 0.31（即梦 AI 产品页）
# ⇒ 判 0 条达标；有料抽样里切题候选覆盖率 0.50-0.63。其它 19 条查询的池内达标数 ≥2
# （最紧的是 Q16 = 2-3，见 T10 报告受控回放表），因此 count==0 的口径不会误报。
TOPIC_COVERAGE_FLOOR = 0.35
# 达标候选数的下限：< 1 即「一条都没有」才降级（保守口径）。
MIN_ON_TOPIC_CANDIDATES = 1


def count_on_topic_candidates(query: str, results: list[SearchResult]) -> int:
    """池内覆盖率达标（≥ `TOPIC_COVERAGE_FLOOR`）的候选条数。"""
    return sum(1 for item in results if query_coverage(query, item) >= TOPIC_COVERAGE_FLOOR)


def has_no_relevant_results(query: str, results: list[SearchResult]) -> bool:
    """池内没有足够的切题候选（< `MIN_ON_TOPIC_CANDIDATES` 条）→ 应对外降级 `no_relevant_results`。"""
    return count_on_topic_candidates(query, results) < MIN_ON_TOPIC_CANDIDATES


# ------------------------------------------------------------------ 三类「无关形态」（2026-10-01 T7，治 Q1）
# ------------------------------------------------------------------ 三类「无关形态」（2026-10-01 T7，治 Q1）
# Q1（2026年9月 国内外重大新闻）三轮恒有 3 条形态明确但主题无关的结果：
#   ① 电视/节目单页：央视《生活圈》20260929（标题是「《节目名》+ 播出日期」，正文只有导航）；
#   ② 院校迎新/开学页：仁川机场院校「2026年9月学期新生迎新」（正文为空）；
#   ③ 开运日历/黄历页：日本「2026年9月の開運日カレンダー」（占卜/吉日主题）。
# 统一判据 = **形态命中 + 主题针对性**（与 is_aggregator_page / is_offtopic_index_page 同源）：
#   形态由标题/内容特征判定（不维护站点黑名单）；「主题针对性」用**查询侧闸门**实现 ——
#   查询本身就是在找这类内容（如「开运」「节目」「开学」）时规则整体不生效。
# 电视/院校两类还要求**正文无实质内容**（避免误伤长篇节目文稿、校园新闻稿）。
# 注意：不要把「第N期 / 完整版」这类**系列文章**常用写法算进来（会把「周报（第3期）」误伤成电视节目页）。
_TV_PROGRAM_TITLE_RE = re.compile(r"《[^》]{1,24}》[\s\-–—]*\d{4,8}|(?:节目单|节目预告|片花|第\s*\d{1,3}\s*集)")
_TV_QUERY_TERMS = ("节目", "电视", "综艺", "视频", "直播", "电视剧", "晚会", "体育赛事")
_CAMPUS_TITLE_RE = re.compile(r"(迎新|开学|新生|入学|招生|报到|军训|开学典礼|校历)")
_CAMPUS_QUERY_TERMS = ("学校", "大学", "学院", "开学", "迎新", "招生", "入学", "教育", "考试", "校园")
_ALMANAC_RE = re.compile(r"(开运|開運|黄历|吉日|宜忌|黄道|占卜|运势|风水|算命|星座|生辰|一粒万倍日)")
_ALMANAC_QUERY_TERMS = ("开运", "開運", "黄历", "吉日", "运势", "星座", "风水", "占卜", "算命", "宜忌")


def off_topic_form(result: SearchResult, query: str) -> str | None:
    """形态命中且与查询主题无关时返回形态名（`tv_program` / `campus_page` / `almanac_page`），否则 None。"""
    q = (query or "").lower()
    title = result.title or ""
    if not any(term in q for term in _TV_QUERY_TERMS):
        if _TV_PROGRAM_TITLE_RE.search(title) and not has_substantive_content(result):
            return "tv_program"
    if not any(term in q for term in _CAMPUS_QUERY_TERMS):
        if _CAMPUS_TITLE_RE.search(title) and not has_substantive_content(result):
            return "campus_page"
    if not any(term in q for term in _ALMANAC_QUERY_TERMS):
        if _ALMANAC_RE.search(f"{title} {result.content or ''}"):
            return "almanac_page"
    return None


# ------------------------------------------------------------------ 非主题页（2026-10-01 T5，治 Q6）
# 2-9 的 Q6（Python 3.13 新特性）线上 3 轮恒 3/5：坏结果是**关键词命中但页面本身不回答查询**的
# 「非主题页」—— 社区**个人主页**（v2ex.com/member/<id> 这类只列最近发帖的页）与**包索引页**
# （formulae.brew.sh/formula/python@3.13 只有一行 Formula JSON API 元数据）。
# 判据与 `is_aggregator_page` **同源**：形态像非主题页 **且** 正文没有实质内容 → 剔除；
# 带实质内容的页面（社区长文、注册表上的完整说明）一律保留，因此不误伤正常站点。
_OFFTOPIC_PROFILE_PATH = re.compile(r"^/(member|members|user|users|people|u|profile|profiles|accounts?)(/|$)", re.IGNORECASE)
_REGISTRY_HOSTS = {
    "formulae.brew.sh", "pypi.org", "npmjs.com", "crates.io", "rubygems.org",
    "packagist.org", "hub.docker.com", "anaconda.org", "conda.anaconda.org",
}
_REGISTRY_PATH = re.compile(r"^/(project|projects|package|packages|formula|formulae|crates|gems|r)(/|$)", re.IGNORECASE)
_IMAGE_BOARD_HOSTS = {
    "pinterest.com", "pinterest.co.uk", "pinterest.de", "pinterest.fr", "pinterest.jp", "pinterest.ru",
}
_IMAGE_BOARD_PATH = re.compile(r"^/(ideas|pin|search|board|boards)(/|$)", re.IGNORECASE)


def looks_like_offtopic_index_page(result: SearchResult) -> bool:
    """**形态**上像「非主题页」：社区个人主页 / 包索引页 / 图片素材板（只看 URL 形态）。"""
    try:
        parts = urlsplit(result.url or "")
    except ValueError:
        return False
    path = "/" + parts.path.strip("/")
    host = (parts.hostname or "").lower()
    if _OFFTOPIC_PROFILE_PATH.search(path):
        return True
    if host in _REGISTRY_HOSTS or any(host.endswith("." + item) for item in _REGISTRY_HOSTS):
        return _REGISTRY_PATH.search(path) is not None
    if host in _IMAGE_BOARD_HOSTS or any(host.endswith("." + item) for item in _IMAGE_BOARD_HOSTS):
        return _IMAGE_BOARD_PATH.search(path) is not None
    return False


def is_offtopic_index_page(result: SearchResult) -> bool:
    """与 `is_aggregator_page` 同源的「非主题页」判据：形态像 + 正文无实质内容 → 剔除。

    只依赖两个客观信号（URL 形态 + 正文实质度），不维护站点黑名单；
    形态命中但正文有实质内容的页面**保留**（保守取向，避免误伤社区里的正常长文）。
    """
    if not looks_like_offtopic_index_page(result):
        return False
    return not has_substantive_content(result)


# 形态轻降权（2026-09-30，P1）：含实质内容的首页/栏目页**保留**（过滤层口径已对齐），
# 但排序层给一点形态偏好，让独立文章更靠前。刻意用**乘子**而不是逐条 if-else 特判：
#   分数 × 0.95（≈ 5% 降权）——只影响"分数接近"的情况，不会把高相关汇总页压到底部。
COLUMN_PAGE_SCORE_MULTIPLIER = 0.95


def form_score_multiplier(result: SearchResult) -> float:
    """排序用的**形态乘子**：含实质内容的首页/栏目页 ×0.95，其余 ×1.0。"""
    return COLUMN_PAGE_SCORE_MULTIPLIER if looks_like_column(result) else 1.0


def apply_form_penalty(results: list[SearchResult]) -> list[SearchResult]:
    """对结果做**轻量形态偏好**排序（稳定排序，不删除任何结果，**不改 score**）。

    与 `is_aggregator_page` 共用同一个形态判据（`looks_like_column`），因此：
    * 只当导航的聚合页仍由过滤层剔除；
    * **日报/汇总类文章**（有实质内容）不会被剔除，只在排序时按 ×0.95 的**有效分**让位；
    * 普通文章结果乘子为 1.0，相对顺序不变。

    **幂等（2026-09-30 P7 修）**：早期实现 `result.score *= 0.95` 是原地修改，
    **被调两次就是 ×0.9025**（重复处理会持续压低分数）。现在改成「**乘子只用于排序 key**」：
    `score` 始终是相关性原始分（对外字段语义不变），顺序按 `score × form_score_multiplier` 排
    ⇒ **对同一批结果重复调用，顺序与 score 都不变**（幂等）。
    分数接近时可能出现「分数略高但因形态让位」的顺序，这是刻意的（不污染对外 score 语义）。
    """
    return sorted(results, key=lambda r: r.score * form_score_multiplier(r), reverse=True)


# ---------------------------------------------------------------- 查询词覆盖度
def query_coverage(query: str, result: SearchResult) -> float:
    """查询词在「标题 + 摘要」里的覆盖率（0-1）。

    复用 fusion 的中文二元组分词：查询词几乎不出现的结果，即便标题堆砌了关键词，
    也很难同时命中二元组（这点是刻意选的——#11 的展会页正是靠堆词骗过单字匹配的）。
    """
    wanted = set(tokenize(query or ""))
    if not wanted:
        return 1.0
    doc = set(tokenize(f"{result.title or ''} {result.content or ''}"))
    return len(wanted & doc) / len(wanted)


# ---------------------------------------------------------------- 组合过滤
def _split(results: list[SearchResult], predicate: Callable[[SearchResult], bool]) -> tuple[list, list]:
    """按判据把结果拆成 (保留, 剔除)，保持原顺序。"""
    kept: list[SearchResult] = []
    dropped: list[SearchResult] = []
    for result in results:
        (dropped if predicate(result) else kept).append(result)
    return kept, dropped


def limit_per_host(results: list[SearchResult], max_per_host: int) -> tuple[list, list]:
    """同站限流：同一可注册域最多保留 max_per_host 条。

    搜索引擎对某些站点（实测 bilibili 单查询 20 条）会灌满结果集，
    挤掉其他来源 —— 对「给 LLM 提供多来源资料」是净损失。
    """
    if max_per_host <= 0:
        return list(results), []
    seen: dict[str, int] = {}
    kept: list[SearchResult] = []
    dropped: list[SearchResult] = []
    for result in results:
        host = registrable_domain(result.url)
        if not host:
            kept.append(result)
            continue
        if seen.get(host, 0) < max_per_host:
            seen[host] = seen.get(host, 0) + 1
            kept.append(result)
        else:
            dropped.append(result)
    return kept, dropped


def apply_rank_filters(
    results: list[SearchResult],
    *,
    query: str,
    max_results: int,
    max_per_host: int = 2,
    min_query_coverage: float = 0.34,
    drop_aggregator_pages: bool = True,
    drop_script_mismatch: bool = True,
) -> tuple[list[SearchResult], dict[str, int]]:
    """按客观质量信号过滤，并在结果不足时按原排序补回。

    返回 `(结果, 各过滤器剔除计数)`；计数用于观测与验收报告，
    **补回的结果也计入剔除计数**（即计数是「曾判为可疑」的条数）。

    补回顺序（候选不足 max_results 时）按缺陷轻重：覆盖度低 → 同站冗余 → 聚合页 → 脚本不匹配。
    即宁可用「关键词没对上但内容可读」的结果凑数，也不轻易把导航页放回来。
    """
    order = {id(result): index for index, result in enumerate(results)}
    kept = list(results)
    dropped: list[SearchResult] = []
    stats: dict[str, int] = {}

    if drop_aggregator_pages:
        # 主题相关性闸门（T10）：只看**池子**里有没有足够的切题候选（纯覆盖率代理）。
        stats["on_topic_candidates"] = count_on_topic_candidates(query, results)
        stats["no_relevant_results"] = int(has_no_relevant_results(query, results))
        # 内容农场/成人视频站：**硬剔除**，不参与后面的"候选不足补回"（垃圾站不因池子空而被放回）。
        farmed = [item for item in kept if is_content_farm(item, query)]
        if farmed:
            stats["content_farm"] = len(farmed)
            kept = [item for item in kept if not is_content_farm(item, query)]

    steps: list[tuple[str, Callable[[list[SearchResult]], tuple[list, list]]]] = []
    if drop_script_mismatch:
        steps.append(
            ("script_mismatch", lambda items: _split(items, lambda r: has_script_mismatch(query, r.title)))
        )
    if drop_aggregator_pages:
        steps.append(("aggregator_page", lambda items: _split(items, is_aggregator_page)))
    if drop_aggregator_pages:
        # 「非主题页」与聚合页同源（形态 + 无实质内容），共用同一个开关：
        # 新闻路径（structural_only）维持原样，不受本轮改动影响。
        steps.append(("offtopic_page", lambda items: _split(items, is_offtopic_index_page)))
    if drop_aggregator_pages:
        # 三类「无关形态」（T7）：电视节目单 / 院校迎新 / 开运日历 —— 形态命中且查询不是找这类内容。
        steps.append(("offtopic_form", lambda items: _split(items, lambda r: off_topic_form(r, query) is not None)))
    spec_tokens = extract_spec_tokens(query)
    if spec_tokens:
        # 规格不匹配（如查询 iPhone 17 Pro 却给 iPhone 8、查询 Python 3.13 却给 3.14）：
        # 词面覆盖率看不出这类错误，只有规格 token 能抓到。候选充足时剔除，不足时按缺陷轻重补回。
        #
        # 2026-09-30 补充「混杂型号页」：一页列了 17/16/15/14/13… 的二手回收/型号大全页，
        # 标题里 17 与 pro 都命中 → token 匹配会误判为「匹配」。这种页面**不能**算规格达标，
        # 与聚合页口径同源处理（形态不对 + 无实质针对性 → 剔除；候选不足时补回并标 degraded）。
        #
        # 2026-10-01 补充「修饰词精确匹配」（T5，治 Q16）：查询 iPhone 17 **Pro** 时，
        # "iPhone 17 Pro Max" 里的 pro 也命中、且只算 partial 被降权 → 线上 3 轮恒有 1 条混进 top5。
        # 现在「缺 Pro」与「只有 Pro Max」都判不匹配（剔除；候选不足才补回），见 spec_tokens.modifier_exact_match。
        steps.append(
            (
                "spec_mismatch",
                lambda items: _split(
                    items,
                    lambda r: (
                        spec_level_for_result(spec_tokens, r) == "none"
                        or is_mixed_model_page(r.title, r.content)
                        or not modifier_exact_match(
                            spec_tokens,
                            title=r.title or "",
                            url=r.url or "",
                        )
                    ),
                ),
            )
        )
    if min_query_coverage > 0:
        steps.append(
            (
                "low_coverage",
                lambda items: _split(items, lambda r: query_coverage(query, r) < min_query_coverage),
            )
        )
    if max_per_host > 0:
        steps.append(("same_host", lambda items: limit_per_host(items, max_per_host)))

    by_stage: list[tuple[str, list[SearchResult]]] = []
    for name, step in steps:
        if not kept:
            stats[name] = 0
            by_stage.append((name, []))
            continue
        kept, removed = step(kept)
        stats[name] = len(removed)
        dropped.extend(removed)
        by_stage.append((name, removed))

    # 补回：过滤后不足 max_results 时把被剔除的结果放回去，
    # 保证质量过滤不会让结果变少（宁可少过滤，也不能掏空结果集）。
    if max_results > 0 and len(kept) < max_results and dropped:
        wanted = max_results - len(kept)
        kept_before_refill = list(kept)
        # 补回**按「缺陷轻重」排序**，而不是一律按原排序：
        # 「覆盖度低」只说明关键词没对上，内容本身还是可读的；
        # 「聚合页 / 脚本不匹配」是结构性缺陷（点进去只有导航，或用户根本读不懂），
        # 它们排在最前时若按原排序补回，第一个补回来的就是它们，过滤等于白做
        # （2-9 #2 实测：AI 产品落地页总排第 1，把 4 条真正的 AI 资讯挤掉一条）。
        stage_priority = {
            "low_coverage": 0,
            "same_host": 1,
            "aggregator_page": 2,
            "offtopic_page": 2,
            "offtopic_form": 2,
            "spec_mismatch": 3,
            "script_mismatch": 4,
        }
        restore: list[SearchResult] = []
        spec_dropped_ids = {id(result) for name, removed in by_stage if name == "spec_mismatch" for result in removed}
        for name, removed in sorted(by_stage, key=lambda item: stage_priority.get(item[0], 9)):
            restore.extend(sorted(removed, key=lambda item: order[id(item)]))
        # 补回的结果一律**追加到末尾**（而不是按原始顺序插回原位）：
        # 它们是被判有缺陷的（覆盖度低 / 同站冗余 / 聚合页 / 规格不匹配 / 脚本不匹配），
        # 插回原位等于让过滤白做（2-9 #2 实测过这个问题）。原顺序在每一类内部保留。
        kept = kept_before_refill
        for result in restore:
            if wanted <= 0:
                break
            kept.append(result)
            wanted -= 1
        # 统计「因候选不足而被补回的规格不匹配条数」——上层据此标 degraded（候选不足时只降权，不静默丢）
        stats["spec_mismatch_refilled"] = sum(1 for r in kept if id(r) in spec_dropped_ids)

    if spec_tokens:
        # 部分匹配（iPhone 17 对 iPhone 17 Pro）**降权**：不动剔除逻辑，只把它们挪到同组末尾。
        partial = [r for r in kept if spec_level_for_result(spec_tokens, r) == "partial"]
        if partial:
            partial_ids = {id(r) for r in partial}
            kept = [r for r in kept if id(r) not in partial_ids] + partial
            stats["spec_partial_downranked"] = len(partial)

    return kept, stats

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
from .spec_tokens import extract_spec_tokens, is_mixed_model_page, spec_level_for_result

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
    """
    text = (result.content or "").strip()
    if not text:
        return False
    if len(text) >= 200:
        return True
    sentences = len(re.findall(r"[。！？!?；;]", text))
    if len(text) >= 120 and sentences >= 2:
        return True
    return len(text) >= 60 and sentences >= 3


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

    旧实现只看 URL/标题形态，把后者也一并剔除了，与判分口径不一致（Q1 的每日新闻汇总就被误伤）。
    """
    if not looks_like_column(result):
        return False
    return not has_substantive_content(result)


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

    steps: list[tuple[str, Callable[[list[SearchResult]], tuple[list, list]]]] = []
    if drop_script_mismatch:
        steps.append(
            ("script_mismatch", lambda items: _split(items, lambda r: has_script_mismatch(query, r.title)))
        )
    if drop_aggregator_pages:
        steps.append(("aggregator_page", lambda items: _split(items, is_aggregator_page)))
    spec_tokens = extract_spec_tokens(query)
    if spec_tokens:
        # 规格不匹配（如查询 iPhone 17 Pro 却给 iPhone 8、查询 Python 3.13 却给 3.14）：
        # 词面覆盖率看不出这类错误，只有规格 token 能抓到。候选充足时剔除，不足时按缺陷轻重补回。
        #
        # 2026-09-30 补充「混杂型号页」：一页列了 17/16/15/14/13… 的二手回收/型号大全页，
        # 标题里 17 与 pro 都命中 → token 匹配会误判为「匹配」。这种页面**不能**算规格达标，
        # 与聚合页口径同源处理（形态不对 + 无实质针对性 → 剔除；候选不足时补回并标 degraded）。
        steps.append(
            (
                "spec_mismatch",
                lambda items: _split(
                    items,
                    lambda r: spec_level_for_result(spec_tokens, r) == "none"
                    or is_mixed_model_page(r.title, r.content),
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

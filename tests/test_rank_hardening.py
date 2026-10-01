"""通用相关性加固的离线测试（2026-09-30）：规格 token 过滤 + 聚合页口径对齐。"""

from __future__ import annotations

import pytest

from utf8_search.models import ExtractItem, SearchRequest, SearchResult
from utf8_search.rank.diversity import (
    apply_rank_filters,
    has_item_like_content,
    has_substantive_content,
    is_aggregator_page,
    is_content_farm,
    is_offtopic_index_page,
    looks_like_offtopic_index_page,
    off_topic_form,
)
from utf8_search.rank.spec_tokens import extract_spec_tokens, modifier_exact_match


def _r(title: str, url: str, content: str = "摘要内容", **kwargs) -> SearchResult:
    return SearchResult(title=title, url=url, content=content, **kwargs)


_LONG = "这是一段有实质内容的正文。" * 12  # 240 字，含多个句末标点


# ---------------------------------------------------------------- D) 聚合页口径
def test_column_page_with_only_navigation_is_aggregator() -> None:
    """正例：频道页 + 短导航摘要 → 聚合页。"""
    page = _r("新浪财经 - 财经首页", "https://finance.sina.com.cn/", "财经 股票 基金 期货 银行")
    assert is_aggregator_page(page) is True
    assert has_substantive_content(page) is False


def test_daily_roundup_with_substantive_content_is_kept() -> None:
    """负例：标题含「日报/汇总」但正文有实质内容 → 必须保留（2-9 的 Q1 就是这种）。"""
    page = _r(
        "2026年9月26日新闻速览：高铁、假期与政策发布",
        "https://www.sina.cn/news/daily/20260926",
        _LONG,
    )
    assert is_aggregator_page(page) is False
    assert has_substantive_content(page) is True


def test_article_path_never_aggregator() -> None:
    """负例：文章路径（含日期/序号）即便摘要很短也不是聚合页。"""
    page = _r("商务部召开例行新闻发布会", "https://www.mofcom.gov.cn/xwfb/202609/t20260903_1.html", "简短")
    assert looks_like_column(page) is False if False else is_aggregator_page(page) is False


def test_boilerplate_homepage_is_aggregator() -> None:
    """T6①：站点首页的「实质内容」若是自我介绍（无条目）→ 判聚合页（Q3 的 newsfilter.io）。"""
    page = _r(
        "Business & Financial News | newsfilter.io",
        "https://newsfilter.io/",
        "We deliver real-time business and markets news to the world covering FDA approvals, M&A, "
        "corporate filings, guidance and other market-moving events as they happen. Our platform "
        "aggregates filings, press releases and regulatory notices so that analysts and investors "
        "can monitor the stories that matter as they develop across global markets.",
    )
    assert has_substantive_content(page) is True   # 旧判据正是被这条放行
    assert has_item_like_content(page) is False
    assert is_aggregator_page(page) is True


def test_homepage_with_dated_items_kept() -> None:
    """反向：首页/栏目页的实质内容是**带日期的条目** → 保持豁免（发改委首页 / 美国之音首页的形态）。"""
    ndrc = _r(
        "中华人民共和国国家发展和改革委员会",
        "https://www.ndrc.gov.cn/",
        "July 22, 2026 — 2026年9月11日国家对成品油价格实施调控 · 拥抱“十五五” 共谋新发展 "
        "“国家发展改革委与美在华跨国企业高层圆桌会”在京举行 · 时政要闻｜习近平给四川大学全体师生回信 "
        "· 国家发展改革委举行9月份新闻发布会 · 关于健全社会信用体系的意见 · 2026年8月全国能源生产情况发布 "
        "· 国家发展改革委下达中央预算内投资支持灾后恢复重建 · 关于印发促进民间投资高质量发展若干措施的通知",
    )
    voa = _r(
        "美国之音中文网新闻 - 美国之音中文网",
        "https://www.voachinese.com/",
        "5 days ago — 唐纳德·特朗普总统在结束接待中国国家主席习近平对美国进行的三天国事访问之际表示，"
        "美国展示了实力以及与中国的友谊。这次在华盛顿举行的美中峰会持续了三天，双方讨论了贸易、"
        "关税与地区安全等议题。白宫方面表示，双方同意继续就相关问题保持沟通。分析人士认为，"
        "这次访问对下一阶段的经贸谈判具有重要影响。",
    )
    assert is_aggregator_page(ndrc) is False
    assert is_aggregator_page(voa) is False


def test_content_farm_dropped_hard_for_unrelated_query() -> None:
    """T6②：短剧/成人视频内容农场站 → 与无关查询硬剔除（不参与候选不足补回）。"""
    farm = _r(
        "高三爱情故事 - 短剧视频在线观看 | 黄果短剧",
        "https://c4cab.kmexvuoz.cc/video/117/",
        "最近，应心理学教授徐立铭的邀请…（色情文案）",
    )
    assert is_content_farm(farm, "最近一周 AI 行业动态") is True
    good = [
        _r("AI 行业本周动态汇总", "https://example.com/blog/ai-weekly", _LONG),
        _r("本周 AI 融资与产品发布", "https://example.com/news/ai-funding", _LONG),
    ]
    kept, stats = apply_rank_filters(
        [farm, *good], query="最近一周 AI 行业动态", max_results=5, min_query_coverage=0.0
    )
    assert farm not in kept            # 硬剔除：即使只剩 2 条也不补回垃圾站
    assert stats["content_farm"] == 1


def test_content_farm_kept_when_query_is_about_it() -> None:
    """查询本身就在找短剧时，这类站点不受该规则影响。"""
    farm = _r("高三爱情故事 - 短剧视频在线观看", "https://c4cab.kmexvuoz.cc/video/117/", "短剧")
    assert is_content_farm(farm, "短剧 推荐 在线观看") is False


# ---------------------------------------------------------------- G) 三类无关形态（2026-10-01 T7，治 Q1）
def test_tv_program_page_dropped() -> None:
    """央视《生活圈》这类「《节目名》+ 播出日期」的节目页（正文只有导航）→ 剔除。"""
    page = _r(
        "《生活圈》 20260929",
        "https://tv.cctv.cn/2026/09/29/VIDESfISMBwPEqekFNwu0TEc260929.shtml",
        "新闻 国内 国际 评论 经济 军事 科技 法治 文娱 人物 公益 图片.高墙内外.",
    )
    assert off_topic_form(page, "2026年9月 国内外重大新闻") == "tv_program"
    results = [
        page,
        _r("从台海到日本，习近平试图“撬动”特朗普的亚太立场", "https://cn.nytimes.com/china/20260928/summit/", _LONG),
        _r("扩大军事足迹 中老两军班根机场联合保障和训练中心挂牌运行", "https://www.rfi.fr/cn/亚洲/20260929-x/", _LONG),
        _r("商务部召开例行新闻发布会", "https://www.mofcom.gov.cn/xwfb/202609/t20260903_1.html", _LONG),
    ]
    kept, stats = apply_rank_filters(
        results, query="2026年9月 国内外重大新闻", max_results=3, min_query_coverage=0.0
    )
    assert "《生活圈》 20260929" not in [r.title for r in kept]
    assert stats["offtopic_form"] == 1


def test_tv_program_kept_when_query_is_about_programs() -> None:
    """查询本身在找节目时，节目页不受影响。"""
    page = _r("《生活圈》 20260929", "https://tv.cctv.cn/2026/09/29/x.shtml", "节目单")
    assert off_topic_form(page, "央视 生活圈 节目 视频") is None


def test_campus_page_dropped() -> None:
    """院校迎新/开学页（正文为空）→ 剔除。"""
    page = _r(
        "2026年9月学期新生迎新 – 仁川国际机场",
        "https://www.jbsc.ac.kr/portal/liuxue_chn/bbs/view.do?boardSeq=81432",
        "",
    )
    assert off_topic_form(page, "2026年9月 国内外重大新闻") == "campus_page"


def test_campus_article_with_content_kept() -> None:
    """负例：标题含「开学」但正文是长文的新闻稿 → 不误伤。"""
    page = _r("多地中小学开学第一课聚焦安全教育", "https://www.example.com/news/20260901/school.html", _LONG)
    assert off_topic_form(page, "2026年9月 国内外重大新闻") is None
    assert off_topic_form(page, "开学 第一课 中小学") is None


def test_almanac_page_dropped() -> None:
    """开运日历/黄历/占卜页 → 剔除（查询不涉及该类主题时）。"""
    page = _r(
        "【2026年9月の開運日カレンダー】一粒万倍日・吉日一覧｜開運待ち受け",
        "https://www.hana-pla.com/wallpaper/luckyday-calendar202609/",
        "2026年9月の開運日カレンダーと、開運待ち受けを取り入れるタイミングをまとめました。一粒万倍日や寅の日…",
    )
    assert off_topic_form(page, "2026年9月 国内外重大新闻") == "almanac_page"
    assert off_topic_form(page, "2026年9月 开运 吉日") is None


# ---------------------------------------------------------------- B) 规格 token 过滤
def test_spec_mismatch_dropped_when_candidates_sufficient() -> None:
    """查询 iPhone 17 Pro：候选充足时剔除「iPhone 8」这类规格不符的结果。"""
    results = [
        _r("iPhone8手机参数 - 京东", "https://www.jd.com/hprm/8.html"),
        _r("Apple iPhone 17 Pro 参数/价格", "https://zh.kalvo.com/iphone-17-pro.html"),
        _r("iPhone 17 Pro 报价 - ZOL", "https://detail.zol.com.cn/17pro.html"),
        _r("iPhone 17 iPhone 对比", "https://example.com/17.html"),
        _r("iPhone 17 Pro 评测", "https://example.com/review.html"),
        _r("iPhone 17 Pro 上市时间", "https://example.com/time.html"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro 价格 参数", max_results=3, min_query_coverage=0.0
    )
    titles = [r.title for r in kept]
    assert "iPhone8手机参数 - 京东" not in titles
    # 2026-10-01（T5）：修饰词精确匹配后，「iPhone 17 iPhone 对比」（缺 Pro）也算不匹配 → 2 条
    assert stats["spec_mismatch"] == 2
    assert kept[0].title.startswith("Apple iPhone 17 Pro")


def test_spec_mismatch_refilled_and_flagged_when_insufficient() -> None:
    """候选不足时只降权并记 refilled（上层据此标 degraded），不静默丢空结果。"""
    results = [
        _r("iPhone8手机参数 - 京东", "https://www.jd.com/hprm/8.html"),
        _r("Apple iPhone 17 Pro 参数", "https://zh.kalvo.com/iphone-17-pro.html"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro", max_results=3, min_query_coverage=0.0
    )
    assert len(kept) == 2  # 补回来了（不掏空结果集）
    assert stats["spec_mismatch_refilled"] == 1
    assert kept[0].title.startswith("Apple")  # 合规结果仍排在前面


def test_partial_spec_downranked_to_end() -> None:
    """品牌短语部分匹配（结果只有 5090、没有 RTX 5090）仍按降权处理：挪到同组末尾。"""
    results = [
        _r("5090 显卡跑分榜", "https://example.com/5090-bench"),
        _r("RTX 5090 评测与价格", "https://example.com/rtx-5090"),
    ]
    kept, stats = apply_rank_filters(
        results, query="RTX 5090 benchmark 价格", max_results=2, min_query_coverage=0.0
    )
    assert [r.title for r in kept][0].startswith("RTX 5090")
    assert stats.get("spec_partial_downranked") == 1


def test_query_without_spec_tokens_unchanged() -> None:
    """没有规格 token 的查询（如「最近一周 AI 行业动态」）行为完全不变：不剔除、不降权。"""
    results = [
        _r("AI行业发展一周动态 - 知乎专栏", "https://zhuanlan.zhihu.com/p/1"),
        _r("每日AI资讯、热点、动态", "https://ai-bot.cn/daily-ai-news/"),
        _r("本周 AI 融资与产品发布汇总", "https://example.com/news/ai-weekly"),
    ]
    kept, stats = apply_rank_filters(
        results, query="最近一周 AI 行业动态", max_results=3, min_query_coverage=0.0
    )
    assert kept == results  # 顺序与内容都不变
    assert "spec_mismatch" not in stats and "spec_partial_downranked" not in stats


def test_date_numbers_do_not_trigger_spec_filter() -> None:
    """「2026年9月 国内外重大新闻」里的年份/月份不是规格 token → 不过滤。"""
    results = [
        _r("习近平访美后续 - 纽约时报中文网", "https://cn.nytimes.com/a"),
        _r("商务部召开例行新闻发布会", "https://www.mofcom.gov.cn/b"),
    ]
    kept, stats = apply_rank_filters(
        results, query="2026年9月 国内外重大新闻", max_results=2, min_query_coverage=0.0
    )
    assert kept == results
    assert "spec_mismatch" not in stats


# ---------------------------------------------------------------- E) 修饰词精确匹配（2026-10-01 T5，治 Q16）
def test_modifier_pro_max_rejected_for_pro_query() -> None:
    """查询 Pro：只有 Pro Max 的结果 = 「多」另一种机型 → 候选充足时剔除（线上 Q16 的 wirefly）。"""
    results = [
        _r("Apple iPhone 17 Pro Max", "https://www.wirefly.com/product/apple-iphone-17-pro-max"),
        _r("iPhone 17 Pro 参数与价格", "https://example.com/products/iphone-17-pro"),
        _r("iPhone 17 Pro 评测", "https://example.com/reviews/iphone-17-pro"),
        _r("Apple iPhone 17 Pro 官方", "https://www.apple.com/iphone-17-pro"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro 价格 参数", max_results=3, min_query_coverage=0.0
    )
    assert "Apple iPhone 17 Pro Max" not in [r.title for r in kept]
    assert stats["spec_mismatch"] == 1


def test_modifier_missing_is_mismatch_not_partial() -> None:
    """查询 Pro：结果只有 iPhone 17（缺修饰词）→ 同样判不匹配，而不是 partial 降权。"""
    results = [
        _r("iPhone 17 256GB 报价", "https://example.com/products/iphone-17-256"),
        _r("iPhone 17 Pro 参数", "https://example.com/products/iphone-17-pro"),
        _r("iPhone 17 Pro 评测", "https://example.com/reviews/iphone-17-pro-review"),
        _r("iPhone 17 Pro 价格", "https://example.com/prices/iphone-17-pro-price"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro 参数", max_results=3, min_query_coverage=0.0
    )
    assert "iPhone 17 256GB 报价" not in [r.title for r in kept]
    assert stats["spec_mismatch"] == 1
    assert "spec_partial_downranked" not in stats


def test_modifier_both_variants_page_kept() -> None:
    """页面同时发布 17 Pro 与 17 Pro Max（Apple 发布会稿）→ 存在独立出现的 Pro → 保留。"""
    page = _r(
        "Apple、iPhone 17 ProとiPhone 17 Pro Maxを発表 - Apple",
        "https://www.apple.com/jp/newsroom/2025/09/apple-unveils-iphone-17-pro-and-iphone-17-pro-max/",
    )
    assert modifier_exact_match(
        extract_spec_tokens("iPhone 17 Pro 价格 参数"), title=page.title, url=page.url
    ) is True
    kept, stats = apply_rank_filters(
        [page, _r("iPhone 17 Pro 参数", "https://example.com/products/iphone-17-pro")],
        query="iPhone 17 Pro 价格 参数",
        max_results=2,
        min_query_coverage=0.0,
    )
    assert page in kept and stats["spec_mismatch"] == 0


def test_modifier_rule_inactive_without_modifier_in_query() -> None:
    """查询没有修饰词（RTX 5090）→ 修饰词规则完全不生效。"""
    assert modifier_exact_match(extract_spec_tokens("RTX 5090 benchmark 价格"), title="RTX 5090 跑分") is True


def test_modifier_ignores_nav_mentions_in_content() -> None:
    """只看标题/URL：Spigen 的 Pro Max 保护壳集合页正文里出现「iPhone 17 Pro」链接也不算匹配。"""
    tokens = extract_spec_tokens("iPhone 17 Pro 价格 参数")
    assert (
        modifier_exact_match(
            tokens,
            title="iPhone 17 Pro Max Case Collection - Spigen.com Official Site",
            url="https://www.spigen.com/collections/iphone-17-pro-max-case-collection",
        )
        is False
    )
    results = [
        _r(
            "iPhone 17 Pro Max Case Collection - Spigen.com Official Site",
            "https://www.spigen.com/collections/iphone-17-pro-max-case-collection",
            "Protect your iPhone 17 Pro Max with one of our cases. iPhone 17 Pro / iPhone 17 / iPhone Air 也可选购。",
        ),
        _r("iPhone 17 Pro 参数与价格", "https://example.com/products/iphone-17-pro"),
        _r("iPhone 17 Pro 评测", "https://example.com/reviews/iphone-17-pro"),
        _r("iPhone 17 Pro 官方", "https://www.apple.com/iphone-17-pro"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro 价格 参数", max_results=3, min_query_coverage=0.0
    )
    assert "iPhone 17 Pro Max Case Collection - Spigen.com Official Site" not in [r.title for r in kept]
    assert stats["spec_mismatch"] == 1


def test_modifier_handles_url_encoded_variant() -> None:
    """URL 里用 +/%20 编码的机型也算「被延长」：Spigen 的 `…device=iPhone+17+Pro+Max` ≠ Pro。"""
    tokens = extract_spec_tokens("iPhone 17 Pro 价格 参数")
    assert (
        modifier_exact_match(
            tokens,
            title="iPhone 17 Pro Max Case Collection - Spigen.com Official Site",
            url=(
                "https://www.spigen.com/collections/iphone-17-pro-max-case-collection"
                "?sort_by=manual&filter.v.option.device=iPhone+17+Pro+Max&current.device.choice=iPhone+17+Pro+Max"
            ),
        )
        is False
    )


# ---------------------------------------------------------------- F) 非主题页（2026-10-01 T5，治 Q6）
_SHORT = "求推荐油管频道，国内后端就业现在什么行情？Python的类型提示越来越复杂了：Python3.13又引入了类型注解新特性"


def test_offtopic_profile_page_dropped() -> None:
    """社区个人主页（V2EX member 页：只有最近发帖列表）→ 非主题页，候选充足时剔除。"""
    page = _r("zywscq - V2EX", "https://www.v2ex.com/member/zywscq", _SHORT)
    assert looks_like_offtopic_index_page(page) is True
    assert is_offtopic_index_page(page) is True
    results = [
        page,
        _r("Python 3.13 新特性详解", "https://example.com/blog/python-313-new-features", _LONG),
        _r("Python 3.13 正式版发布", "https://example.com/news/python-313-released", _LONG),
        _r("Python 3.13 的 REPL 改进", "https://example.com/blog/python-313-repl", _LONG),
        _r("Python 3.13 性能与新特性", "https://example.com/blog/python-313-performance", _LONG),
    ]
    kept, stats = apply_rank_filters(
        results, query="Python 3.13 新特性", max_results=3, min_query_coverage=0.0
    )
    assert "zywscq - V2EX" not in [r.title for r in kept]
    assert stats["offtopic_page"] == 1


def test_registry_formula_page_dropped() -> None:
    """包索引页（brew formula：正文只有一行元数据）→ 非主题页，候选充足时剔除。"""
    page = _r(
        "python@3.13",
        "https://formulae.brew.sh/formula/python@3.13",
        "Formula JSON API: /api/formula/python@3.13.json",
    )
    assert is_offtopic_index_page(page) is True
    results = [
        page,
        _r("Python 3.13 新特性", "https://example.com/blog/python-313-whats-new", _LONG),
        _r("Python 3.13 发布说明", "https://example.com/news/python-313-release-notes", _LONG),
        _r("Python 3.13 REPL", "https://example.com/blog/python-313-repl-guide", _LONG),
        _r("Python 3.13 JIT", "https://example.com/blog/python-313-jit", _LONG),
    ]
    kept, stats = apply_rank_filters(
        results, query="Python 3.13 新特性", max_results=3, min_query_coverage=0.0
    )
    assert "python@3.13" not in [r.title for r in kept]
    assert stats["offtopic_page"] == 1


def test_image_board_page_dropped() -> None:
    """图片素材板（Pinterest ideas 页，无文章内容）→ 非主题页，候选充足时剔除。"""
    page = _r(
        "Iphone 17 Pro Aesthetic",
        "https://ru.pinterest.com/ideas/iphone-17-pro-aesthetic/950517759345/",
        "Ознакомьтесь с наилучшими идеями на тему «Iphone 17 pro aesthetic» от Pinterest",
    )
    assert is_offtopic_index_page(page) is True


def test_offtopic_form_keeps_substantive_page() -> None:
    """形态命中但正文有实质内容 → 保留（不误伤社区长文与注册表的完整说明页）。"""
    forum_post = _r("zywscq - V2EX", "https://www.v2ex.com/member/zywscq", _LONG)
    pypi_page = _r("requests · PyPI", "https://pypi.org/project/requests/", _LONG)
    assert looks_like_offtopic_index_page(forum_post) is True
    assert is_offtopic_index_page(forum_post) is False
    assert is_offtopic_index_page(pypi_page) is False


def test_offtopic_rule_off_when_aggregator_filter_disabled() -> None:
    """新闻路径（drop_aggregator_pages=False）不受非主题页规则影响：结果原样保留。"""
    page = _r("python@3.13", "https://formulae.brew.sh/formula/python@3.13", "Formula JSON API")
    kept, stats = apply_rank_filters(
        [page],
        query="Python 3.13 新特性",
        max_results=1,
        min_query_coverage=0.0,
        drop_aggregator_pages=False,
    )
    assert kept == [page] and "offtopic_page" not in stats


# ---------------------------------------------------------------- C) 混杂型号/回收列表页
def test_mixed_model_recycle_page_dropped() -> None:
    """Q16 的京东「苹果8x参数」二手回收页：标题里 17/16/15/14/13… 与 pro 都命中，
    但它是型号大全/回收列表，不能算规格匹配 → 与聚合页同源剔除。"""
    from utf8_search.rank.spec_tokens import is_mixed_model_page

    title = "Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus 二手手机"
    assert is_mixed_model_page(title) is True
    results = [
        _r(title, "https://www.jd.com/hprm/8.html", "苹果8x参数 二手回收"),
        _r("Apple iPhone 17 Pro - 参数/价格", "https://zh.kalvo.com/17pro.html", "iPhone 17 Pro 规格"),
        _r("iPhone 17 Pro 报价 - ZOL", "https://detail.zol.com.cn/17pro.html", "iPhone 17 Pro 报价"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro 价格 参数", max_results=2, min_query_coverage=0.0
    )
    assert all("二手" not in r.title for r in kept)
    assert stats["spec_mismatch"] == 1


def test_compare_page_between_two_models_is_kept() -> None:
    """两型号对比页（17 Pro vs 17 Pro Max）不算混杂列表 → 保留。"""
    from utf8_search.rank.spec_tokens import is_mixed_model_page

    assert is_mixed_model_page("iPhone 17 Pro vs iPhone 17 Pro Max 对比") is False
    results = [
        _r("iPhone 17 Pro vs iPhone 17 Pro Max 对比", "https://example.com/compare", "两机型参数对比"),
        _r("Apple iPhone 17 Pro 参数", "https://example.com/pro", "规格"),
    ]
    kept, stats = apply_rank_filters(
        results, query="iPhone 17 Pro", max_results=2, min_query_coverage=0.0
    )
    assert len(kept) == 2
    assert stats["spec_mismatch"] == 0


def test_mixed_model_rule_not_applied_without_spec_tokens() -> None:
    """无规格 token 的查询（如「最近一周 AI 行业动态」）完全不受混杂型号判据影响。"""
    results = [
        _r("2025/2024/2023 年度盘点合集", "https://example.com/roundup", "历年盘点"),
        _r("AI 行业周报", "https://example.com/weekly", "本周动态"),
    ]
    kept, stats = apply_rank_filters(
        results, query="最近一周 AI 行业动态", max_results=2, min_query_coverage=0.0
    )
    assert kept == results
    assert "spec_mismatch" not in stats


# ---------------------------------------------------------------- P1 形态轻降权
def test_form_penalty_downranks_column_page_mildly() -> None:
    """含实质内容的首页/栏目页 ×0.95：分数不变的是普通文章，汇总页轻微降权后让位。"""
    from utf8_search.rank.diversity import apply_form_penalty, form_score_multiplier

    article = _r("商务部召开例行新闻发布会（2026年9月3日）", "https://www.mofcom.gov.cn/xwfb/202609/t20260903_1.html", _LONG)
    roundup = _r("2026年9月26日新闻速览：高铁、假期与政策发布", "https://www.sina.cn/news/", _LONG)
    article.score, roundup.score = 0.60, 0.61  # 汇总页原本略高
    assert form_score_multiplier(article) == 1.0
    assert form_score_multiplier(roundup) == 0.95

    ordered = apply_form_penalty([roundup, article])
    assert [r.title for r in ordered][0].startswith("商务部")  # 0.61×0.95=0.5795 < 0.60
    assert roundup in ordered  # 只降权、不剔除


def test_form_penalty_keeps_daily_roundup_not_over_penalized(settings, tmp_path) -> None:
    """日报/汇总类文章不得被误降到底部：与同分文章相比只差 5%。"""
    from utf8_search.rank.diversity import apply_form_penalty

    roundup = _r("AI 行业发展一周动态", "https://zhuanlan.zhihu.com/", _LONG)
    other = _r("某篇普通文章", "https://example.com/a/1.html", _LONG)
    roundup.score, other.score = 0.80, 0.78
    ordered = apply_form_penalty([roundup, other])
    # 分数接近时让位（有效分 0.80×0.95=0.76 < 0.78）—— 这正是"轻微降权"的预期效果，不是误杀
    assert ordered[0] is other
    # P7：score 不再被原地修改（乘子只用于排序 key），对外字段保持相关性原始分
    assert roundup.score == pytest.approx(0.80, abs=1e-9)
    assert other.score == pytest.approx(0.78, abs=1e-9)
    # 反向：汇总页明显更相关时依然排第一
    roundup.score, other.score = 0.80, 0.60
    assert apply_form_penalty([roundup, other])[0] is roundup


def test_form_penalty_is_idempotent() -> None:
    """P7 回归：重复调用 apply_form_penalty 结果不变（不许出现 ×0.9025 的二次降权）。"""
    from utf8_search.rank.diversity import apply_form_penalty

    column_a = _r("2026年9月26日新闻速览", "https://www.sina.cn/news/", _LONG)
    column_b = _r("AI 行业发展一周动态", "https://zhuanlan.zhihu.com/", _LONG)
    article = _r("商务部召开例行新闻发布会", "https://www.mofcom.gov.cn/xwfb/202609/t20260903_1.html", _LONG)
    column_a.score, column_b.score, article.score = 0.61, 0.60, 0.60
    original_scores = {id(r): r.score for r in (column_a, column_b, article)}

    once = apply_form_penalty([column_a, column_b, article])
    twice = apply_form_penalty(list(once))
    thrice = apply_form_penalty(list(twice))

    assert [r.title for r in once] == [r.title for r in twice] == [r.title for r in thrice]
    for result in (column_a, column_b, article):
        assert result.score == pytest.approx(original_scores[id(result)], abs=1e-12)


# ---------------------------------------------------------------- C) Bing 兜底相关性闸门
class _BingProvider:
    name = "bing"

    def __init__(self, hits) -> None:
        self._hits = hits

    async def search(self, query, **kwargs):  # noqa: ANN003
        return list(self._hits)


class _EmptySearxng:
    name = "searxng"
    unresponsive_engines: list[str] = []

    async def search(self, query, **kwargs):  # noqa: ANN003
        return []


class _Extractor:
    async def fetch_date(self, url, *, download_timeout=None):  # noqa: ANN001
        return None

    async def extract(self, url, **kwargs):  # noqa: ANN001
        return ExtractItem(url=url, raw_content="正文", chars=2)


async def _pipeline(settings, tmp_path, providers):
    import httpx

    from utf8_search.cache.store import CacheStore
    from utf8_search.core.pipeline import SearchPipeline

    cache = CacheStore(str(tmp_path / "rank.db"))
    await cache.open()
    return SearchPipeline(
        settings, client=httpx.AsyncClient(), cache=cache, providers=providers, extractor=_Extractor()
    )


async def test_bing_fallback_low_relevance_not_injected(settings, tmp_path) -> None:
    """兜底结果与查询无关（沃尔玛滤水器页 vs AI 行业动态）→ 不入池，并记 degraded 原因。"""
    from utf8_search.providers.base import SearchHit

    junk = [
        SearchHit(title="Walmart Water Filters", url="https://www.walmart.com/browse/water-filters",
                  snippet="Shop water filters"),
        SearchHit(title="2026 FIFA World Cup", url="https://en.wikipedia.org/wiki/2026_FIFA_World_Cup",
                  snippet="The 2026 World Cup"),
    ]
    pipeline = await _pipeline(settings, tmp_path, [_EmptySearxng(), _BingProvider(junk)])
    hits, engines_used, _failed, degraded = await pipeline._collect_hits(
        SearchRequest(query="最近一周 AI 行业动态", max_results=3, topic="general")
    )
    assert hits == []
    assert "bing" not in engines_used
    assert degraded is not None and "fallback_low_relevance" in degraded
    await pipeline.close()


async def test_bing_fallback_relevant_result_still_injected(settings, tmp_path) -> None:
    """命中查询词的兜底结果仍可入池（闸门只挡无关项，不禁用兜底）。"""
    from utf8_search.providers.base import SearchHit

    good = [
        SearchHit(title="AI 行业动态一周汇总", url="https://example.com/ai-weekly",
                  snippet="最近一周 AI 行业动态与融资事件"),
    ]
    pipeline = await _pipeline(settings, tmp_path, [_EmptySearxng(), _BingProvider(good)])
    hits, engines_used, _failed, _degraded = await pipeline._collect_hits(
        SearchRequest(query="最近一周 AI 行业动态", max_results=3, topic="general")
    )
    assert len(hits) == 1 and engines_used == ["bing"]
    await pipeline.close()

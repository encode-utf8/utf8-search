"""通用相关性加固的离线测试（2026-09-30）：规格 token 过滤 + 聚合页口径对齐。"""

from __future__ import annotations

from utf8_search.models import ExtractItem, SearchRequest, SearchResult
from utf8_search.rank.diversity import apply_rank_filters, has_substantive_content, is_aggregator_page


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
    assert stats["spec_mismatch"] == 1
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


def test_partial_spec_downranked() -> None:
    """部分匹配（iPhone 17 对 iPhone 17 Pro）降权到末尾，而不是剔除。"""
    results = [
        _r("【苹果iPhone 17 256GB】报价_参数", "https://detail.zol.com.cn/17.html"),
        _r("Apple iPhone 17 Pro 参数", "https://zh.kalvo.com/17pro.html"),
    ]
    kept, stats = apply_rank_filters(results, query="iPhone 17 Pro", max_results=2, min_query_coverage=0.0)
    assert [r.title for r in kept][0].startswith("Apple")
    assert stats.get("spec_partial_downranked") == 1


def test_query_without_spec_tokens_unchanged() -> None:
    """没有规格 token 的查询（如「最近一周 AI 行业动态」）行为完全不变：不剔除、不降权。"""
    results = [
        _r("AI行业发展一周动态 - 知乎专栏", "https://zhuanlan.zhihu.com/p/1"),
        _r("每日AI资讯、热点、动态", "https://ai-bot.cn/daily-ai-news/"),
        _r("npm nocache 包", "https://www.npmjs.com/package/nocache"),
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

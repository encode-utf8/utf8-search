"""结果质量与多样性单测（验收项 5.3-2 ~ 5.3-6），全部离线。

覆盖同站限流、脚本一致性、聚合页识别、查询词覆盖度，以及「候选不足时按原排序补回」这一兜底原则。
"""

from __future__ import annotations

from utf8_search.models import SearchResult
from utf8_search.rank.diversity import (
    apply_rank_filters,
    has_script_mismatch,
    is_aggregator_page,
    is_cjk_query,
    limit_per_host,
    query_coverage,
    registrable_domain,
)


def _r(title: str, url: str, content: str = "示例正文" * 10) -> SearchResult:
    return SearchResult(title=title, url=url, content=content)


# ---------------------------------------------------------------- 域名与同站
def test_registrable_domain_handles_multi_label_suffix() -> None:
    assert registrable_domain("https://typhoon.slt.zj.gov.cn/a/b") == "zj.gov.cn"
    assert registrable_domain("https://typhoon.weather.com.cn/x") == "weather.com.cn"
    assert registrable_domain("https://post.smzdm.com/p/1") == "smzdm.com"
    assert registrable_domain("https://m.news.example.co.uk/x") == "example.co.uk"
    assert registrable_domain("bad-url") == ""


def test_limit_per_host_keeps_first_n() -> None:
    results = [_r(f"标题{i}", "https://www.bilibili.com/video/1") for i in range(5)]
    results.append(_r("别站", "https://example.com/a"))
    kept, dropped = limit_per_host(results, 2)
    assert len(kept) == 3  # 同站前 2 条 + 别站 1 条
    assert len(dropped) == 3
    assert kept[0].title == "标题0" and kept[1].title == "标题1"


def test_limit_per_host_disabled_when_zero() -> None:
    results = [_r("a", "https://x.com/1"), _r("b", "https://x.com/2"), _r("c", "https://x.com/3")]
    kept, dropped = limit_per_host(results, 0)
    assert kept == results and dropped == []


# ---------------------------------------------------------------- 脚本一致性
def test_is_cjk_query_detects_mixed_queries() -> None:
    """中英混排查询也要启用脚本过滤（#16 的俄语开箱正是这样漏掉的）。"""
    assert is_cjk_query("台风 最新消息 路径")
    assert is_cjk_query("iPhone 17 Pro 价格 参数")
    assert is_cjk_query("RTX 5090 benchmark 价格")
    assert not is_cjk_query("how does HTTP/3 QUIC work")
    assert not is_cjk_query("EU AI Act compliance requirements")


def test_script_mismatch_only_drops_other_scripts() -> None:
    query = "iPhone 17 Pro 价格 参数"
    # 混排标题（俄语 + 拉丁）也要判出不匹配 —— 这是 #16 的真实形态
    assert has_script_mismatch(query, "ГОД С iPHONE 17 / PRO / AIR - YouTube")
    assert has_script_mismatch("扫地机器人 推荐", "레고 배트맨 공략")
    # 中文 / 英文 / 日文结果都必须保留
    assert not has_script_mismatch(query, "【苹果iPhone 17 Pro 256GB】报价_参数")
    assert not has_script_mismatch(query, "Apple unveils iPhone 17 Pro and iPhone 17 Pro Max")
    assert not has_script_mismatch("台风 路径", "台風情報 - 気象庁")
    # 纯英文查询不启用该过滤
    assert not has_script_mismatch("latest news", "ГОД С iPHONE")


# ---------------------------------------------------------------- 聚合页
def test_is_aggregator_page() -> None:
    assert is_aggregator_page(_r("某站首页", "https://www.ai.ch/"))  # 站点首页
    assert is_aggregator_page(_r("新闻资讯 - 新闻超市 分类频道", "https://www.uijae.com/news"))
    assert is_aggregator_page(_r("产品中心", "https://example.com/products/list.html"))
    # 频道 / 标签 / 专题页（URL 形态通用约定，不针对具体站点）
    assert is_aggregator_page(_r("国产显卡_最新动态", "https://m.ithome.com/tags/%E5%9B%BD%E4%BA%A7%E6%98%BE%E5%8D%A1"))
    assert is_aggregator_page(_r("数据出境安全评估申报指南", "https://www.toutiao.com/topic/7552310933662533666/"))
    assert is_aggregator_page(_r("摩尔线程资讯", "https://pinpai.smzdm.com/315440/news/"))
    # 正常文章页不能误伤
    assert not is_aggregator_page(_r("台风路径", "https://typhoon.slt.zj.gov.cn/typhoon/detail"))
    assert not is_aggregator_page(_r("报价", "https://detail.zol.com.cn/cell_phone/index1234.shtml"))
    assert not is_aggregator_page(_r("文章", "https://post.smzdm.com/p/av7k3q5m/"))
    assert not is_aggregator_page(_r("台风紫檀最新消息", "https://hz.bendibao.com/news/2026824/172470.shtm"))
    assert not is_aggregator_page(_r("AI 行业新闻", "https://aidaily.fyi/zh/s/industry"))


# ---------------------------------------------------------------- 覆盖度
def test_query_coverage_bounds() -> None:
    assert query_coverage("扫地机器人 推荐 性价比", _r("扫地机器人推荐", "https://a.com/1")) > 0.6
    assert query_coverage("最近一周 AI 行业动态", _r("Appenzell Innerrhoden", "https://ai.ch/1")) == 0.0


# ---------------------------------------------------------------- 组合过滤
def test_apply_rank_filters_composes_and_restores() -> None:
    """候选充足时各过滤器生效（低覆盖 / 同站冗余）。"""
    results = [
        _r("扫地机器人 2026 高性价比推荐", "https://post.smzdm.com/p/1"),
        _r("扫地机器人 全价位对比", "https://www.zhihu.com/question/2"),
        _r("【乐高蝙蝠侠攻略】玩具直销", "https://www.saahov.com/news/lego-1.html"),  # 低覆盖
        _r("美的净水机价格报价", "https://www.jd.com/item/2.html"),  # 低覆盖
        _r("扫地机器人 评测 推荐", "https://post.smzdm.com/p/3"),  # 同站第 2 条
        _r("扫地机器人 选购指南", "https://post.smzdm.com/p/4"),  # 同站第 3 条
    ]
    kept, stats = apply_rank_filters(
        results, query="扫地机器人 推荐 性价比", max_results=2, max_per_host=2, min_query_coverage=0.34
    )
    assert stats["low_coverage"] == 2
    assert stats["same_host"] == 1
    assert stats["aggregator_page"] == 0
    titles = [r.title for r in kept]
    assert "【乐高蝙蝠侠攻略】玩具直销" not in titles
    assert "美的净水机价格报价" not in titles
    assert "扫地机器人 选购指南" not in titles  # 同站超出上限的那条
    assert len(kept) == 3


def test_apply_rank_filters_restores_when_short() -> None:
    """质量过滤绝不能把结果掏空：不足 max_results 时补回被剔除的结果，且保持原排序。"""
    results = [
        _r("无关内容一", "https://a.com/news/detail/1.html"),
        _r("无关内容二", "https://b.com/news/detail/2.html"),
    ]
    kept, stats = apply_rank_filters(results, query="扫地机器人 推荐", max_results=5, min_query_coverage=0.34)
    assert stats["low_coverage"] == 2
    assert kept == results  # 全部补回，且顺序不变


def test_apply_rank_filters_restores_low_coverage_before_aggregator() -> None:
    """补回顺序按缺陷轻重：先补「只有覆盖弱」的，聚合页留到最后。"""
    results = [
        _r("某站_官网首页", "https://agg.com/"),                 # 聚合页，且排在最前
        _r("无关内容一", "https://a.com/news/detail/1.html"),      # 低覆盖
        _r("无关内容二", "https://b.com/news/detail/2.html"),      # 低覆盖
    ]
    kept, stats = apply_rank_filters(
        results, query="扫地机器人 推荐", max_results=2, min_query_coverage=0.34
    )
    assert stats["aggregator_page"] == 1 and stats["low_coverage"] == 2
    # 两条低覆盖的先把名额占满，聚合页（原本排第 1）仍被挡在外面
    assert [r.title for r in kept] == ["无关内容一", "无关内容二"]

    # 实在凑不齐时才把聚合页放回来，但仍然保持原有的相对顺序
    kept_all, _ = apply_rank_filters(
        results, query="扫地机器人 推荐", max_results=3, min_query_coverage=0.34
    )
    assert [r.title for r in kept_all] == ["某站_官网首页", "无关内容一", "无关内容二"]


def test_apply_rank_filters_disabled_is_identity() -> None:
    results = [_r("无关内容", "https://a.com/news/x/1.html"), _r("另一条", "https://a.com/news/x/2.html")]
    kept, _ = apply_rank_filters(
        results,
        query="扫地机器人",
        max_results=5,
        max_per_host=0,
        min_query_coverage=0.0,
        drop_aggregator_pages=False,
        drop_script_mismatch=False,
    )
    assert kept == results

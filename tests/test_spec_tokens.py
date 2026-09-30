"""规格 token 匹配的纯函数测试（2026-09-30）。"""

from __future__ import annotations

from utf8_search.rank.spec_tokens import extract_spec_tokens, match_spec_tokens


def test_extract_versions_and_modifiers() -> None:
    assert extract_spec_tokens("Python 3.13 新特性") == ["3.13"]
    # 品牌短语 + 裸数字都抽出来：iPhone 17（短语）、17（裸数字）、pro（修饰词）
    assert extract_spec_tokens("iPhone 17 Pro 价格 参数") == ["iphone 17", "17", "pro"]
    assert extract_spec_tokens("RTX 5090 benchmark 价格") == ["rtx 5090", "5090"]
    # 连写型号单独成 token（S4000）；「MTT」不是数字邻接词，不单独作为 token
    assert extract_spec_tokens("摩尔线程 MTT S4000 最新型号") == ["s4000"]


def test_extract_ignores_years_and_dates() -> None:
    """年份/日期不是规格 token —— 否则「2026年 新能源汽车 补贴政策」会被误伤。"""
    assert extract_spec_tokens("2026年 新能源汽车 补贴政策") == []
    assert extract_spec_tokens("2026年9月 国内外重大新闻") == []
    assert extract_spec_tokens("美国 关税 最新政策") == []
    assert extract_spec_tokens("最近一周 AI 行业动态") == []


def test_no_tokens_returns_na_level() -> None:
    """没有规格 token 的查询：level = n/a，调用方必须完全保持原行为。"""
    assert match_spec_tokens([], title="任何标题", content="任何内容").level == "n/a"


def test_full_partial_none_levels() -> None:
    tokens = extract_spec_tokens("iPhone 17 Pro 价格 参数")
    assert match_spec_tokens(tokens, title="Apple iPhone 17 Pro - 参数/价格").level == "full"
    # 只有 17 没有 Pro（iPhone 17 256GB 页）→ 部分匹配
    assert match_spec_tokens(tokens, title="【苹果iPhone 17 256GB】报价_参数").level == "partial"
    # 型号完全不符（iPhone 8）→ 不匹配
    assert match_spec_tokens(tokens, title="iPhone8手机参数 - 京东").level == "none"


def test_version_mismatch_is_none() -> None:
    """Q6：查询 3.13，文章讲 3.14 —— 覆盖度看不出，规格匹配必须判不匹配。"""
    tokens = extract_spec_tokens("Python 3.13 新特性")
    assert match_spec_tokens(tokens, title="python3.13 3.14 新特性好好好").level == "full"  # 同页提到 3.13
    assert match_spec_tokens(tokens, title="Python 3.14 新特性解读").level == "none"
    # 3.13 不能命中 3.130（边界）
    assert match_spec_tokens(tokens, title="build 3.130 released").level == "none"


def test_token_in_url_counts() -> None:
    """URL 里出现版本号也算命中（官方文档路径 /whatsnew/3.13.html 很常见）。"""
    tokens = extract_spec_tokens("Python 3.13 新特性")
    assert match_spec_tokens(tokens, url="https://docs.python.org/zh-cn/dev/whatsnew/3.13.html").level == "full"
    assert match_spec_tokens(tokens, url="https://example.com/2026/09/news").level == "none"


def test_multi_token_mixed_order() -> None:
    """多 token 混排：命中部分 → partial；全中 → full；全不中 → none。"""
    tokens = extract_spec_tokens("RTX 5090 价格 参数 评测")
    assert tokens[0] == "rtx 5090"
    assert match_spec_tokens(tokens, title="PassMark - GeForce RTX 5090 - Price").level == "full"
    assert match_spec_tokens(tokens, title="5090 二手行情").level == "partial"
    assert match_spec_tokens(tokens, title="RTX 4090 评测").level == "none"

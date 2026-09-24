"""融合、去重、重排、域名过滤的单元测试。"""

from __future__ import annotations

from utf8_search.models import SearchResult
from utf8_search.providers.base import SearchHit
from utf8_search.rank.fusion import (
    bm25_scores,
    domain_of,
    filter_domains,
    fuse,
    normalize_url,
    rerank,
    tokenize,
)


def test_normalize_url_removes_tracking_and_fragment() -> None:
    """跟踪参数、fragment、末尾斜杠都应被归一化掉。"""
    url = "https://Example.com/news/1/?utm_source=x&id=7#section"
    assert normalize_url(url) == "https://example.com/news/1?id=7"
    assert normalize_url("https://example.com/a/") == "https://example.com/a"


def test_domain_of_strips_www() -> None:
    assert domain_of("https://www.example.com/a") == "example.com"


def test_fuse_deduplicates_across_engines() -> None:
    """同一 URL 被两个引擎命中时只保留一条，且得分高于单引擎结果。"""
    group_a = [
        SearchHit(title="A", url="https://site.com/a?utm_source=1", snippet="短", engine="brave"),
        SearchHit(title="B", url="https://site.com/b", snippet="只有 brave 命中", engine="brave"),
    ]
    group_b = [
        SearchHit(title="A 完整标题", url="https://site.com/a", snippet="更长的摘要内容", engine="bing"),
    ]
    fused = {result.url: result for result in fuse([group_a, group_b])}

    assert len(fuse([group_a, group_b])) == 2
    multi = next(r for r in fused.values() if r.engine == "bing,brave")
    assert multi.score > next(r for r in fused.values() if r.engine == "brave").score
    assert multi.content == "更长的摘要内容"
    assert multi.title == "A 完整标题"


def test_tokenize_supports_chinese_and_english() -> None:
    tokens = tokenize("OpenAI 发布 GPT-6 模型")
    assert "openai" in tokens
    assert "模型" in tokens  # 中文二元字组


def test_bm25_and_rerank_prioritise_relevant_document() -> None:
    docs = ["OpenAI GPT-6 模型发布", "今天天气不错，适合出门散步"]
    scores = bm25_scores("OpenAI GPT-6", docs)
    assert scores[0] > scores[1]

    results = [
        SearchResult(title="天气", url="https://a.com", content="今天天气不错", score=0.9),
        SearchResult(title="OpenAI", url="https://b.com", content="OpenAI GPT-6 模型发布", score=0.1),
    ]
    ranked = rerank(results, "OpenAI GPT-6")
    assert ranked[0].url == "https://b.com"


def test_filter_domains() -> None:
    results = [
        SearchResult(title="A", url="https://www.gov.cn/a"),
        SearchResult(title="B", url="https://spam.com/b"),
    ]
    assert len(filter_domains(results, include_domains=["gov.cn"])) == 1
    assert len(filter_domains(results, exclude_domains=["spam.com"])) == 1
"""多源结果融合：RRF 排序 + URL 归一化去重 + 轻量 BM25 重排 + 域名过滤。"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..models import SearchResult
from ..providers.base import SearchHit

# 需要在归一化时剔除的跟踪参数
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "spm",
    "from",
    "ref",
    "ref_src",
    "share_token",
    "fbclid",
    "gclid",
    "msclkid",
}

_ASCII_WORD = re.compile(r"[a-zA-Z0-9_]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def normalize_url(url: str) -> str:
    """URL 归一化：小写主机、去跟踪参数、去 fragment、去末尾斜杠。"""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k.lower() not in TRACKING_PARAMS]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query),
            "",
        )
    )


def domain_of(url: str) -> str:
    """取域名（去掉 www. 前缀，便于白/黑名单匹配）。"""
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def tokenize(text: str) -> list[str]:
    """轻量分词：英文按单词，中文按二元字组（避免引入分词依赖）。"""
    lowered = (text or "").lower()
    tokens = _ASCII_WORD.findall(lowered)
    cjk_chars = _CJK.findall(lowered)
    tokens.extend(a + b for a, b in zip(cjk_chars, cjk_chars[1:]))
    tokens.extend(cjk_chars)
    return tokens


def fuse(hit_groups: list[list[SearchHit]], *, k: int = 60) -> list[SearchResult]:
    """RRF 融合多路结果，并按归一化 URL 去重。

    score = Σ 1 / (k + rank_i)，多引擎命中的结果天然获得更高分。
    """
    merged: dict[str, SearchResult] = {}
    engines: dict[str, set[str]] = defaultdict(set)
    rrf_score: dict[str, float] = defaultdict(float)

    for hits in hit_groups:
        for rank, hit in enumerate(hits):
            key = normalize_url(hit.url)
            if not key:
                continue
            rrf_score[key] += 1.0 / (k + rank + 1)
            engines[key].add(hit.engine or "unknown")
            existing = merged.get(key)
            if existing is None:
                merged[key] = SearchResult(
                    title=hit.title,
                    url=hit.url,
                    content=hit.snippet,
                    engine=hit.engine,
                    published_date=hit.published_date,
                )
            else:
                # 同一 URL 被多个引擎命中：摘要取更长的那个，标题取更完整的
                if len(hit.snippet) > len(existing.content):
                    existing.content = hit.snippet
                if len(hit.title) > len(existing.title):
                    existing.title = hit.title
                if not existing.published_date and hit.published_date:
                    existing.published_date = hit.published_date

    for key, result in merged.items():
        result.score = round(rrf_score[key], 6)
        result.engine = ",".join(sorted(engines[key]))
    return list(merged.values())


def bm25_scores(query: str, docs: list[str], *, k1: float = 1.5, b: float = 0.75) -> list[float]:
    """极简 BM25（本地毫秒级），用于在 RRF 基础上按查询相关性重排。"""
    query_terms = set(tokenize(query))
    if not query_terms or not docs:
        return [0.0] * len(docs)

    tokenized = [tokenize(doc) for doc in docs]
    doc_count = len(tokenized)
    avg_len = sum(len(t) for t in tokenized) / doc_count if doc_count else 0.0
    df: dict[str, int] = defaultdict(int)
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    scores: list[float] = []
    for tokens in tokenized:
        length = len(tokens) or 1
        tf: dict[str, int] = defaultdict(int)
        for term in tokens:
            tf[term] += 1
        score = 0.0
        for term in query_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (doc_count - df[term] + 0.5) / (df[term] + 0.5))
            denominator = tf[term] + k1 * (1 - b + b * length / (avg_len or 1))
            score += idf * (tf[term] * (k1 + 1)) / (denominator or 1)
        scores.append(score)
    return scores


def rerank(results: list[SearchResult], query: str, *, weight: float = 0.6) -> list[SearchResult]:
    """把「查询相关性（BM25）」与「多引擎一致性（RRF）」线性加权。

    weight 是相关性权重：默认 0.6，让真正切题的结果优先；
    剩余权重给 RRF，用于在同等相关时让多引擎共同命中的结果靠前。
    两者各自归一化到 0-1 后再加权，避免量纲差异导致某一项主导。
    """
    if not results:
        return results
    bm25 = bm25_scores(query, [f"{r.title} {r.content}" for r in results])
    max_bm25 = max(bm25) or 1.0
    max_rrf = max(r.score for r in results) or 1.0
    for result, relevance in zip(results, bm25):
        result.score = round(
            (1 - weight) * (result.score / max_rrf) + weight * (relevance / max_bm25),
            6,
        )
    return sorted(results, key=lambda r: r.score, reverse=True)


def filter_domains(
    results: list[SearchResult],
    *,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> list[SearchResult]:
    """按域名白/黑名单过滤。"""
    if include_domains:
        allow = tuple(d.lower().lstrip(".") for d in include_domains)
        results = [r for r in results if any(domain_of(r.url).endswith(d) for d in allow)]
    if exclude_domains:
        deny = tuple(d.lower().lstrip(".") for d in exclude_domains)
        results = [r for r in results if not any(domain_of(r.url).endswith(d) for d in deny)]
    return results
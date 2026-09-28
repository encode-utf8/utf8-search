"""M6 阶段 1（查询扩展埋点测量）的离线回归。

要点：埋点**不增加任何上游调用、不改变行为**；判定逻辑是纯函数；指标进 `/metrics`。
"""

from __future__ import annotations

import httpx
import pytest

from utf8_search.cache.store import CacheStore
from utf8_search.config import Settings
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.models import SearchRequest
from utf8_search.providers.base import BaseProvider, SearchHit
from utf8_search.providers.searxng import SearxngProvider
from utf8_search.verify.expansion import ExpansionMetrics, expansion_needed


# ---------------------------------------------------------------- 纯函数判定
def test_expansion_needed_uses_candidate_shortfall() -> None:
    """占位判据就是 5.2 的原始「不足」口径：候选数 < 目标候选池。"""
    assert expansion_needed(23, 24) == "candidates"
    assert expansion_needed(24, 24) is None
    assert expansion_needed(30, 24) is None


def test_expansion_needed_optional_coverage_threshold() -> None:
    """覆盖率门槛是可选参数（阶段 1 不拍数字）；不给就不参与判定。"""
    assert expansion_needed(24, 24, 0.42) is None  # 未给门槛 → 不看覆盖率
    assert expansion_needed(24, 24, 0.42, min_coverage=0.5) == "coverage"
    assert expansion_needed(24, 24, 0.62, min_coverage=0.5) is None
    # 两条都命中
    assert expansion_needed(5, 24, 0.3, min_coverage=0.5) == "candidates,coverage"
    # 覆盖率缺失（无结果）时不误判
    assert expansion_needed(24, 24, None, min_coverage=0.5) is None


def test_expansion_needed_ignores_zero_target() -> None:
    """目标候选池为 0（理论上不会出现）时不应把一切都判成不足。"""
    assert expansion_needed(0, 0) is None


# ---------------------------------------------------------------- 目标候选池
def _settings(**overrides) -> Settings:
    base = Settings(searxng_url="http://searxng-test:8080", api_keys="")
    return base.model_copy(update=overrides) if overrides else base


class _CountingProvider(BaseProvider):
    """计数用假主源：返回固定条数，并记录被调用次数。"""

    name = "searxng"

    def __init__(self, hits: int) -> None:
        self._hits = hits
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        optional_wait=None,
    ):
        self.calls += 1
        return [
            SearchHit(title=f"r{i}", url=f"https://s{i}.example/a", snippet="x", engine="brave")
            for i in range(min(self._hits, max_results))
        ]


class _NullExtractor:
    async def extract(self, *args, **kwargs):  # pragma: no cover - basic 模式不抓页
        raise AssertionError("basic 模式不应抓页")


async def _pipeline(tmp_path, settings: Settings, provider: BaseProvider) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "expansion.db"))
    await cache.open()
    return SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=[provider],
        extractor=_NullExtractor(),
    )


async def test_candidate_target_matches_topic_pools(tmp_path) -> None:
    """目标候选池 = max(max_results, 页数预算, 该主题的候选池)。"""
    settings = _settings(rank_candidate_pool=24, news_candidate_pool=30)
    pipeline = await _pipeline(tmp_path, settings, _CountingProvider(1))

    general = pipeline._candidate_target(SearchRequest(query="q", max_results=5, depth="basic"))
    news = pipeline._candidate_target(
        SearchRequest(query="q", max_results=5, depth="basic", topic="news")
    )
    await pipeline.close()

    assert general == 24
    assert news == 30


async def test_candidate_target_honours_configured_pool(tmp_path) -> None:
    """候选池大小可参数化（阶段 2a 的 A/B/C 就靠它），改默认值仍需用户拍板。"""
    settings = _settings(rank_candidate_pool=40, news_candidate_pool=40)
    pipeline = await _pipeline(tmp_path, settings, _CountingProvider(1))

    target = pipeline._candidate_target(SearchRequest(query="q", max_results=5, depth="basic"))
    await pipeline.close()

    assert target == 40


async def test_provider_records_raw_result_count() -> None:
    """上游**原始**返回条数被记录下来（我们自己会把 hits 截断，所以必须单独记）。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": f"https://site{i}.example/a", "title": f"t{i}", "content": "c", "engine": "brave"}
                    for i in range(30)
                ],
                "unresponsive_engines": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SearxngProvider("http://searxng-test", client, timeout_limit=None)
    hits = await provider.search("q", max_results=5)
    await client.aclose()

    assert len(hits) == 5  # 我们截断到 max_results
    assert provider.raw_result_count == 30  # 但原始条数被记下来


async def test_measurement_adds_no_upstream_calls(tmp_path) -> None:
    """关键回归：埋点**不增加上游调用**（一次搜索仍然只有一次主源调用），且样本被记录。"""
    provider = _CountingProvider(30)
    settings = _settings(rank_candidate_pool=24)
    pipeline = await _pipeline(tmp_path, settings, provider)

    response = await pipeline.search(SearchRequest(query="埋点测试", max_results=5, depth="basic"))
    await pipeline.close()

    assert provider.calls == 1  # 采样没有引入第二次上游调用
    assert pipeline.expansion_metrics.samples == 1
    metrics = pipeline.expansion_metrics
    assert metrics.candidates.count == 1
    assert metrics.candidates.total == pytest.approx(24.0)  # 主源返回 24 条候选
    assert metrics.targets.total == pytest.approx(24.0)
    assert metrics.distinct_hosts.total == pytest.approx(5.0)  # 最终 top5 来自 5 个不同域名
    assert len(response.results) == 5


async def test_expansion_metrics_render_into_pipeline_metrics(tmp_path) -> None:
    """埋点指标进 `/metrics`（`pipeline.render_metrics()` 同时含闸门与扩展两族）。"""
    provider = _CountingProvider(3)  # 候选不足（3 < 24）→ 应命中占位判据
    settings = _settings(rank_candidate_pool=24)
    pipeline = await _pipeline(tmp_path, settings, provider)
    await pipeline.search(SearchRequest(query="渲染测试", max_results=5, depth="basic"))
    text = pipeline.render_metrics()
    await pipeline.close()

    for metric in (
        "utf8search_upstream_active",  # 闸门族仍在
        "utf8search_expansion_samples_total",
        "utf8search_expansion_candidates_bucket",
        "utf8search_expansion_raw_candidates_bucket",
        "utf8search_expansion_coverage_bucket",
        "utf8search_expansion_distinct_hosts_bucket",
        "utf8search_expansion_trigger_total",
    ):
        assert metric in text
    assert 'utf8search_expansion_trigger_total{reason="candidates"} 1' in text


def test_expansion_metrics_observe_and_render_pure() -> None:
    """指标对象自身的行为（不依赖 pipeline）。"""
    metrics = ExpansionMetrics()
    metrics.observe(candidates=10, target=24, coverage_mean=0.5, distinct_hosts=4, reason="candidates")
    metrics.observe(candidates=24, target=24, coverage_mean=0.9, distinct_hosts=5, reason=None)
    metrics.observe(candidates=24, target=24, coverage_mean=0.3, distinct_hosts=3, reason="coverage")

    assert metrics.samples == 3
    assert metrics.trigger_total == 2
    assert metrics.trigger_by_reason == {"candidates": 1, "coverage": 1}
    text = metrics.render()
    assert 'utf8search_expansion_trigger_total{reason="candidates"} 1' in text
    assert 'utf8search_expansion_trigger_total{reason="coverage"} 1' in text
    assert "utf8search_expansion_samples_total 3" in text
    assert text.endswith("\n")

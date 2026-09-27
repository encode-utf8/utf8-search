"""上游并发闸门测试（M5 并发保护，全部离线）。

覆盖：闸门放行 / 排队 / 队列满 / 排队超时、配置解析（含 .env 变量名）、
Prometheus 指标输出，以及两条**关键回归**——

1. 闸门拒绝时 pipeline 必须抛 `UpstreamOverloaded`，**不能**退化成「返回 0 条」；
2. 过载时**不得**降级到兜底源（Bing 等），避免把压力转嫁给更脆弱的抓取源。
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from utf8_search.cache.store import CacheStore
from utf8_search.config import Settings
from utf8_search.core.pipeline import SearchPipeline
from utf8_search.core.upstream_gate import UpstreamGate, UpstreamOverloaded
from utf8_search.models import SearchRequest
from utf8_search.providers.base import BaseProvider, SearchHit


# ---------------------------------------------------------------- 闸门机制
async def test_gate_admits_up_to_limit_without_queueing() -> None:
    """limit 之内立即放行，不排队。"""
    gate = UpstreamGate(limit=2, queue_limit=4, max_wait=1.0)

    async with gate.slot():
        async with gate.slot():
            assert gate.active == 2
            assert gate.waiting == 0
    assert gate.active == 0


async def test_gate_queues_then_serves_on_release() -> None:
    """超过 limit 时排队；前一个释放后把槽位**转交**给队首。"""
    gate = UpstreamGate(limit=1, queue_limit=2, max_wait=1.0)
    await gate.acquire()  # 占满唯一槽位
    served = asyncio.Event()

    async def waiter() -> None:
        await gate.acquire()
        served.set()

    task = asyncio.create_task(waiter())
    await asyncio.sleep(0.01)
    assert gate.waiting == 1 and not served.is_set()

    gate.release()
    await asyncio.wait_for(served.wait(), timeout=1.0)
    assert gate.active == 1  # 槽位转交，不是先减后加
    assert gate.waiting == 0
    gate.release()
    await task
    assert gate.metrics.acquire_seconds.count == 1  # 排队时长被记录


async def test_gate_rejects_immediately_when_queue_full() -> None:
    """队列满 → 立即拒绝（不排队、不挂到超时）。"""
    gate = UpstreamGate(limit=1, queue_limit=1, max_wait=5.0)
    await gate.acquire()
    queued = asyncio.create_task(gate.acquire())  # 占掉唯一的排队位
    await asyncio.sleep(0.01)
    assert gate.waiting == 1

    with pytest.raises(UpstreamOverloaded) as info:
        await gate.acquire()
    assert info.value.reason == "queue_full"
    assert info.value.retry_after == pytest.approx(5.0)
    assert gate.metrics.rejected_by_reason == {"queue_full": 1}

    gate.release()
    await queued
    gate.release()


async def test_gate_rejects_when_max_wait_exceeded() -> None:
    """排队超过 max_wait → 立即拒绝，并把等待者移出队列（不留悬挂槽位）。"""
    gate = UpstreamGate(limit=1, queue_limit=4, max_wait=0.05)
    await gate.acquire()

    with pytest.raises(UpstreamOverloaded) as info:
        await gate.acquire()
    assert info.value.reason == "timeout"
    assert gate.waiting == 0
    assert gate.active == 1  # 占用者不受影响

    gate.release()
    assert gate.active == 0


async def test_gate_track_records_upstream_latency_and_result() -> None:
    """`track()` 记录上游调用时长与结果标签。"""
    gate = UpstreamGate(limit=1, queue_limit=1, max_wait=0.1)

    async with gate.track():
        await asyncio.sleep(0.01)
    with pytest.raises(RuntimeError):
        async with gate.track():
            raise RuntimeError("上游炸了")

    assert gate.metrics.requests_total == {"ok": 1, "error": 1}
    assert gate.metrics.request_seconds.count == 2


async def test_try_acquire_fails_fast_without_queueing_or_histogram() -> None:
    """非阻塞获取：满了立即 False —— 不排队、不写排队直方图、不产生客户端 429 计数。"""
    gate = UpstreamGate(limit=1, queue_limit=0, max_wait=5.0)

    assert await gate.try_acquire() is True
    assert await gate.try_acquire() is False
    assert gate.waiting == 0  # 没有排队者
    assert gate.metrics.acquire_seconds.count == 0  # 不污染排队直方图
    assert gate.metrics.rejected_total == 0  # 失败的 try_acquire 不等于客户端被拒

    gate.release()
    assert gate.active == 0


async def test_track_non_blocking_reports_no_capacity() -> None:
    """`track(non_blocking=True)` 拿不到容量时抛 reason=no_capacity，且不排队。"""
    gate = UpstreamGate(limit=1, queue_limit=2, max_wait=5.0)
    await gate.acquire()

    with pytest.raises(UpstreamOverloaded) as info:
        async with gate.track(non_blocking=True):
            pass

    assert info.value.reason == "no_capacity"
    assert gate.metrics.rejected_by_reason == {"no_capacity": 1}
    assert gate.metrics.acquire_seconds.count == 0
    gate.release()


# ---------------------------------------------------------------- 配置解析
def test_gate_settings_defaults_and_env_override(monkeypatch) -> None:
    """默认 3 / 12 / 4.0s（「排队优先」档，见参数矩阵）；`UTF8SEARCH_UPSTREAM_*` 可覆盖，metrics 开关可关。"""
    base = Settings()
    assert (base.upstream_max_concurrency, base.upstream_queue_limit) == (3, 12)
    assert base.upstream_max_wait == pytest.approx(4.0)
    assert base.metrics_enabled is True
    gate = UpstreamGate.from_settings(base)
    assert (gate.limit, gate.queue_limit, gate.max_wait) == (3, 12, pytest.approx(4.0))

    monkeypatch.setenv("UTF8SEARCH_UPSTREAM_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("UTF8SEARCH_UPSTREAM_QUEUE_LIMIT", "0")
    monkeypatch.setenv("UTF8SEARCH_UPSTREAM_MAX_WAIT", "1.5")
    monkeypatch.setenv("UTF8SEARCH_METRICS_ENABLED", "false")
    override = Settings()
    assert (override.upstream_max_concurrency, override.upstream_queue_limit) == (2, 0)
    assert override.upstream_max_wait == pytest.approx(1.5)
    assert override.metrics_enabled is False


def test_gate_can_be_disabled_with_zero_limit() -> None:
    """limit=0 表示关闭闸门：acquire/release 都是空操作（行为与旧版一致）。"""
    gate = UpstreamGate(limit=0, queue_limit=0, max_wait=0.1)
    assert gate.retry_after == pytest.approx(1.0)  # 兜底建议值仍 ≥1s


async def test_disabled_gate_never_rejects() -> None:
    gate = UpstreamGate(limit=0, queue_limit=0, max_wait=0.01)
    async with gate.slot():
        async with gate.slot():
            pass
    assert gate.active == 0


# ---------------------------------------------------------------- 指标输出
async def test_metrics_render_prometheus_text() -> None:
    """Prometheus 文本：gauge / counter / histogram（含 +Inf、sum、count）齐备。"""
    gate = UpstreamGate(limit=1, queue_limit=0, max_wait=0.05)
    async with gate.track():
        pass
    await gate.acquire()
    with pytest.raises(UpstreamOverloaded):
        await gate.acquire()  # queue_limit=0 → 队列满，立即拒绝
    gate.release()

    text = gate.render_metrics()

    for metric in (
        "utf8search_upstream_active",
        "utf8search_upstream_waiting",
        "utf8search_upstream_rejected_total",
        "utf8search_upstream_requests_total",
        "utf8search_upstream_acquire_seconds",
        "utf8search_upstream_request_seconds",
    ):
        assert f"# TYPE {metric} " in text
    assert 'utf8search_upstream_requests_total{result="ok"} 1' in text
    assert 'utf8search_upstream_rejected_total{reason="queue_full"} 1' in text
    # nit：不再输出无标签聚合线（否则 Prometheus sum() 会与带标签序列重复计数）
    assert "utf8search_upstream_rejected_total 1" not in text
    assert 'utf8search_upstream_request_seconds_bucket{le="+Inf"} 1' in text
    assert "utf8search_upstream_request_seconds_count 1" in text
    assert text.endswith("\n")


# ---------------------------------------------------------------- pipeline 回归
def _hits(count: int, engine: str = "brave") -> list[SearchHit]:
    return [
        SearchHit(title=f"结果{i}", url=f"https://site{i}.com/a", snippet=f"摘要{i}", engine=engine)
        for i in range(1, count + 1)
    ]


class _OverloadProvider(BaseProvider):
    """总是被闸门拒绝的「主源」。"""

    name = "searxng"

    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        non_blocking=False,
    ):
        self.calls += 1
        raise UpstreamOverloaded(reason="queue_full", retry_after=2.5)


class _RecordingProvider(BaseProvider):
    """兜底源：只要被调用就计数（用来断言「过载不降级」）。"""

    def __init__(self, name: str, hits: list[SearchHit]) -> None:
        self.name = name
        self._hits = hits
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        non_blocking=False,
    ):
        self.calls += 1
        return self._hits[:max_results]


class _NewsMainOkGeneralNoCapacity(BaseProvider):
    """news 主路成功、通用补充路**没拿到容量**（用于验证 degraded 原因）。

    同时记录补充路是否用了 `non_blocking=True`（可选调用不得占用主源的排队额度）。
    """

    name = "searxng"

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits
        self.calls = 0
        self.general_non_blocking: bool | None = None

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        non_blocking=False,
    ):
        self.calls += 1
        if topic == "news":
            return self._hits[:max_results]
        self.general_non_blocking = non_blocking
        raise UpstreamOverloaded(reason="no_capacity", retry_after=2.5)


class _NullExtractor:
    async def extract(self, *args, **kwargs):  # pragma: no cover - basic 模式不抓页
        raise AssertionError("basic 模式不应触发正文抓取")


async def _make_pipeline(tmp_path, settings, providers) -> SearchPipeline:
    cache = CacheStore(str(tmp_path / "gate.db"))
    await cache.open()
    return SearchPipeline(
        settings,
        client=httpx.AsyncClient(),
        cache=cache,
        providers=providers,
        extractor=_NullExtractor(),
    )


async def test_pipeline_raises_overload_instead_of_returning_empty(settings, tmp_path) -> None:
    """关键回归：闸门拒绝时 pipeline 抛 UpstreamOverloaded，**不返回 0 条结果**。"""
    pipeline = await _make_pipeline(tmp_path, settings, [_OverloadProvider()])

    with pytest.raises(UpstreamOverloaded):
        await pipeline.search(SearchRequest(query="过载回归-不返回空", max_results=3, depth="basic"))
    await pipeline.close()


async def test_overload_does_not_fall_back_to_secondary_provider(settings, tmp_path) -> None:
    """关键回归：过载时不得降级到兜底源（不把压力转嫁给更脆弱的抓取源）。"""
    fallback = _RecordingProvider("bing", _hits(5))
    pipeline = await _make_pipeline(tmp_path, settings, [_OverloadProvider(), fallback])

    with pytest.raises(UpstreamOverloaded):
        await pipeline.search(SearchRequest(query="过载回归-不降级", max_results=3, depth="basic"))
    assert fallback.calls == 0
    await pipeline.close()


class _EmptySearxng(BaseProvider):
    """主源正常返回但 0 条结果（会触发兜底源），自身不占闸门。"""

    name = "searxng"

    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self, query, *, max_results, topic="general", time_range=None, engines=None, language="all",
        non_blocking=False,
    ):
        self.calls += 1
        return []


async def test_fallback_is_skipped_without_capacity(settings, tmp_path) -> None:
    """兜底源非阻塞取容量：没容量就跳过并记 degraded，不排队拖慢主流程。"""
    primary = _EmptySearxng()
    fallback = _RecordingProvider("bing", _hits(5))
    scoped = settings.model_copy(update={"upstream_max_concurrency": 1})
    pipeline = await _make_pipeline(tmp_path, scoped, [primary, fallback])
    await pipeline.gate.acquire()  # 占满唯一槽位

    response = await pipeline.search(SearchRequest(query="兜底-无容量", max_results=3, depth="basic"))
    pipeline.gate.release()

    assert fallback.calls == 0  # 不排队、不调用
    assert response.degraded is True
    assert response.degraded_reason == "fallback_no_capacity"
    await pipeline.close()


async def test_news_general_supplement_skipped_without_capacity(settings, tmp_path) -> None:
    """news 通用补充路没容量时跳过：主源结果照常返回 + degraded 记明原因（不是 429、也不是空结果）。"""
    provider = _NewsMainOkGeneralNoCapacity(_hits(6))
    scoped = settings.model_copy(update={"news_include_general": True})
    pipeline = await _make_pipeline(tmp_path, scoped, [provider])

    response = await pipeline.search(
        SearchRequest(query="过载降级-news", max_results=3, depth="basic", topic="news")
    )

    assert response.degraded is True
    assert response.degraded_reason == "news_general_no_capacity"
    assert response.results  # 仍有可用结果
    assert provider.general_non_blocking is True  # 可选补充路必须非阻塞
    await pipeline.close()


async def test_mcp_web_search_reports_overload_as_readable_tool_error(monkeypatch) -> None:
    """MCP 通道：过载返回可读 isError 文本，而不是空结果。"""
    from mcp.server.mcpserver.exceptions import ToolError

    from utf8_search.server import mcp_server

    class _OverloadedPipeline:
        async def search(self, request):
            raise UpstreamOverloaded(reason="timeout", retry_after=2.5)

    async def fake_get_pipeline(settings=None):
        return _OverloadedPipeline()

    monkeypatch.setattr(mcp_server, "get_pipeline", fake_get_pipeline)

    with pytest.raises(ToolError) as info:
        await mcp_server.web_search(query="过载 MCP")

    message = str(info.value)
    assert "上游搜索过载" in message
    assert "秒后重试" in message

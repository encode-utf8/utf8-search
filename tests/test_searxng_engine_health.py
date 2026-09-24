"""SearxngProvider 接入引擎健康度的集成测试（验收项 5.1-8、5.1-9），全部离线。

重点覆盖两件事：
1. 冷却中的引擎不会进入下一次查询的 `engines` 参数；
2. **瞬时错误重试时不再抛弃 `engines`**（旧实现会退回 SearXNG 默认引擎集合，
   等于让返回内容脱离本服务控制），而是保留约束、只剔除冷却中的引擎。
"""

from __future__ import annotations

import httpx

from utf8_search.providers.engine_health import EngineHealthTracker
from utf8_search.providers.searxng import SearxngProvider


class _Clock:
    """可手动推进的假时钟。"""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _FakeResponse:
    """最小的 httpx.Response 替身。"""

    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self.request = None
        self._payload = payload if payload is not None else {"results": []}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)


class _ScriptedClient:
    """按脚本顺序返回响应，并记录每次请求的参数。"""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    async def get(self, url, params=None, timeout=None):  # noqa: ANN001
        self.calls.append(dict(params or {}))
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        return self._responses[index]


def _unresponsive(engine: str, reason: str) -> _FakeResponse:
    return _FakeResponse(payload={"results": [], "unresponsive_engines": [[engine, reason]]})


def _one_hit() -> _FakeResponse:
    return _FakeResponse(
        payload={"results": [{"url": "https://example.com/a", "title": "标题", "content": "摘要"}]}
    )


# ---------------------------------------------------------------- 冷却引擎不入下一查
async def test_cooling_engine_excluded_from_next_query() -> None:
    clock = _Clock()
    tracker = EngineHealthTracker(clock=clock, min_active=1, probe_slots=0)
    client = _ScriptedClient(
        [
            _unresponsive("brave", "Suspended: too many requests"),
            _FakeResponse(),
        ]
    )
    provider = SearxngProvider(
        "http://searxng:8080",
        client,
        default_engines=["brave", "yandex"],
        engine_health=tracker,
    )

    await provider.search("第一条", max_results=5)
    assert client.calls[0]["engines"] == "brave,yandex"

    await provider.search("第二条", max_results=5)
    # brave 已被冷却 → 不再占用查询；约束仍然显式传给 SearXNG
    assert client.calls[1]["engines"] == "yandex"
    assert "categories" not in client.calls[1]


async def test_unresponsive_reasons_exposed() -> None:
    """旧代码只留引擎名、丢掉原因，而原因正是分级退避的依据。"""
    clock = _Clock()
    tracker = EngineHealthTracker(clock=clock, min_active=1)
    client = _ScriptedClient([_unresponsive("quark", "Suspended: CAPTCHA")])
    provider = SearxngProvider(
        "http://searxng:8080", client, default_engines=["quark", "yandex"], engine_health=tracker
    )

    await provider.search("测试", max_results=5)
    assert provider.unresponsive_engines == ["quark"]
    assert provider.unresponsive_reasons == {"quark": "Suspended: CAPTCHA"}
    assert tracker.snapshot()["cooling"][0]["class"] == "captcha"


# ---------------------------------------------------------------- 5.1-8 重试保留约束
async def test_retry_keeps_explicit_engines() -> None:
    """502 重试必须保留 engines 约束（旧实现会 pop 掉，退回 SearXNG 默认引擎集合）。"""
    client = _ScriptedClient([_FakeResponse(status_code=502), _one_hit()])
    provider = SearxngProvider("http://searxng:8080", client, default_engines=["yandex", "naver"])

    hits = await provider.search("测试", max_results=5)

    assert len(client.calls) == 2
    assert client.calls[0]["engines"] == "yandex,naver"
    assert client.calls[1]["engines"] == "yandex,naver"  # 关键回归点：仍然受约束
    assert len(hits) == 1  # 重试成功照样返回结果


async def test_retry_drops_cooling_engine_but_keeps_others() -> None:
    """重试用「剔除冷却中引擎」的集合，而不是抛弃引擎列表。"""
    clock = _Clock()
    tracker = EngineHealthTracker(clock=clock, min_active=1, probe_slots=0)
    tracker.observe(["quark"], [("quark", "Suspended: CAPTCHA")])

    client = _ScriptedClient([_FakeResponse(status_code=503), _one_hit()])
    provider = SearxngProvider(
        "http://searxng:8080",
        client,
        default_engines=["quark", "yandex", "naver"],
        engine_health=tracker,
    )

    hits = await provider.search("测试", max_results=5)
    assert client.calls[0]["engines"] == "yandex,naver"
    assert client.calls[1]["engines"] == "yandex,naver"
    assert len(hits) == 1


async def test_categories_branch_retry_unchanged() -> None:
    """没有显式引擎列表（走 categories）时，重试参数也不应被改动。"""
    client = _ScriptedClient([_FakeResponse(status_code=502), _one_hit()])
    provider = SearxngProvider("http://searxng:8080", client)

    await provider.search("测试", max_results=5)
    assert client.calls[0]["categories"] == "general"
    assert "engines" not in client.calls[0]
    assert client.calls[1]["categories"] == "general"
    assert "engines" not in client.calls[1]


# ---------------------------------------------------------------- 5.1-9 关闭开关
async def test_disabled_health_keeps_all_engines() -> None:
    """未注入 tracker（开关关闭）时，引擎列表原样透传。"""
    client = _ScriptedClient(
        [
            _unresponsive("brave", "Suspended: too many requests"),
            _FakeResponse(),
        ]
    )
    provider = SearxngProvider("http://searxng:8080", client, default_engines=["brave", "yandex"])

    await provider.search("第一条", max_results=5)
    await provider.search("第二条", max_results=5)
    assert client.calls[1]["engines"] == "brave,yandex"
    assert provider.engine_health_snapshot() is None


async def test_health_snapshot_lists_cooling_and_active() -> None:
    clock = _Clock()
    tracker = EngineHealthTracker(clock=clock, min_active=1, probe_slots=0)
    tracker.observe(["brave"], [("brave", "Suspended: CAPTCHA")])
    provider = SearxngProvider(
        "http://searxng:8080",
        _ScriptedClient([_FakeResponse()]),
        default_engines=["brave", "yandex"],
        news_engines=["duckduckgo news"],
        engine_health=tracker,
    )

    snapshot = provider.engine_health_snapshot()
    assert snapshot is not None
    assert [item["engine"] for item in snapshot["cooling"]] == ["brave"]
    # 快照里的 active 是「按当前健康度实际会发出的引擎集合」
    assert snapshot["active"] == ["yandex", "duckduckgo news"]
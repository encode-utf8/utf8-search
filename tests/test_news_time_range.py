"""按引擎白名单透传 time_range（M6 news 时效，2026-09-30）。

背景：同一个 `time_range` 对不同引擎效果相反 ——
  * `duckduckgo news` 带 `time_range=day` 直接返回 0 条；
  * `sina` 恰恰靠 `time_range=day` 给出「当天内」的中文结果（实测 90/90 在 7 日内）。
所以旧的全局面量 `news_pass_time_range` 无法同时服务两者，改成按引擎白名单：
白名单引擎带 time_range 发一次，其余引擎不带发一次，结果合并去重（仍在同一个闸门槽位内）。
"""

from __future__ import annotations

import httpx

from utf8_search.config import Settings
from utf8_search.providers.searxng import SearxngProvider


class _RecordingClient:
    """记录每次请求参数；按 URL 里的 host 片段返回不同结果，便于区分两组请求。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def get(self, url, params=None, timeout=None):  # noqa: ANN001
        self.calls.append(dict(params or {}))
        engine = (params or {}).get("engines", "")
        # 每条结果都带上「来源引擎名」，方便断言合并结果来自两组
        payload = {
            "results": [
                {
                    "url": f"https://example.com/{engine or 'default'}/{index}",
                    "title": f"{engine} 结果 {index}",
                    "content": "摘要",
                    "engine": engine or "default",
                }
                for index in range(3)
            ]
        }
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


def _provider(client: _RecordingClient, **kwargs) -> SearxngProvider:
    return SearxngProvider(
        "http://searxng:8080",
        client,  # type: ignore[arg-type]
        default_engines=kwargs.pop("default_engines", ["resulthunter", "yandex"]),
        news_engines=kwargs.pop("news_engines", ["duckduckgo news", "sina"]),
        news_time_range_engines=kwargs.pop("news_time_range_engines", {"sina"}),
        **kwargs,
    )


async def test_whitelisted_engine_gets_time_range_others_do_not() -> None:
    """sina 在白名单里 → 拆两次请求：sina 带 day，其余新闻引擎不带。"""
    client = _RecordingClient()
    provider = _provider(client)
    hits = await provider.search("新能源汽车 补贴政策", max_results=5, topic="news", time_range="day")

    assert len(client.calls) == 2, client.calls
    ranged, plain = client.calls
    assert ranged["engines"] == "sina" and ranged["time_range"] == "day"
    assert plain["engines"] == "duckduckgo news" and "time_range" not in plain

    # 结果合并：两组各 3 条（URL 不同）都被带回
    assert len(hits) == 5
    assert {hit.engine for hit in hits} == {"sina", "duckduckgo news"}


async def test_no_whitelisted_engine_keeps_single_call_without_time_range() -> None:
    """新闻列表里没有白名单引擎时，行为与改动前一致：一次请求、不透传 time_range。"""
    client = _RecordingClient()
    provider = _provider(client, news_engines=["duckduckgo news", "google news"])
    await provider.search("测试", max_results=5, topic="news", time_range="day")

    assert len(client.calls) == 1
    assert client.calls[0]["engines"] == "duckduckgo news,google news"
    assert "time_range" not in client.calls[0]


async def test_legacy_global_flag_still_passes_time_range_to_all() -> None:
    """旧开关 `news_pass_time_range=true` 仍等价于「全部新闻引擎都透传」（排障用）。"""
    client = _RecordingClient()
    provider = _provider(client, news_pass_time_range=True)
    await provider.search("测试", max_results=5, topic="news", time_range="day")

    assert len(client.calls) == 1
    assert client.calls[0]["engines"] == "duckduckgo news,sina"
    assert client.calls[0]["time_range"] == "day"


async def test_general_topic_still_passes_time_range_to_all() -> None:
    """通用主题（含 news 的「日期回补补充路」）不变：一次请求、time_range 直接透传。"""
    client = _RecordingClient()
    provider = _provider(client, default_engines=["google", "yandex"])
    await provider.search("测试", max_results=5, topic="general", time_range="day")

    assert len(client.calls) == 1
    assert client.calls[0]["engines"] == "google,yandex"
    assert client.calls[0]["time_range"] == "day"


def test_settings_whitelist_default_and_parsing() -> None:
    """默认白名单**为空**（sina 因 0 条带日期被撤回）；机制仍在，逗号列表可解析为集合。"""
    assert Settings().news_time_range_engine_set == set()
    custom = Settings(news_time_range_engines="sina, tiger news ,")
    assert custom.news_time_range_engine_set == {"sina", "tiger news"}


def test_settings_news_general_engines_has_no_sina_and_no_360search() -> None:
    """日期回补补充路：撤出 sina（实测 0 条带日期，只会稀释候选），且不引用已删除的 360search。"""
    engines = Settings().news_general_engine_list
    assert "sina" not in engines
    assert "360search" not in engines

"""引擎健康度自适应单测（验收项 5.1-1 ~ 5.1-7、5.1-9），全部离线。

用可注入的假时钟验证：失败原因分级冷却、连续失败指数退避与封顶、租约到期自愈、
覆盖率下限、探测名额有界、空结果不惩罚、候选顺序稳定、开关关闭等价旧行为。
"""

from __future__ import annotations

import pytest

from utf8_search.config import Settings
from utf8_search.providers.engine_health import (
    CLASS_CAPTCHA,
    CLASS_DENIED,
    CLASS_OTHER,
    CLASS_RATE_LIMIT,
    CLASS_TIMEOUT,
    EngineHealthTracker,
)


class _Clock:
    """可手动推进的假时钟，用来验证租约到期与指数退避，避免测试真的 sleep。"""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _tracker(clock: _Clock, **kwargs) -> EngineHealthTracker:
    return EngineHealthTracker(clock=clock, **kwargs)


def _retry_after(tracker: EngineHealthTracker, engine: str) -> float | None:
    """读取某引擎当前的剩余冷却时长；不在冷却中返回 None。"""
    for item in tracker.snapshot()["cooling"]:
        if item["engine"] == engine:
            return item["retry_after"]
    return None


# ---------------------------------------------------------------- 5.1-1 原因分级
@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("Suspended: CAPTCHA", CLASS_CAPTCHA),
        ("Suspended: access denied", CLASS_DENIED),
        ("HTTP 403 Forbidden", CLASS_DENIED),
        ("Suspended: too many requests", CLASS_RATE_LIMIT),
        ("HTTP 429 Too Many Requests", CLASS_RATE_LIMIT),
        # 无原因的 suspended 按限流处理（SearXNG 惩罚盒默认就是「请求过多」语义）
        ("Suspended", CLASS_RATE_LIMIT),
        ("httpx.ReadTimeout: timed out", CLASS_TIMEOUT),
        ("Timeout while fetching", CLASS_TIMEOUT),
        ("Parse error in response", CLASS_OTHER),
        ("", CLASS_OTHER),
        # 中文文案：SearXNG 按 Accept-Language 本地化错误消息，本服务的客户端带 zh-CN，
        # 实测同一实例返回的就是这些（2026-09-24 踩过坑：只写英文规则时全部落进 other 档）
        ("暂停服务: 验证码", CLASS_CAPTCHA),
        ("暂停服务: 拒绝访问", CLASS_DENIED),
        ("暂停服务: 请求过于频繁", CLASS_RATE_LIMIT),
        ("暂停服务: 超时", CLASS_TIMEOUT),
        ("暂停服务", CLASS_RATE_LIMIT),
    ],
)
def test_classify_reasons(reason: str, expected: str) -> None:
    assert EngineHealthTracker.classify(reason) == expected


def test_english_and_chinese_reasons_map_to_same_class() -> None:
    """中英文文案必须归到同一档，否则冷却时长会随 Accept-Language 漂移。"""
    pairs = [
        ("Suspended: CAPTCHA", "暂停服务: 验证码"),
        ("Suspended: access denied", "暂停服务: 拒绝访问"),
        ("Suspended: too many requests", "暂停服务: 请求过于频繁"),
    ]
    for english, chinese in pairs:
        assert EngineHealthTracker.classify(english) == EngineHealthTracker.classify(chinese)


def test_cooldown_uses_reason_class() -> None:
    """不同原因落进对应档位的冷却时长。"""
    clock = _Clock()
    tracker = _tracker(
        clock,
        cooldown_captcha=1800.0,
        cooldown_denied=900.0,
        cooldown_rate_limit=180.0,
        cooldown_timeout=90.0,
        cooldown_other=120.0,
        cooldown_max=3600.0,
    )
    tracker.observe(["google"], [("google", "Suspended: CAPTCHA")])
    assert _retry_after(tracker, "google") == 1800.0
    assert tracker.snapshot()["cooling"][0]["class"] == CLASS_CAPTCHA


# ---------------------------------------------------------------- 5.1-2 指数退避
def test_repeated_failures_backoff_and_cap() -> None:
    clock = _Clock()
    tracker = _tracker(clock, cooldown_rate_limit=180.0, cooldown_max=600.0)

    tracker.observe(["naver"], [("naver", "Suspended: too many requests")])
    assert _retry_after(tracker, "naver") == 180.0  # 第 1 次：基数

    clock.advance(181)
    tracker.observe(["naver"], [("naver", "Suspended: too many requests")])
    assert _retry_after(tracker, "naver") == 360.0  # 第 2 次：2 倍

    clock.advance(361)
    tracker.observe(["naver"], [("naver", "Suspended: too many requests")])
    assert _retry_after(tracker, "naver") == 600.0  # 第 3 次：720 被 600 封顶


# ---------------------------------------------------------------- 5.1-3 租约自愈
def test_lease_expiry_and_success_self_heal() -> None:
    clock = _Clock()
    tracker = _tracker(clock, cooldown_rate_limit=180.0, min_active=1)
    candidates = ["yandex", "naver", "zapmeta"]

    tracker.observe(["naver"], [("naver", "Suspended: too many requests")])
    # min_active=1 且健康引擎还有 2 个 → 冷却中的 naver 不参与
    assert tracker.select(candidates) == ["yandex", "zapmeta"]

    # 租约到期后自动回到候选集（无需人工干预、不依赖重启）
    clock.advance(181)
    assert tracker.select(candidates) == candidates

    # 成功即清零失败计数，快照里不再有冷却项
    tracker.observe(["yandex", "naver", "zapmeta"], [])
    assert tracker.snapshot()["cooling"] == []

    # 再次失败时从第 1 档重新开始（证明计数确实被清零，而不是残留 2 次）
    tracker.observe(["naver"], [("naver", "Suspended: too many requests")])
    assert _retry_after(tracker, "naver") == 180.0


# ---------------------------------------------------------------- 5.1-4 覆盖率下限
def test_coverage_floor_keeps_min_active() -> None:
    clock = _Clock()
    tracker = _tracker(clock, min_active=6, probe_slots=0)
    candidates = [f"e{i}" for i in range(10)]
    for name in candidates[:7]:
        tracker.observe([name], [(name, "Suspended: too many requests")])

    selected = tracker.select(candidates)
    # 健康的 3 个 + 按「最早解冻优先」补足 3 个 = 6（下限不被击穿）
    assert len(selected) == 6
    assert set(candidates[7:]) <= set(selected)
    assert selected == [name for name in candidates if name in set(selected)]  # 顺序仍是候选序


def test_single_candidate_never_fully_excluded() -> None:
    """候选只有一个且它正在冷却时也不能返回空集合，否则会退化成「没引擎可用」。"""
    clock = _Clock()
    tracker = _tracker(clock, min_active=6)
    tracker.observe(["yandex"], [("yandex", "Suspended: CAPTCHA")])
    assert tracker.select(["yandex"]) == ["yandex"]


# ---------------------------------------------------------------- 5.1-5 探测名额
def test_probe_slots_bounded_and_earliest_first() -> None:
    clock = _Clock()
    tracker = _tracker(clock, min_active=1, probe_slots=1)
    candidates = [f"e{i}" for i in range(8)]

    # e0 冷却 180s、e1 冷却 900s、e2 冷却 1800s：最早解冻的是 e0
    tracker.observe(["e0"], [("e0", "too many requests")])
    tracker.observe(["e1"], [("e1", "access denied")])
    tracker.observe(["e2"], [("e2", "CAPTCHA")])

    selected = tracker.select(candidates)
    probing = [name for name in selected if name in {"e0", "e1", "e2"}]
    assert probing == ["e0"]  # 只带入 1 个，且是最早解冻的那个
    assert len(selected) == 6  # 其余 5 个健康引擎全在

    # 显式要求不带探测（重试路径就是这么用的）
    assert "e0" not in tracker.select(candidates, probe_slots=0)


# ---------------------------------------------------------------- 5.1-6 空结果不惩罚
def test_empty_results_do_not_penalize() -> None:
    """zapmeta / reloado 对中文长尾会返回 0 条但完全健康，不能算失败。"""
    clock = _Clock()
    tracker = _tracker(clock, min_active=1)
    tracker.observe(["zapmeta", "reloado"], [])
    tracker.observe(["zapmeta", "reloado"], [])
    assert tracker.snapshot()["cooling"] == []
    assert tracker.select(["zapmeta", "reloado"]) == ["zapmeta", "reloado"]


def test_unresponsive_not_in_sent_is_still_recorded() -> None:
    """走 categories 分支时没有显式引擎列表，但失败信息本身是真实的，照样记录。"""
    clock = _Clock()
    tracker = _tracker(clock, min_active=1)
    tracker.observe([], [("resulthunter", "Suspended: too many requests")])
    assert _retry_after(tracker, "resulthunter") == 180.0


def test_sent_engine_success_recorded_only_for_sent() -> None:
    """没被请求过的引擎不会被误判成「成功」（它根本没机会失败）。"""
    clock = _Clock()
    tracker = _tracker(clock, min_active=1)
    tracker.observe(["yandex"], [("brave", "Suspended: CAPTCHA")])
    snapshot = tracker.snapshot()
    assert [item["engine"] for item in snapshot["cooling"]] == ["brave"]
    assert snapshot["tracked"] == 2


# ---------------------------------------------------------------- 5.1-7 顺序稳定
def test_order_preserved_for_healthy_engines() -> None:
    clock = _Clock()
    tracker = _tracker(clock, min_active=1, probe_slots=0)
    candidates = ["zapmeta", "yandex", "naver", "yahoo"]
    tracker.observe(["naver"], [("naver", "Suspended: CAPTCHA")])
    assert tracker.select(candidates) == ["zapmeta", "yandex", "yahoo"]

    # 全健康时原样返回，不做任何重排
    clock.advance(2000)
    assert tracker.select(candidates) == candidates


def test_unknown_engines_are_optimistic() -> None:
    clock = _Clock()
    tracker = _tracker(clock, min_active=1)
    assert tracker.select(["brand-new"]) == ["brand-new"]


# ---------------------------------------------------------------- 5.1-9 开关
def test_disabled_passthrough() -> None:
    clock = _Clock()
    tracker = _tracker(clock, enabled=False, min_active=1, probe_slots=0)
    tracker.observe(["brave"], [("brave", "Suspended: CAPTCHA")])
    assert tracker.select(["brave", "yandex"]) == ["brave", "yandex"]


def test_from_settings_disabled_returns_none(tmp_path) -> None:
    off = Settings(engine_health_enabled=False, cache_path=str(tmp_path / "c.db"))
    assert EngineHealthTracker.from_settings(off) is None

    on = Settings(engine_health_enabled=True, cache_path=str(tmp_path / "c.db"))
    tracker = EngineHealthTracker.from_settings(on)
    assert tracker is not None
    assert tracker.min_active == on.engine_health_min_active
    assert tracker.probe_slots == on.engine_health_probe_slots
    assert tracker.cooldown_max == on.engine_health_cooldown_max


def test_empty_candidates_returns_empty() -> None:
    clock = _Clock()
    tracker = _tracker(clock)
    assert tracker.select([]) == []
"""鉴权与限流测试。"""

from __future__ import annotations

import pytest
from starlette.exceptions import HTTPException

from utf8_search.auth import AccessGuard, RateLimiter
from utf8_search.config import Settings


def _guard(**kwargs) -> AccessGuard:
    base = {"api_keys": "key-1,key-2", "rate_limit_rpm": 2}
    base.update(kwargs)
    return AccessGuard(Settings(**base))


async def test_no_keys_means_open_access() -> None:
    """未配置 Key 时不鉴权（本机自用场景）。"""
    guard = _guard(api_keys="")
    assert await guard.authorize() == "anonymous"


async def test_bearer_and_header_and_body_keys() -> None:
    """三种传 Key 的方式都应被接受。"""
    guard = _guard()
    assert await guard.authorize(authorization="Bearer key-1") == "key-1"
    assert await guard.authorize(x_api_key="key-2") == "key-2"
    assert await guard.authorize(body_api_key="key-1") == "key-1"


async def test_invalid_key_rejected() -> None:
    guard = _guard()
    with pytest.raises(HTTPException) as exc:
        await guard.authorize(authorization="Bearer wrong")
    assert exc.value.status_code == 401


async def test_rate_limit_blocks_after_quota() -> None:
    """超过每分钟配额后应返回 429。"""
    guard = _guard(rate_limit_rpm=2)
    await guard.authorize(x_api_key="key-1")
    await guard.authorize(x_api_key="key-1")
    with pytest.raises(HTTPException) as exc:
        await guard.authorize(x_api_key="key-1")
    assert exc.value.status_code == 429


def test_rate_limiter_disabled_when_zero() -> None:
    limiter = RateLimiter(0)
    for _ in range(10):
        ok, _retry = limiter.allow("k")
        assert ok
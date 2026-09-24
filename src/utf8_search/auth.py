"""访问鉴权与限流：API Key 校验（兼容 Tavily 的 Bearer / X-API-Key / body.api_key 三种传法）+ 每 Key 滑动窗口限流。"""

from __future__ import annotations

import hmac
import time
from collections import deque

from starlette.exceptions import HTTPException

from .config import Settings, get_settings


class RateLimiter:
    """滑动窗口限流器（按 Key 统计最近 60 秒请求数）。"""

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> tuple[bool, float]:
        """返回 (是否放行, 建议重试等待秒数)。"""
        if self.rpm <= 0:
            return True, 0.0
        now = time.time()
        window = self._hits.setdefault(key, deque())
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.rpm:
            retry_after = max(1.0, 60 - (now - window[0]))
            return False, round(retry_after, 1)
        window.append(now)
        return True, 0.0


class AccessGuard:
    """统一鉴权入口。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.keys = settings.api_key_set
        self.rate_limiter = RateLimiter(settings.rate_limit_rpm)

    @property
    def enabled(self) -> bool:
        """是否启用鉴权（未配置任何 Key 则关闭，便于本机自用）。"""
        return bool(self.keys)

    def extract_key(
        self,
        authorization: str | None = None,
        x_api_key: str | None = None,
        body_api_key: str | None = None,
    ) -> str | None:
        """从三种常见位置提取 Key。"""
        candidates = []
        if authorization:
            value = authorization.strip()
            if value.lower().startswith("bearer "):
                value = value[7:].strip()
            candidates.append(value)
        if x_api_key:
            candidates.append(x_api_key.strip())
        if body_api_key:
            candidates.append(body_api_key.strip())
        for candidate in candidates:
            if candidate:
                return candidate
        return None

    def verify(self, candidate: str | None) -> bool:
        """常量时间比较，避免时序侧信道。"""
        if not self.keys:
            return True
        if not candidate:
            return False
        return any(hmac.compare_digest(candidate, key) for key in self.keys)

    async def authorize(
        self,
        authorization: str | None = None,
        x_api_key: str | None = None,
        body_api_key: str | None = None,
    ) -> str:
        """校验通过返回使用的 Key 标识，否则抛出 401 / 429。"""
        if not self.enabled:
            return "anonymous"
        candidate = self.extract_key(authorization, x_api_key, body_api_key)
        if not self.verify(candidate):
            raise HTTPException(
                status_code=401,
                detail="无效的 API Key：请在 Authorization: Bearer <key>、X-API-Key 或请求体 api_key 中提供。",
            )
        assert candidate is not None
        allowed, retry_after = self.rate_limiter.allow(candidate)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {retry_after} 秒后重试。",
                headers={"Retry-After": str(int(retry_after))},
            )
        return candidate


_guard: AccessGuard | None = None


def get_guard(settings: Settings | None = None) -> AccessGuard:
    """获取全局鉴权器单例。"""
    global _guard
    if _guard is None:
        _guard = AccessGuard(settings or get_settings())
    return _guard
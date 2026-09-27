"""测试公共配置：所有离线测试不依赖网络与外部服务，也不依赖生产 `.env` 的鉴权设置。"""

from __future__ import annotations

import os

# 必须在**任何测试模块导入之前**执行。`utf8_search.server.http_api` 在模块级调用
# `get_settings()` 构造 `Settings`，而生产 `.env` 里 `UTF8SEARCH_API_KEYS` 非空会打开鉴权，
# 于是与鉴权无关的接口用例（`tests/test_api.py`）会拿到 401 —— 这是测试与运行环境的耦合。
# 这里把该变量中性化，保证 `Settings` 首次构造就落在「鉴权关闭」。
# 鉴权行为本身仍由 `tests/test_auth.py` 自建 `AccessGuard` 真实覆盖，不受影响。
os.environ["UTF8SEARCH_API_KEYS"] = ""

import pytest  # noqa: E402 - 需先完成上面的环境中性化

from utf8_search.config import Settings  # noqa: E402 - 同上


@pytest.fixture
def settings(tmp_path) -> Settings:
    """构造一份指向临时目录的测试配置。"""
    return Settings(
        searxng_url="http://searxng-test:8080",
        cache_path=str(tmp_path / "cache.db"),
        cache_enabled=True,
        fetch_timeout=0.5,
        advanced_budget=0.6,
        deep_budget=0.6,
        page_total_timeout=0.6,
        request_timeout=1.0,
        advanced_pages=3,
        deep_pages=5,
        page_max_chars=200,
        raw_content_max_chars=400,
        enable_jina_fallback=False,
        api_keys="",
        rate_limit_rpm=3,
    )
@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """离线测试不真正做 DNS 解析：把域名统一解析到一个公网 IP。

    SSRF 校验会解析域名，若测试环境真去查 DNS 会引入网络依赖与超时；
    这里统一打桩，需要验证解析行为的测试可自行覆盖 `utf8_search.security._resolve`。
    """
    from utf8_search import security

    async def fake_resolve(host: str, port: int | None = None) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(security, "_resolve", fake_resolve)
    yield

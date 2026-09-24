"""测试公共配置：所有离线测试不依赖网络与外部服务。"""

from __future__ import annotations

import pytest

from utf8_search.config import Settings


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

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
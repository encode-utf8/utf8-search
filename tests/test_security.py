"""SSRF 防护测试：URL 校验规则 + 抓取链路（重定向逐跳复检）。"""

from __future__ import annotations

import httpx
import pytest
import respx

from utf8_search import security
from utf8_search.cache.store import CacheStore
from utf8_search.extract.extractor import PageExtractor

PAGE = (
    "<html><head><title>内网页面</title></head><body><article>"
    + "<p>这是内网测试页面的正文内容，用于验证关闭防护后仍可正常抓取。</p>" * 4
    + "</article></body></html>"
)

# 字面量内网 / 保留地址，一律应被拒绝
BLOCKED_IP_URLS = [
    "http://127.0.0.1:8888/search",          # 回环
    "http://127.1.2.3/",                     # 回环网段
    "http://10.0.0.1/",                      # 私有 A 类
    "http://192.168.1.1/admin",              # 私有 C 类
    "http://172.16.5.4/",                    # 私有 B 类
    "http://169.254.169.254/latest/meta-data/",  # 云元数据
    "http://0.0.0.0/",                       # 本网络
    "http://100.64.0.1/",                    # 运营商级 NAT
    "http://224.0.0.1/",                     # 组播
    "http://[::1]/",                         # IPv6 回环
    "http://[fc00::1]/",                     # IPv6 唯一本地
    "http://[fe80::1]/",                     # IPv6 链路本地
    "http://[::ffff:127.0.0.1]/",            # IPv4-mapped IPv6 绕过
]

# 内网主机名，一律应被拒绝
BLOCKED_HOST_URLS = [
    "http://localhost:8888/",
    "http://localhost/",
    "http://foo.internal/",
    "http://nas.local/",
    "http://router/",                        # 无点单标签
    "http://metadata.google.internal/computeMetadata/v1/",
]

# 非 http(s) 协议，一律应被拒绝
BLOCKED_SCHEME_URLS = [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "gopher://example.com/",
    "data:text/html,<h1>x</h1>",
    "javascript:alert(1)",
]

# 正常公网地址，应放行
ALLOWED_URLS = [
    "https://example.com/",
    "https://example.com:8443/a/b?c=d",
    "http://8.8.8.8/",
    "http://1.1.1.1:8080/path",
]


@pytest.mark.parametrize("url", BLOCKED_IP_URLS)
async def test_blocks_literal_private_ip(url: str) -> None:
    """字面量内网 / 保留 IP 必须被拒绝（4.1-2/3/4）。"""
    allowed, reason = await security.check_url(url)
    assert allowed is False, f"{url} 不应被放行"
    assert reason


@pytest.mark.parametrize("url", BLOCKED_HOST_URLS)
async def test_blocks_internal_hostname(url: str) -> None:
    """内网主机名与单标签主机名必须被拒绝（4.1-5）。"""
    allowed, _ = await security.check_url(url)
    assert allowed is False, f"{url} 不应被放行"


@pytest.mark.parametrize("url", BLOCKED_SCHEME_URLS)
async def test_blocks_non_http_scheme(url: str) -> None:
    """只允许 http/https（4.1-1）。"""
    allowed, reason = await security.check_url(url)
    assert allowed is False
    assert "协议" in reason


@pytest.mark.parametrize("url", ALLOWED_URLS)
async def test_allows_public_address(url: str) -> None:
    """正常公网地址应放行（4.1-7）。"""
    allowed, reason = await security.check_url(url)
    assert allowed is True, f"{url} 被误拦：{reason}"
    assert reason == ""


async def test_blocks_domain_resolving_to_private(monkeypatch) -> None:
    """域名解析结果包含内网 IP 时必须拒绝（4.1-6）。"""
    async def fake_resolve(host: str, port: int | None = None) -> list[str]:
        return ["93.184.216.34", "10.0.0.5"]

    monkeypatch.setattr(security, "_resolve", fake_resolve)
    allowed, reason = await security.check_url("https://evil.example.org/")
    assert allowed is False
    assert "10.0.0.5" in reason


async def test_allows_domain_when_dns_fails(monkeypatch) -> None:
    """DNS 解析失败时放行，交由真正的连接去失败（避免误伤与 500）。"""
    async def boom(host: str, port: int | None = None) -> list[str]:
        raise OSError("dns down")

    monkeypatch.setattr(security, "_resolve", boom)
    allowed, _ = await security.check_url("https://unresolvable.example.org/")
    assert allowed is True


async def test_switch_off_allows_internal() -> None:
    """关闭防护开关后内网地址放行（4.1-10）。"""
    allowed, _ = await security.check_url("http://127.0.0.1:8888/", block_private_hosts=False)
    assert allowed is True


@respx.mock
async def test_extractor_rejects_internal_url_without_request(settings, tmp_path) -> None:
    """抽取器遇到内网地址直接拒绝，且不发出任何请求。"""
    route = respx.get("http://127.0.0.1:6379/").mock(return_value=httpx.Response(200, text="redis"))
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        extractor = PageExtractor(settings, client, cache)
        assert await extractor.extract("http://127.0.0.1:6379/") is None
    assert route.call_count == 0
    await cache.close()


@respx.mock
async def test_extractor_blocks_redirect_to_metadata(settings, tmp_path) -> None:
    """重定向到云元数据地址必须被拦下（4.1-8）。"""
    respx.get("https://evil.example/").mock(
        return_value=httpx.Response(
            302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
        )
    )
    metadata = respx.get("http://169.254.169.254/latest/meta-data/").mock(
        return_value=httpx.Response(200, text="SECRET-TOKEN")
    )
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    # 生产环境客户端是 follow_redirects=True，这里保持一致以验证「逐跳复检」确实生效
    async with httpx.AsyncClient(follow_redirects=True) as client:
        extractor = PageExtractor(settings, client, cache)
        assert await extractor.extract("https://evil.example/") is None
    assert metadata.call_count == 0, "内网地址不应被真正请求"
    await cache.close()


@respx.mock
async def test_extractor_gives_up_after_max_redirects(settings, tmp_path) -> None:
    """循环重定向达到上限后放弃，不会无限循环（4.1-9）。"""
    route = respx.get("https://loop.example/").mock(
        return_value=httpx.Response(302, headers={"location": "https://loop.example/"})
    )
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        extractor = PageExtractor(settings, client, cache)
        assert await extractor.extract("https://loop.example/") is None
    assert route.call_count == settings.max_redirects + 1
    await cache.close()


@respx.mock
async def test_extractor_allows_internal_when_protection_disabled(settings, tmp_path) -> None:
    """关闭开关后，内网地址仍能正常抓取（内网自用场景）。"""
    route = respx.get("http://127.0.0.1:9000/page").mock(
        return_value=httpx.Response(
            200, text=PAGE, headers={"content-type": "text/html; charset=utf-8"}
        )
    )
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    local = settings.model_copy(update={"block_private_hosts": False})
    async with httpx.AsyncClient(follow_redirects=True) as client:
        extractor = PageExtractor(local, client, cache)
        item = await extractor.extract("http://127.0.0.1:9000/page", fmt="text", max_chars=200)
    assert item is not None and item.raw_content
    assert route.call_count == 1
    await cache.close()
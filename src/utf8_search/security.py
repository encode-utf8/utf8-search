"""URL 安全校验：防止 SSRF（服务端请求伪造）。

背景：`/extract`、`/v1/extract`、MCP `web_fetch` 以及 advanced/deep 模式的抓取，
都会访问「调用方给出的 URL」。若不加限制，公网部署后可被用来探测内网服务或云元数据接口，
例如 `http://127.0.0.1:6379`（Redis）、`http://169.254.169.254/latest/meta-data/`（AWS 元数据）。

本模块只负责判断「目标地址是否可信」，不负责抓取本身；
重定向需要调用方逐跳复检（见 `PageExtractor._download`）。
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# 只放行 http/https：file / ftp / gopher / data 等一律拒绝
ALLOWED_SCHEMES = frozenset({"http", "https"})

# 明确禁止的主机名（内网与云元数据的常见目标）
BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata",
        "metadata.google.internal",
        "instance-data",
    }
)

# 视为内网的域名后缀
BLOCKED_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".lan", ".home", ".corp", ".intranet")

# 保留网段：内网 / 回环 / 链路本地 / 组播 / 文档示例段等
BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",          # 本网络
        "10.0.0.0/8",         # 私有
        "100.64.0.0/10",      # 运营商级 NAT
        "127.0.0.0/8",        # 回环
        "169.254.0.0/16",     # 链路本地（含云元数据 169.254.169.254）
        "172.16.0.0/12",      # 私有
        "192.0.0.0/24",       # IETF 协议分配
        "192.0.2.0/24",       # TEST-NET-1
        "192.168.0.0/16",     # 私有
        "198.18.0.0/15",      # 基准测试
        "198.51.100.0/24",    # TEST-NET-2
        "203.0.113.0/24",     # TEST-NET-3
        "224.0.0.0/4",        # 组播
        "240.0.0.0/4",        # 保留
        "::/128",             # 未指定
        "::1/128",            # 回环
        "fc00::/7",           # 唯一本地
        "fe80::/10",          # 链路本地
        "ff00::/8",           # 组播
    )
)


async def _resolve(host: str, port: int | None = None) -> list[str]:
    """解析主机名对应的 IP 列表。

    单独抽成模块级函数是为了便于测试打桩（离线测试不应真正查 DNS）。
    """
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port or 0, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


def _is_blocked_ip(raw: str) -> bool:
    """判断 IP 是否落在保留网段；解析失败一律视为不可信。"""
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return True
    # IPv4-mapped IPv6（如 ::ffff:127.0.0.1）要先还原成 IPv4 再判断
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip in net for net in BLOCKED_NETWORKS)


def _check_host_without_dns(host: str) -> str | None:
    """不依赖 DNS 的主机名静态检查：返回拒绝原因，通过则返回 None。"""
    name = host.strip().strip("[]").rstrip(".").lower()
    if not name:
        return "主机名为空"
    if name in BLOCKED_HOSTNAMES:
        return f"主机名 {name} 不允许访问"
    if any(name.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        return f"主机名 {name} 属于内网域名"
    if "." not in name:
        # 单标签主机名（nas / router / db 之类）几乎都是内网地址
        return f"主机名 {name} 是单标签名称，疑似内网地址"
    return None


async def check_url(url: str, *, block_private_hosts: bool = True) -> tuple[bool, str]:
    """校验 URL 是否允许抓取，返回 (是否允许, 原因)。

    `block_private_hosts=False` 时只做协议校验（供内网自用场景显式关闭防护）。
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False, "URL 解析失败"

    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        return False, f"不支持的协议: {scheme or '(空)'}"

    host = parts.hostname
    if not host:
        return False, "URL 缺少主机名"

    if not block_private_hosts:
        return True, ""

    reason = _check_host_without_dns(host)
    if reason:
        return False, reason

    # 字面量 IP：直接判断，无需 DNS
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None
    if literal is not None:
        if _is_blocked_ip(str(literal)):
            return False, f"目标 IP {literal} 属于保留网段"
        return True, ""

    # 域名：解析后检查全部 IP（任一命中内网即拒绝）
    try:
        addresses = await _resolve(host, parts.port)
    except Exception as exc:  # noqa: BLE001 - DNS 失败不应让请求直接 500
        # 解析失败放行：真正连接时同样解析不出来，构不成 SSRF；
        # 这样也避免测试环境无 DNS 时被误伤。
        logger.debug("DNS 解析失败，交由后续连接处理: %s (%s)", host, exc)
        return True, ""

    blocked = sorted({addr for addr in addresses if _is_blocked_ip(addr)})
    if blocked:
        return False, f"域名 {host} 解析到内网地址 {', '.join(blocked)}"
    return True, ""
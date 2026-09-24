"""SearXNG 配置一致性测试。

`searxng/settings.yml` 是云端默认（直连出网），`searxng/settings.local.yml` 是本机开发用
（多一段 `outgoing.proxies`，让容器走宿主机代理）。两份文件靠人工同步，很容易改一份忘另一份，
这里用测试强制约束：除 `outgoing.proxies` 外必须逐行一致。
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "searxng" / "settings.yml"
LOCAL = Path(__file__).resolve().parents[1] / "searxng" / "settings.local.yml"


def _effective_lines(path: Path, *, drop_proxies_block: bool = False) -> list[str]:
    """去掉注释与空行后的有效配置行；可选剔除 outgoing.proxies 块及其子行。"""
    lines: list[str] = []
    skipping = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if drop_proxies_block:
            indent = len(line) - len(line.lstrip())
            if skipping:
                # proxies 的子行缩进更深，跳过；遇到同级或更浅的键则结束跳过
                if indent > 2:
                    continue
                skipping = False
            if stripped == "proxies:":
                skipping = True
                continue
        lines.append(line)
    return lines


def test_local_settings_differs_only_by_proxy() -> None:
    """settings.local.yml 与 settings.yml 除 outgoing.proxies 外必须完全一致。"""
    assert LOCAL.exists(), "缺少本机开发用的 searxng/settings.local.yml"
    assert _effective_lines(LOCAL, drop_proxies_block=True) == _effective_lines(BASE)


def test_base_settings_has_no_proxy() -> None:
    """基础配置不能带代理：海外服务器直连可达，写死代理会让云端全部引擎失败。"""
    assert "proxies:" not in BASE.read_text(encoding="utf-8")


def test_local_settings_points_to_host_proxy() -> None:
    """本机配置必须指向宿主机代理，且代理主机名与 docker-compose 的 extra_hosts 对应。"""
    text = LOCAL.read_text(encoding="utf-8")
    assert "proxies:" in text
    assert "host.docker.internal" in text

    compose = (Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text(encoding="utf-8")
    assert "host.docker.internal:host-gateway" in compose, "docker-compose 缺少 extra_hosts 映射"
    assert "SEARXNG_SETTINGS_FILE" in compose, "docker-compose 缺少可切换的 settings 挂载"

"""探针的「引擎注册校验」离线测试（2026-09-30）。

背景：SearXNG 对 `engines=` 里未注册的名字是**静默丢弃**的，全部无效时还会**回退到默认引擎集合**。
2026-09-30 就因此造过假结论：`engines=sina`（sina 未注册）实际跑的是默认集合，
却把「90/90 带日期且 7 日内」记到了 sina 头上。所以探针发查询前必须先把关。
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from engine_probe import assert_engines_registered, missing_engines  # noqa: E402


class _ConfigClient:
    """只实现 /config 的假客户端。"""

    def __init__(self, engines: list[str]) -> None:
        self.engines = engines

    async def get(self, url, timeout=None):  # noqa: ANN001
        return httpx.Response(
            200,
            json={"engines": [{"name": name} for name in self.engines]},
            request=httpx.Request("GET", url),
        )


def test_missing_engines_pure_function() -> None:
    registered = ["google news", "chinaso news", "sina"]
    assert missing_engines(["google news", "sina"], registered) == []
    assert missing_engines(["google news", "bilibili"], registered) == ["bilibili"]
    assert missing_engines([], registered) == []
    # 空白项不算「缺失」，避免 --engines "" 这类调用误报
    assert missing_engines([""], registered) == []


async def test_assert_engines_registered_passes_for_registered() -> None:
    client = _ConfigClient(["google news", "sina"])
    await assert_engines_registered(client, "http://probe", ["sina"])  # 不应抛错


async def test_assert_engines_registered_exits_for_unregistered(capsys) -> None:
    """未注册的引擎必须立刻退出（而不是让 SearXNG 静默回退），并打印可用引擎列表。"""
    client = _ConfigClient(["google news", "chinaso news"])
    with pytest.raises(SystemExit) as excinfo:
        await assert_engines_registered(client, "http://probe", ["sina"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "sina" in err and "未注册" in err
    assert "google news" in err and "chinaso news" in err  # 可用引擎列表要打出来

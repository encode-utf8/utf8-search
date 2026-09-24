"""命令行入口：

    utf8-search              # 默认以 stdio 方式运行 MCP 服务（供 Claude Desktop / Codex / Cursor）
    utf8-search stdio        # 同上
    utf8-search serve        # 启动 HTTP 服务（REST + MCP Streamable HTTP）
"""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .config import get_settings


def _setup_logging(level: str) -> None:
    """日志输出到 stderr：stdio 模式下 stdout 是协议通道，绝不能污染。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> None:
    """解析参数并启动对应模式。"""
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="utf8-search", description="面向 LLM 的免费高速联网搜索服务")
    parser.add_argument("--version", action="version", version=f"utf8-search {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("stdio", help="以 stdio 方式运行 MCP 服务（默认）")
    serve = subparsers.add_parser("serve", help="启动 HTTP 服务（REST + MCP Streamable HTTP）")
    serve.add_argument("--host", default=settings.host, help=f"监听地址，默认 {settings.host}")
    serve.add_argument("--port", type=int, default=settings.port, help=f"监听端口，默认 {settings.port}")
    args = parser.parse_args(argv)

    _setup_logging(settings.log_level)

    if args.command == "serve":
        import uvicorn

        if not settings.auth_enabled:
            logging.getLogger(__name__).warning(
                "未配置 UTF8SEARCH_API_KEYS，HTTP 接口处于开放状态，建议仅在可信网络内使用。"
            )
        uvicorn.run(
            "utf8_search.server.http_api:app",
            host=args.host,
            port=args.port,
            log_level=settings.log_level.lower(),
        )
        return

    # 默认：stdio 模式
    from .server.mcp_server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
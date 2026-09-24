"""全局配置：全部可通过环境变量或 .env 覆盖（前缀 UTF8SEARCH_）。"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """服务配置。环境变量前缀 UTF8SEARCH_，例如 UTF8SEARCH_SEARXNG_URL。"""

    model_config = SettingsConfigDict(
        env_prefix="UTF8SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 上游搜索服务 ----------
    searxng_url: str = Field(default="http://127.0.0.1:8888", description="SearXNG 基础地址")
    default_engines: str = Field(
        default="resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,sogou,reloado,yep,brave,quark",
        description="传给 SearXNG 的 engines 参数，逗号分隔；留空表示使用 SearXNG 默认引擎集合",
    )
    language: str = Field(default="all", description="搜索语言，all 表示不限（中英兼顾）")
    safe_search: int = Field(default=0, description="SearXNG 安全搜索等级 0/1/2")
    search_timeout_limit: float = Field(
        default=2.5, gt=0, description="SearXNG 聚合搜索的时间上限（秒）；到点即返回已拿到的结果，避免个别引擎拖慢整体"
    )

    # ---------- 监听 ----------
    host: str = Field(default="0.0.0.0", description="serve 模式监听地址")
    port: int = Field(default=8000, description="serve 模式监听端口")
    log_level: str = Field(default="INFO", description="日志级别")

    # ---------- 鉴权与限流 ----------
    api_keys: str = Field(default="", description="逗号分隔的 API Key；留空则关闭鉴权")
    rate_limit_rpm: int = Field(default=60, ge=0, description="每个 Key 每分钟允许的请求数，0 表示不限")

    # ---------- 超时与并发 ----------
    request_timeout: float = Field(default=8.0, gt=0, description="单次上游搜索请求超时（秒）")
    fetch_timeout: float = Field(default=4.0, gt=0, description="单页「下载」硬超时（秒），超时立即放弃该页")
    page_total_timeout: float = Field(
        default=5.0, gt=0, description="单页总时长上限（秒，含下载+解析+兜底），超过即放弃该页"
    )
    advanced_budget: float = Field(default=5.0, gt=0, description="advanced 模式抓取阶段总预算（秒）")
    deep_budget: float = Field(default=12.0, gt=0, description="deep 模式抓取阶段总预算（秒，可放宽）")
    extract_budget: float = Field(
        default=10.0,
        gt=0,
        description=(
            "批量抽取接口（/extract、web_fetch）的总时间预算（秒）。"
            "与搜索不同，调用方已明确指定 URL，不在延迟竞赛中，因此给更宽松的预算以保证成功率。"
        ),
    )
    deep_page_timeout: float = Field(
        default=8.0, gt=0, description="deep 模式的单页总时长上限（秒）；deep 以覆盖为先，可比 advanced 放宽"
    )
    extract_workers: int = Field(
        default=8,
        ge=1,
        description=(
            "正文解析线程池大小。trafilatura 的解析是 GIL 受限的纯 Python 计算，"
            "线程数并非越多越快：实测 2-8 线程最快，32 线程反而因争抢 GIL 变慢。"
        ),
    )
    deep_download_timeout: float = Field(
        default=5.0, gt=0, description="deep 模式的单页下载上限（秒）；大页较多，需比 advanced 宽松"
    )
    max_fetch_concurrency: int = Field(default=24, ge=1, description="并发抓取上限")
    fetch_early_stop_ratio: float = Field(
        default=0.5, gt=0, le=1.0, description="深度模式读到该比例的目标页面即提前返回（0-1）"
    )
    fetch_min_pages: int = Field(default=3, ge=1, description="提前返回所需的最少成功页面数")
    deep_early_stop_ratio: float = Field(
        default=0.8,
        gt=0,
        le=1.0,
        description="deep 模式的提前返回比例；deep 以覆盖为先，读过更多页面才停（对标「读几十个网页」）",
    )

    # ---------- 深度模式 ----------
    advanced_pages: int = Field(default=6, ge=0, description="advanced 模式抓取的页面数")
    deep_pages: int = Field(default=24, ge=0, description="deep 模式抓取的页面数（对标「读几十个网页」）")
    page_max_chars: int = Field(default=3000, gt=0, description="深度模式下单页返回给 LLM 的字符上限")
    raw_content_max_chars: int = Field(default=20000, gt=0, description="include_raw_content 时单页字符上限")

    # ---------- 缓存 ----------
    cache_path: str = Field(default="data/cache.db", description="SQLite 缓存文件路径")
    cache_query_ttl: int = Field(default=600, ge=0, description="查询结果缓存 TTL（秒）")
    cache_page_ttl: int = Field(default=21600, ge=0, description="网页正文缓存 TTL（秒）")
    cache_result_ttl: int = Field(default=300, ge=0, description="最终结果包缓存 TTL（秒）")
    cache_memory_size: int = Field(default=256, ge=0, description="内存 LRU 条目上限")
    cache_enabled: bool = Field(default=True, description="是否启用缓存")

    # ---------- 网络代理 ----------
    # 说明：Windows 上若启用了系统代理（如本地 Clash/V2Ray 的 127.0.0.1:7897），
    # httpx 会把「连回环地址的请求」也发给代理，导致访问本机 SearXNG 时收到 502。
    # 因此默认让下列主机绕过代理直连。
    trust_env: bool = Field(default=True, description="是否读取系统/环境变量中的代理设置")
    http_proxy: str = Field(default="", description="显式指定代理（如 http://127.0.0.1:7897）；留空则使用系统代理")
    bypass_proxy_hosts: str = Field(
        default="127.0.0.1,localhost,[::1],searxng",
        description="绕过代理直连的主机（逗号分隔），默认包含本机与容器内 SearXNG 主机名",
    )
    # ---------- 抽取 ----------
    enable_jina_fallback: bool = Field(default=True, description="抽取失败时是否用 r.jina.ai 兜底")
    jina_prefix: str = Field(default="https://r.jina.ai/", description="Jina Reader 前缀")
    jina_timeout: float = Field(default=3.0, gt=0, description="Jina Reader 兜底的单页超时（秒）")
    jina_fallback_depths: str = Field(
        default="deep",
        description="允许 Jina 兜底的深度模式（逗号分隔）；advanced 保持纯本地抓取以保证速度",
    )
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 utf8-search/0.1"
        ),
        description="抓取网页时使用的 User-Agent",
    )

    # ---------- MCP HTTP ----------
    mcp_allowed_hosts: str = Field(default="", description="MCP Streamable HTTP 允许的 Host，逗号分隔")
    mcp_json_response: bool = Field(default=False, description="MCP HTTP 是否使用纯 JSON 响应（禁用 SSE 流）")

    @property
    def api_key_set(self) -> frozenset[str]:
        """解析后的 API Key 集合。"""
        return frozenset(k.strip() for k in self.api_keys.split(",") if k.strip())

    @property
    def auth_enabled(self) -> bool:
        """是否启用鉴权：配置了 Key 才启用。"""
        return bool(self.api_key_set)

    @property
    def engine_list(self) -> list[str]:
        """解析后的默认引擎列表。"""
        return [e.strip() for e in self.default_engines.split(",") if e.strip()]

    @property
    def jina_depth_list(self) -> list[str]:
        """允许 Jina 兜底的深度模式列表。"""
        return [d.strip() for d in self.jina_fallback_depths.split(",") if d.strip()]

    @property
    def bypass_proxy_host_list(self) -> list[str]:
        """解析后的代理绕过主机列表。"""
        return [h.strip() for h in self.bypass_proxy_hosts.split(",") if h.strip()]
    @property
    def allowed_host_list(self) -> list[str]:
        """解析后的 MCP 允许 Host 列表。"""
        return [h.strip() for h in self.mcp_allowed_hosts.split(",") if h.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()
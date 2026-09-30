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
        default="resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark,360search",
        description="传给 SearXNG 的 engines 参数，逗号分隔；留空表示使用 SearXNG 默认引擎集合",
    )
    language: str = Field(default="all", description="搜索语言，all 表示不限（中英兼顾）")
    safe_search: int = Field(default=0, description="SearXNG 安全搜索等级 0/1/2")
    search_timeout_limit: float = Field(
        default=2.5, gt=0, description="SearXNG 聚合搜索的时间上限（秒）；到点即返回已拿到的结果，避免个别引擎拖慢整体"
    )

    # ---------- 查询质量与多样性（M5-5.3） ----------
    # 说明：2-9 抽检未达标的查询暴露的问题（同站重复、聚合页、无关脚本、低覆盖结果）
    # 全部用客观信号修掉，不维护站点黑名单。所有过滤都遵循「候选充足才过滤」：
    # 过滤后不足 max_results 时会按原排序补回，绝不让质量过滤把结果掏空。
    rank_max_per_host: int = Field(
        default=2,
        ge=0,
        description="最终结果里同一可注册域最多保留几条（0=不限）；实测 bilibili 单查询会灌 20 条同站结果",
    )
    rank_min_query_coverage: float = Field(
        default=0.34,
        ge=0.0,
        le=1.0,
        description="查询词覆盖率下限：候选充足时剔除覆盖率低于该值的结果（0=关闭）",
    )
    rank_drop_aggregator_pages: bool = Field(
        default=True, description="候选充足时剔除站点首页/栏目页这类聚合页（正文只是导航，对 LLM 无价值）"
    )
    rank_drop_script_mismatch: bool = Field(
        default=True, description="查询含中文时，剔除标题为纯西里尔/阿拉伯/韩文等非中文/非英文脚本的结果"
    )
    general_recency_intent: bool = Field(
        default=True,
        description=(
            "通用主题命中「最新/最近/latest」等时间词时按新鲜度重排。"
            "只用 URL 内嵌日期与标题里的跨年年份（零网络开销），不抓页面、不丢弃无日期结果，"
            "因此不影响 basic 速度"
        ),
    )
    rank_candidate_pool: int = Field(
        default=24,
        ge=1,
        description=(
            "通用主题向上游索取的候选条数（M5-5.3）。必须是「候选池」而不是 top-N："
            "SearXNG 本来就把整批结果一次返回给本地，多留候选不增加任何网络开销；"
            "但候选数等于结果数时，质量过滤会因为「不足 max_results」被全部补回，等于失效"
        ),
    )

    # ---------- 引擎健康度自适应（M5-5.1） ----------
    # 说明：实测 SearXNG 对处于惩罚期（suspended）的引擎是*快速失败*（0.03-0.19s、不发上游请求），
    # 剔除它们并不省延迟；自适应的目的是让引擎集合随上游健康状态自动收敛与恢复，
    # 避免静态名单过期带来的覆盖率损失（实测引擎健康度是分钟级漂移的）。
    engine_health_enabled: bool = Field(
        default=True, description="是否启用引擎健康度自适应（关闭后行为与旧版完全一致）"
    )
    engine_health_min_active: int = Field(
        default=6,
        ge=1,
        description="候选引擎里至少要保留的可用数；不足时按「最早解冻优先」补入冷却中的引擎，防止引擎集合萎缩",
    )
    engine_health_probe_slots: int = Field(
        default=0,
        ge=0,
        description="每次查询额外带入的冷却中引擎数（0 表示只靠冷却到期自动恢复，零额外浪费）",
    )
    engine_health_cooldown_captcha: float = Field(
        default=1800.0, gt=0, description="CAPTCHA 类失败的冷却时长（秒）；需人工/换出口 IP 才能解，退避最久"
    )
    engine_health_cooldown_denied: float = Field(
        default=900.0, gt=0, description="access denied / 403 类失败的冷却时长（秒）"
    )
    engine_health_cooldown_rate_limit: float = Field(
        default=180.0,
        gt=0,
        description="限流类失败的冷却时长（秒）：too many requests / 429 / 无原因 suspended（与 SearXNG 惩罚盒同量级）",
    )
    engine_health_cooldown_timeout: float = Field(
        default=90.0, gt=0, description="超时类失败的冷却时长（秒）"
    )
    engine_health_cooldown_other: float = Field(
        default=120.0, gt=0, description="其他原因失败的冷却时长（秒）"
    )
    engine_health_cooldown_max: float = Field(
        default=3600.0, gt=0, description="连续失败指数退避的冷却上限（秒）"
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
    # ---------- 上游并发闸门（M5 并发保护） ----------
    # 背景：docs/04 §4.4 实测并发 10 冷查询会劣化到 ~12s，瓶颈在上游聚合（吞吐仅 1.3-2.0 req/s）。
    # 闸门只限制「同时打到 SearXNG 的聚合请求数」，不改搜索语义；目标是「宁可快速失败，不要一起慢」。
    upstream_max_concurrency: int = Field(
        default=3,
        ge=0,
        description="同时打到 SearXNG 的聚合请求上限（0 = 关闭闸门，不推荐）；实测并发 1-3 时 P50≈1.3s",
    )
    # 默认值来自 2026-09-27 的参数矩阵扫描（见 docs/reports/m5-concurrency-gate-20260927.md）：
    # 「排队优先、拒绝为例外」——queue 6 时 @10 只有 18% 成功率，queue 12 才把 @10 拉到 100%；
    # max_wait 取满足「@10 ≥90% 且 P95 ≤6s」的最小值 4.0s（@30 实测 15-27%，在 25% 阈值附近抖动）。
    # 兜底型调用的 OPTIONAL_WAIT 在「主源不足才补」结构改完后重扫 1.0/1.5/3.0s，
    # 取满足「news@10 降级率 ≤30% 且 空结果率 ≤10% 且 P95 ≤6.5s」的最小值 1.0s。
    upstream_queue_limit: int = Field(
        default=12,
        ge=0,
        description="上游闸门允许排队的请求数上限；队列满立即返回 429，避免把上游压垮",
    )
    upstream_max_wait: float = Field(
        default=4.0,
        gt=0,
        description="上游闸门排队等待上限（秒）；超过立即返回 429，避免所有请求一起慢",
    )
    upstream_optional_wait: float = Field(
        default=1.0,
        ge=0,
        description=(
            "兜底型上游调用（news 的通用引擎补充、Bing 兜底）取容量的有限等待（秒）。"
            "0 = 立即失败。等不到容量即 429，绝不静默跳过（跳过会返回空结果）"
        ),
    )
    metrics_enabled: bool = Field(
        default=True, description="是否暴露 Prometheus 文本格式的 /metrics（沿用 REST 鉴权）"
    )
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
    # ---------- 安全（SSRF 防护） ----------
    # 说明：/extract、web_fetch 与深度模式抓取都会访问调用方给出的 URL。
    # 默认禁止访问内网 / 回环 / 云元数据等保留地址，避免公网部署后被用于内网探测。
    block_private_hosts: bool = Field(
        default=True,
        description="是否禁止抓取内网与保留地址（SSRF 防护）；内网自用场景可显式关闭",
    )
    max_redirects: int = Field(
        default=5,
        ge=0,
        description="抓取时允许的最大重定向次数；每一跳都会重新做一次安全校验",
    )

    # ---------- 时效性（M5-5.2） ----------
    news_engines: str = Field(
        default="duckduckgo news,sogou wechat,google news",
        description=(
            "topic=news 时传给 SearXNG 的新闻类目引擎（逗号分隔）。留空表示交给 SearXNG "
            "自己的 news 类目引擎集合。默认三个引擎是 2026-09-24 逐引擎隔离实测的结果："
            "duckduckgo news 日期覆盖 100%、英文时效最好但纯中文查询会返回 0 条；"
            "sogou wechat 补中文盲区（8/8 查询各 10 条且 100% 带日期）；"
            "google news 中文覆盖最全但不返回发布日期，需靠 URL/页面回补日期"
        ),
    )
    news_fresh_days: int = Field(
        default=7, ge=1, description="新闻结果视为「新鲜」的天数窗口（未显式指定 time_range 时生效）"
    )
    news_date_backfill: bool = Field(
        default=True, description="新闻结果缺少发布日期时，抓取页面用 htmldate 推断补齐"
    )
    news_date_pages: int = Field(default=16, ge=0, description="日期回补最多抓取的页面数（0 表示关闭）")
    news_date_budget: float = Field(default=4.0, gt=0, description="日期回补阶段的总时间预算（秒）")
    news_candidate_pool: int = Field(
        default=30,
        ge=1,
        description=(
            "topic=news 时向上游索取的候选条数。必须是候选池而不是 top-N，"
            "否则融合后已无可挑选的余地，时效排序无意义"
        ),
    )
    news_include_general: bool = Field(
        default=True,
        description=(
            "topic=news 时是否额外打一次通用引擎补充候选。"
            "实测免费新闻源对中文长尾覆盖差（8 条查询中 3 条返回 0 条），需要通用引擎兜候选"
        ),
    )
    news_general_engines: str = Field(
        default="resulthunter,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,brave,quark",
        description=(
            "新闻主题做「通用引擎新鲜候选补充」时用的引擎列表（逗号分隔）。"
            "默认排除 yandex：实测 yandex 配合 time_range 会返回大量垃圾农场内容"
            "（成人站/盗播站），而这一路只用来补最新候选，用更干净的引擎集更划算。"
            "2026-09-30 调整：移除已从 SearXNG 删除的 360search；同日实测 sina 注册后"
            "**60 条结果里 0 条带发布日期**（此前「90/90 带日期」是引擎未注册触发回退的假象），"
            "它只会稀释候选，因此**不再加入**，本条恢复为「只含通用引擎」的语义。"
            "留空表示复用 default_engines"
        ),
    )
    news_pass_time_range: bool = Field(
        default=False,
        description=(
            "[旧开关，保留兼容] topic=news 时是否把 time_range 透传给**所有**新闻引擎。"
            "实测大部分免费新闻引擎不支持该过滤（duckduckgo news 传 time_range=day 返回 0 条），"
            "因此默认关闭；是否透传改由 news_time_range_engines 白名单逐引擎决定。"
            "置 true 等价于「所有新闻引擎都透传」，仅用于排障对比。"
        ),
    )
    news_time_range_engines: str = Field(
        default="",
        description=(
            "topic=news 时**允许透传 time_range** 的引擎白名单（逗号分隔，逗号分隔、默认为空）。"
            "为什么要白名单而不是全局开关：同一个 time_range 对不同引擎效果相反 —— "
            "duckduckgo news、chinaso news、tiger news 带 time_range=day 都返回 0 条，"
            "而真正支持它的引擎（如将来验证过的中文源）需要透传；一个全局布尔服务不了两者。"
            "**默认留空**：2026-09-30 实测唯一被考虑过的候选 sina 注册后 0 条带发布日期，已撤回"
            "（当初把它写进白名单的依据是一条假测量 —— 引擎未注册时 SearXNG 会回退默认集合）。"
            "机制保留：白名单非空时，白名单引擎与其余新闻引擎会拆成两次上游请求"
            "（仍在同一个闸门槽位内），结果合并去重。"
        ),
    )
    news_drop_stale: bool = Field(
        default=True, description="新闻主题下丢弃已知过期结果（仅在非过期结果已够 max_results 时生效）"
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
    def news_general_engine_list(self) -> list[str]:
        """新闻主题「通用引擎新鲜候选补充」用的引擎列表。"""
        return [e.strip() for e in self.news_general_engines.split(",") if e.strip()]

    @property
    def news_time_range_engine_set(self) -> set[str]:
        """解析后的「允许透传 time_range」引擎白名单。"""
        return {e.strip() for e in self.news_time_range_engines.split(",") if e.strip()}

    @property
    def news_engine_list(self) -> list[str]:
        """解析后的新闻引擎列表（topic=news 时使用）。"""
        return [e.strip() for e in self.news_engines.split(",") if e.strip()]

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

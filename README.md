# utf8-search

> 面向 LLM / Agent 的**免费**联网检索服务：MCP Server + Tavily-compatible REST。
> 单栈自托管（Docker Compose），无付费搜索 API 依赖。

## TL;DR

| 面 | 现状（2026-10-03） |
| --- | --- |
| 协议 | MCP：`stdio` / Streamable HTTP（`/mcp`，JSON-RPC + SSE）；REST：`/v1/search`、`/v1/extract`（别名 `/search`、`/extract`） |
| 检索栈 | SearXNG 聚合 **12 通用 + 4 新闻**免费引擎 → RRF 融合 + URL 归一化去重 + BM25 重排（中文 bigram） |
| 质量 | 候选池 24；同域限流 / 聚合页 / 内容农场 / 非主题页过滤；spec-token（版本·型号）匹配；`degraded_reason` 如实降级 |
| 时效 | news 源 + `time_range` + 日期回补（htmldate）；中文时效不足时返回 `freshness_unverified`（不伪造新鲜度） |
| 稳定性 | upstream gate `3 / 12 / 4.0s / 1.0s`；引擎健康冷却（CAPTCHA/429/timeout）；过载 429 + `Retry-After` |
| 安全 | API key（`Authorization: Bearer` / `X-API-Key` / body `api_key`）；RPM 60/key；SSRF 防护；Caddy TLS（ACME） |
| 验收 | 2-9 线上 **19/19/19**（median 19 / min 19）；`mcp_selfcheck` **24/24**；8 需求 **7 ✅ / 1 ⚠️ / 0 ❌** |
| 说明站 | `https://<host>/guide/` — 分点目录 + 全文搜索 + 节点探测 + REST/MCP 调试台（纯前端） |

## 架构

```text
Client (LLM / Agent)
  ├─ MCP stdio ─────────────┐
  ├─ MCP HTTP  /mcp ────────┤
  └─ REST      /v1/search ──┤
                            ▼
                    utf8-search (FastAPI)
                      ├─ rank: RRF / BM25 / filters
                      ├─ cache: SQLite (3-level)
                      ├─ extract: trafilatura
                      └─ fallback: Bing HTML
                            │
                            ▼
                        SearXNG ──▶ free engines

Caddy (TLS/ACME, 80/443) ──▶ utf8-search:8000
                          └─▶ docs:80  (/guide/*)
```

* Services：`searxng` / `utf8-search` / `caddy` / `docs`（均 `restart: unless-stopped`，日志轮转 10MB×3）
* Runtime：Python ≥3.10、FastAPI + uvicorn、httpx、MCP SDK；缓存 SQLite；TLS 由 Caddy 自动签发/续期
* Ports：公网仅 Caddy `80/443`；app `127.0.0.1:8000`、SearXNG `127.0.0.1:8888`、docs `127.0.0.1:8080`

## 快速开始

### Docker（推荐）

```bash
cp .env.example .env
# 必改：UTF8SEARCH_API_KEYS / UTF8SEARCH_MCP_ALLOWED_HOSTS
docker compose up -d
curl -s http://127.0.0.1:8000/health | jq .
.venv/bin/python scripts/mcp_selfcheck.py --base-url http://127.0.0.1:8000 --api-key "$KEY"
```

### 本地开发

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q -m "not net"        # 389 passed / 4 deselected
utf8-search                             # MCP stdio
utf8-search serve --host 127.0.0.1 --port 8000
```

> 本机 `.venv` 是 editable 安装、指向主仓库 `src/`：复测必须**在主仓库切分支**运行，勿用 `git worktree`。

### 中国大陆网络

SearXNG 出口**不读**宿主机代理环境变量；需 `SEARXNG_SETTINGS_FILE=./searxng/settings.local.yml`（含代理）后重启 searxng。

## .env 速查

| Key | 默认 | 说明 |
| --- | --- | --- |
| `UTF8SEARCH_API_KEYS` | 空 | 逗号分隔；空 = 关闭鉴权（`/health` 恒免鉴权） |
| `UTF8SEARCH_MCP_ALLOWED_HOSTS` | 空 | MCP DNS-rebinding 白名单（Host 精确匹配，未命中 421） |
| `UTF8SEARCH_SEARXNG_URL` | `http://127.0.0.1:8888` | 容器内为 `http://searxng:8080` |
| `UTF8SEARCH_DEFAULT_ENGINES` | 12 个通用引擎 | `resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark` |
| `UTF8SEARCH_NEWS_ENGINES` | 4 个新闻引擎 | `duckduckgo news,google news,chinaso news,tiger news` |
| `UTF8SEARCH_RATE_LIMIT_RPM` | `60` | 每 Key 每分钟请求数；`0` = 不限 |
| `UTF8SEARCH_CACHE_QUERY_TTL` | `600` | 查询缓存 TTL（秒）；复测须绕缓存 |
| `UTF8SEARCH_UPSTREAM_MAX_CONCURRENCY/QUEUE_LIMIT/MAX_WAIT/OPTIONAL_WAIT` | `3/12/4.0/1.0` | 上游并发闸门（**禁止多 worker**，否则限流失效） |

完整键表：`docs/05-服务器部署手册.md` §4；容器注入策略：`docs/reports/m6-env-wiring-plan-20260930.md`。

## API 摘要

| Endpoint | 方法 | 说明 |
| --- | --- | --- |
| `/v1/search`、`/search` | POST | Tavily-compatible 搜索；`query/max_results/search_depth/topic/time_range/days/engines/...` |
| `/v1/extract`、`/extract` | POST | URL → Markdown/text（`urls[]` ≤10） |
| `/mcp` | POST | MCP Streamable HTTP：`initialize → notifications/initialized → tools/call` |
| `/health` | GET | 服务与引擎快照（`engines.active/cooling`）；免鉴权 |
| `/metrics` | GET | Prometheus 文本（闸门/上游延迟直方图）；需鉴权 |

* Auth：`Authorization: Bearer <key>` ≡ `X-API-Key: <key>` ≡ body `api_key`（仅 REST）
* `degraded_reason`（逗号分隔、可多值）：`freshness_unverified` / `no_relevant_results` / `spec_unverified` / `fallback_low_relevance` / `news_structure_unverified` / `index_page_unverified` / `upstream_overloaded`
* `topic=news` 的 `time_range/days` 是**强偏好**而非硬过滤；以每条结果的 `published_date` 为准

## 质量 / 稳定性（实测）

* **服务契约**：@≤5 并发 → 100% 成功 / 0 降级 / P95 ≤5.2s；@10 → ≥95% / P95 ≤6.5s；过载快速 429（`Retry-After`）
* **2-9 相关性**：登记口径（固定 commit + 20 条 + `--no-cache` + 单并发 + ≥3 轮取中位）= **19/19/19**；agent 初评 + 校准集 + 盲评，敏感性口径（严格判）同时披露
* **长稳**：24h / 6h / 1h soak 可用率 **100%**；6h（镜像 `3a521d3e6f9d`）P50 **1052ms** / P95 **2113ms**；
  现网镜像（`258749c7a318`）1h P50 1353ms / P95 2598ms
* **引擎**：冷却分级（CAPTCHA 30min / denied 15min / rate-limit 3min / timeout 90s）+ 指数退避；`/health.engines.cooling` 可观测
* **候选池实验**：SearXNG 整批返回 31–47 条，池 24→40 覆盖率 0.832→0.843、零额外网络成本；默认保持 **24** 未改

## 工程脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/mcp_selfcheck.py` | stdio / HTTP-MCP / REST / ratelimit 全通道自检（24 项） |
| `scripts/soak.py` | 长稳（`--status` / `--summarize`，强杀不丢结论） |
| `scripts/loadtest.py` | 并发压测（429/降级/延迟分布） |
| `scripts/relevance.py` | 2-9 抽检采集/判定（`--score-file`、`--compare-hygiene`） |
| `scripts/replay_pool.py` | 固定候选池受控回放（改前/改后归因；支持 `REPLAY_SRC`） |
| `scripts/ops_check.py` | 巡检：health / metrics / 证书 / 备份 / 磁盘 + 指标快照 CSV（cron 每 5min） |
| `scripts/backup.sh` | 加密备份（`BACKUP_PASSPHRASE`；`SHA256SUMS`；保留策略） |
| `scripts/check_refs.py` | 非忽略文件引用完整性（CI/离线套件）；`scripts/build_docs_site.py` 生成 `/guide` 站点（`--check`） |

## 已知限制

* **中文新闻时效**：免费中文新鲜源不可得（评估结论）；返回 `freshness_unverified`，不伪造日期
* **Q2 类主题查询**：上游池无切题候选时返回 `no_relevant_results`（不硬凑）
* **Tavily 兼容差异**（有意保留）：`answer` 恒 `null`、图片字段恒空、`score` 量纲不同、`usage.credits` 恒 0
* **免费源无 SLA**：CAPTCHA / 限流为常态，靠健康冷却 + 兜底 + 缓存吸收
* 待触发项：闸门上限自适应（等坏日样本）、TLS 证书续期核对（2026-11-24 前后）

## 文档索引

* 客户端接入：`docs/03-客户端接入指南.md`（MCP / REST / 7 类客户端 / 故障对照）
* 部署运维：`docs/05-服务器部署手册.md`（架构 / .env / 证书 / 备份 / 回滚）
* 路线图与遗留：`docs/04-后续路线图.md`、`checklist.md`（§8 工作记录）
* 验收报告索引：`docs/reports/README.md`（报告类链接统一经此索引）
* 在线说明站（含测试台）：`https://43.106.104.49.sslip.io/guide/`

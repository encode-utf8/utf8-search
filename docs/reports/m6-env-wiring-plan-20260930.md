# 容器 env 接线方案（只写方案，不改 compose / 不改 .env）（2026-09-30）

> 本轮**不动容器接线**：`docker-compose.yml` 与 `.env` 保持现状（只保留上一轮为「引擎列表落地」做的最小注入）。
> 本文给下一步实施用的方案、逐键分类、回归清单、风险与回滚，等拍板后再动。报告分支 `docs/env-wiring-plan-20260930`。

## 0. 结论（先看这三条）

1. **病根**：`Settings` 的 `env_file=".env"` 是相对**进程工作目录**解析的，容器工作目录是 `/app`，
   镜像里没有 `.env`、compose 也没挂载；而 compose 的 `.env` 只用于**变量替换**、不会自动注入容器。
   结果：容器只拿到 4 个显式注入的变量（现为 6 个），**其余 ~64 项 `.env` 设置全部跑 `config.py` 代码默认值**。
2. **建议写法**：`env_file: [.env]` 全量继承 + `environment:` **显式覆盖清单**（compose 里 `environment` 优先于 `env_file`）。
   覆盖清单很短：`SEARXNG_URL`（容器内必须换地址）+ 3 个安全/限流键（保持现值）+ 代理三件套（容器内必须中性化）。
3. **必须重测**：接线会让容器的引擎集合、时效窗口、日期回补预算、rank 过滤、闸门参数**第一次真正生效**，
   所以**先前经容器路径得到的质量/时效数字全部作废**（§5 列了清单与对照基线）。

## 1. 现状事实（可复核）

```bash
$ docker inspect utf8-search-app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep UTF8SEARCH
UTF8SEARCH_API_KEYS=…
UTF8SEARCH_RATE_LIMIT_RPM=60
UTF8SEARCH_MCP_ALLOWED_HOSTS=43.106.104.49:*,43.106.104.49.sslip.io
UTF8SEARCH_DEFAULT_ENGINES=resulthunter,…,quark          # 上一轮新增的最小注入
UTF8SEARCH_NEWS_ENGINES=duckduckgo news,google news,chinaso news,tiger news   # 同上
UTF8SEARCH_SEARXNG_URL=http://searxng:8080
$ docker exec utf8-search-app ls /app/.env     # → 不存在
$ grep -cE '^[A-Z0-9_]+=' .env.example        # → 70（本方案的分类对象）
```

- 代码依据：`src/utf8_search/config.py` 里 `SettingsConfigDict(env_prefix="UTF8SEARCH_", env_file=".env", extra="ignore")`；
  环境变量**优先于** `.env`（pydantic-settings 的既有优先级），所以「显式覆盖」可靠。
- 容器启动命令是 `uvicorn … --host 0.0.0.0 --port 8000`（Dockerfile `CMD`），**不经过 `settings.host/port`**
  （那两项只在 `utf8-search serve` 子命令里用）⇒ 注入 `HOST`/`PORT` 对容器无效。

## 2. 逐键三分类（70 键，取自 `.env.example`）

### A. 容器应继承（60 键）——理由：这些是产品行为参数，容器就是产品

| 键 | .env 值 | 容器内应为 | 理由/代码依据 |
| --- | --- | --- | --- |
| `UTF8SEARCH_REQUEST_TIMEOUT` | 8 | 同 | 抓取 HTTP 超时（`extract`/`pipeline`） |
| `UTF8SEARCH_FETCH_TIMEOUT` | 4.0 | 同 | 单页抓取超时 |
| `UTF8SEARCH_PAGE_TOTAL_TIMEOUT` | 5.0 | 同 | 单页总时长上限 |
| `UTF8SEARCH_ADVANCED_BUDGET` / `_DEEP_BUDGET` / `_EXTRACT_BUDGET` | 5.0 / 12 / 10 | 同 | 各深度阶段的抓取预算 |
| `UTF8SEARCH_DEEP_PAGE_TIMEOUT` / `_DEEP_DOWNLOAD_TIMEOUT` | 8 / 5 | 同 | deep 模式单页时长 |
| `UTF8SEARCH_EXTRACT_WORKERS` / `_MAX_FETCH_CONCURRENCY` | 8 / 24 | 同 | 抓取并发 |
| `UTF8SEARCH_FETCH_EARLY_STOP_RATIO` / `_FETCH_MIN_PAGES` / `_DEEP_EARLY_STOP_RATIO` | 0.5 / 3 / 0.8 | 同 | 早停判据 |
| `UTF8SEARCH_ADVANCED_PAGES` / `_DEEP_PAGES` | 6 / 24 | 同 | 读页目标 |
| `UTF8SEARCH_PAGE_MAX_CHARS` / `_RAW_CONTENT_MAX_CHARS` | 3000 / 20000 | 同 | 正文截断 |
| `UTF8SEARCH_UPSTREAM_MAX_CONCURRENCY` / `_QUEUE_LIMIT` / `_MAX_WAIT` / `_OPTIONAL_WAIT` | 3 / 12 / 4.0 / 1.0 | 同 | **闸门参数**（本轮不改，接线后 .env 成为唯一事实源；现值与代码默认一致） |
| `UTF8SEARCH_METRICS_ENABLED` | true | 同 | `/metrics` 开关（M5） |
| `UTF8SEARCH_CACHE_QUERY_TTL` / `_PAGE_TTL` / `_RESULT_TTL` | 600 / 21600 / 300 | 同 | 缓存 TTL |
| `UTF8SEARCH_LANGUAGE` / `_SAFE_SEARCH` | all / 0 | 同 | 搜索语言/安全等级 |
| `UTF8SEARCH_SEARCH_TIMEOUT_LIMIT` | 2.5 | 同 | SearXNG 聚合时间上限 |
| `UTF8SEARCH_DEFAULT_ENGINES` | 12 引擎 | 同 | 通用路径引擎列表（**已接线**） |
| `UTF8SEARCH_ENGINE_HEALTH_ENABLED` / `_MIN_ACTIVE` / `_PROBE_SLOTS` | true / 6 / 0 | 同 | 5.1 健康自适应 |
| `UTF8SEARCH_ENGINE_HEALTH_COOLDOWN_{CAPTCHA,DENIED,RATE_LIMIT,TIMEOUT,OTHER,MAX}` | 1800/900/180/90/120/3600 | 同 | 各失败类别的冷却时长 |
| `UTF8SEARCH_ENABLE_JINA_FALLBACK` / `_JINA_FALLBACK_DEPTHS` / `_JINA_TIMEOUT` | true / deep / 3 | 同 | 抽取失败兜底 |
| `UTF8SEARCH_NEWS_ENGINES` | 4 个（含两个新中文源） | 同 | 新闻主源列表（**已接线**） |
| `UTF8SEARCH_NEWS_FRESH_DAYS` | 7 | 同 | 时效窗口（5.2 门槛口径） |
| `UTF8SEARCH_NEWS_DATE_BACKFILL` / `_DATE_PAGES` / `_DATE_BUDGET` | true / 16 / 4.0 | 同 | 日期回补策略（直接影响时效门槛） |
| `UTF8SEARCH_NEWS_CANDIDATE_POOL` | 30 | 同 | 新闻候选池 |
| `UTF8SEARCH_NEWS_INCLUDE_GENERAL` / `_PASS_TIME_RANGE` / `_DROP_STALE` | true / false / true | 同 | 新闻补充路与本地过滤口径 |
| `UTF8SEARCH_RANK_CANDIDATE_POOL` / `_RANK_MAX_PER_HOST` / `_RANK_MIN_QUERY_COVERAGE` | 24 / 2 / 0.34 | 同 | 5.3 质量与多样性过滤 |
| `UTF8SEARCH_RANK_DROP_AGGREGATOR_PAGES` / `_RANK_DROP_SCRIPT_MISMATCH` / `_GENERAL_RECENCY_INTENT` | true / true / true | 同 | 同上 |
| `UTF8SEARCH_BLOCK_PRIVATE_HOSTS` / `_MAX_REDIRECTS` | true / 5 | 同 | SSRF 防护（**必须保持 true**，容器同样暴露公网链路） |
| `UTF8SEARCH_LOG_LEVEL` | INFO | 同 | 日志级别 |
| `UTF8SEARCH_CACHE_PATH` | `data/cache.db` | **同（无需覆盖）** | 相对路径：容器 cwd=`/app` 且 `./data:/app/data` 已挂载 ⇒ 落到宿主机 `./data/cache.db`，与现在一致 |

> 归类说明：A 类里的 `DEFAULT_ENGINES`/`NEWS_ENGINES`/`API_KEYS`/`RATE_LIMIT_RPM`/`MCP_ALLOWED_HOSTS`
> **必须显式注入**（值同 `.env`），因为它们是「服务身份/资源」而不是可选项；其余 A 类靠 `env_file` 继承即可。

### B. 容器必须覆盖为**不同值**（1 键）

| 键 | .env 值（宿主机视角） | 容器内必须为 | 为什么不能继承 |
| --- | --- | --- | --- |
| `UTF8SEARCH_SEARXNG_URL` | `http://127.0.0.1:8888` | **`http://searxng:8080`** | 容器内的 `127.0.0.1` 是容器自己；SearXNG 是同 compose 网络里的 `searxng` 服务（现在靠 environment 覆盖，已经是正确值，接线后必须保留这条覆盖） |

### C. 不应注入容器（6 键）

| 键 | .env 值 | 为什么不该进容器 |
| --- | --- | --- |
| `SEARXNG_SETTINGS_FILE` | `./searxng/settings.yml` | **compose 变量**（决定 searxng 容器挂哪份配置），不是应用设置；应用 `Settings(extra="ignore")` 会忽略它，注入只会造成误解 |
| `UTF8SEARCH_HOST` / `UTF8SEARCH_PORT` | 0.0.0.0 / 8000 | 只服务 `utf8-search serve` 子命令；容器用 `uvicorn --host/--port` 固定值。注入无效，且会误导「改了就能改监听」 |
| `UTF8SEARCH_TRUST_ENV` | true | 宿主机代理开关。容器应**显式中性化**（见 §3），避免大陆开发机上把 `HTTP_PROXY` 带进服务器容器 |
| `UTF8SEARCH_HTTP_PROXY` | 空 | 同上；显式置空 |
| `UTF8SEARCH_BYPASS_PROXY_HOSTS` | `127.0.0.1,localhost,[::1],searxng` | 同上；显式置空 |

（计数口径：**A 60 + 服务身份 3 + B 1 + C 6 = 70**。那 3 个身份键——`UTF8SEARCH_API_KEYS` /
`UTF8SEARCH_RATE_LIMIT_RPM` / `UTF8SEARCH_MCP_ALLOWED_HOSTS`——取值与宿主机相同（属「继承」），
但必须**显式注入**，因为它们决定「公网鉴权 + 限流 + Host 白名单」，不能依赖 `env_file` 是否被解析。）

## 3. 接线写法建议（下一轮实施）

```yaml
services:
  utf8-search:
    env_file:
      - .env                     # ① 全量继承（A 类 60 键）
    environment:                 # ② 显式覆盖（compose 的 environment 优先级高于 env_file）
      - UTF8SEARCH_SEARXNG_URL=http://searxng:8080        # B 类：容器内地址必须不同
      - UTF8SEARCH_API_KEYS=${UTF8SEARCH_API_KEYS:-}      # 服务身份（值同 .env）
      - UTF8SEARCH_RATE_LIMIT_RPM=${UTF8SEARCH_RATE_LIMIT_RPM:-60}
      - UTF8SEARCH_MCP_ALLOWED_HOSTS=${UTF8SEARCH_MCP_ALLOWED_HOSTS:-}
      - UTF8SEARCH_DEFAULT_ENGINES=${UTF8SEARCH_DEFAULT_ENGINES:-resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark}
      - UTF8SEARCH_NEWS_ENGINES=${UTF8SEARCH_NEWS_ENGINES:-duckduckgo news,google news,chinaso news,tiger news}
      # ③ 显式中性化宿主机专用项（C 类）
      - UTF8SEARCH_TRUST_ENV=false
      - UTF8SEARCH_HTTP_PROXY=
      - UTF8SEARCH_BYPASS_PROXY_HOSTS=
```

**显式覆盖清单（逐条）**：

| 键 | 容器值 | 为什么不能继承 |
| --- | --- | --- |
| `UTF8SEARCH_SEARXNG_URL` | `http://searxng:8080` | 宿主机值是 `127.0.0.1:8888`（容器内的回环地址） |
| `UTF8SEARCH_API_KEYS` / `_RATE_LIMIT_RPM` / `_MCP_ALLOWED_HOSTS` | 同 `.env` | 必须显式注入以保证「公网鉴权 + 限流 + Host 白名单」不依赖 env_file 的解析顺序 |
| `UTF8SEARCH_DEFAULT_ENGINES` / `_NEWS_ENGINES` | 同 `.env` | 引擎列表是路由契约，显式注入避免 `env_file` 缺项时静默落回代码默认值（曾经踩过 `360search`） |
| `UTF8SEARCH_TRUST_ENV` | `false` | 容器应无视宿主机代理环境；`true` 会在未来有人给 `.env` 加代理时把流量导向不存在的代理 |
| `UTF8SEARCH_HTTP_PROXY` / `_BYPASS_PROXY_HOSTS` | 空 | 同上，显式清空 |

> 备选方案（更省事但不推荐）：只挂载 `./.env:/app/.env:ro` 并删掉所有 `environment` 里的引擎/鉴权项。
> 缺点：① 宿主机代理项会被容器读到（C 类问题仍在）；② `SEARXNG_URL` 会被 `.env` 的值覆盖（除非同时保留 environment 覆盖）；
> ③ 「容器读的是挂载文件」不如 `env_file` 直观（`docker inspect` 里看不到）。

## 4. 实施后的回归清单（全部在**容器路径**上跑）

| # | 项目 | 命令/口径 | 通过标准 |
| --- | --- | --- | --- |
| 1 | 配置生效核对 | `docker inspect` 的 `Config.Env` + `/health.active` | 引擎列表/时效窗口等与 `.env` 一致；`SEARXNG_URL=http://searxng:8080` |
| 2 | 全通道自检 | `scripts/mcp_selfcheck.py --base-url http://127.0.0.1:8000 --api-key "$KEY"` | **24/24** |
| 3 | 2-9 相关性 | `scripts/relevance.py --no-cache` + agent 初评（含校准集） | ≥18/20（并按敏感性披露严格判） |
| 4 | news 时效门槛 | `scripts/news_check.py --no-cache --time-range day` | ≥80%（当前基线 60%，见 §5） |
| 5 | 闸门行为 | 并发 10 / 并发 20 压测 + 429 形态 + `/metrics` 计数 | 并发 10 全成功；过载 429 带 `Retry-After`；`rejected_total{queue_full|timeout}` 正常增长；无 5xx |
| 6 | 鉴权与限流 | 无 Key/错 Key → 401；RPM=1 独立实例 → 第 2 次 429+`Retry-After` | 与现在一致（确认没被 `.env` 覆盖搞坏） |
| 7 | `/metrics` | 带 Key 200，含 `utf8search_upstream_*` 与 `utf8search_expansion_*` | 指标族齐全 |
| 8 | 6 小时短长稳 | `scripts/soak.py --duration-hours 6 --interval 300 --http-url … --unique` | 可用率 ≥99%、覆盖率 ≥95%、异常/疑似休眠 0、内存平稳 |
| 9 | 端口矩阵 | `docker ps` / `compose config` | app 仅 `127.0.0.1:8000`，对外仅 80/443 |

## 5. 「接线前测得的数字不作数」清单（下一轮对照基线）

接线前容器跑的是**代码默认值**（`default_engines` 还含 `360search`），所以：

| 数字 | 现在是多少 | 为什么不作数 | 接线后应对比的对象 |
| --- | --- | --- | --- |
| **容器路径**的 news 时效 | 未单独测（脚本路径 28% / google 恢复后 60%） | 容器此前甚至没读 `.env` 的新闻列表 | 脚本路径同一口径的 60%（google news 恢复后），要求 ≥80% |
| **容器路径**的 2-9 | 未单独测（脚本路径 16/20 = 80%） | 同上 | 脚本路径 16/20（并重跑一次容器路径的同批查询） |
| 引擎集合相关结论（哪条引擎贡献多少、`360search` 空转 ~1s） | 换引擎轮的 `sweep`/`compare` 数字 | 那些是 **SearXNG 直连**测量的，与容器配置无关，仍然有效；但容器路径过去 24h 的「现网行为」等于 13 引擎（含 360search），不能与接线后的 12 引擎直接比 | 接线后重跑 `scripts/engine_probe.py sweep` + 一次容器路径 2-9/news |
| 卫生度（覆盖率 0.735 / 独立站点 4.75 / 空内容 3） | 脚本路径 | 同上（脚本已读 `.env`，可作为对照；但容器路径要重测） | 同上 |
| `google news` 相关结论 | 本地冷却盒、重启即恢复；补测 60% | 结论本身有效（B 节已证明） | 接线后若再遇 CAPTCHA，先 `restart searxng` 再测 |

> 一句话：**脚本路径（读 `.env`）的数字可以当对照基线；容器路径的历史数字只代表「代码默认值配置」，不能当基线。**

## 6. 风险与回滚

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 一次性打开 ~64 项设置 | 时效窗口、日期回补、rank 过滤、闸门参数会首次真正生效，行为可能与过去 24h 不同 | 先 `docker compose config` 干跑核对注入值；再 `up -d --no-deps utf8-search`（只重建 app）；随后按 §4 逐项回归 |
| 代理项误注入 | 大陆开发机的 `HTTP_PROXY` 若被带进服务器容器，会让抓取全部走不存在的代理 | §3 的 C 类显式中性化三条 |
| `SEARXNG_URL` 被覆盖错 | 一旦丢了 environment 覆盖，容器会去连自己的 8888 | 该键保留在 environment，并在 §4-1 核对 |
| 鉴权/RPM 被 `.env` 覆盖搞坏 | `API_KEYS`/`MCP_ALLOWED_HOSTS` 若缺失，公网会裸奔或全部 421 | 保留显式注入 + §4-6 回归；`.env` 已备份 |
| 回滚 | —— | `cp /root/deploy-backups-20260929/env.20260930-pre-engine-list.bak .env`（如需）+ `git checkout <旧 commit> -- docker-compose.yml` + `docker compose up -d --no-deps utf8-search`；镜像侧 `utf8-search-utf8-search:pre-m5-20260929` 仍是回滚锚点（本轮不需重建镜像） |

**回滚演练步骤**（实施轮执行）：

```bash
cp docker-compose.yml /root/deploy-backups-20260929/compose-config-$(date +%Y%m%d).yml.bak   # 备份 compose
docker compose config | grep -A 12 'utf8-search:' | head -30                                  # 干跑核对
docker compose up -d --no-deps utf8-search && sleep 10 && curl -s http://127.0.0.1:8000/health
# 回滚：git checkout <旧 commit> -- docker-compose.yml && docker compose up -d --no-deps utf8-search
```

## 7. 非目标（本轮明确不做）

- 不改 `docker-compose.yml`、不改 `.env`（只出方案）；不改 `src/`；不动闸门参数与 `searxng/settings.yml`；不动人工项 3-9。

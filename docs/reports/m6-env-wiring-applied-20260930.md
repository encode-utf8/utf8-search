# 容器 env 接线实施（让 `.env` 真正对容器生效）（2026-09-30）

> 本轮改 `docker-compose.yml`（接线）+ 重建 app 容器；**未改 `src/`、未动闸门参数、未动 `settings.yml`、未碰人工项 3-9**。
> 方案依据：`docs/reports/m6-env-wiring-plan-20260930.md`（A/B/C 三分类）。
> 分支 `chore/env-wiring-20260930`（**未合并 main**）。

## 0. 摘要

| 项 | 之前 | 现在 |
| --- | --- | --- |
| 容器收到的配置 | 只有 4 个显式变量，其余全部回落 `config.py` **代码默认值** | `env_file: [.env]` 全量继承 **65 键**（`.env` 里的全部），另 12 键显式覆盖/中性化 |
| 通用引擎集合（容器实际使用） | 代码默认 13 个（**含已删除的 `360search`**，实测每次空转 ~1s） | `.env` 的 **12 个**（无 `360search`） |
| 新闻引擎集合 | 代码默认 3 个（含悬空 `sogou wechat`） | `.env` 的 4 个（`duckduckgo news,google news,chinaso news,tiger news`） |
| 代理设置 | 由代码默认 `trust_env=true` 决定（容器内无代理变量，等价） | **显式中性化**：`TRUST_ENV=false` + 两个代理键置空 |
| 端口矩阵 | app `127.0.0.1:8000`、searxng `127.0.0.1:8888`、对外仅 80/443 | **完全不变** |

**生效证明（不是只看配置文件）**：① 容器 `Config.Env` 与 `.env` **逐键对照 0 缺失**（53 键一致 + 12 键按预期覆盖/中性化）；
② 容器内 `Settings()` 打印确认关键字段；③ 四项行为验证（引擎列表 / 闸门 429 / 缓存落盘 / 鉴权与 RPM）全部通过；
④ `/metrics` 200 且 `requests_total{ok}`、`rejected_total{queue_full}` 正常推进。

**新基线（接通后）**：2-9 **17/20 = 85%（未达 90%）**、news 时效 **脚本路径 28% / 容器路径 32%（未达 80%）**、
卫生度覆盖率 0.708 / 独立站点 4.90 / 空内容 2；6h 短长稳**已启动**（结果待跑满）。旧数字与新数字并列见 §4。

## 1. A) 前置合并（均已推送）

| 合并提交 | 内容 | 合并后离线套件 |
| --- | --- | --- |
| `f62de2f` | `merge: 引擎列表落地（.env + compose 最小接线）+ 复验`（`chore/engine-list-env-20260930` b43994a） | 274 passed, 4 deselected |
| `3b7475d` | `merge: 容器 env 接线方案（70 键三分类）+ google news 诊断附录`（`docs/env-wiring-plan-20260930` 3596ffe） | 274 passed, 4 deselected |

`git push origin main` → `7437215..3b7475d`；本轮两条分支的 `diff --stat`：**17 files changed, 2831 insertions(+), 3 deletions(-)**。

## 2. B) 改动

### 2.1 `docker-compose.yml`（唯一的部署改动）

```diff
   utf8-search:
     ...
     ports:
       - "127.0.0.1:8000:8000"
+    env_file:
+      - .env
     environment:
       # B 类：容器内地址
       - UTF8SEARCH_SEARXNG_URL=http://searxng:8080
       # A 类中的服务身份 / 路由契约（显式注入，防 env_file 缺项回落默认值）
       - UTF8SEARCH_API_KEYS=${UTF8SEARCH_API_KEYS:-}
       - UTF8SEARCH_RATE_LIMIT_RPM=${UTF8SEARCH_RATE_LIMIT_RPM:-60}
       - UTF8SEARCH_MCP_ALLOWED_HOSTS=${UTF8SEARCH_MCP_ALLOWED_HOSTS:-}
       - UTF8SEARCH_DEFAULT_ENGINES=${UTF8SEARCH_DEFAULT_ENGINES:-…12 个…}
       - UTF8SEARCH_NEWS_ENGINES=${UTF8SEARCH_NEWS_ENGINES:-duckduckgo news,google news,chinaso news,tiger news}
       # C 类：宿主机专用键，容器内中性化
       - SEARXNG_SETTINGS_FILE=/etc/searxng/settings.yml
       - UTF8SEARCH_HOST=0.0.0.0
       - UTF8SEARCH_PORT=8000
       - UTF8SEARCH_TRUST_ENV=false
       - UTF8SEARCH_HTTP_PROXY=
       - UTF8SEARCH_BYPASS_PROXY_HOSTS=
```

`environment` 共 **12 条**（方案 §3 的 9 条清单 + 用户点名的另外 3 个 C 键 `SEARXNG_SETTINGS_FILE`/`HOST`/`PORT`）。
compose 里 `environment` 优先级高于 `env_file`，而环境变量又优先于 pydantic 的 `.env`，所以这 12 条不会被 `.env` 改写。

### 2.2 备份与回滚点（改前）

```
/root/deploy-backups-20260929/docker-compose.20260930-pre-env-wiring.yml    (md5 fe00e42ff2155afa35a74112ac1bee7e)
/root/deploy-backups-20260929/env.20260930-pre-env-wiring.bak              (md5 7d6a9f9bb337ca7f8672ebebd535e708)
/root/deploy-backups-20260929/app-container-before-env-wiring.json
/root/deploy-backups-20260929/app-images-before-env-wiring.txt              (latest=03bf40b20341；pre-m5-20260929=ba8912a353c6)
```

### 2.3 生效方式

```bash
docker compose config > docs/reports/env-wiring-compose-resolved-20260930.yml   # 干跑核对（Key 已脱敏）
docker compose up -d --no-deps utf8-search                                     # 只重建 app；searxng / caddy 未动
```

## 3. C) 生效证据

### 3.1 容器 env 与 `.env` 逐键对照

```
.env 键数（UTF8SEARCH_* + SEARXNG_SETTINGS_FILE）= 65
容器里同口径键数 = 65     缺失 = 0
[覆盖/中性化] 12 键（全部按预期）：
  UTF8SEARCH_SEARXNG_URL      .env=http://127.0.0.1:8888  容器=http://searxng:8080
  UTF8SEARCH_TRUST_ENV        .env=true                   容器=false
  UTF8SEARCH_BYPASS_PROXY_HOSTS .env=127.0.0.1,localhost,[::1],searxng  容器=（空）
  UTF8SEARCH_HTTP_PROXY       两者均为空
  SEARXNG_SETTINGS_FILE       .env=./searxng/settings.yml 容器=/etc/searxng/settings.yml
  UTF8SEARCH_HOST/PORT        0.0.0.0 / 8000（容器监听值，显式写死）
  UTF8SEARCH_API_KEYS / RATE_LIMIT_RPM / MCP_ALLOWED_HOSTS / DEFAULT_ENGINES / NEWS_ENGINES  与 .env 同值（显式注入）
其余继承键：完全一致 53 个，不一致 0 个
```

补充事实：`.env.example` 有 70 键，服务器 `.env` 只设置了 65 键 —— 未设置的 5 键是
`METRICS_ENABLED` 与闸门 4 项（`UPSTREAM_MAX_CONCURRENCY/QUEUE_LIMIT/MAX_WAIT/OPTIONAL_WAIT`），
它们走代码默认值（`metrics_enabled=True`、闸门 `3/12/4.0/1.0`），与预期一致，**闸门参数本轮未被改动**。

### 3.2 容器内 `Settings()` 实测（证明不是只改了 YAML）

```
searxng_url      = http://searxng:8080
metrics_enabled  = True
upstream gate    = 3 12 4.0 1.0
default_engines  = resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark
news_engines     = duckduckgo news,google news,chinaso news,tiger news
trust_env        = False | http_proxy= '' | bypass= ''
cache_path       = data/cache.db
news_fresh_days  = 7 | date_pages= 16 | date_budget= 4.0
rank             = 24 2 0.34
engine_health    = True 6 1800.0
block_private    = True | log_level= INFO
```

### 3.3 四项行为验证

| 项目 | 结果 |
| --- | --- |
| **① 生效的引擎列表** | `/health.engines.active` = 12 个通用引擎（**无 `360search`**）+ `duckduckgo news, google news, chinaso news, tiger news`；`cooling` 空 |
| **② 闸门（4 参数）** | 并发 18 / 36 请求 → **15 成功 + 21 个闸门 429**（0 个限流 429）；样本 `429 + Retry-After: 4`，文案「上游搜索过载（queue_full）」；`/metrics`：`rejected_total{queue_full}=21`、`requests_total{ok}=17` |
| **③ 缓存落在宿主机同一份 `data/`** | `docker inspect` 挂载 = `bind /root/utf8-search/data -> /app/data (rw)`；跑 1 次容器搜索后宿主机 `data/cache.db-wal` **mtime 前进、size 45352 → 94792**，容器内 `/app/data/cache.db-wal` 是**同一 inode/大小/时间**；`/health.cache_entries` 69 → 71 |
| **④ 鉴权与 RPM 未被破坏** | `POST /v1/search`、`POST /v1/extract`、`GET /metrics` 无 Key → **401**；错 Key → 401；对 Key → 200。RPM：连续 65 次 `/metrics` → **前 60 次 200，第 61 次起 429**，`Retry-After: 59`，body「请求过于频繁」⇒ 限流仍按 `RATE_LIMIT_RPM=60` 工作 |
| **⑤ `/metrics` 可达 + 计数推进** | 带 Key 200；`utf8search_upstream_requests_total{result="ok"}` 与 `rejected_total{queue_full}` 随上述压测推进；无 `result="error"` 序列 |

## 4. D) 新基线（接通后）与旧数字并列

| 指标 | 接线前（旧） | 接通后（新基线） | 说明 |
| --- | --- | --- | --- |
| **2-9 达标率** | 16/20 = 80%（脚本路径，09-30 11:0x） | **17/20 = 85%（未达 90%）**，平均 4.35；未达标 Q2(1/5)、Q6(2/5)、Q16(2/5) | 通用引擎集合从「13（含 360search）」变成「12」，且上游漂移大 |
| **news 时效门槛** | 脚本路径 28%（google news 在处罚盒）/ 60%（google news 健康时） | **脚本路径 11/40 = 28%**；**容器路径（部署服务实测）13/40 = 32%** | 两者都未达 80%；`google news` 本次测量时**又在 CAPTCHA** |
| **卫生度（只报数）** | 覆盖率 0.735 / 独立站点 4.75 / 空内容 3 | 覆盖率 **0.708** / 独立站点 **4.90** / 空内容 **2**（同站冗余/聚合页/脚本不匹配均 0） | 采样波动范围内 |
| **容器路径通用引擎集合** | 13 个（含 `360search`，代码默认） | **12 个（.env）** | 这是接线带来的**真实行为变化**：容器不再打 `360search`（实测每次空转 ~1s） |
| **6h 短长稳** | —— | **已启动**（见 §5），结果待跑满 | 打已部署服务、`--unique` 避开缓存 |

> 口径提醒：`relevance.py` / `news_check.py` 跑在宿主机进程内（读 `.env`），接线前后**配置相同**；
> 容器路径此前是「代码默认值配置」，所以**container 路径的历史数字不作数**（计划 §5）。
> 本次新增的「容器路径 32%」是第一个真正代表部署服务的时效数字。

## 5. 6 小时短长稳（已启动）

```bash
setsid nohup .venv/bin/python -X utf8 scripts/soak.py --duration-hours 6 --interval 300 --warmup 2 \
  --http-url http://127.0.0.1:8000 --api-key "$KEY" --rss-pid <app 容器主机 PID> --unique \
  --out data/soak-6h-envwiring.csv --json data/soak-6h-envwiring.json > data/soak-6h-envwiring.out.log 2>&1 &
```

- 启动 **2026-09-30 11:14:33**，PID **169593**（以 `data/soak-6h-envwiring.meta.json` 的 `pid` 为准），预计 **17:14** 结束。
- 启动后状态（11:20:36 读取）：`--status` **存活**，心跳 11:19:34（64s 前，在 3 个周期内）；
  已写 2 个采样（#1 11:14:34 OK 1053ms / #2 11:19:34 OK 1034ms，间隔 ~300s），
  结果均 5 条、**RSS 104.5 → 111.3MB**（新容器，内存从零重新计数；前 2 个为预热，不计入统计）。
- 跑满后用 `scripts/soak.py --summarize --out data/soak-6h-envwiring.csv --json data/soak-6h-envwiring.json`
  出可用率/覆盖率/内存结论（口径同 3-4）。

## 6. 回滚

```bash
# ① 回滚 compose（去掉 env_file 与 12 条 environment），再重建 app
cp /root/deploy-backups-20260929/docker-compose.20260930-pre-env-wiring.yml docker-compose.yml
docker compose up -d --no-deps utf8-search
docker inspect utf8-search-app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -c UTF8SEARCH   # 应回到 6 条

# ② 若同时需要回退 .env（引擎列表等）
cp /root/deploy-backups-20260929/env.20260930-pre-env-wiring.bak .env && docker compose up -d --no-deps utf8-search

# ③ 镜像级回滚锚点（本轮不需要重建镜像）
docker tag utf8-search-utf8-search:pre-m5-20260929 utf8-search-utf8-search:latest && docker compose up -d --no-deps --force-recreate utf8-search
```

回滚只影响 app 容器（~10 秒不可用）；searxng / caddy 不需要动。

## 7. 观察窗口

- **1 小时**：盯 `/health.engines.cooling`（是否长期新增）、`/metrics` 的 `upstream_requests_total{result="error"}`、
  Caddy 访问日志错误率；确认 12 引擎（去掉 360search）后通用查询延迟是否下降。
- **6 小时**：等 §5 的长稳跑满，用 `--summarize` 出结论。
- 注意：`.env` 现在真的生效了，**以后改 `.env` 必须 `docker compose up -d --no-deps utf8-search`**（env_file 变更需要 recreate，不是 restart）。

## 8. 遗留（写入 `docs/04` §8）

1. news 时效门槛仍未达标（脚本 28% / 容器 32%）：`google news` 反复进 CAPTCHA 且不给日期；
   **下一轮 ② 的方向**已备好原始数据（见附录）：`sina`+`time_range=day` 与 `bilibili`+`time_range=day`
   在 6 条中文查询上都给出**约 90 条带日期、7 日内**的结果（`chinaso news` 只有 2 条、`tiger news` 0 条）。
2. 兜底源（Bing）离题结果仍未修（本轮 2-9 的 Q2 又出现短剧站/动漫/AI 女友站，Q6 出现 Docker/公式页）。
3. 容器 env 已全量接线；**建议后续把 `METRICS_ENABLED` 与闸门 4 项也显式写进 `.env`**（现在靠代码默认值，值一致但不够显式）。

## 9. 证据文件

| 内容 | 路径 |
| --- | --- |
| compose 解析结果（Key 已脱敏） | `docs/reports/env-wiring-compose-resolved-20260930.yml` |
| 容器 env 与 `.env` 逐键对照（Key 已脱敏） | `docs/reports/env-wiring-env-compare-20260930.txt` |
| 容器内 `Settings()` 实测 | `docs/reports/env-wiring-container-settings-20260930.txt` |
| 闸门 429 受控观测（分类 + 指标增量 + 明细） | `docs/reports/env-wiring-gate-burst429-20260930.json` |
| news 门槛：脚本路径 / 容器路径 | `docs/reports/env-wiring-news-script-path-20260930.md`、`env-wiring-news-container-path-20260930.json` |
| 2-9：明细 / 速览 / 打分 / 判定 | `docs/reports/m2-9-env-wiring-20260930{,-brief,-scores,-scores-judge}.md/.csv` |
| 卫生度 JSON | `docs/reports/env-wiring-hygiene-20260930.json` |
| 中文源只读探测（给 ② 用） | `docs/reports/env-wiring-zh-source-probe-20260930.json` |
| 改前备份（仓库外） | `/root/deploy-backups-20260929/{docker-compose.20260930-pre-env-wiring.yml,env.20260930-pre-env-wiring.bak,app-container-before-env-wiring.json}` |
| 长稳产物（`data/` 不入库） | `data/soak-6h-envwiring.{csv,json,meta.json,out.log}` |

## 附录：中文新闻源只读探测（为下一轮 ② 备料，未改任何配置）

6 条中文查询 × 6 个候选源 ×（无 time_range / `time_range=day`）：

| 引擎 | time_range | 结果 | 带日期 | **7 日内** | 中位年龄 |
| --- | --- | --- | --- | --- | --- |
| `chinaso news` | 无 | 32 | 32 | **2** | ~70 天 |
| `chinaso news` | day | 0 | 0 | 0 | — |
| `tiger news` | 无 / day | 0 | 0 | 0 | — |
| **`sina`** | 无 | 260 | 11 | 11 | ~1 天 |
| **`sina`** | **day** | **143** | **90** | **90** | **0.6 天** |
| **`bilibili`** | 无 | 260 | 10 | 10 | ~1 天 |
| **`bilibili`** | **day** | **146** | **90** | **90** | **0.65 天** |
| `duckduckgo news` | 无 | 31 | 31 | 11 | ~171 天 |
| `duckduckgo news` | day | 0 | 0 | 0 | — |
| `google news` | 无 / day | 0 | 0 | 0 | （测量时在 CAPTCHA） |

**读法**：`sina` 在 `time_range=day` 下能给出大量**带日期且当天内**的中文结果（90/90），
是当前唯一「非视频站 + 支持 time_range + 带日期」的候选；`bilibili` 同样达标但是视频站（需 `rank_max_per_host` 限流）。
这正是下一轮 ② 可以直接验证的方向（把 `sina` 加进 `NEWS_ENGINES` 或 `news_general_engines` 后重跑门槛）。

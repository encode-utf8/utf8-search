# M5 上游并发闸门 + 过载快速返回 验收报告（2026-09-27）

- 分支：`feature/m5-concurrency-gate`（基于 `main` @ `5f16f28`）
- 背景：`docs/04` §4.4 实测——并发 1-3 时 P50 ≈ 1.3s，并发 10 冷查询劣化到 ~12s；直连 SearXNG 探测显示
  上游聚合吞吐仅 1.3-2.0 req/s，**瓶颈在上游聚合而非本服务**。目标改为「**宁可快速失败，不要一起慢**」。
- 前提：本报告的 loadtest 需要**真实上游 SearXNG**（`127.0.0.1:8888`）与回环访问，且必须在**沙箱外**执行
  （沙箱内 `aiosqlite` 线程被拦、回环不可达）。测试期间入口限流已关（`UTF8SEARCH_RATE_LIMIT_RPM=0`），
  以聚焦上游并发；两次运行相隔数分钟、上游引擎状态可能漂移，结论按同一时段背靠背对比。

## 1. 改动

| 文件 | 变更 |
| --- | --- |
| `src/utf8_search/core/upstream_gate.py` | 新增：有界队列 + 等待上限的上游并发闸门，`UpstreamOverloaded` 异常，最小 Prometheus 指标集 |
| `src/utf8_search/providers/searxng.py` | 闸门包住**整次 `search()`**（含内部重试），重试计入同一个槽位 |
| `src/utf8_search/core/pipeline.py` | 过载**不被 `except Exception` 吞掉**、**不降级到兜底源（Bing）**；已有结果时按 `degraded=True` 返回 |
| `src/utf8_search/server/http_api.py` | 过载 → **HTTP 429 + `Retry-After`**（向上取整）；新增 `GET /metrics`（沿用 REST 鉴权） |
| `src/utf8_search/server/mcp_server.py` | 过载 → `ToolError`（可读 `isError` 文本，不是空结果） |
| `src/utf8_search/models.py` | 响应新增 `degraded` / `degraded_reason` |
| `src/utf8_search/config.py`、`.env.example` | `UPSTREAM_MAX_CONCURRENCY=3` / `UPSTREAM_QUEUE_LIMIT=6` / `UPSTREAM_MAX_WAIT=2.5` / `METRICS_ENABLED=true` |
| `scripts/loadtest.py` | 新增 `--topic`（news 组需要） |

**未改**：搜索语义、融合、时效分层、引擎健康自适应逻辑。

## 2. 12s 的根因（经实测确认）

在**并发 30 冷查询**下用「闸门关」复现了 §4.4 的 12s 量级，并拿到了两处直接证据：

```
（general @30，闸门关）客户端延迟：P50 10675ms  P90 12158ms  P95 12268ms  max 12458ms
（§4.4 记录，2026-09-24）          P50 12138ms  P95 12838ms
```

```
# 服务日志（同一轮）：37 次「SearXNG 连接异常，0.4s 后重试一次」+ 30 次「Provider searxng 搜索失败」
# /metrics：upstream_requests_total{result="ok"} 32，{result="error"} 30   ← 近一半上游调用失败
```

**根因链**：上游被同时打爆 → 连接异常 / 瞬时错误（5xx）→ 本地 `_request()` 的**重试一次**再撞在
同一批被打爆的上游上 → 单次尝试上限 5.5s（`search_timeout_limit 2.5 + 3`）× 2 次 ≈ **11s**，
正是 10.7-12.5s 的来源。§4.4 的 12.1s/12.8s 与本次复现吻合。

**闸门消掉的就是这一段**：改动后同一场景**重试 0 次、上游 error 0**，超载部分改为 429 立即返回。

## 3. loadtest 对比（`scripts/loadtest.py`，冷查询，`RPM=0`）

### 3.1 主对比

| 组 | 闸门 | 成功 2xx | 429 | 5xx | 超时 | 墙钟 | 吞吐 | P50 | P90 | P95 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| general @10 | 关（基线） | 50/50 | 0 | 0 | 0 | 12.36s | 4.0 req/s | 2259ms | 2796ms | 2944ms | 3072ms |
| general @10 | **开 3/6/2.5s** | 9/50 | 41 | 0 | 0 | 3.27s | 15.3 req/s | 1843ms | 3259ms | 3259ms | 3259ms |
| news @10 | 关（基线） | 50/50 | 0 | 0 | 0 | 31.43s | 1.6 req/s | 5598ms | 8768ms | **9030ms** | **10088ms** |
| news @10 | **开** | 4/50 | 46 | 0 | 0 | 5.38s | 9.3 req/s | 4858ms | 5382ms | **5382ms** | **5382ms** |
| general @30 | 关（饱和复现） | 60/60 | 0 | 0 | 0 | 22.19s | 2.7 req/s | **10675ms** | 12158ms | **12268ms** | **12458ms** |
| general @30 | **开** | 9/60 | 51 | 0 | 0 | 2.84s | 21.1 req/s | 1695ms | 2831ms | **2831ms** | **2831ms** |

**要点**：

- 12s 级 P95 只在「上游被同时打爆」时出现；news @10（每请求 2 次上游调用，等效 20 并发）与 general @30
  都进入了该区间（9.0s / 12.3s）。**闸门开启后两者都被压到 5.4s / 2.8s**。
- general @10 今天上游状态较好，基线 P95 仅 2.9s，**闸门没有把成功请求的尾延迟再压低**（3.26s，含排队），
  它在这里的作用是**把过载流量换成快速 429**：同样 50 个请求，墙钟 12.36s → 3.27s。
- 所有场景 5xx = 0、超时 = 0：过载不再表现为「一起挂到超时」。

### 3.2 「成功数 vs P95」权衡表

| 组 | 闸门 | 成功数 | 成功率 | 成功 P95 | 被拒数 | 被拒时延 |
| --- | --- | --- | --- | --- | --- | --- |
| general @10 | 关 | 50 | 100% | 2944ms | 0 | — |
| general @10 | 开 | 9 | **18%** | **3259ms** | 41 | 立即（同轮墙钟 3.27s） |
| news @10 | 关 | 50 | 100% | 9030ms | 0 | — |
| news @10 | 开 | 4 | **8%** | **5382ms** | 46 | 立即 |
| general @30 | 关 | 60 | 100% | 12268ms | 0 | — |
| general @30 | 开 | 9 | **15%** | **2831ms** | 51 | 立即 |

**取舍很直白**：并发 10-30 的冷查询突发下，闸门把成功率从 100% 降到 8-18%，换来的是
尾延迟可控（2.8-5.4s，且不再有 12s 级）与 3-8 倍的墙钟吞吐（失败立即返回，释放客户端）。
这正是本轮目标「宁可快速失败，不要一起慢」的直接体现；单请求/低并发场景不受影响（见 3.3）。

### 3.3 单请求（并发 1）无回退

| 组 | 闸门 | 成功 | P50 | P90 | P95 | max |
| --- | --- | --- | --- | --- | --- | --- |
| general @1 | 关 | 10/10 | 892ms | 1315ms | 1380ms | 1380ms |
| general @1 | **开** | 10/10 | 746ms | 1228ms | 1407ms | 1407ms |

**P95 +2.0%、max +2.0%（阈值 5%）→ 单请求延迟无显著回退**；P50 反而更低（上游抖动）。

## 4. 上游侧与闸门指标（`GET /metrics`，改动后）

| 组 | upstream ok | upstream error | 被拒 queue_full | 被拒 timeout | 排队次数 | 平均排队 |
| --- | --- | --- | --- | --- | --- | --- |
| general @10 基线 | 52 | 0 | 0 | 0 | 0 | — |
| general @10 开 | 11 | 0 | 41 | 0 | 6 | 1.29s |
| news @10 基线 | 104 | 0 | 0 | 0 | 0 | — |
| news @10 开 | 12 | 0 | 89 | 3 | 5 | 0.85s |
| general @30 基线 | 32 | **30** | 0 | 0 | 0 | — |
| general @30 开 | 11 | **0** | 51 | 0 | 0 | — |

`upstream error` 从 30 降到 0 是闸门的核心价值：**上游不再被打爆**。

## 5. news 请求占两个槽位（对并发上限的影响，必须知道）

`topic=news` 会**并发**打两路上游（新闻主源 + 通用引擎补充）。因此：

- 客户端并发 10 的 news ≈ **20 个上游请求并发**，这也是 news @10 基线能复现 9-10s 的原因；
- 闸门 `limit=3` 时，一个 news 请求要占 **2 个槽位**，等效只允许 **1.5 个 news 请求**同时进行 ——
  news 的 429 比例因此显著高于 general（46/50 vs 41/50，且上游侧被拒 92 次 ≈ 2×）；
- **调参提示**：以 news 为主的负载若嫌拒绝太多，应优先调大 `UPSTREAM_QUEUE_LIMIT`（吸收突发）
  或按「闸门上限 ÷ 2」估算 news 的等效并发，而不是直接调大 `UPSTREAM_MAX_CONCURRENCY`（那会把上游重新打爆）。

## 6. 单测（离线，全绿）

`pytest -q -m "not net"` → **251 passed, 4 deselected**（本轮新增 16 条：闸门 13 + REST/metrics 3）。

- `tests/test_upstream_gate.py`：放行 / 排队后转交 / 队列满立即拒 / 排队超时拒 / `track()` 记录时长与结果 /
  配置解析（默认 3-6-2.5、`UTF8SEARCH_UPSTREAM_*` 覆盖、metrics 开关）/ limit=0 关闭闸门 / Prometheus 文本 /
  **过载不被吞成空结果** / **过载不降级到兜底源** / news 第二路被拒时 `degraded=True` / MCP `ToolError` 可读。
- `tests/test_api.py`：过载 → 429 + `Retry-After: 3`；`/metrics` 渲染；`METRICS_ENABLED=false` → 404。

## 7. 复现命令

```bash
# 起临时服务（沙箱外；RPM=0 关掉入口限流，聚焦上游并发）
UTF8SEARCH_API_KEYS=lt-key UTF8SEARCH_RATE_LIMIT_RPM=0 UTF8SEARCH_UPSTREAM_MAX_CONCURRENCY=3 \
  .venv/bin/python -m utf8_search serve --host 127.0.0.1 --port 8012 &

# 冷查询压测（general / news；基线把 UPSTREAM_MAX_CONCURRENCY 设为 0）
.venv/bin/python scripts/loadtest.py --url http://127.0.0.1:8012 --api-key lt-key \
  --concurrency 10 --n 50 --topic general --warmup 2 --json data/loadtest-general-gated.json

# 指标（沿用 REST 鉴权）
curl -sS -H 'X-API-Key: lt-key' http://127.0.0.1:8012/metrics
```

原始输出留档在 `data/loadtest-*.out.txt` 与 `data/loadtest-*.json`（`data/` 被 gitignore）。

## 8. 已知限制

- 闸门是**单进程**的：本项目 `serve` 单 worker，够用；多 worker 需按 worker 数分摊上限（`.env.example` 已写明）。
- 高并发下成功率下降是**设计取舍**（见 3.2），不是缺陷；如需更高成功率，应调大队列而不是解除闸门。
- 本轮上游状态好于 2026-09-24（general @10 基线仅 2.9s），对比结论以**同一时段背靠背**的 news/general@30 为准。

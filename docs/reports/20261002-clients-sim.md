# 各客户端仿真联调报告

- 生成时间：2026-10-02 16:37:32 +0800
- 目标服务：`http://127.0.0.1:8000`（MCP `/mcp` + REST `/v1/search`、`/v1/extract`）
- 查询：`2026年 新能源汽车 补贴政策`，max_results=3；`--unique`：每个客户端尾部空格不同，均为冷查询
- 共执行 45 项检查：通过 45，失败 0

## 1. 逐客户端结果

### Claude Desktop

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → command | PASS | 0.00s | /root/utf8-search/.venv/bin/utf8-search |
| initialize | PASS | 2.82s | utf8-search 0.1.0 |
| tools/list | PASS | 0.01s | 工具 web_search,web_fetch |
| call web_search | PASS | 2.50s | （冷查询）3 条结果（1.912s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[resulthunter] 补贴新政来了，26年新能源车有救了？ - OFweek新 |

### Cursor (stdio)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → command | PASS | 0.00s | /root/utf8-search/.venv/bin/utf8-search |
| initialize | PASS | 2.77s | utf8-search 0.1.0 |
| tools/list | PASS | 0.01s | 工具 web_search,web_fetch |
| call web_search | PASS | 2.66s | （冷查询）3 条结果（2.554s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] qdzb07b20260116C |

### Codex

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → command | PASS | 0.00s | /root/utf8-search/.venv/bin/utf8-search（docs 模板，解析器 tomli） |
| initialize | PASS | 2.82s | utf8-search 0.1.0 |
| tools/list | PASS | 0.01s | 工具 web_search,web_fetch |
| call web_search | PASS | 0.76s | （冷查询）3 条结果（0.658s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] qdzb07b20260116C |

### Codex（真实配置）

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → command | PASS | 0.00s | /root/utf8-search/.venv/bin/utf8-search（/root/.codex/config.toml，解析器 tomli） |
| initialize | PASS | 2.78s | utf8-search 0.1.0 |
| tools/list | PASS | 0.01s | 工具 web_search,web_fetch |
| call web_search | PASS | 1.69s | （冷查询）3 条结果（1.582s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[resulthunter] 补贴新政来了，26年新能源车有救了？ - OFweek新 |

### Cherry Studio (stdio)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → command | PASS | 0.00s | /root/utf8-search/.venv/bin/utf8-search |
| initialize | PASS | 3.03s | utf8-search 0.1.0 |
| tools/list | PASS | 0.01s | 工具 web_search,web_fetch |
| call web_search | PASS | 2.37s | （冷查询）3 条结果（2.257s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 2026年新能源汽车补贴最新消息：地方购新补贴全面铺开 ；[resulthunter] 补贴新政来了，26年新能源车有救了？ - OFweek新 |

### Cursor (HTTP)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → url+headers | PASS | 0.00s | http://127.0.0.1:8000/mcp｜X-API-Key |
| initialize | PASS | 0.02s | utf8-search |
| tools/list | PASS | 0.04s | 工具 web_search,web_fetch |
| call web_search | PASS | 0.74s | （冷查询）3 条结果（0.715s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] 2026年4月汽车国补置换2万元申请全攻略：手把手教你领 |

### Cherry Studio (HTTP)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → url+headers | PASS | 0.00s | http://127.0.0.1:8000/mcp｜X-API-Key |
| initialize | PASS | 0.02s | utf8-search |
| tools/list | PASS | 0.04s | 工具 web_search,web_fetch |
| call web_search | PASS | 0.64s | （冷查询）3 条结果（0.619s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] 2026年4月汽车国补置换2万元申请全攻略：手把手教你领 |

### 自研 Agent (MCP)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → url+headers | PASS | 0.00s | http://127.0.0.1:8000/mcp｜X-API-Key（等价 MCP SDK / 自研客户端） |
| initialize | PASS | 0.02s | utf8-search |
| tools/list | PASS | 0.04s | 工具 web_search,web_fetch |
| call web_search | PASS | 0.62s | （冷查询）3 条结果（0.6s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] qdzb07b20260116C |

### Dify

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → 请求方式 | PASS | 0.00s | POST http://127.0.0.1:8000/v1/search｜bearer |
| 无 Key 应 401 | PASS | 0.01s | HTTP 401 |
| call /v1/search | PASS | 0.61s | （冷查询）3 条结果（0.598s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] qdzb07b20260116C |

### n8n

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → 请求方式 | PASS | 0.00s | POST http://127.0.0.1:8000/v1/search｜x-api-key |
| 无 Key 应 401 | PASS | 0.01s | HTTP 401 |
| call /v1/search | PASS | 0.60s | （冷查询）3 条结果（0.586s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] 2026年陵水新能源汽车购车补贴金额及档次标准- 海口本 |

### 自研 Agent (REST)

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → 请求方式 | PASS | 0.00s | POST http://127.0.0.1:8000/v1/search｜body api_key（api_key 放在请求体里（Tavily 兼容写法）） |
| 无 Key 应 401 | PASS | 0.01s | HTTP 401 |
| call /v1/search | PASS | 0.61s | （冷查询）3 条结果（0.6s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] qdzb07b20260116C |

### 已有 Tavily 代码

| 步骤 | 结果 | 耗时 | 细节 |
| --- | --- | --- | --- |
| 配置解析 → 请求方式 | PASS | 0.00s | POST http://127.0.0.1:8000/v1/search｜bearer（Tavily 字段断言 + /v1/extract） |
| 无 Key 应 401 | PASS | 0.01s | HTTP 401 |
| call /v1/search | PASS | 0.61s | （冷查询）3 条结果（0.598s）[yandex] 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1；[yandex] 别光顾着过年，快来买车 625亿元“国补”已经发放 - ；[yandex] 2026年陵水新能源汽车购车补贴金额及档次标准- 海口本 |
| call /v1/extract | PASS | 0.02s | 1 条，首条正文 156 字符 |

## 2. 结论

**全部通过**（`SKIP` 表示该项按条件跳过，不计入失败）。

## 3. 覆盖与边界

- 覆盖 docs/03 §2 表格里的每一行客户端：stdio 走 MCP SDK 起子进程，HTTP 走 Streamable HTTP 客户端，
  REST 走原生 HTTP（与 Dify / n8n / 自研 Agent 的实际调用方式一致）。
- **不覆盖**：客户端界面里「把配置粘进去 / 点保存」这个动作本身（无法自动化）；
  但配置文本与连接方式已在上面逐项验证，粘贴只剩机械操作。
- `/mcp` 的鉴权只认 `Authorization` 或 `X-API-Key` 头（服务端 `mcp_auth_middleware`），
  **不支持 URL 里带 Key**：HTTP 传输的客户端必须能自定义请求头。

## 4. 复现命令

```bash
.venv/bin/python scripts/clients_sim.py --base-url http://127.0.0.1:8000 --api-key <Key> --unique --out <报告路径>
```

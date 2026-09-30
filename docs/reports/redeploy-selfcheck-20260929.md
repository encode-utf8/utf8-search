# M4-4.3 客户端联调自检报告

- 生成时间：2026-09-29 19:40:17 +0800
- 运行环境：Python 3.10.12 / Linux-5.15.0-191-generic-x86_64-with-glibc2.35
- 仓库：`/root/utf8-search`
- 覆盖通道：stdio, stdio-raw, http-mcp, rest, ratelimit
- 服务实例：http://127.0.0.1:8000（复用外部实例）；http://127.0.0.1:41011（临时实例，API Key=utf8…IEEA，RPM=1）
- 查询：`2026年 新能源汽车 补贴政策`；新闻查询：`最近一周 AI 行业动态`；抽取 URL：`https://example.com`
- 结论：**全部通过**（执行 24 项，跳过 0 项）

## 1. 汇总

| 通道 | 执行 | 通过 | 失败 | 跳过 | 耗时合计 |
| --- | --- | --- | --- | --- | --- |
| stdio | 5 | 5 | 0 | 0 | 8.7s |
| stdio-raw | 1 | 1 | 0 | 0 | 4.1s |
| http-mcp | 6 | 6 | 0 | 0 | 0.2s |
| rest | 10 | 10 | 0 | 0 | 8.7s |
| ratelimit | 2 | 2 | 0 | 0 | 0.0s |

## 2. 明细

| # | 通道 | 检查项 | 结果 | 耗时 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 1 | stdio | initialize | 通过 | 2.97s | utf8-search 0.1.0，协议 2025-11-25 |
| 2 | stdio | tools/list | 通过 | 0.01s | 工具 web_fetch,web_search（参数/必填/枚举均符合契约） |
| 3 | stdio | call web_search(basic) | 通过 | 2.97s | 5 条结果（1 条带日期），首条 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ |
| 4 | stdio | call web_search(news) | 通过 | 2.06s | 5 条结果（3 条带日期），首条 传媒行业动态跟踪：海外AI瓶颈之一：存储_行业研究_ |
| 5 | stdio | call web_fetch | 通过 | 0.68s | https://example.com 抽取 156 字符 |
| 6 | stdio-raw | handshake | 通过 | 4.10s | stdout 2 行全为合法 JSON-RPC，工具 ['web_fetch', 'web_search'] |
| 7 | http-mcp | 无 Key 应 401 | 通过 | 0.01s | HTTP 401（期望 401）{"detail":"无效的 API Key：请在 Authorization: Bearer <key>、X-API-Key 或请求体 api_key 中提供。","error":"无效的 API  |
| 8 | http-mcp | 错误 Key 应 401 | 通过 | 0.01s | HTTP 401（期望 401）{"detail":"无效的 API Key：请在 Authorization: Bearer <key>、X-API-Key 或请求体 api_key 中提供。","error":"无效的 API  |
| 9 | http-mcp | 伪造 Host 应 421 | 通过 | 0.01s | HTTP 421（期望 421）Invalid Host header |
| 10 | http-mcp | initialize | 通过 | 0.02s | utf8-search，协议 2025-11-25 |
| 11 | http-mcp | tools/list | 通过 | 0.06s | 工具 web_fetch,web_search（参数/必填/枚举均符合契约） |
| 12 | http-mcp | call web_search | 通过 | 0.05s | 3 条结果（0 条带日期），首条 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ |
| 13 | rest | GET /health | 通过 | 0.02s | HTTP 200，status=ok，SearXNG=ok，鉴权=开 |
| 14 | rest | POST /v1/search（X-API-Key） | 通过 | 0.01s | 3 条结果（0 条带日期），首条 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ |
| 15 | rest | POST /v1/search（Bearer） | 通过 | 0.01s | 3 条结果（0 条带日期），首条 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ |
| 16 | rest | POST /search（body.api_key） | 通过 | 0.01s | 3 条结果（0 条带日期），首条 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ |
| 17 | rest | 无 Key 应 401 | 通过 | 0.01s | HTTP 401 |
| 18 | rest | 错误 Key 应 401 | 通过 | 0.01s | HTTP 401 |
| 19 | rest | days=1 → time_range=day | 通过 | 4.28s | 带日期 3 条中 3 条落在 7 天窗口内（覆盖率 100%，门槛 80%）；最旧 3.5 天（仅诊断，不参与判定） |
| 20 | rest | include_domains 生效 | 通过 | 0.03s | 白名单 post.smzdm.com：1 条结果全部命中 |
| 21 | rest | POST /v1/extract | 通过 | 0.04s | HTTP 200，https://example.com → 156 字符 |
| 22 | rest | advanced + include_raw_content | 通过 | 4.31s | HTTP 200，读取 3 页，3/3 条附带正文 |
| 23 | ratelimit | 第 1 次请求放行 | 通过 | 0.01s | HTTP 200 |
| 24 | ratelimit | 第 2 次请求被限流 | 通过 | 0.02s | HTTP 429，Retry-After=60 |

## 3. 失败详情

无。

## 4. 人工联调清单（待回填）

自动化只能覆盖协议、参数、鉴权、限流；**各客户端自身的配置界面与文件名**必须在客户端里点一次。
步骤见 `docs/03-客户端接入指南.md`；跑通后在「跑通」列填 ✅，失败写进备注并回修文档或代码。

| 客户端 | 接入方式 | 跑通 | 备注 |
| --- | --- | --- | --- |
| Claude Desktop | MCP stdio（claude_desktop_config.json） | ☐ | |
| Codex | MCP stdio（config.toml）；新版可用 Streamable HTTP | ☐ | |
| Cursor | MCP stdio 或 Streamable HTTP（/mcp） | ☐ | |
| Cherry Studio | MCP stdio 或 Streamable HTTP（/mcp） | ☐ | |
| Dify | Tavily 兼容 REST（自定义工具 / OpenAPI） | ☐ | |
| n8n | Tavily 兼容 REST（HTTP Request 节点） | ☐ | |
| 自研 Agent | MCP stdio / Streamable HTTP / REST 任选 | ☐ | |

## 5. 复现命令

```bash
.venv/bin/python -u scripts/mcp_selfcheck.py --mode all --out /root/deploy-backups-20260929/selfcheck-after.md
# 复用已启动的服务（跳过临时实例）：
.venv/bin/python -u scripts/mcp_selfcheck.py --mode rest,http --base-url http://127.0.0.1:8000 --api-key <你的 Key>
```

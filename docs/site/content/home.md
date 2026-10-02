# 快速开始

这里是 **utf8-search 使用说明站**：把仓库里的接入指南、客户端配置包、部署手册整理成按场景查找的页面。
站点是纯前端静态页，随项目一起部署、随 `docker compose up -d` 启动，不依赖任何外部 CDN 或后端服务。

## 这是什么

utf8-search 是一个**免费、高速的联网搜索服务**：对 LLM 客户端提供 MCP（stdio / Streamable HTTP）与
Tavily 兼容的 REST 接口，底层聚合 SearXNG 的免费搜索引擎，不要求任何付费 Key。

## 30 秒发起一次搜索

```bash
# 本机部署（默认只绑回环）
curl -s http://127.0.0.1:8000/v1/search \
  -H "Authorization: Bearer $UTF8SEARCH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python 3.13 新特性", "max_results": 5, "search_depth": "basic"}'
```

```python
# 已有 Tavily 代码：只换 base_url 与 key
from tavily import TavilyClient

client = TavilyClient(api_key="<你的 Key>", api_base="http://127.0.0.1:8000")
results = client.search("Python 3.13 新特性", max_results=5)
```

## 三种 Key 传法

1. `Authorization: Bearer <Key>`（推荐，MCP 与 REST 通用）；
2. `X-API-Key: <Key>`（自定义头）；
3. 请求体字段 `"api_key": "<Key>"`（仅 REST `/v1/search`、`/search` 支持；MCP 不适用）。

> 不知道 Key 从哪来、怎么确认 Key 有效？见「服务测试台」页的
> [API Key 是什么](#page-tester--api-key)——含来源说明与一键「验证 Key」。

> 公网访问还必须带**白名单内的 Host**（例如 `your-domain.example`，写成你实际部署的域名），否则会被 DNS 重绑定防护拒绝（421）。

## 按场景查找

| 我要… | 去哪里 |
| --- | --- |
| 把服务接进 AI 客户端 | 「客户端接入指南」——MCP / REST 原理、鉴权、限流、常见问题 |
| 复制某个客户端的配置 | 「客户端配置包」——Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent |
| 自己部署一套 | 「自部署与运维」——架构端口、首次部署、证书续期、备份恢复 |
| 排查 401 / 421 / 429 | 顶部搜索框直接搜 `429`、`421`、`401`，或看「客户端配置包」的故障对照表 |
| 看不懂返回的 `degraded` | 搜 `degraded` / `freshness_unverified` / `no_relevant_results` |

## 服务地址

| 场景 | 地址 |
| --- | --- |
| 本机默认 | `http://127.0.0.1:8000`（REST）；`http://127.0.0.1:8000/mcp`（Streamable HTTP） |
| 公网（你自己的部署） | `https://<你的域名>`（需要 Key + Host 白名单） |
| 自托管控制台（本页） | 随项目 `docs` 服务启动：本机 `http://localhost:8080/`；用自带 Caddy 部署时为 `https://<你的域名>/guide/` |

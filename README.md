# utf8-search

面向 LLM 的**免费、高速**联网搜索服务（MCP Server + REST API），目标是在不购买任何商业搜索 API 的前提下，达到接近 Tavily 的使用效果。

## 核心思路

- **搜索聚合**：自建 SearXNG 聚合 **13 个免费引擎**（`resulthunter` / `google` / `yandex` / `naver` / `privacywall` / `zapmeta` / `yahoo` / `fynd` / `sogou` + 机会型 `reloado` / `yep` / `brave` / `quark`），单次查询可拿 80+ 条原始结果，完全免费、可自托管
- **兜底源**：SearXNG 返回 0 条时自动切换 Bing HTML 直取 Provider
- **正文抽取**：本地并发抓取 + trafilatura 正文提取，失败时降级到 Jina Reader
- **融合重排**：RRF 多路融合 + URL 归一化去重 + BM25 重排 + 中文二元组分词
- **速度优化**：连接池、单页硬超时与提前返回、解析线程池调优（GIL 限制）、三级缓存
- **双协议接入**：MCP（stdio / Streamable HTTP）与 REST，兼容 Claude Desktop、Codex、Cursor、Cherry Studio、Dify、n8n 及自研 Agent
- **鉴权与限流**：API Key（Bearer / X-API-Key / body）+ 按 Key 滑动窗口限流

## 快速开始

```powershell
# 1) 起 SearXNG（首次查询需 20–60 秒加载引擎）
docker compose up -d searxng

# 2) 安装依赖
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 3A) 以 stdio 方式跑 MCP（给桌面客户端用）
utf8-search

# 3B) 或起 HTTP 服务（REST + MCP over HTTP）
$env:UTF8SEARCH_API_KEYS="test123"
utf8-search serve --host 0.0.0.0 --port 8000
```

验证：

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/v1/search -H "Content-Type: application/json" `
  -H "X-API-Key: test123" --data-binary '{"query":"2026年 人工智能 政策","search_depth":"deep"}'
```

## 实测性能（冷启动，美国出口 IP）

| 模式 | P50 | P95 | 平均读页 |
| --- | --- | --- | --- |
| basic | 1048 ms | 1095 ms | 0 |
| advanced | 3775 ms | 3914 ms | 3.0 |
| deep | 9234 ms | 9492 ms | 16.2（14–19 页） |

基准脚本：`.\.venv\Scripts\python.exe scripts\bench.py --n 5 --fresh`

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not net"   # 34 项离线测试
.\.venv\Scripts\python.exe -m pytest -q -m net         # 4 项联网冒烟测试（需 SearXNG + 可出网）
```

## 文档

- `docs/01-前期调研与可行性分析.md`：同类产品调研、免费搜索源与引擎级实测、性能瓶颈分析、实测延迟
- `docs/02-技术方案与开发计划.md`：分层架构、MCP 接口设计、速度策略、里程碑与验收指标
- `docs/03-客户端接入指南.md`：Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent 接入示例
- `checklist.md`：各阶段可勾选的验收清单与实测记录

## 当前状态

**M1 / M2 已完成并通过实测验收**，M3 主体完成（10 并发压测与 24 h 长稳待补）。已知限制：免费搜索引擎会被上游限流，需配合缓存与兜底源使用。
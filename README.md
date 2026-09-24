# utf8-search

面向 LLM 的**免费、高速**联网搜索服务（MCP Server + REST API），目标是在不购买任何商业搜索 API 的前提下，达到接近 Tavily 的使用效果。

## 核心思路

- **搜索聚合**：自建 SearXNG 聚合 **12 个免费通用引擎**（`resulthunter` / `google` / `yandex` / `naver` / `privacywall` / `zapmeta` / `yahoo` / `fynd` + 机会型 `reloado` / `yep` / `brave` / `quark`），单次查询可拿 80+ 条原始结果，完全免费、可自托管
- **新闻时效性**：`topic=news` 走 3 个免费新闻源（`duckduckgo news` / `sogou wechat` / `google news`），并用通用引擎的 `time_range` 过滤补最新候选；发布日期缺失时先读 URL 内嵌日期、再抓页面用 `htmldate` 回补
- **引擎健康度自适应**：把每个引擎的失败按原因分级冷却（CAPTCHA 30 分钟 / 拒绝访问 15 分钟 /
  限流 3 分钟 / 超时 90 秒），连续失败指数退避、到期自动恢复；被挂掉的引擎不再进入查询，
  实测同一批查询的上游「不可用引擎」报告次数从 142 降到 0，而结果条数不变。
  快照见 `GET /health` 的 `engines` 字段（`engine_health_enabled=false` 可完全关闭）
- **兜底源**：SearXNG 返回 0 条时自动切换 Bing HTML 直取 Provider
- **正文抽取**：本地并发抓取 + trafilatura 正文提取，失败时降级到 Jina Reader
- **融合重排**：RRF 多路融合 + URL 归一化去重 + BM25 重排 + 中文二元组分词 + 低质结果过滤（无标题 / 裸域名标题）
- **时效性处理**：新闻结果按「新鲜 > 过期 > 无日期」分层稳定排序，剔除已知过期结果（2-9 抽检暴露的「台风查询返回 2021 年旧闻」问题已知修复）
- **`time_range` / `days` 是「强偏好」而不是硬过滤**：`topic=news` 下丢弃阈值取
  `max(time_range 对应天数, news_fresh_days)`（默认 7 天）。原因是免费源给不出足够的当天结果，
  若拿 1 天当硬阈值会把 2-7 天的近期新闻丢掉、再用「无日期」结果补位（实测反而更差）。
  实际新鲜度请以每条结果的 `published_date` 为准，不要假定 `time_range=day` 就一定是当天内容。
- **速度优化**：连接池、单页硬超时与提前返回、解析线程池调优（GIL 限制）、三级缓存
- **双协议接入**：MCP（stdio / Streamable HTTP）与 REST，兼容 Claude Desktop、Codex、Cursor、Cherry Studio、Dify、n8n 及自研 Agent
- **鉴权与限流**：API Key（Bearer / X-API-Key / body）+ 按 Key 滑动窗口限流
- **SSRF 防护**：抓取前校验协议与目标地址，拒绝内网 / 保留网段 / 云元数据（逐跳复检重定向，防 302 绕过）

## 快速开始

```powershell
# 1) 起 SearXNG（首次查询需 20–60 秒加载引擎）
docker compose up -d searxng

# ⚠ 中国大陆网络：google.com / duckduckgo.com 直连不可达（ConnectTimeout），
# SearXNG 出口不读 HTTP_PROXY 环境变量，必须切到带代理的配置：
#   在 .env 里写 SEARXNG_SETTINGS_FILE=./searxng/settings.local.yml 后重新 up -d searxng
# 海外服务器直连可达，用默认 settings.yml 即可。

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
| basic（`topic=news`，`time_range=day`） | 1060–1270 ms | — | 0 |

基准脚本：`.\.venv\Scripts\python.exe scripts\bench.py --n 5 --fresh`

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not net"   # 177 项离线测试
.\.venv\Scripts\python.exe -m pytest -q -m net         # 4 项联网冒烟测试（需 SearXNG + 可出网）
```

## 验收脚本

```powershell
# 并发压测（先起服务；压测期间建议 UTF8SEARCH_RATE_LIMIT_RPM=0 关闭限流）
.\.venv\Scripts\python.exe scripts\loadtest.py --concurrency 10 --n 50 --api-key test123

# 24h 长稳（定时查询，逐行记录成功率与 RSS）
.\.venv\Scripts\python.exe scripts\soak.py --duration-hours 24 --interval 300

# 相关性抽检（生成 20 条中英查询的 top5 明细与打分模板，填好后用 --score-file 判定）
.\.venv\Scripts\python.exe scripts\relevance.py --depth basic

# 引擎健康度自适应 A/B 基准（对比静态名单与自适应：覆盖率 / 延迟 / 上游异常次数）
.\.venv\Scripts\python.exe scripts\bench_engines.py --rounds 3 --out data\bench-engines.md

# 时效性验收（topic=news + time_range=day，输出逐条时效统计与 Markdown 报告）
.\.venv\Scripts\python.exe scripts\news_check.py --time-range day --max-results 5 --no-cache --out data\news-check.md
```

实测结论（2026-09-24，详见 `checklist.md` 第 9 节）：

- 并发压测 10 并发 × 50 请求：**无 5xx、无超时**；但冷查询 P50 约 12 s，瓶颈在上游 SearXNG 聚合能力（约 1.3-2.0 req/s），建议并发 ≤ 3。
- 相关性抽检 20 条：达标 15/20（75%），平均相关 4.25 条；短板在中文商品类与强时效类，已转入 M5 优化。
- 时效性验收（2026-09-24，详见 `checklist.md` 第 10 节）：8 条中英新闻查询在 `topic=news` +
  `time_range=day` 下连续 4 轮 **95–100% 带 7 日内日期**（门槛 ≥ 80%），端到端 1.06–1.27s。

## 文档

- `docs/01-前期调研与可行性分析.md`：同类产品调研、免费搜索源与引擎级实测、性能瓶颈分析、实测延迟
- `docs/02-技术方案与开发计划.md`：分层架构、MCP 接口设计、速度策略、里程碑与验收指标
- `docs/03-客户端接入指南.md`：Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent 接入示例
- `docs/04-后续路线图.md`：M4 上线就绪（SSRF 防护 / 云部署 / 客户端联调）、M5 质量与时效、M6 能力扩展
- `checklist.md`：各阶段可勾选的验收清单与实测记录

## 当前状态

**M1 / M2 已完成并通过实测验收**，M3 主体完成（10 并发压测通过、24 h 长稳待补）；
M4-4.1 SSRF 防护、M5-5.2 时效性增强已完成。下一步：M5-5.1 引擎健康度自适应、M4-4.3 真实客户端联调。

已知限制：免费搜索引擎会被上游限流，需配合缓存与兜底源使用；中文商品类查询的相关性（2-9 抽检 5 条未达标）仍待 5.3 处理；
中国大陆网络下 SearXNG 需走 `searxng/settings.local.yml` 的代理配置才能访问 Google / DuckDuckGo。
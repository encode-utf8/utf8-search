# news 时效：日期可信度分组、门槛新口径、时效降级信号（2026-09-30）

> 分支 `fix/news-date-trust-20260930`（**未合并 main**）。改动：`src/`（可信日期白名单 + 降级信号）、
> `scripts/engine_probe.py dates`（日期可信度抽检）、`scripts/searxng_dates.py`（纯函数）、单测、文档。
> **未改闸门参数、未改 `searxng/settings.yml`、未做 Bing 兜底相关性闸门与型号 token 匹配、未碰人工项 3-9。**
> 已重建并上线 app（降级信号生效）。

## 0. 摘要

| 项 | 结果 |
| --- | --- |
| 可信日期源分组（B1/B2） | 新增抽检工具与判据：**可信 = `duckduckgo news` / `chinaso news`**；**仅索引日期 = `yandex`**；其余（naver/yahoo/fynd/resulthunter/google news/tiger news 等）**无日期** |
| 门槛新口径（B3） | **英文组 ≥80% 保持，实测 87-100% 达标**；**中文组不再作为待达标项**，改写为「已知限制 + 降级信号」，附失败清单（§3） |
| 时效降级信号（B4） | 新增 `degraded=true` + `degraded_reason="freshness_unverified"`（仅我们的扩展字段）；**REST 与 MCP 同一套字段**，已有 6 条单测；**线上已验证** |
| 复测操作规范（B5） | 「容器路径复测必须绕缓存（`CACHE_QUERY_TTL=600`）」写入复测操作单与本文；此前基于缓存快照的容器数字**标注为无效** |
| 中文新鲜源评估（C） | 已在 `docs/04` 立项（本轮不实现） |
| 部署 | 新镜像 `0aeea61b027f`；回滚锚点 `pre-datetrust-20260930` = `c2205226f7fc` |

## 1. A) 收尾与合并

- **A2 已完成**：`e2fc922 merge: news 时效收口（新鲜度判据 + Bing 让位 + 撤 sina + 探测加固）`，
  `push be82c74..e2fc922`；合并后 main 复跑 **291 passed / 4 deselected**；
  `diff --stat be82c74..main` = **11 files changed, 633 insertions(+), 60 deletions(-)**。
- **A1（两个 6h 长稳）都还在跑**（本轮开工 12:41 时：跨镜像那个 18 个采样、干净那个 8 个采样，心跳均正常）：

| 长稳 | 起点 / 预计 | 性质 | 回填口径 |
| --- | --- | --- | --- |
| `data/soak-6h-envwiring.csv` | 11:14:33 / 17:14 | **跨镜像**（12:00 重建），且重建后 **RSS 记 n/a**（采样的 PID 已消失） | **只报可用率**；内存只有重建前 10 个采样（104.5 → 111.3MB），**不可与其它轮次比较** |
| `data/soak-6h-freshness.csv` | 12:05:13 / 18:05 | 干净（单镜像、单 PID） | **报完整结论**（可用率 + 覆盖率 + 内存 + 异常/休眠） |

  期间 `/metrics` 只有 `requests_total{result="ok"}`，**没有任何 `rejected_total` 序列** ⇒ 长稳无 429。

## 2. B1 + B2) 日期可信度：分组与抽检工具

### 2.1 判据（可自动化，纯函数）

`scripts/searxng_dates.py`：

* `year_clues()`：从标题 / 摘要 / URL 抽 4 位年份；
* `classify_date_trust()`：按「**内容年份比上报年份旧**」的比例 + 「**同日扎堆**」给引擎定性：
  - **可信**：≥5 条带日期、年份冲突 ≤20%、无同日扎堆（≥5 条同一天）；
  - **仅索引日期**：年份冲突 ≥50% **或**同日扎堆；
  - **无日期**：带日期样本 <5；
  - 介于两者之间 → 待人工确认。

命令行：`scripts/engine_probe.py dates <base> --engines <…>`（发查询前仍会先做**引擎注册校验**）。

### 2.2 实测分组（现网出口，2026-09-30）

| 引擎 | 样本 | 带日期 | 年份冲突 | 同日最多 | 判定 |
| --- | --- | --- | --- | --- | --- |
| `duckduckgo news` | 14 | 14 | 1（7%） | 2 | **可信** |
| `chinaso news` | 10 | 10 | 0 | 2 | **可信** |
| **`yandex`（`time_range=day`）** | 15 | **15** | 2（13%） | **13** | **仅索引日期** ⚠️ |
| `naver` | 75 | **0** | — | — | 无日期 |
| `yahoo` | 41 | **0** | — | — | 无日期 |
| `fynd` | 35 | **0** | — | — | 无日期 |
| `resulthunter` | 117 | **0** | — | — | 无日期 |
| `tiger news` / `google news` / `google` / `zapmeta` / `reloado` / `quark` / `brave` / `yep` / `privacywall` | 0-2 | 0 | — | — | 无日期（本轮 0 结果或 CAPTCHA） |
| Bing 兜底（HTML 兜底源，非 SearXNG 引擎） | — | 0 | — | — | 无日期 |

**`yandex` 的判定样例（写进遗留，防止再被"100% 新鲜"骗）**：

```
上报 2026-09-29 ← 内容年份 [2017]  《天津2017年新能源汽车地补政策发布，纯电动汽车最高补贴2.2万》
上报 2026-09-30 ← 内容年份 [2018,2019,2023] 《东风全系车型迎超级补贴… - OFweek》
15 条结果里 13 条「同一天」——典型抓取/索引日期
```

⇒ 结论：`yandex` **不是"高新鲜度源"，而是"索引日期源"**；它能让"7 日内比例"变成 100%，但那是假绿。

## 3. B3) 门槛新口径（分语言）

| 组 | 口径 | 本轮实测 | 判定 |
| --- | --- | --- | --- |
| **英文** | **≥80% 保持**（与原来一致） | 87%（2 轮）、100%（容器路径绕缓存） | ✅ 达标 |
| **中文** | **不再作为待达标项**；改为「已知限制」+ 降级信号 | 52%、68%（脚本）、52%（容器） | ⚠️ 已知限制 |

**中文失败清单（本轮脚本第 1 轮，逐条 7 日内/5）**：

| 查询 | 7 日内 | 缺什么 |
| --- | --- | --- |
| 2026年9月 国内外重大新闻 | 1/5 | 主源 0 条（`chinaso news` 报错、`google news` CAPTCHA）→ 只能靠回补路的**不带日期**通用引擎 |
| 最近一周 AI 行业动态 | 3/5 | 同上；回补路拿到的多为无日期结果 |
| 台风 最新消息 路径 | 2/5 | `chinaso news` 结果偏旧（8-37 天）；`tiger news` 0 条 |
| 美国 关税 最新政策 | 3/5 | 同上 |
| 2026年 新能源汽车 补贴政策 | 4/5 | `chinaso news` 索引旧（60-104 天） |

**当前可信日期源的 7 日内比例**：`chinaso news` 在中文查询上本轮 **0-40%**（索引旧）、`duckduckgo news` 对纯中文查询基本 0 条、
`tiger news` 0 条；英文侧 `duckduckgo news` 稳定 87-100% ⇒ 差距就是「**缺一个带真实发布日期、且能覆盖中文的源**」。

## 4. B4) 时效降级信号（本轮核心交付）

**规则**：请求带 `time_range` 时，若「**可信日期白名单**（`news_trusted_date_engines`，默认 `duckduckgo news,chinaso news`）
给的窗口内结果数 < `max_results`」，则响应带

```
degraded: true
degraded_reason: "freshness_unverified"
```

**只落在我们的扩展字段位**（`SearchResponse.degraded` / `degraded_reason` 早已存在），
**不动 Tavily 标准字段语义**（`results` / `answer` / `response_time` 等一律不变）；REST 与 MCP 返回同一套字段
（MCP `web_search` 直接 `model_dump`，无需额外接线）。

**线上验证（新镜像，2026-09-30，查询加尾空格绕缓存）**：

| 请求 | degraded | reason |
| --- | --- | --- |
| `美国 关税 最新政策` + `topic=news` + `days=1` | **true** | freshness_unverified |
| `台风 最新消息 路径` + `days=1` | **true** | freshness_unverified |
| `OpenAI latest news` + `days=1` | false | — |
| `python 3.13`（无 time_range） | false | — |

容器路径整轮：**6/8 查询**被标降级（英文两条有 5 条可信新鲜结果、不降级）；这正说明"中文时效无法验证"被如实暴露出来。

**单测（`tests/test_news_degraded_signal.py`，6 条）**：可信源 5 条 → 不降级；只有 `yandex`（索引日期）→ 降级；
无日期源 → 降级；**无 `time_range` 不降级**；REST 响应体含 `degraded`/`degraded_reason`；MCP `web_search` 同样含。

## 5. B5) 复测必须绕缓存（操作规范）

- 应用缓存 `CACHE_QUERY_TTL=600`（10 分钟）：**同一查询直接打 HTTP 会命中缓存**，读到的是十几分钟前的快照。
- 实测同一时刻：`台风最新消息路径` 原样查询 **28%**、加尾空格 **56%**；容器路径 3 轮"完全一致"的 52% 就是缓存回放。
- **规范**：用 HTTP 路径复测时效门槛时，必须让查询字符串唯一（脚本里加尾空格/时间戳后缀），
  或等待 TTL 过期；**报告里必须注明是否绕缓存**。
- **无效数字标注**：`m6-news-freshness-20260930.md` §0/§3 里"容器路径 52%"的 3 轮缓存回放数据**不作为样本**；
  该报告里首次未缓存的 55%、绕缓存后的 72%，以及本文的 70% 才是有效数据。

## 6. C) 立项：中文新鲜源评估（本轮不实现）

写入 `docs/04-后续路线图.md` 的 M6 候选项：

1. **目标**：找一个**带真实发布日期**、覆盖中文、且不灌垃圾的中文新闻源，把中文组从 52-68% 拉到达标区间。
2. **候选方向**（各 1-2 个，先做可行性调研再决定是否新增 provider）：
   - **报刊/媒体官方 RSS**（如人民网/新华网/澎湃等公开 RSS）：日期是编辑发布时间、结构稳定、无需爬虫；
     风险：RSS 覆盖面窄（多数只给栏目最新 N 条）、robots/条款需复核、部分站点限流。
   - **免费新闻 API**（聚合类）：字段规范、有发布时间；风险：免费额度/限流、必须核对**日期是否为发布时间**
     （用本文的抽检工具做验收）、以及署名与合规要求。
3. **可行性调研必须包含**：稳定性（连续 N 天可用率）、robots/条款、限流特征、字段里**日期是否可信**（跑抽检）、
   以及"加入后 news 时效门槛与 2-9/卫生度的前后对照"。
4. **验收必须含日期可信度抽检**（`engine_probe.py dates`），否则不许作为"新鲜源"接入。

## 7. 部署与回滚

```bash
docker tag utf8-search-utf8-search:latest utf8-search-utf8-search:pre-datetrust-20260930  # c2205226f7fc
docker compose build utf8-search && docker compose up -d --no-deps utf8-search
# 新镜像 0aeea61b027f；searxng / caddy 未重启
# 回滚：
docker tag utf8-search-utf8-search:pre-datetrust-20260930 utf8-search-utf8-search:latest
docker compose up -d --no-deps --force-recreate utf8-search
```

## 8. 证据

| 内容 | 路径 |
| --- | --- |
| 日期可信度抽检（引擎分组） | `scripts/engine_probe.py dates` 输出（本文 §2.2 表）；判据 `scripts/searxng_dates.py` |
| 门槛复测（脚本 2 轮 + 容器绕缓存） | `data/measure/news-datetrust-20260930/{news-1.md,news-2.md,container.json}` |
| 降级信号单测 | `tests/test_news_degraded_signal.py`、`tests/test_searxng_dates.py` |
| 引擎盘点补充（可信度分组） | `docs/reports/m6-engine-inventory-20260928.md` §「日期可信度分组」 |
| 复测操作单（缓存规范） | `docs/reports/manual-acceptance-checklist-20260928.md` |

离线套件：**301 passed, 4 deselected**。

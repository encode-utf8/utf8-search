# T10：AIHOT 误剔除修复 + 主题相关性降级信号（`no_relevant_results`）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 范围：第 1 步（AIHOT 日报被「无实质聚合页」误剔除的查因与修复）→ 第 2 步（池内无切题候选时降级）
> → 第 3 步（登记口径验收）。分支 `fix/topic-relevance-gate-20261001`（代码提交 **`62b1e1a`**），
> **未合并 main**；只动 rank 层与响应字段；未碰闸门参数 / `.env` / `settings.yml` / 人工项 3-9。

## 0. 结论摘要（含如实披露）

| 项 | 结果 |
| --- | --- |
| 第 1 步 AIHOT 查因 + 修复 | ✅ 根因 = 短摘要（53 字）被长度/标点阈值判「无实质」→ 聚合页剔除；已补「条目式」分支（≥2 类时间线索） |
| 第 2 步 降级信号 | ✅ 纯函数 `has_no_relevant_results` + `degraded_reason="no_relevant_results"`；多 reason 口径写清并测通 |
| 误报检查（其它 19 条 × 3 轮） | ✅ **0 次**（三轮都只有 Q2 被标记） |
| Q2 专项 · 无料抽样走降级 | ✅ 3/3 轮（本轮 3 轮 Q2 全部 `no_relevant_results`，top5 为 nocache/短剧/门户等） |
| Q2 专项 · 有料抽样 ≥4/5 | ❌ 观测到 1 个「有料」抽样（受控回放 replay1）→ **3/5**（池内实际只有 3 条切题：知乎周刊/ai-bot/**AIHOT**；第 4 槽被门户页占、第 5 槽是内容农场漏网页） |
| 整体中位 ≥19/20 | ❌ **18/18/18（中位 18）** —— Q1 从 5 掉到 3（上游漂移，见 §3.2 归因） |
| 其它 19 条不下降 | ❌ **Q1 5→3**（同样上游漂移；配对回放证明 T10 改动对 Q1/Q2 top5 **零影响**） |

⇒ **降级信号本身可用且无副作用，但 T10 的验收条未全部达成**；按 T9 方案的出口条款，下一步应当在
「实施 T9 方案①（意图×来源类型）」与「把 Q2 登记为已知限制并关闭」之间做选择（§4）。

## 1. 第 1 步：AIHOT 为什么被剔除（查因 → 修复 → 两侧证据）

**查因（不猜）**：从 T9 固定候选池取原始条目 ——

```
title: AI 日报 · AIHOT      url: https://aihot.virxact.com/daily
content(53 字): "4 weeks ago — AIHOT 每日 8:00 自动生成的过去 24 小时一手 AI 动态精选报。"
```

`looks_like_column=True`（一层浅路径 `/daily`）→ 走聚合页豁免分支 → 但 `has_substantive_content`
的长度阈值（≥60 字且 ≥3 个句末标点）把这条 53 字摘要判成「无实质」→ `is_aggregator_page=True` → 剔除。
**即：不是日期/条目判据缺失，而是「短条目 + 时间线索」没被认成实质内容。**

**修复**：`has_substantive_content` 增补**条目式分支** ——
`len(text) ≥ 30` 且出现 **≥2 类**时间线索（`date` / `clock` / `relative` 三类）即判实质。
「两类」是刻意的保守设计：纯导航页通常只有一枚日期（一类）→ 仍判聚合页。

**两侧证据（同一份 T9 池条目，before=`c5eb1ac` / after=`62b1e1a`）**：

```
BEFORE: subst= False aggregator= True     # 被剔除
AFTER : subst= True  aggregator= False    # 豁免保留
```

受控回放 replay1（实现后抓取）里 AIHOT 已进入 Q2 top5 第 3 位（`AI 日报 · AIHOT`）——
修复在真实排序里生效。

**单测（两侧都覆盖）**：

* `test_dated_daily_brief_not_aggregator`：AIHOT 形态（"4 weeks ago … 8:00 …"）→ 判实质、非聚合页；
* `test_navigation_page_with_single_date_still_aggregator`：带单枚日期的纯导航页 → 仍判聚合页（反例）。

## 2. 第 2 步：主题相关性降级信号（`no_relevant_results`）

**判据（纯函数，无 LLM/embedding、无站点黑名单、无 Q2 特判）**：

```python
TOPIC_COVERAGE_FLOOR = 0.35      # query_coverage（既有实现）的达标线
MIN_ON_TOPIC_CANDIDATES = 1      # < 1 ⇒ 一条都没有 ⇒ 判「池内无切题候选」
count_on_topic_candidates(query, results)  # 纯函数
has_no_relevant_results(query, results)    # 纯函数
```

**阈值怎么定的（数据）**：Q2 的**无料抽样**里全池最高覆盖率 0.31（即梦 AI 产品页）→ 达标数 0；
有料抽样里切题候选 0.50-0.63。其它 19 条查询的池内达标数 ≥2（最紧的是 Q16 = 2-3）。
因此取「**达标数为 0 才降级**」——宁漏报、不误报，正好满足「其它 19 条不得出现该降级」的保守要求。

**接线**：

* `apply_rank_filters` 记录 `on_topic_candidates` / `no_relevant_results` 两个统计（只在通用主题路径，与聚合页过滤同开关）；
* `core/pipeline.py` 新增 `merge_degraded_reason()`：**逗号分隔、去重、保序**；
* 触发时响应带 `degraded=true` + `degraded_reason` 含 `no_relevant_results`（REST 与 MCP 同一字段）。

**与 `freshness_unverified` 的关系（明确口径）**：**同一次响应允许多个 reason**（逗号分隔）。
当前分工：`no_relevant_results` 只作用于通用主题路径，`freshness_unverified` 只作用于新闻+`time_range` 路径
⇒ **两者不会同时出现**；但与 `fallback_low_relevance`/`spec_unverified` 可以叠加。

**响应层测试（4 条）**：

* 单原因：垃圾池 → `degraded_reason` 含 `no_relevant_results`；
* 多原因：`fallback_low_relevance,no_relevant_results`（逗号拼接、去重保序）；
* 新闻路径：`topic=news + time_range` → 只有 `freshness_unverified`，不含 `no_relevant_results`；
* 纯函数：垃圾池判真、有料池判假、空池判真、只有 1 条达标也判假（保守边界）。

## 3. 第 3 步：验收（登记口径，固定 `62b1e1a`、20 条、`--no-cache`、单并发、3 轮）

### 3.1 逐项结果

| 轮次 | 窗口 | no_relevant_results | Q2 相关数 | 整体达标数 |
| --- | --- | --- | --- | --- |
| run1 | 00:01:09 → 00:01:28 | **仅 Q2** | 0（nocache/SO/GitHub/微软文档） | 18/20（Q1=3、Q2=0） |
| run2 | 00:01:28 → 00:01:45 | **仅 Q2** | 0（即梦+nocache×4） | 18/20（Q1=3、Q2=0） |
| run3 | 00:01:45 → 00:02:03 | **仅 Q2** | 1（天极资讯频道） | 18/20（Q1=3、Q2=1） |

* **误报检查 ✅**：三轮里只有 Q2 被标记（其它 19 条 0 次）；
* **Q2 无料抽样走降级 ✅**：三轮 Q2 的 `on_topic_candidates` 均为 0/1 → 全部带 `no_relevant_results`；
* **Q2 有料抽样 ≥4/5 ❌**：受控回放 replay1（`on_topic=2`，未被标记）Q2 = **3/5** ——
  池内实际只有 3 条切题（知乎周刊、ai-bot、**AIHOT**），第 4 槽是 AIBase 门户页、第 5 槽是内容农场漏网页
  （`author.knwxfhxd.cc`，标题含「AI成人短剧」但**不含**视频站尾部标记 → T6 的内容农场判据没命中）；
* **整体中位 ≥19 ❌**：18/18/18；**其它 19 条不下降 ❌**：只有 Q1 下降（5→3）。

### 3.2 归因（不猜，用配对回放）

`scripts/replay_pool.py` 对**同一份固定候选池**分别过 `c5eb1ac`（pre-T10）与 `62b1e1a`（T10）的排序层：

```
diff before.json after.json   ⇒ 空            # Q1/Q2 的 top5 逐位一致
```

⇒ T10 的两处改动对 Q1/Q2 的 top5 **零影响**。Q1 的 5→3 来自**上游漂移**：
本轮三轮 Q1 的 top5 都被「日语 9 月活动/杂志页」（`秋の合同相談会`、`日経エンタテインメント 2026年 9 月号`、
`IRONMAN 2026年9月号`、`鳴く虫と菊の節供`）占掉 2 个槽位 —— 这些页 `col=0`（不是栏目页）、`subst=1`，
既不受聚合页判据影响，也不受本轮的条目式分支影响；它们正是 T9 方案里「**词面命中但主题不符**」的抽样问题。

## 4. 下一步选择（按 T9 方案的出口条款）

| 选项 | 说明 | 代价 |
| --- | --- | --- |
| A. 实施 T9 方案①（意图×来源类型） | 同时治 Q2 的「门户/产品页占槽位」与 Q1 本轮的「日期活动页」：新闻意图要求**内容页形态**；门户/产品形态候选充足才剔除 | ~0.5-1 天 + 一轮验收 |
| B. 只保留降级信号，登记 Q2 为已知限制并关闭 | 本轮降级信号已验证无副作用；Q2 在有料抽样仍可能 3/5（池内切题 <4） | 0 天 |
| C. 补 T6 内容农场判据的漏网形态 | 如「AI成人短剧」这类**只有标记、没有视频尾部**的农场页 | ~0.2 天（但只解决第 5 槽，不解决第 4 槽的门户页） |

**本轮建议**：先接受 A 或 B 的拍板；若选 B，则把「Q1 的日期活动页」与「Q2 的门户/农场占位」
统一记为**上游主题匹配类已知限制**（`no_relevant_results` 只覆盖"完全无料"的极端情形）。

## 5. 回滚与约束

* 回滚：`git revert 62b1e1a`（纯 rank 层 + 响应字段）；未部署（本轮不合并 main），线上仍为 `dc7b5f4257ff`；
* 未动：闸门参数、`settings.yml`、`.env`、人工项 3-9；
* 离线全量：**358 passed / 4 deselected**（单测 +8）。

## 6. 产物

| 内容 | 路径 |
| --- | --- |
| 探针工具（明细 + 降级/池内统计） | `scripts/topic_gate_probe.py` |
| 三轮明细与 gate 统计 | `docs/reports/m29-t10-20261002-run{1..3}-{brief.md,gate.json}` |
| 受控回放（有料抽样） | `docs/reports/m29-t10-20261002-replay1-{brief.md,gate.json}` |
| 配对回放（Q1/Q2 零影响） | `docs/reports/t10-paired-{before,after}-20261002.json`、`t10-q1q2-pool-20261002.json` |

# T11：新闻意图 × 内容页形态（T9 方案①）+ 内容农场漏网形态（C）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 分支 `fix/topic-relevance-gate-20261001` 继续提交（代码 **`8de0351`**）；**未合并 main**。
> 只动 rank 层与响应字段；未碰闸门参数 / `settings.yml` / `.env` / 人工项 3-9。
> **因果结论一律来自脚本对拍**（`replay_pool.py`，固定候选池）；实时采样只用于验收计数。

## 0. 结论摘要

| 项 | 结果 |
| --- | --- |
| ① 意图×来源类型 | ✅ 纯函数 `has_news_intent` / `news_non_content_form`（站点/门户首页 + 日期活动页/杂志目录页）；候选充足剔除、不足补回并标 `news_structure_unverified` |
| C 内容农场漏网 | ✅ `is_content_farm` 补形态：农场标记 + 成人向标记（无「在线观看」尾部也算） |
| 因果对拍（20 条固定池） | ✅ **top5 逐位零变化**；规则确实生效（**48 条被剔除**，见 §1.2） |
| 登记口径 3 轮 | ✅ **19/19/19（中位 19、最低 19 ≥18）**；**Q1 = 5/5/5**（T10 基线 3）；Q2 = 0/0/0 且 3/3 轮 `no_relevant_results` |
| 误报检查 | ✅ 三轮唯一降级条目 = Q2；新剔除规则在其它查询**零 top5 变化**、`news_structure_unverified` 未触发 |
| 其它查询稳定下降 | ⚠️ **Q6 中位 5→4**（上游漂移；固定池对拍零影响；见 §3.3） |

## 1. 第 1 步：因果对拍（先证据）

### 1.1 方法

```bash
# ① 固定候选池（20 条查询各抓一次，禁缓存、单并发）
.venv/bin/python scripts/diag_candidates.py 1..20 --dump-pool data/measure/t11-pool-all.json
# ② 同一份池子分别过 pre-T11（a13f5e5）与 T11（8de0351）的排序层
PYTHONPATH=/tmp/t11-before/src .venv/bin/python scripts/replay_pool.py <pool> --out before.json
PYTHONPATH=/root/utf8-search/src  .venv/bin/python scripts/replay_pool.py <pool> --out after.json
diff before.json after.json
```

**结果：20 条查询的 top5 全部逐位一致（0 处变化）** —— 即在这份固定候选池下，T11 的两处改动

> ⚠️ **2026-10-02 T15 更正**：当时用 `PYTHONPATH` 做 before/after，但 `replay_pool.py` 会强制把**脚本自身仓库**的 `src`
> 插到 `sys.path` 最前 ⇒ 两侧其实加载了**同一份代码**，上面的「0 处变化」结论**无效**。
> 用修好的 `REPLAY_SRC` 机制重跑（`a13f5e5 → 8de0351`，同一份固定池）：**Q1 与 Q2 的 top5 确有变化** ——
> Q1 位4/5：`「秋の合同相談会」/IRONMAN 2026年9月号` → `DW 中国2027议题 / 2026 Wikipedia`；
> Q2 位4/5：`lianzu.uk 动画 / 浙江在线` → `中金网 / lianzu.uk`。即 **T11 的两条规则确实改变了 top5**（方向与后续线上 Q1 5/5 一致），
> 但「对其它查询零影响」这句不成立，特此更正。T6/T7/T10 的同类结论已用同一机制复核：**成立**。
**没有改变任何查询的最终 top5**（Q1、Q2 及其它 18 条都一样）。
证据：`docs/reports/t11-paired-{before,after}-20261002.json`、`t11-pool-all-20261002.json`。

### 1.2 规则确实生效（48 条被剔除的明细）

对拍证明"没改 top5"，但规则本身必须真的在干活。同一份池子逐条统计新判据命中的条目：

| 查询 | 剔除数（形态分布） | 其中被**补回**进 top5 |
| --- | --- | --- |
| Q1 2026年9月 国内外重大新闻 | 11（门户首页 6 + 日期活动页/杂志 5） | 0 |
| Q2 最近一周 AI 行业动态 | **22**（门户首页 21 + 内容农场 1） | **4**（门户页，候选不足补回；农场页硬剔除不补回） |
| Q3 semiconductor export controls | 3（门户 3） | 0 |
| Q4 台风 最新消息 路径 | 5（门户 5） | 0 |
| Q5 美国 关税 最新政策 | 1（门户 1） | 0 |
| Q12 数据出境安全评估办法 最新 | 2（门户 2） | 0 |
| Q15 COPPA update | 1（门户 1） | 0 |
| Q20 摩尔线程 最新型号 | 3（门户 3） | 0 |
| 其余 12 条（非新闻意图） | 0 | — |

**解释**：Q1 剔掉的 11 条（含 5 条日期活动页/杂志目录页）本来就不在该池的 top5 里；
只有 Q2 因为池内内容页不足触发了补回（4 条门户页被放回末位），所以 top5 不变而规则已生效。
非新闻意图的 12 条查询完全不受影响（`news_non_content_form` 恒 None）。

## 2. 实现（纯函数 + 单测）

### ① 新闻/动态意图 × 内容页形态（`rank/diversity.py`）

```python
has_news_intent(query)          # 词面：新闻/动态/资讯/要闻/快讯/报道/news/headlines/latest/update + 既有时间意图词
news_non_content_form(result, query) -> str | None
    # 非新闻意图 → None（完全不受影响）
    # portal_homepage：looks_like_column（站点/栏目/频道/专题形态）
    # dated_ephemera：标题前 30 字有日期 + 活动/刊物词（月号/開催/共催/イベント/説明会/相談会/セミナー/举办/举行/讲座/沙龙…）
```

接入 `apply_rank_filters` 的 `news_non_content` 步骤：候选充足时剔除；不足时按既有补回机制放回，
并在 `pipeline` 里标 **`news_structure_unverified`**（`merge_degraded_reason`，多 reason 逗号分隔）。

### C 内容农场漏网形态（并入 `is_content_farm`）

判据升级为：**农场标记（短剧/漫剧/擦边/成人视频…）∩（视频站尾部 ∪ 成人向标记）**。
覆盖 T10 第 5 槽的漏网页 `AI成人短剧《高三爱情故事》第4到20… | 17黑料网`（有标记、无「在线观看」尾部）；
反例（只谈短剧市场的研究页）不受影响。

### 单测（+6，离线 **364 passed / 4 deselected**）

意图纯函数 / 门户首页候选充足剔除 / 非新闻意图不生效 / 日期活动页剔除 + 带日期的新闻标题不误伤 /
候选不足补回标 `news_structure_unverified` / 农场漏网形态（含反例）。

## 3. 第 2 步：验收（登记口径 3 轮，固定 `8de0351`）

### 3.1 数字

| 轮次 | 整体达标数 | Q1 | Q2 | 降级条目 |
| --- | --- | --- | --- | --- |
| run1（00:29:00 → 00:29:17） | **19/20** | **5/5** | 0/5 + `no_relevant_results` | 仅 Q2 |
| run2（00:29:17 → 00:29:34） | **19/20** | **5/5** | 0/5 + `no_relevant_results` | 仅 Q2 |
| run3（00:29:34 → 00:29:53） | **19/20** | **5/5** | 0/5 + `no_relevant_results` | 仅 Q2 |

* **整体：19/19/19 → 中位 19、最低 19（≥18 基线）✅**；
* **Q1：5/5/5**（T10 为 3/3/3）—— 日期活动页/杂志目录页被剔除后，补位的是 RFI/SBS/外交部/NYT/DW 等新闻页 ✅；
* **Q2：三轮全部是「无料」抽样**（`on_topic_candidates=0`）→ **3/3 轮走 `no_relevant_results`** ✅；
  本轮未出现「有料」抽样，故「有料 ≥4/5」条款**本轮无样本可验**（如实说明）；
* **误报检查 ✅**：三轮里 `no_relevant_results` 仅 Q2；`news_structure_unverified` 三轮均未触发
  （本轮各池内容页充足，没有发生补回）。

### 3.2 Q2 抽到的三类坏结果（三无料轮）

`nocache`（npm/GitHub/Yarn）/ StackOverflow 缓存问答 / DuckDuckGo 知乎-Reddit —— 与 T9 证据一致，
均属「上游池里没有切题内容」，本轮按设计降级而不是硬凑。

### 3.3 其它查询的稳定下降（如实披露）

逐条中位对比 T10：**Q1 3→5 ↑、Q5 4→5 ↑、Q6 5→4 ↓**，其余持平（Q3/Q4/Q8–Q14/Q17/Q19/Q20 = 5，Q7/Q15/Q16/Q18 = 4）。

* **Q6 是唯一下降项**：`has_news_intent("Python 3.13 新特性")=False` ⇒ 本轮两条规则**都不适用**；
  固定池对拍里 Q6 top5 **零变化** ⇒ 下降来自上游漂移（本轮 3 轮中有 2 轮混进了
  `docker.aityp.com` 的 `python:3.13.5` 镜像页 —— 这是 T5 注册表判据未覆盖的 mirror 域名）。
* 建议（不属本轮范围）：把 registry 形态从"域名白名单"扩展为"**路径/标题形态**"
  （`/formula|package|project|镜像下载/` + 版本号），可一并覆盖 docker mirror 这类页面。

## 4. 结论与后续

* T11 的两项改动**收益明确**：Q1 稳定 5/5；Q2 的坏抽样一律降级；误报为零；
* 但 **Q2 仍未在任何一轮达到 ≥4/5**（本轮 3 轮全是无料抽样）——
  按 T9 的出口条款，现在应当在 **B（登记 Q2 为已知限制并关闭）** 与 **继续等有料抽样验证 ① 的收益** 之间拍板；
* 本轮对拍已证明：① 在固定池下不会改变任何查询的 top5（无副作用），只在"有料但门户占位"的抽样里才会真正换位。

## 5. 回滚与约束

* 回滚：`git revert 8de0351`（纯 rank 层 + 响应字段）；未部署（未合并 main），线上仍为 `dc7b5f4257ff`；
* 未动：闸门参数、`settings.yml`、`.env`、人工项 3-9。

## 6. 产物

| 内容 | 路径 |
| --- | --- |
| 因果对拍（20 条固定池） | `docs/reports/t11-pool-all-20261002.json`、`t11-paired-{before,after}-20261002.json` |
| 规则命中明细（48 条） | `docs/reports/t11-rule-stats-20261002.json` |
| 三轮明细 + gate 统计 + 打分 | `docs/reports/m29-t11-20261002-run{1..3}-{brief.md,gate.json,scores.csv}` |

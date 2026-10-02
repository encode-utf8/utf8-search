# T6：对拍证据 + 三条缺陷修复 + 把 90% 抬出压线（2026-10-01）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 分支 `fix/q6-q16-20261001` 继续提交（T6 代码提交 `2823daf`）；**未合并 main**。
> 只动 rank 层；未改闸门参数 / `settings.yml` / `.env`；未碰人工项 3-9。

## 0. 结论摘要

| 项 | 结果 |
| --- | --- |
| 第 0 步 对拍（Q2/Q3，固定候选集 before/after） | **top5 逐位一致（diff 为空）** —— 「T5 规则与 Q2/Q3 无因果」由文字论证升级为可检验证据 |
| ① Q3 newsfilter.io | 判据**确属过松**（被「正文有实质内容」单独放行）→ 已收紧；**Q3 三轮 5/5（T5 中位 4）** |
| ② Q2 短剧/内容农场垃圾站 | 新增内容农场判据 + **硬剔除**；T6 三轮 top5 中该类站点**全部消失** |
| ③ Q2 StackOverflow 缓存问答 | 判定为**主题匹配**（非站点形态），本轮不写代码，记入报告与后续立项 |
| 验收（固定 `2823daf`、20 条、`--no-cache`、单并发、3 轮取中位） | **每轮 18/18/18 → 中位 18/20、最低 18/20**（不再压线）✅ |
| 「其它查询中位数不降」 | 19/20 满足；**Q1 3→2（−1）** —— 上游漂移 + 本轮范围外（Q1 只做诊断），如实报告 ⚠️ |

离线全量：**345 passed / 4 deselected**（新增 4 条单测）。

## 1. 第 0 步：对拍（固定候选集、before/after）

做法（新增工具）：

```bash
# 1) 固定候选集（受控回放：单并发、禁缓存）
.venv/bin/python scripts/diag_candidates.py 2 3 --dump-pool data/measure/t6/pool-q2-q3.json
# 2) 同一份候选池，分别过「改动前（main=ccadc21）」与「T5 改动后」的排序层
PYTHONPATH=/tmp/t6-before/src .venv/bin/python scripts/replay_pool.py <pool> --out /tmp/t6-before.json
PYTHONPATH=/root/utf8-search/src  .venv/bin/python scripts/replay_pool.py <pool> --out /tmp/t6-after.json
diff <(json.tool /tmp/t6-before.json) <(json.tool /tmp/t6-after.json)   # ⇒ 空
```

结果：**Q2（23 条候选）与 Q3（24 条候选）在改动前后 top5 逐位完全一致**。
即：T5 的两条新规则（非主题页形态 / 修饰词精确匹配）对 Q2/Q3 的最终排序**零影响** ——
T5 报告里「Q2/Q3 中位下降与改动无因果」由此从文字论证变成**可复现的对拍证据**。

证据（随代码入库）：
`docs/reports/t6-pool-q2-q3-20261001.json`（固定候选池）、
`docs/reports/t6-paired-q2-q3-{before,after}-20261001.json`（两侧 top5）。

## 2. 第 1 步：三条缺陷的处置

### ① newsfilter.io（Q3）——判据过松，已收紧

**查因**：`newsfilter.io` 是**站点首页**（path 为空 → `looks_like_column=True`），
但正文是站点自我介绍（"We deliver real-time business and markets news to the world…"，204 字）
→ `has_substantive_content=True` → 旧 `is_aggregator_page` 的「实质内容豁免」把它放行；
`is_offtopic_index_page` 不覆盖它（非个人主页/包索引/图片板）。**结论：豁免条件确实过松。**

**收紧**：新增 `has_item_like_content()` —— 首页/栏目页的「实质内容」还必须**像条目**
（带日期 `2026-09-26 / 2026年9月`、「N 天前 / ago / published」、或 ≥3 个 `·`/`|` 分隔）。
`is_aggregator_page` 改为「有实质内容 **且** 像条目」才豁免。
已按既有裁决逐条核对：**发改委首页**（"2026年9月11日…"）、**美国之音首页**（"5 days ago —"）、
**外交部栏目页**（"（2026-09-26）"）都带日期 → 保持豁免（单测覆盖）。

效果：T6 三轮 Q3 的 top5 里 **newsfilter.io 全部消失**，Q3 = 5/5/5。

### ② 短剧/内容农场垃圾站（Q2）——站点形态，硬剔除

**判据**：`is_content_farm()` = 「短剧/漫剧/擦边/成人视频…」标记 **且** 「在线观看/免费观看/在线播放/全集」尾部，
且**查询本身不是这类内容**（查询含「短剧」等词时不生效）。
命中即**硬剔除**（不参与「候选不足补回」——垃圾站不该因为池子空就被放回来）。

效果：T5 三轮 top5 里出现过的短剧垃圾站（`bd477.hwqlgzvsk.cc`、`c4cab.kmexvuoz.cc` 等），
在 T6 三轮里**全部消失**。

### ③ StackOverflow 缓存问答（Q2）——判定为**主题匹配**

**证据**：T6 三轮 Q2 的 top5 分别是「npm `nocache` / Stack Overflow `?nocache=1` / GitHub `nocache` / Yarn `nocache`」
（run1/2）与「知乎/Reddit 的 DuckDuckGo」（run3）。这些页面**形态正常**（问答页/包页/帖子）、内容实质，
失败原因是**上游候选池里根本没有切题的 AI 行业动态**，剩下的相关候选在「候选不足补回」阶段被拉起。
⇒ 属**主题匹配**问题（不是站点形态），rank 层只能把它们排在后面，无法凭空造出相关结果。
**本轮不写代码**；后续立项：主题相关性闸门（对补回项设覆盖度下限，或为 Q2 这类查询加兜底策略）。

## 3. 第 2 步：验收（登记口径）

固定 commit **`2823daf`**、20 条查询、`--no-cache`、单并发、**3 轮取中位数**
（2026-10-01 20:02:29 → 20:03:23；明细 `docs/reports/m29-t6-20261001-run{1..3}-{brief.md,scores.csv}`）。

| 轮次 | 窗口 | 相关数 ≥4 的查询 | 平均相关 | <4 的查询 |
| --- | --- | --- | --- | --- |
| run1 | 20:02:29 → 20:02:48 | **18/20 = 90%** | 4.45 | Q1(2)、Q2(0) |
| run2 | 20:02:48 → 20:03:06 | **18/20 = 90%** | 4.45 | Q1(2)、Q2(0) |
| run3 | 20:03:06 → 20:03:23 | **18/20 = 90%** | 4.50 | Q1(2)、Q2(0) |

**中位 18/20、三轮最低 18/20 → 不再压线 ✅**；按逐条中位口径也是 **18/20 = 90%**。

**逐条中位 vs T5**（只列有变化）：

| 查询 | T6 三轮 | 中位 | T5 中位 | 变化 |
| --- | --- | --- | --- | --- |
| Q3 semiconductor export controls | 5/5/5 | 5 | 4 | **+1**（newsfilter 剔除后由 CSIS/VOA/tmtpost 等补位） |
| Q6 Python 3.13 新特性 | 5/5/5 | 5 | 4 | +1 |
| Q18 扫地机器人 | 4/5/5 | 5 | 4 | +1 |
| Q1 2026年9月 国内外重大新闻 | 2/2/2 | 2 | 3 | **−1 ⚠️** |

其余 16 条持平（Q2 中位 0、Q4/Q5/Q7–Q17/Q19/Q20 均在 4–5）。

**Q1 的 −1 归因（如实披露）**：三轮 Q1 的 top5 都是「央视《生活圈》+ 仁川机场迎新页 + 日本开运日历」
这三条固定垃圾 + RFI + NYT ⇒ 2/5；这三条与 T5 的差异来自**上游候选漂移**（T5 三轮里有两轮给了
观察者网/发改委 这类可用条目）。Q1 属你明确「只做诊断、本轮不修」的查询，且**与本轮/T5 的规则无关**
（Q1 无规格 token、三条规则均不命中）。是否顺手修 Q1 的「节目页/院校页/日历页」形态，请你裁决。

## 4. 回滚与约束

* 回滚：`git revert 2823daf`（纯 rank 层）；现网未部署（本轮不合并 main），线上仍为 `5694bdc297e2`。
* 未动：闸门参数、`settings.yml`、`.env`、人工项 3-9。

## 5. 产物

| 内容 | 路径 |
| --- | --- |
| 对拍工具 | `scripts/replay_pool.py`（+ `diag_candidates.py --dump-pool`） |
| 对拍证据 | `docs/reports/t6-{pool-q2-q3,paired-q2-q3-before,paired-q2-q3-after}-20261001.json` |
| 复测明细与打分 | `docs/reports/m29-t6-20261001-run{1..3}-{brief.md,scores.csv}` |
| 单测（+4） | `tests/test_rank_hardening.py` |

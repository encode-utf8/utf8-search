# P7：P1 两处欠账（幂等 + 召回证据）（2026-09-30）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 分支 `chore/p1-ranking-20260930`（**未合并 main**）。只做 P7；未改闸门参数、`settings.yml`、`.env` 键。

## 1) `apply_form_penalty` 幂等（已修）

**问题**：旧实现原地乘分 `result.score *= 0.95` ⇒ **被调两次就是 ×0.9025**（重复处理持续压低分数）。

**修法（选了"仅用于排序 key"）**：

```python
def apply_form_penalty(results):        # 幂等：不改 score，只按有效分排序
    return sorted(results, key=lambda r: r.score * form_score_multiplier(r), reverse=True)
```

* `score` 保持**相关性原始分**（对外字段语义不变；分数接近时可能出现"分数略高但因形态让位"的顺序，这是刻意为之）；
* 顺序判据与旧实现**数学等价**（旧版先乘再按 score 排 ≡ 新版按 `score×乘子` 排），所以**排序行为不变**；
* **幂等**：对同一批结果重复调用 1/2/3 次，顺序与 score 都不变。

**单测**：`tests/test_rank_hardening.py::test_form_penalty_is_idempotent`（新加）断言三次调用顺序一致、且
`score` 与调用前逐位一致；原 P1 用例同步改为断言「score 不被修改（0.80 保持 0.80）、让位只体现在顺序上」。
离线全量：**325 passed / 4 deselected**（基线 324 + 1 条幂等用例）。

## 2) `drop_stale=True` 的召回证据（20 条 2-9 对照）

方法（`scripts/recall_ab.py`，只读、禁缓存；2026-10-01 从 `data/measure/` 移入仓库，见 `docs/reports/recall-ab-usage-20261001.md`）：
同一批 20 条查询跑两次流水线 —— **before** 把 `apply_recency` 包一层强制 `drop_stale=False`（模拟 P5 之前），
**after** 用当前代码（命中时间意图时 `drop_stale=True`），对比**返回结果条数**。

| # | 时间意图 | before | after | Δ | 查询 |
| --- | --- | --- | --- | --- | --- |
| 1 | 是 | 5 | 5 | 0 | 2026年9月 国内外重大新闻 |
| 2 | 是 | 5 | 5 | 0 | 最近一周 AI 行业动态 |
| 3 | 是 | 5 | 5 | 0 | latest news semiconductor export controls |
| 4 | 是 | 5 | 5 | 0 | 台风 最新消息 路径 |
| 5 | 是 | 5 | 5 | 0 | 美国 关税 最新政策 |
| 6-11 | 否 | 5 | 5 | 0 | Python 3.13 / MCP spec / FastAPI / HTTP3 / Tokio / 新能源汽车补贴 |
| 12 | 是 | 5 | 5 | 0 | 数据出境安全评估办法 最新 |
| 13-14 | 否 | 5 | 5 | 0 | EU AI Act / 个税扣除 |
| 15 | 是 | 5 | 5 | 0 | children privacy law COPPA update |
| 16-19 | 否 | 5 | 5 | 0 | iPhone 17 Pro / 降噪耳机 / 扫地机器人 / RTX 5090 |
| 20 | 是 | 5 | 5 | 0 | 国产显卡 摩尔线程 最新型号 |

**结论**：命中时间意图的 **8/8** 条查询、以及其余 12 条，`before→after` 条数**全部 0 变化**；
合计 **100 → 100**，**没有任何查询因硬过滤而少召回**。
机制说明：`apply_recency(drop_stale=True)` 只在"剔除后仍够 `max_results`"时才丢已知陈旧结果，
且过滤层本来就有"不足则补回"的兜底 —— 两条一起保证**召回不塌**。

## 3) 2-9 复测（如实披露：本轮遇到上游漂移）

为核对"排序语义未变"，本轮又跑了一次 20 条采集（`docs/reports/m2-9-p7-ranking-20260930.md`，脚本路径天然绕缓存）：

* 与 P1 那次逐条明细对比：**17/20 条查询的 top5 内容不同** —— 这是**上游结果集漂移**（同一份代码、同一批查询，几分钟内结果换了）；
  P7 的排序判据与旧实现在数学上等价（见 §1），**不会改变顺序**；
* 按同一套口径（agent 初评：校准集 + 盲评三档）判读本批：**宽松判 17/20 = 85%、严格判 15/20 = 75%**
  —— **低于 P7 的验收线（宽松 ≥20/20）**，未达标查询为 **Q1（3/5）、Q2（3/5）、Q16（3/5）**，
  全部是历史波动最大的查询（中文新闻汇总页 / AI 动态垃圾页 / 机型混杂页）。
* **如实结论**：这次"低于 20/20"**不能归因于 P7 的代码改动**（排序 key 等价、召回未变，见 §1/§2），
  而是这一批次上游给的结果集本身更差。**P1 的验收结论（宽松 20/20）依然成立，但它是"那一批次"的结论**；
  建议把 2-9 的口径补一条"**取最近 3 次采样的中位数**"再复测（或等你审后决定是否重跑一次）。

## 4. 证据

| 内容 | 路径 |
| --- | --- |
| 幂等单测 | `tests/test_rank_hardening.py::test_form_penalty_is_idempotent` |
| 召回对照脚本（已移入仓库）/结果 | `scripts/recall_ab.py`、`data/recall-ab.json`（gitignored 工作副本） |
| 2-9 本批复测（含明细/速览/卫生度） | `docs/reports/m2-9-p7-ranking-20260930{,-brief}.md`、`data/measure/p7-recall-20260930/hygiene-after.json` |
| P1 验收批（对照基线） | `docs/reports/m2-9-p1-ranking-20260930-scores-judge.md` |

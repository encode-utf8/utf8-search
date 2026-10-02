# P1 排序层形态降权 + P5 英文时新意图硬过滤（2026-09-30）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 分支 `chore/p1-ranking-20260930`（**未合并 main**）。**只改 rank 层 + pipeline 的排序段**；
> 未改闸门参数、未改 `settings.yml`、未加 `.env` 键。

## P1 形态降权（轻量乘子）

### 实现

`rank/diversity.py`：

```python
COLUMN_PAGE_SCORE_MULTIPLIER = 0.95          # 含实质内容的首页/栏目页：×0.95（只降权、不剔除）
def form_score_multiplier(result): return COLUMN_PAGE_SCORE_MULTIPLIER if looks_like_column(result) else 1.0
def apply_form_penalty(results):             # 乘子 + 稳定重排（不删除任何结果）
```

接入点：`pipeline._rank_hits()` 的通用主题收尾（`apply_form_penalty(merged)`），**过滤层不动** ——
因此「只是导航的聚合页」仍由 `is_aggregator_page` 剔除，而**日报/汇总类文章只降 5%**。
乘子而非逐条特判：分数接近时才换位，高相关汇总页仍然排在前面。

### 单测（`tests/test_rank_hardening.py` 新增 2 条）

* `test_form_penalty_downranks_column_page_mildly`：0.61（汇总页） vs 0.60（文章）→ 汇总页 ×0.95 后让位，且**仍在结果里**；
* `test_form_penalty_keeps_daily_roundup_not_over_penalized`：分数接近时让位、分数明显更高时仍第一，乘子恒为 **0.95**（不会被误杀）。

## P5 英文时新意图（对齐中文）

复核发现 `_RECENCY_WORDS` **早就包含** `latest/recent/today/update/breaking/news`，真正缺的是
**命中时间意图后的硬过滤**。本轮：

* 词表补 `last week` / `past week`（对齐「最近一周」）；
* 通用主题命中时间意图时，`apply_recency(drop_stale=True)` **硬过滤已知陈旧**结果
  （仅在"剩余结果仍够 max_results"时生效，不会掏空；无日期的实时页保留）；
* 单测 `tests/test_recency.py::test_recency_intent_covers_english_time_words`（5 正例 + 3 反例）。

口径提醒：2-9 判「切题」不判「最新」，本项只影响**检索排序/过滤**，不改 2-9 的判分口径（docs/04 §8 遗留 3-①）。

## 验收：2-9 前后对照 + 卫生度（复测绕缓存）

`scripts/relevance.py --depth basic --no-cache`（脚本路径天然不读应用缓存）+ agent 初评（校准集 + 盲评三档）：

| 项 | 改动前（09-30 相关性加固轮） | **本轮（P1 后）** |
| --- | --- | --- |
| **宽松判** | 19/20 = 95% | **20/20 = 100%**（门槛 90%，达标） |
| **严格判（勉强=0）** | 15/20 = 75% | **15/20 = 75%**（未退化，如实披露） |
| 平均相关条数 | 4.65 | **4.75** |
| 未达标查询 | Q16（2/5） | **无** |
| 覆盖率均值 | 0.773 | 0.770（噪声内） |
| 独立站点均值 | 4.75 | 4.70 |
| 同站冗余 / 聚合页 / 脚本不匹配 / 空内容 | 0 / 0 / 0 / 2 | 0 / 0 / 0 / 2 |

**逐条差异（关键 4 条）**：

* **Q2**：垃圾短剧站从第 1 位消失（原 `#1 短剧站` → 现在 4 条真实 AI 周报/资讯 + 1 条不相关）；
* **Q16**：京东「苹果8x参数」二手回收列表页从第 1 位消失（现在 4/5 相关，仅剩 wirefly `Pro Max` 机型不符）；
* **Q6**：仍是 4/5（V2EX 帖排第 5），无退化；
* **Q1**：仍是 4/5（仁川机场迎新页第 5），汇总/栏目页按裁决口径保留、仅轻微让位。

**严格判的 5 个失败查询**（与上轮同源，属"勉强相关"承重）：Q1、Q2、Q7、Q10、Q16 —— 未恶化。

## 回滚

纯 rank 层改动，回滚只需还原一个 commit：

```bash
git revert <本轮的 feat commit>      # 或 git checkout <上一个 main> -- src/utf8_search/rank src/utf8_search/core/pipeline.py
.venv/bin/python -m pytest -q -m "not net"
```

无需重建容器即可在脚本路径验证；要让现网生效需按 docs/05 §14.1 rebuild + `up -d --no-deps`。

## 证据

| 内容 | 路径 |
| --- | --- |
| 2-9 明细 / 速览 / 打分 / 判定 | `docs/reports/m2-9-p1-ranking-20260930{,-brief,-scores,-scores-judge}.md/.csv` |
| 卫生度 JSON（P1 后） | `data/measure/p1-ranking-20260930/hygiene-after.json` |
| 上轮对照 | `docs/reports/m2-9-relevance-hardening-20260930-scores-judge.md`、`data/measure/relevance-hardening-20260930/hygiene-after.json` |
| 代码 | `src/utf8_search/rank/diversity.py`（乘子）、`src/utf8_search/core/pipeline.py`（接入 + 时间意图硬过滤）、`src/utf8_search/rank/recency.py`（词表） |
| 单测 | `tests/test_rank_hardening.py`、`tests/test_recency.py` |

离线套件：**324 passed, 4 deselected**。

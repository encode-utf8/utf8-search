# docs/reports/ —— 验收报告留痕

`data/` 目录被 `.gitignore` 忽略，报告放在那里会随代码一起丢掉。因此**关键验收报告统一归档到本目录**
（原文件仍在 `data/` 下作为工作副本）。命名约定：`<里程碑>-<主题>-<日期>.md`，
日期用采集当天（`YYYYMMDD`）。

## 索引

| 文件 | 里程碑 / 验收项 | 内容 |
| --- | --- | --- |
| `m4-4.3-client-selfcheck-20260924.md` | M4-4.3（4.3-1 ~ 4.3-11） | **客户端联调自检报告**：stdio / stdio-raw / Streamable HTTP / REST / 限流五通道共 24 项检查的汇总与逐项明细、失败详情、**人工联调清单（待回填）**、复现命令 |
| `m5-5.3-verification-20260924.md` | M5-5.3（5.3-1 ~ 5.3-12） | **总验收报告**：目标、结论表、实测数据、改动清单、复现命令、人工打分指引 |
| `m5-5.3-rank-ab-same-candidates-20260924.md` | 5.3-8 | 受控 A/B：**同一批候选**下「改动前 / 改动后」排序对比（含逐查询 top5 对照） |
| `m5-5.3-hygiene-compare-raw-20260924.txt` | 5.3-8 | 端到端 `--compare-hygiene` 原始输出（改动前 → 改动后） |
| `m5-5.3-hygiene-legacy-20260924.json` / `m5-5.3-hygiene-after-20260924.json` | 5.3-8 | 两份卫生度汇总 JSON（可用 `relevance.py --compare-hygiene` 重新判定） |
| `m5-5.3-relevance-after-20260924.md` | 5.3-12 | 20 条查询 top5 明细（改动后）——**人工打分对象** |
| `m5-5.3-relevance-legacy-20260924.md` | 5.3-12 | 同一套查询的「改动前」明细（对照用） |
| `m5-5.3-relevance-scores-20260924.csv` | 5.3-12 | 人工打分模板（`scores` 填 5 个 0/1；`note` 写理由）——**待填写** |
| `m5-5.3-news-timeliness-ab-20260924.md` | 5.3-10（5.2 回归） | 时效性配对 A/B：逐条交替「开/关质量过滤」，确认过滤没挤掉新鲜结果 |
| `m5-5.2-news-timeliness-20260924.md` | 5.2-7 | 时效性验收：`topic=news` + `time_range=day` 的 7 日内日期比例 |
| `m5-5.1-bench-engines-20260924.md` | 5.1-13 | 引擎健康度自适应 A/B：覆盖率 / 延迟 / 上游异常次数 |
| `m2-9-relevance-judge-baseline-20260924.md` | 2-9 基线 | **未达标基线（75%）**：M5-5.3 要修的问题清单来源 |
| `m2-9-relevance-scores-20260924.csv` | 2-9 基线 | 基线逐条打分与理由 |

## 联调回填（4.3-12，人工）

协议、参数、鉴权、限流已由 `scripts/mcp_selfcheck.py` 覆盖（最近一次：24/24 通过）。
**各客户端自身的配置界面 / 配置文件**需要按 `docs/03-客户端接入指南.md` 第 10.2 节逐客户端点一次，
把「跑通」列（✅ / 失败备注）回填到 `m4-4.3-client-selfcheck-20260924.md` 第 4 节的表里。

## 复现

各报告的复现命令写在 `m5-5.3-verification-20260924.md` 第 6 节。

## 打分（5.3-12，人工）

```powershell
# 1) 读 docs/reports/m5-5.3-relevance-after-20260924.md，给 20 条查询的 top5 打分（1=相关）
# 2) 把分数填进 docs/reports/m5-5.3-relevance-scores-20260924.csv 的 scores 列（5 个 0/1）
.\.venv\Scripts\python.exe scripts\relevance.py --score-file docs\reports\m5-5.3-relevance-scores-20260924.csv
```

门槛：top5 相关数 ≥ 4 的查询占比 ≥ 90%。

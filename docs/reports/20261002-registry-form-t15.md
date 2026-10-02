# T15：registry/包索引判据扩展为「路径+标题形态」（治 docker mirror 页）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> 分支 `fix/registry-form-20261002`（代码 `8f4fd1b` + 工具修正 `3b1dd0a`）；**已于 2026-10-02 经 T19 `--no-ff` 合并进 main（merge `bb34b19`）并部署上线（镜像 `258749c7a318`；线上 Q6 5/5/5）**。
> 依据：`docs/04` §8 第 16 条 ③、T11 报告 §3.3、总表 §2 遗留 #9。
> 约束：只动 rank 层与响应字段；未改闸门参数 / `settings.yml` / `.env`；未碰人工项。

## 0. 结论摘要

| 项 | 结果 |
| --- | --- |
| 诊断（固定池） | docker mirror 页 `https://docker.aityp.com/image/docker.io/python:3.13.9-slim`（标题「…- 镜像下载」、正文 117 字命令）→ 旧判据只看**域名白名单**，未命中 → 进入 Q6 实时 top5（判 0） |
| 改动 | `looks_like_offtopic_index_page` 增加「**路径 / 标题形态 + 版本号 token**」分支；口径不变（形态命中**且**无实质内容才剔除；候选充足才剔除、不足补回并标 `index_page_unverified`） |
| 因果证据（真实 before/after） | Q6 固定池 top5 **位 5**：`docker.io/python:3.13.9-slim - 镜像下载` → `Python 3.13 alpha 1 contains breaking changes`（0 分项换成切题内容页） |
| 验收（登记口径 3 轮） | **19/19/20 → 中位 19、最低 19（≥18）✅**；**Q6 5/5/5**（基线 4）；**Q2 3/3/4**（基线 1）；**无任何查询下降** |
| 离线套件 | **380 passed / 4 deselected**（基线 375 + 5 新单测） |
| 附带修正 | 发现并修好 `replay_pool.py` 的 before/after 代码切换缺陷（`PYTHONPATH` 无效）→ T6/T7/T10 历史结论复核**成立**、**T11 结论更正**（见 §3.2） |

## 1. 诊断（先证据）

固定池抓取（`scripts/diag_candidates.py 6 --dump-pool`）命中坏结果：

```
title : docker.io/python:3.13.9-slim - 镜像下载 | docker.io
url   : https://docker.aityp.com/image/docker.io/python:3.13.9-slim
content(117 字): sed -i 's#python:3.13.9-slim#swr.cn-north-4.myhuaweicloud.com/…#' deployment.yaml.
```

逐条判据（改前）：

| 判据 | 结果 |
| --- | --- |
| host ∈ registry 域名白名单 | ❌ `docker.aityp.com` 不在名单（白名单只有 formulae.brew.sh / pypi.org / npmjs.com / crates.io / …） |
| `/image/…` ∈ registry 路径正则 | ❌ 旧正则只覆盖 `/project|package|formula|crates|gems|r` |
| `looks_like_column` / `has_substantive_content` | `False / False`（正文是元数据片段） |
| → `is_offtopic_index_page` | **False（漏网）**，且该条在实时抓取里**确实进入 Q6 top5**（`top5` 标记） |

## 2. 改动（rank 层纯函数）

`rank/diversity.py` 新增三分支并接入 `looks_like_offtopic_index_page`：

* **路径形态**：`/formula|formulae|packages?|projects?|pypi|crates|gems|mirrors?|images?|downloads?|artifacts?|repositor(y|ies)|library/`；
* **标题形态**：`镜像下载 / 镜像源 / 镜像仓库 / 包索引 / package / formula / docker.io/ / pypi / crates.io / npmjs`；
* **版本号 token**：`3.13.9` 这类语义版本，或 `python:3.13` 这类 tag；
* 三者满足「路径或标题」+「版本号」，再叠加**既有**的「形态命中 **且** 正文无实质内容」才剔除 ——
  带实质内容的页面（如 `/downloads/` 下的长教程）**照旧保留**（单测覆盖）。

补降级口子：`apply_rank_filters` 记录 `offtopic_page_refilled`，`pipeline.merge_degraded_reason` 合并
**`index_page_unverified`**（候选不足、镜像/包索引页被补回时对外告知；REST/MCP 同一字段）。

单测 +5：镜像页按形态剔除 / 有实质内容保留 / 无版本号不判 / 候选充足剔除 / 候选不足补回标降级。

## 3. 因果证据

### 3.1 真实 before/after 固定池 diff（T15 本体）

```bash
REPLAY_SRC=/tmp/t15-before/src .venv/bin/python scripts/replay_pool.py <Q6 固定池> --out before.json   # 7fe8b80（改前）
REPLAY_SRC=/opt/utf8-search/src  .venv/bin/python scripts/replay_pool.py <Q6 固定池> --out after.json   # 8f4fd1b（改后）
```

| 位 | 改前 top5 | 改后 top5 |
| --- | --- | --- |
| 1 | Python 3.14 新特性学习(第一部分) | 同 |
| 2 | python3.13 3.14 新特性 好好好 - 博客园 | 同 |
| 3 | Python 3.13 Debuts With New Interactive Interpreter | 同 |
| 4 | The new REPL in Python 3.13 - Trey Hunner | 同 |
| 5 | **docker.io/python:3.13.9-slim - 镜像下载**（0 分） | **Python 3.13 alpha 1 contains breaking changes**（切题） |

### 3.2 方法学修正：`replay_pool.py` 的 before/after 之前是**失效的**

`replay_pool.py` 会把**脚本自身仓库**的 `src` 插到 `sys.path` 最前 ⇒ 早前用 `PYTHONPATH=<worktree>/src`
做「改前/改后」时，两侧其实加载了同一份代码。**已修**：新增 `REPLAY_SRC=<worktree>/src` 显式切换。

用修好的机制复核历史结论（同一份旧固定池）：

| 轮次 | 原结论 | 真实复核（同池） | 判定 |
| --- | --- | --- | --- |
| T6（T5 规则 → Q2/Q3） | top5 零变化 | 零变化 | ✅ 成立 |
| T7（T6 规则 → Q1） | top5 零变化 | 零变化 | ✅ 成立 |
| T10（T10 规则 → Q1/Q2） | top5 零变化 | 零变化 | ✅ 成立 |
| T11（T11 规则 → 20 条） | top5 零变化 | **Q1、Q2 有位移**（Q1 位4/5：日期活动页→DW/Wikipedia；Q2 位4/5 门户换位） | ❌ **已更正**（T11 报告已加更正注：规则确实改变了 top5，方向与线上 Q1 5/5 一致） |

## 4. 验收（登记口径：20 条 + `--no-cache` + 单并发 + 3 轮取中位）

| 轮次 | 窗口 | 相关数 ≥4 的查询 | 平均相关 | <4 |
| --- | --- | --- | --- | --- |
| run1 | 17:16:49 → 17:17:15 | 19/20 | 4.80 | Q2(3) |
| run2 | 17:17:15 → 17:17:43 | 19/20 | 4.80 | Q2(3) |
| run3 | 17:17:43 → 17:18:01 | **20/20** | 4.80 | — |

* **中位 19/20、最低 19（≥18）✅**；逐条中位口径 19/20；
* **Q6 专项：5/5/5**（T12 基线 4/4/5 → 中位 4）——三轮 top5 里 **docker 镜像页全部消失**，
  由知乎/docs.python.org/博客园/Phoronix/Trey Hunner 等切题内容页占据；
* **Q2：3/3/4**（基线 1）——镜像/门户类形态被压掉后，知乎周报/ai-bot 稳定在前三；
* **相比 T12 线上基线，无任何查询的逐条中位下降**（Q2 +2、Q6 +1，其余持平）。

## 5. 离线套件与约束

* `pytest -q -m "not net"` → **380 passed / 4 deselected**（基线 375 + 5）；
* 未改闸门参数 / `settings.yml` / `.env` / 人工项；回滚：`git revert 8f4fd1b`（纯 rank 层 + 响应字段）。

## 6. 产物

| 内容 | 路径 |
| --- | --- |
| 固定池与诊断 | `docs/reports/t15-q6-pool-20261002.json` |
| 真实 before/after | `docs/reports/t15-paired-q6-{before,after}-20261002.json` |
| 三轮明细/gate/打分 | `docs/reports/m29-t15-20261002-run{1..3}-{brief.md,gate.json,scores.csv}` |
| 单测 | `tests/test_rank_hardening.py`（+5） |

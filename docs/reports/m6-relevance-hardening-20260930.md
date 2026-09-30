# 通用相关性加固：规格 token + 兜底闸门 + 聚合页口径对齐（2026-09-30）

> 分支 `fix/relevance-hardening-20260930`（**未合并 main**）。改动：`src/utf8_search/rank/`（新模块 + 三条判据）、
> `src/utf8_search/core/pipeline.py`（兜底闸门 + 降级信号）、单测；已重建并上线 app。
> **未改闸门参数、未做中文新鲜源、未碰人工项 3-9**；Bing 兜底的**相关性闸门**本轮已做（不是"下一轮"）。

## 0. 摘要

| 项 | 结果 |
| --- | --- |
| **2-9 达标率** | **19/20 = 95%（门槛 90%）→ 通过**（上一轮 16/20 = 80%）；未达标仅 **Q16（iPhone 17 Pro，2/5）** |
| 卫生度 | 覆盖率 **0.773**（上轮 0.708）、独立站点 4.75、同站冗余/聚合页/脚本不匹配 **0**、空内容 2 |
| 规格 token（B） | 新增 `rank/spec_tokens.py`：抽数字/版本/修饰词/品牌数字短语 → 完全/部分/不匹配；**Q6 从 3/5 → 5/5**（3.14 与构建报错页被剔除） |
| 兜底相关性闸门（C） | Bing 结果入池前过**查询词覆盖率**（≥0.34）；无关项不入池，全被挡下时响应带 `degraded_reason="fallback_low_relevance"` |
| 聚合页口径（D） | `is_aggregator_page` 改为「**形态像栏目 且 正文没有实质内容**」→ **Q2 从 1/5 → 4/5**（日报/汇总页不再被误杀），Q1 也从 3/5 → 4/5 |
| 部署 | 新镜像 `40f87e4a5f9d`；回滚锚点 `pre-relevance-hardening-20260930` = `0aeea61b027f` |

## 1. A) 收尾与合并

- **A2 已完成**：`e1808e9 merge: news 日期可信度分组 + 门槛分语言口径 + 时效降级信号`，`push e2fc922..e1808e9`；
  合并后 main 复跑 **301 passed / 4 deselected**；`diff --stat` = **11 files, +653**。
- **A1 两个 6h 长稳仍在跑**（本轮结束前状态）：跨镜像那个 49 采样、干净那个 39 采样，**可用率均 100%**、异常/空结果/跳过均 0；
  `/metrics` **无 rejected 序列** ⇒ **期间无 429**。跨镜像那个 12:00 后 RSS 记 n/a（PID 已消失）⇒ **内存不可比，只报可用率**；
  干净那个（18:05 结束）报完整结论 —— 跑满后按 `--summarize` 回填 §22/§24。

## 2. B) 规格 token 匹配

**实现**（`src/utf8_search/rank/spec_tokens.py`，纯函数）：

* `extract_spec_tokens(query)`：抽取 ① 版本号（`3.13`）② 品牌+数字短语（`RTX 5090` / `iPhone 17`）③ 裸数字（`17`/`5090`）④ 型号修饰词（`Pro/Max/Plus/mini/Ultra/Air/SE`）；
  **年份与日期不算**（`2026`、`2026年9月`、`9月`、`30日`、`9号`）——否则「2026年 新能源汽车 补贴政策」这类查询会被误伤；
* `match_spec_tokens(tokens, title, content, url)`：在**标题 + 摘要 + 正文开头 500 字 + URL**（统一小写）里匹配，
  前界 `(?<![\d.])` 挡住 `3.130` 里的 `3.13`、`3.17` 里的 `17`，后界只挡数字（允许 `3.13.html`）；
  返回 **full / partial / none / n/a**（查询没有规格 token 时是 `n/a`）。

**接入**（`rank/diversity.apply_rank_filters`）：

* 新增 `spec_mismatch` 阶段：**候选充足时剔除 `none`**；候选不足时按缺陷轻重补回，并记
  `spec_mismatch_refilled` → 上层在响应里标 `degraded_reason="spec_unverified"`（"只降权、不静默丢"）；
* `partial`（iPhone 17 对 iPhone 17 Pro）**降权**到同组末尾，不剔除（记 `spec_partial_downranked`）；
* **没有规格 token 的查询完全不变**（单测断言：结果列表与顺序都不动）。

**单测**：`tests/test_spec_tokens.py` 7 条（抽取、年份排除、n/a、三档、版本边界、URL 命中、多 token 混排）+
`tests/test_rank_hardening.py` 4 条（充足时剔除、不足时补回并记 refilled、partial 降权、无 token 不变）。

## 3. C) 兜底相关性闸门

`pipeline._filter_fallback_hits()`：**Bing 结果入池前**用 5.3 的 `query_coverage` 过闸（阈值 = `rank_min_query_coverage`，默认 0.34）；
不合格的直接不注入；若全被挡下 → 记 `degraded_reason="fallback_low_relevance"`，**宁可少几条也不把无关结果当兜底**。
对"主源失败后的兜底"与"新闻让位后的兜底"两条路径都生效；单测 2 条（无关的沃尔玛/世界杯页面被挡 + 命中查询词的仍入池）。

## 4. D) 聚合页/栏目页口径对齐

**旧实现**只看 URL/标题形态（标题含「汇总/日报」即判聚合页），把 Q1 的每日新闻汇总、Q2 的 AI 周报这类**有实质内容**的页面也剔除了 ——
与 2-9 的判分口径（"聚合形态本身不等于不相关；站点首页/栏目页这类『只是导航』才判 0"）不一致。

**新实现**：`is_aggregator_page = looks_like_column(形态) and not has_substantive_content(实质内容)`；
`has_substantive_content` 用长度 + 句末标点密度（≥200 字，或 ≥120 字且 ≥2 句，或 ≥60 字且 ≥3 句）。
口径写进代码注释与本文；单测 4 条（频道页+短导航 → 过滤；日报+长正文 → 保留；文章路径 → 不过滤）。

## 5. E) 2-9 复测结论

口径：`scripts/relevance.py --depth basic --no-cache`（脚本路径，天然绕缓存）+ agent 初评（校准集 + 盲评三档）。

| 项 | 上一轮（09-30 早） | **本轮** |
| --- | --- | --- |
| 达标率 | 16/20 = 80%（不通过） | **19/20 = 95%（通过）** |
| 平均相关条数 | 4.50 | **4.65** |
| 未达标 | Q1 / Q2 / Q6 / Q16 | **仅 Q16（iPhone 17 Pro，2/5）** |
| 覆盖率均值 | 0.708 | **0.773** |
| 独立站点均值 | 4.75 | 4.75 |
| 同站冗余 / 聚合页 / 脚本不匹配 / 空内容 | 0 / 0 / 0 / 2 | 0 / 0 / 0 / 2 |

**逐条归因**：Q6（Python 3.13）3/5 → **5/5**（规格 token 剔除 3.14/构建页）；Q2（AI 行业动态）1/5 → **4/5**（聚合页口径改后，
AI 周报/日报类页面保留）；Q1（国内外重大新闻）3/5 → **4/5**（同上，外交部栏目页保留）；
Q16 仍 2/5：京东「苹果8x参数」二手回收页与 wirefly **Pro Max**、ZOL **iPhone 17（非 Pro）**—— 前者的标题同时含 `17` 与 `pro`
（混杂机型列表），规格 token 无法区分，属**遗留**（下一步可加"型号 token 必须与主型号同时出现/不能出现在混杂列表页"的更强判据）。

**校准集**：本轮样本里的历史 ❌ 同类条目（短剧站、Wheeler School 声明页、GitHub 他人聚合 issue 等）均判 0 ✓。

**容器路径**：本轮部署后抽查（绕缓存）：`Python 3.13 新特性` → 前 3 条全是 3.13 官方/中文解读；
`iPhone 17 Pro 价格 参数` → 前 3 条全是 iPhone 17 Pro 页 ⇒ 线上效果与脚本路径一致。

## 6. 部署与回滚

```bash
docker tag utf8-search-utf8-search:latest utf8-search-utf8-search:pre-relevance-hardening-20260930  # 0aeea61b027f
docker compose build utf8-search && docker compose up -d --no-deps utf8-search   # 新镜像 40f87e4a5f9d
# 回滚：docker tag utf8-search-utf8-search:pre-relevance-hardening-20260930 utf8-search-utf8-search:latest \
#       && docker compose up -d --no-deps --force-recreate utf8-search
```

`searxng` / `caddy` 未重启；端口矩阵不变。**提醒**：容器路径复测仍必须**绕缓存**（`CACHE_QUERY_TTL=600`），本轮抽查用了尾空格。

## 7. 遗留

1. **Q16 类"型号混杂列表页"**：标题同时出现主型号与其它型号（京东二手回收页）时，规格 token 会误判为匹配；
   下一步建议：识别"列表/回收/参数对比"形态 + 要求**主型号 token 出现在标题主体**（而不是混杂列表里）。
2. 长稳回填（§22/§24）与两个长稳的最终结论（跨镜像只报可用率、干净那个报完整结论）。
3. 中文新鲜源评估（上一轮立项，未实施）。

## 8. 证据

| 内容 | 路径 |
| --- | --- |
| 2-9 明细 / 速览 / 打分 / 判定 | `docs/reports/m2-9-relevance-hardening-20260930{,-brief,-scores,-scores-judge}.md/.csv` |
| 卫生度 JSON | `data/measure/relevance-hardening-20260930/hygiene-after.json` |
| 代码 | `src/utf8_search/rank/spec_tokens.py`、`rank/diversity.py`、`core/pipeline.py` |
| 单测 | `tests/test_spec_tokens.py`、`tests/test_rank_hardening.py` |

离线套件：**318 passed, 4 deselected**。

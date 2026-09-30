# news 时效收口：新鲜度判据 + Bing 让位 + 撤 sina + 探测加固（2026-09-30）

> 分支 `fix/news-freshness-20260930`（**未合并 main**）。改动：`src/`（判据、Bing 让位、白名单默认值）、
> `scripts/engine_probe.py`（引擎注册校验）、单测；**已重建并上线 app 容器**（searxng / caddy 未动）。
> **未改闸门参数、未改 `searxng/settings.yml`、未碰人工项 3-9**。

## 0. 摘要

| 目标 | 结果 |
| --- | --- |
| 回补触发判据改为「7 日内结果数 < max_results」 | ✅ 已改；**中文组从 0% 提到 52-56%**（合计 28% → **72%**） |
| Bing 让位（主源 → 日期回补 → Bing） | ✅ 已改；实测主源 0 条的查询现在会走回补路（此前被 Bing 先占位） |
| `sina` 撤出回补白名单（含机制保留） | ✅ 已撤（实测 60 条 0 条带日期）；白名单机制保留、默认空 |
| B4 `yandex` 受控 A/B | ✅ 结论：**维持排除** —— 放回能让门槛「100% 通过」，但那是**假绿**（见 §4） |
| 探测加固（未注册引擎立即报错） | ✅ `scripts/engine_probe.py` + 3 条单测 |
| **news 时效门槛（部署服务）** | ❌ **72%（中文 56% / 英文 100%），仍未达 80%** —— 结论是**源不足**，不是排序（§6） |
| 重建并上线 app | ✅ 新镜像 `c2205226f7fc`（回滚锚点 `pre-freshness-20260930` = `03bf40b20341`） |

**顺带挖出一个方法论坑（重要）**：容器 HTTP 路径首次测得 52%，与脚本路径（70-72%）不符 ——
根因是**应用缓存**（`CACHE_QUERY_TTL=600`）。同一批查询加一个尾空格绕开缓存后，容器路径回到 **72%**，
与脚本一致。**以后用 HTTP 路径复测门槛必须绕缓存**，否则读到的是十几分钟前的快照。

## 1. A) 收尾与合并

- **A2 已完成**：`be82c74 merge: news 按引擎 time_range 白名单 + sina 进回补路（含源实测更正）`，
  `push 4017e93..be82c74`；合并后 main 复跑离线套件 **280 passed / 4 deselected**；
  `diff --stat 4017e93..main` = **8 files changed, 444 insertions(+), 24 deletions(-)**。
- **A1（6h 长稳）仍在跑**：11:14:33 启动、预计 **17:14** 结束。截至 11:59:35 已 10 个采样、**全部 OK、0 失败**，
  延迟中位 **2525ms**；`/metrics` 只看到 `requests_total{result="ok"}`（42），**没有任何 `rejected_total` 序列**
  ⇒ 长稳期间**没有 429**（既没有闸门拒绝也没有 RPM 限流）。
  ⚠️ 12:00 的 app 重建让这次长稳**跨了两个镜像**（10 个采样在旧镜像、之后的在新镜像）；
  但本次接线/镜像变更不涉及 `.env`/compose，**「env 接线后可用率与内存」的结论仍然成立**（回填时按时间切分报告）。
  另一个副作用：长稳启动时抓的是**旧容器的 PID**，重建后该 PID 消失 ⇒ 12:04 起的采样 **RSS 记为 n/a**，
  所以这次长稳**只能给出可用率结论，内存只有重建前 10 个采样**（104.5 → 111.3MB）。
  **因此另起了一个干净的 6h 长稳**（`data/soak-6h-freshness.csv`，12:05:13 启动、新容器 PID 183149、预计 18:05 结束），
  它同时覆盖可用率与内存；回填 A1 时两个一起报。

## 2. B) 实现

### 2.1 撤出 `sina`、白名单默认置空（B1）

- `news_general_engines` 默认值去掉 `sina`（同时确认不含已删除的 `360search`）。
- `news_time_range_engines` 默认改为**空**；注释写明撤回理由：**实测 sina 注册后 60 条结果 0 条带发布日期**，
  当初把它写进白名单的依据是一条假测量（未注册引擎触发 SearXNG 回退默认集合）。**机制保留**（白名单非空时按引擎拆分请求）。

### 2.2 回补触发判据：结果数 → 新鲜度（B2）

`_needs_general_extra` 由「`len(hits) < max_results`」改为
**「窗口内带发布日期的新鲜结果数 < max_results」**（`_fresh_count`，复用 `rank.recency.parse_published`）。
口径：**无日期不计入分子、但不丢弃**（仍进候选池，只是在时效排序里靠后）。
单测覆盖三种输入：全带日期且新鲜 / 全无日期 / 混合（含"新鲜 5 条 + 过期与无日期混杂"不触发）。

### 2.3 Bing 让位而非禁用（B3）

`_collect_hits` 在 **new + `time_range`** 场景把兜底源（Bing）**延后**：顺序变为
**主源 → 日期回补 → Bing**；Bing 结果仍可入池（避免空结果），但它不再抢先填满 `max_results` 把回补路旁路掉。
provider 调用抽成 `_call_provider`（主源循环与让位后的兜底共用同一套闸门/异常语义）。
单测：主源 0 条 → 回补路先跑且够 5 条时 Bing 完全不调用；回补路补不出时 Bing 兜住；无 `time_range` 时保持旧顺序。

### 2.4 探测加固（B5）

`scripts/engine_probe.py` 新增 `missing_engines()`（纯函数）+ `assert_engines_registered()`：
发查询前先读目标实例 `/config`，**点名的引擎只要有一个未注册就报错退出并打印可用引擎列表**；
`retest` / `compare` / `sweep`（显式列表）都已接入。新增 `tests/test_engine_probe_registry.py`（3 条，离线）。

## 3. 复测：news 时效门槛（按语言拆）

口径：`topic=news` + `time_range=day`，`max_results=5`，"7 日内"= 发布日期在 7 天内。

| 轮次 | 合计 | 中文组 | 英文组 |
| --- | --- | --- | --- |
| 改动前（脚本，09-30 11:0x） | 11/40 = 28% | **0/25 = 0%** | 11/15 = 73% |
| 改动后 · 脚本第 1 轮 | 35/40 = **88%** | 20/25 = 80% | 15/15 = 100% |
| 改动后 · 脚本第 2-3 轮 | 29/40 = **72%** | 14/25 = 56% | 15/15 = 100% |
| **改动后 · 容器路径（绕缓存）2 轮** | **29/40 = 72%** | **14/25 = 56%** | **15/15 = 100%** |

逐条明细（改动后，容器路径第 1 轮）：`国内外重大新闻 1/5`、`AI 行业动态 3/5`、`台风 2/5`、`关税 4/5`、
`新能源汽车补贴 4/5`；英文三条 5/5。路径归因（`news_decompose`）：**主源 0 条的查询现在会走 `searxng:general` 回补路**
（如 `国内外重大新闻` 从 `['bing']` 变成 `['searxng:general']` 且 5/5 新鲜）。

**`google news` 状态**：整个复测期间**都在 CAPTCHA 处罚盒**里（容器 `/health.cooling` 里也有它，`reason=captcha`）；
英文组的 100% 完全不依赖它（靠 `duckduckgo news`）。

## 4. B4 受控 A/B：要不要把 `yandex` 放回日期回补路

### 4.1 上游候选层（5 条中文查询 × 2 轮，`time_range=day`，只读）

| 组 | 结果 | 带日期 | 7 日内 | 覆盖均值 | 同站冗余 | 聚合页 | 空内容 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A 当前默认（无 yandex） | 131 | **0** | **0** | 0.171 | 2.3 | 1.4 | 0.3 |
| B 加回 yandex | 312 | **150** | **150** | 0.248 | 5.7 | 4.5 | 1.2 |

（同站冗余/聚合页/空内容是**绝对条数**；按结果数归一化后 A ≈1.76%/1.07%/0.23%、B ≈1.83%/1.44%/0.38%。）

### 4.2 结论：**维持排除** —— 放回能"通过"但是**假绿**

把 yandex 放进回补路后，**管线级**门槛确实 3/3 轮 100%（中文 25/25），但把最终 top5 打出来看：

```
最近一周 AI 行业动态   #2 yandex 2026-09-29 91crdj.com  「神豪修罗场-成人短剧 全集在线观看」
                      #5 yandex 2026-09-29 aihuangdou.com 「琼明神女录 - AI成人短剧在线观看」
新能源汽车 补贴政策    #1 yandex 2026-09-29 kknews.cc    「天津2017年新能源汽车地补政策发布」（2017 年旧文）
                      #3 yandex 2026-09-29 gist.github.com「94327_onwfe」（spam gist）
台风 最新消息 路径      #2/#5 yandex → 成人短剧站 / YouTube 直播
```

两个证据说明「100% 新鲜」是假的：
1. **日期是索引日期不是发布日期**：2017 年的天津地补政策被标成 `2026-09-29`；
2. **内容级垃圾**：成人短剧站、spam gist、YouTube 视频——都是当年 5.2 排除 yandex 的同一类「垃圾农场」。

⇒ **维持排除**（`news_general_engines` 不含 yandex），并把「yandex 会伪造新鲜日期」这条写进遗留，
避免以后有人只看门槛数字又把它放回来。

## 5. B7 部署

```bash
docker tag utf8-search-utf8-search:latest utf8-search-utf8-search:pre-freshness-20260930   # 回滚锚点 03bf40b20341
docker compose build utf8-search            # 58s
docker compose up -d --no-deps utf8-search  # 只重建 app；searxng / caddy 未重启
# 新镜像 sha256:c2205226f7fc…（创建 2026-09-30T03:59Z）；健康检查通过
```

**回滚**：`docker tag utf8-search-utf8-search:pre-freshness-20260930 utf8-search-utf8-search:latest &&
docker compose up -d --no-deps --force-recreate utf8-search`（约 10 秒不可用；`.env`/compose 未改，无需回退）。

**部署前后行为对照（同一查询、同为 `days=1`）**：

| 查询 | 旧镜像 | 新镜像 |
| --- | --- | --- |
| 最近一周 AI 行业动态 | `engines_used=['bing']`、7 日内 0/5 | 走 `searxng:general` 回补路、7 日内 3/5 |
| 美国 关税 最新政策 | `engines_used=['searxng']`、7 日内 0/5 | `searxng` + 回补路、7 日内 4/5 |

## 6. 归因：是源不足还是排序问题？

**是源不足**，判据/排序这次已经改对了：

- 判据改动**确实生效**：中文组 0/25 → 14-20/25；主源 0 条的查询从 `['bing']` 变成走 `['searxng:general']` 回补路；
  英文组 73% → 100%。
- 剩余差距的原因：**回补路能拿到的「带真实发布日期」的中文候选数量随上游可用性波动**：
  `chinaso news` 索引偏旧（本轮 60-104 天）、`tiger news` 经常 0 条、`google news` 全程 CAPTCHA 且本身不给日期、
  `sogou wechat` 在当前出口失效、`sina` 无日期、`bilibili` 是视频站；
  只有 `duckduckgo news`（英文）稳定。
  这解释了"有些轮次 88%、多数 72%"：**上游给得出新鲜候选时就达标，给不出就不达标**。
- 因此**不调参数**（窗口/预算/阈值都不动）；下一步要么找**可信的中文新鲜源**（真实发布日期、非垃圾站），
  要么承认「中文查询的 80% 时效门槛在现有免费源条件下不可达」并按语言重设口径（产品决策）。

## 7. 证据文件

| 内容 | 路径 |
| --- | --- |
| 门槛：脚本 3 轮 / 容器绕缓存 2 轮 / 逐条明细 | `data/measure/news-freshness-20260930/{news-after.md,news-container-nocache.json,decompose-after.txt}` |
| B4 A/B（上游候选层，含 top5 与卫生度） | `data/measure/news-freshness-20260930/backfill-ab.json` |
| B4 管线级对照（含 yandex 三连 100% 的原始报告） | `/tmp/ncy-{1,2,3}.md`（工作区临时；结论已写入本文 §4） |
| 代码 | `src/utf8_search/{config.py,core/pipeline.py}`、`scripts/engine_probe.py` |
| 单测 | `tests/test_news_freshness_trigger.py`、`tests/test_engine_probe_registry.py`、`tests/test_news_time_range.py`、`tests/test_upstream_gate.py` |
| 长稳（进行中） | `data/soak-6h-envwiring.{csv,json,meta.json}` |

离线套件：**291 passed, 4 deselected**。

# 引擎集合优化 阶段 1：现网复测 + 候选评估 + 替换方案（2026-09-28）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> **本阶段只测量与出方案**：**未改动 `searxng/settings.yml`，未改产品代码，未提交**。
> 背景：`docs/reports/m6-engine-inventory-20260928.md` 的结论是「先换引擎（补中文源）→ 再谈重排」，
> 但那份隔离探针只跑了 **2 条查询**、对中文源不公平 —— 本报告用**中文本地化查询**重测。
>
> **口径说明（2026-09-28 复测修订）**：本报告第一版的全新实例探针**只覆盖了 16 个引擎中的 12 个**
> （漏了 `naver` / `yahoo` / `fynd` / `brave`，且 §4 的「现有 8 引擎」基线里 `brave`/`yahoo`/`fynd`
> **没在探针注册**，实际只跑到 5 个引擎）。**已重跑**：探针改为 **现网 16 引擎全部 + 4 个候选 = 20 引擎**
> 登记，§3/§4 全部按新数据重写；旧数据留档在 `data/measure/engine-selection-20260928/retest_probe16_partial_20260928.json`。

## 0. 结论摘要（先看这一段）

1. **中文源现状**：`360search` 与 `sogou wechat` 在**全新实例 + 6 条中文本地化查询**下仍然
   **0 结果** ⇒ **不是"探针查询不合适"，也不是现网处罚盒，而是在当前出口真的失效**
   （5.2/5.3 的「10 条/查询」「4 条/查询」是 2026-09-24 在**美国出口 IP** 上测的，出口已变）。
   `360search` 还**每次空转 ~1000ms**（不是快速失败）⇒ 纯成本，而且**它一个人把整条查询的 P50 抬到 1s 级**。
2. **现网被拒的引擎分两类**：`privacywall` / `yep` / `resulthunter` 在全新实例**仍被拒/限流**
   ⇒ 上游对该出口的持续限制；`google` / `google news` 在全新实例**可用（59 / 60 条）**
   ⇒ 现网的 CAPTCHA 是**实例累计请求触发的处罚盒**（5.1 健康度自适应会冷却它，属预期行为）。
3. **候选实测（6 条中文查询，全新实例）**：`chinaso news` **24 条全带日期**（286ms）、
   `tiger news` **60 条全带日期**（250ms）、`sina` **60 条无日期但支持 time_range**（218ms）、
   `bilibili` **120 条全带日期**（476ms，**单站灌满**，非新闻源需单独定位）。
4. **扇出/收益（20 引擎探针，交错 A/B，每档 6 条中文查询 × 2 轮 = 12 样本）**：
   - **移除** `360search` + `sogou wechat`：**结果数一条都不少（736 → 737）**，延迟 P50
     **1024ms → 688ms（−33%）**、max **1444ms → 1005ms** ⇒ **纯赚**。
   - 在「移除后」的基础上**再加** `chinaso news`/`sina`/`bilibili`：结果 **737 → 1144 条（+55%）**、
     **带日期 27 → 314 条（×11.6）**，延迟 P50 **688 → 789ms**，仍比现状 **1024ms 低 23%**。
   - 结构上每加 1 个引擎 = 每查询多 1 路出站请求（闸门管不到 SearXNG 内部扇出）。
5. **方案（不动手）**：**移除** `360search`（0 结果 + ~1s 空转）、`sogou wechat`（0 结果 + 150ms 空转）；
   **新增** `chinaso news`（首选）、`tiger news`（备选）、`sina`（可选）；**`bilibili` 单独说明**
   （只在需要中文长尾/视频场景启用，且必须靠 `rank_max_per_host=2` 限流）；
   `google` / `google news` / `naver` / `yahoo` / `fynd`、`privacywall` / `yep` / `resulthunter` / `brave` /
   `reloado` / `zapmeta` / `quark` 先**保留**（判定依据见 §5.3：**「0 结果」不等于该删，要看它是否占延迟**）。

## 1. 方法（公平复测怎么做）

- **查询集**（6 条中文本地化，覆盖政策/地方政策/地方新闻/产业动态/商品评测）：
  `2026年 新能源汽车 补贴政策`、`四川省 数字经济 扶持 政策 申报 条件`、`深圳 地铁 新线路 开通 最新`、
  `国产 大模型 产业 动态 2026`、`扫地机器人 推荐 性价比 2026`、`折叠屏 手机 参数 对比 2026`。
- **两个被测面**：① **现网实例**（`127.0.0.1:8888`，只读查询）；② **独立探针容器**
  （同镜像、`127.0.0.1:8899`、`keep_only` 只开被测引擎、启用 JSON、**全新实例无历史处罚盒**）——
  这样可以把「探针查询不合适」与「现网处罚盒」与「出口真的不可用」区分开。
- 每引擎：6 条查询 + 2 次 `time_range`（day/week）探测；记录结果数、带发布日期数、延迟、`unresponsive_engines`。
- **探针引擎集合 = 现网 keep_only 的 16 个 + 4 个候选（`chinaso news`/`sina`/`bilibili`/`tiger news`）= 20 个**
  （全部显式 `disabled: false` + `inactive: false`），这样「现网引擎」与「候选」在**同一实例、同一时刻**可比。
- 探针配置留档：`data/measure/engine-selection-20260928/probe20-settings.yml`。
- 探针容器用完即删（`docker rm -f searx-probe`），**现网配置未改**。

## 2. 现网复测（8 个"0 结果/被拒"引擎 × 6 条中文查询，2026-09-28 18:06）

被测的 8 个是当时 `/metrics` + 逐引擎探测里"0 结果 / 被上游拒绝"的那几个
（另外 8 个当时仍出结果，未逐个复测）。现网是**已运行 2 天的长跑实例**（各引擎都进过处罚盒），
所以这一节只反映"此刻服务状态"，**不能用来判定引擎本身好坏** —— 判定一律以 §3 的全新实例为准。

| 引擎 | 6 查询总结果 | 带日期 | time_range(day/week) | P50 | 上游报告原因 |
| --- | --- | --- | --- | --- | --- |
| `privacywall` | 0 | 0 | 0 / 0 | 7ms | Suspended: access denied |
| `google` | 0 | 0 | 0 / 0 | 6ms | Suspended: CAPTCHA |
| `zapmeta` | 0 | 0 | 0 / 0 | 173ms | — |
| `yep` | 0 | 0 | 0 / 0 | 7ms | Suspended: access denied |
| `quark` | 0 | 0 | 0 / 0 | 16ms | — |
| `360search` | 0 | 0 | 0 / 0 | 947ms | — |
| `sogou wechat` | 0 | 0 | 0 / 0 | 147ms | — |
| `google news` | 0 | 0 | 0 / 0 | 9ms | CAPTCHA |

> 同一时刻对照：`yandex` 15 条、`resulthunter` 报 `too many requests`、`duckduckgo news` 0（中文查询，符合预期）。
> 说明**现网此刻整体处于限流状态**，单看现网数据会误判"引擎坏了" —— 所以必须做下面的全新实例复测。

## 3. 全新实例公平复测（20 引擎 = 现网 16 全部 + 4 候选，6 条中文本地化查询 + time_range 探测）

| 引擎 | 在现网? | 总结果 | 带日期 | time_range(day/week) | P50 | 上游原因 | 归类 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **`bilibili`** | 候选 | **120** | **120** | **20 / 20** | 476ms | — | ⚠️ 非新闻源，需单独定位 |
| `yandex` | ✔ | 90 | 1 | 15 / 15 | 624ms | — | 保留（主力） |
| `naver` | ✔ | 75 | 0 | 1 / 13 | 781ms | — | 保留（韩/多语；中文侧一般） |
| `google news` | ✔ | 60 | **0** | 0 / 0 | 216ms | — | 保留（无日期，与 5.2 一致） |
| **`sina`** | 候选 | 60 | 0 | **10 / 10** | 218ms | — | ⚠️ 候选可选（无日期） |
| **`tiger news`** | 候选 | **60** | **60** | 0 / 0 | 250ms | — | ✅ 候选备选 |
| `google` | ✔ | 59 | 0 | 10 / 10 | 451ms | — | 保留（fresh 可用；现网 CAPTCHA 是处罚盒） |
| `yahoo` | ✔ | 42 | 0 | 7 / 7 | 732ms | — | 保留（多语） |
| `fynd` | ✔ | 35 | 0 | 0 / 0 | 549ms | — | 保留（英文为主） |
| **`chinaso news`** | 候选 | **24** | **24** | 0 / 0 | 286ms | — | ✅ 候选首选 |
| `duckduckgo news` | ✔ | 12 | 12 | 0 / 0 | 225ms | — | 保留（英文新闻） |
| **`360search`** | ✔ | **0** | 0 | 0 / 0 | **996ms** | — | ❌ **当前出口失效 + 空转 ~1s** |
| `sogou wechat` | ✔ | **0** | 0 | 0 / 0 | 150ms | — | ❌ **当前出口失效** |
| `zapmeta` | ✔ | 0 | 0 | 0 / 0 | 179ms | — | ➖ 英文元搜索（中文侧无贡献） |
| `reloado` | ✔ | 0 | 0 | 0 / 0 | 196ms | — | ➖ 英文元搜索（中文侧无贡献） |
| `quark` | ✔ | 0 | 0 | 0 / 0 | 18ms | — | ➖ 中文侧无贡献但**快速失败** |
| `resulthunter` | ✔ | 0 | 0 | 0 / 0 | 7ms | Suspended: too many requests | ➖ 本次被限流（历史上是稳定主力） |
| `privacywall` | ✔ | 0 | 0 | 0 / 0 | 8ms | Suspended: access denied | ➖ 被拒但成本仅 8ms |
| `yep` | ✔ | 0 | 0 | 0 / 0 | 13ms | Suspended: access denied | ➖ 被拒但成本仅 13ms |
| `brave` | ✔ | 0 | 0 | 0 / 0 | 11ms | Suspended: too many requests | ➖ 被拒但成本仅 11ms |

> 原始数据：`data/measure/engine-selection-20260928/retest_probe20_20260928.json`
> （20 引擎 × 6 条中文查询 + 2 次 time_range 探测 = 160 次单引擎查询，全部 200）。
> 探针配置见 `data/measure/engine-selection-20260928/probe20-settings.yml`（keep_only = 20 个引擎）。

**关键判定**：

- `360search` / `sogou wechat`：**全新实例同样 0 结果** ⇒ **不是探针查询问题，也不是现网处罚盒**；
  结合 5.2/5.3 是"美国出口 IP"上测的，判定为**当前出口对这两个中文源不可用**
  （出口已核实：`ipinfo.io` → `203.0.113.10` / **Singapore**）。
- `google`：fresh 可用（59 条）⇒ 现网 CAPTCHA 属**实例处罚盒**（5.1 会冷却与自愈，保留即可）；
  `google news` 在 fresh 也是 60 条，但**一条日期都不带**（与 5.2 结论一致）。
- `chinaso news` 在 5.3 曾被判"注册失败"而排除，**本次 fresh 实例注册并返回 24 条全带日期结果** ⇒ 值得复测重估。
- **「0 结果」本身不是删除依据**：`resulthunter` / `privacywall` / `yep` / `brave` / `quark` 都是 0 结果，
  但**7-18ms 快速失败**（被拒/挂起时 SearXNG 直接返回），对延迟几乎无影响；
  真正伤延迟的只有 **`360search`（996ms 空转）**，次一级是 `sogou wechat`（150ms）。
- `zapmeta` / `reloado` 的 0 结果**属预期**（英文元搜索，中文查询本就 0），不是"坏了"；
  它们与 `quark` 一样只应在**英文侧**按历史结论（inventory 轮：reloado 2 查询 77 条）评估去留。

## 4. 扇出与收益实测（现网 16 引擎 vs 移除 2 vs 移除 2 + 加 3）

同一探针实例内**逐条交错**跑（6 条中文查询 × 2 轮 = 每档 12 个样本）：

| 配置 | 结果/查询 | 12 样本合计 | **带日期合计** | 延迟 P50 | 延迟 P90 | 延迟 P95 | 延迟 max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **`deployed16`** = 现网 keep_only 的全部 16 引擎 | 60 条 | 736 | **26** | **1024ms** | 1059ms | 1233ms | 1444ms |
| **`deployed16-2`** = 16 −（`360search`,`sogou wechat`） | 60 条 | **737** | 27 | **688ms（−33%）** | 998ms | 1003ms | 1005ms |
| **`deployed16-2+3`** = 上面 +（`chinaso news`,`sina`,`bilibili`） | **97 条** | **1144（+55%）** | **314（×11.6）** | **789ms（−23%）** | 1001ms | 1009ms | 1012ms |
| `base8`（旧报告的"现有 8 引擎"口径，仅作对照） | 48 条 | 585 | 27 | 669ms | 990ms | 1025ms | 1046ms |

> n=12 时 P95 与 max 几乎重合，**P95 只作趋势参考**；基线请读「P50 + max + 异常样本」。

> 原始数据：`docs/reports/engine-selection-fanout-round2-20260928.json`（上表）；
> `engine-selection-fanout-round1-20260928.json` 为同法第一轮交叉验证（`deployed16` 延迟 P50 1085ms、max 含 1 个
> **20015ms 异常样本**）⇒ 现网 16 引擎混跑的基线区间是 **P50 1024-1085ms**，
> 且**出现过 20s 级尾延迟**（1/24 样本，非探针请求超时，是 SearXNG 侧在等某个引擎）。

**三条可直接对上的结论**：

1. **移除 `360search` + `sogou wechat` 是纯赚**：结果数 736 → 737（一条不少，因为两者本来就 0 条），
   延迟 P50 **1024 → 688ms（−33%）**、max 1444 → 1005ms ⇒ 它们现在只贡献延迟、不贡献结果。
   （机制：`360search` 每次空转 ~1s，而 SearXNG 的聚合等待由最慢引擎决定。）
2. **加 3 个中文候选＝结果与日期覆盖的乘数级提升**：结果 +55%，
   **带日期候选 27 → 314 条（×11.6）**（→ 直接喂 5.2 的时效判定），
   延迟 **789ms 仍比现状 1024ms 低 23%**。
3. **旧报告的 §4 表作废**：旧数据里 `brave`/`yahoo`/`fynd` 三个引擎**没在探针注册**
   （SearXNG 对未注册名静默丢弃，见 checklist 第 6 条），"现有 8 引擎"实际只跑到 5 个，
   所以旧数字（35 条/694ms）既不能代表 8 引擎、也不能代表现网。以本节数据为准。

**结构说明**：SearXNG 对**每个引擎各发一次上游请求**，所以每加 1 个引擎 = **每查询多 1 路出站请求**
（本服务并发 5 时：现网 16 引擎 ≈ 80 路/波；移除 2 → 14 引擎 ≈ 70 路/波；再 +3 → 17 引擎 ≈ 85 路/波）。
本服务的闸门只约束"进 SearXNG 的请求数"，**管不到 SearXNG 内部的扇出** —— 这是"加引擎"的主要成本项。
因此「减 2 加 3」虽然把延迟从 1024ms 拉到 789ms，**上游扇出仍是净增 1 个引擎（+6%）**，
实施时也要按这个口径观察上游错误率，而不能只看延迟变小。

## 5. 替换方案（**只出方案，不动手**）

### 5.1 移除

| 引擎 | 证据 | 风险 | 回滚 |
| --- | --- | --- | --- |
| **`360search`**（**建议直接移**） | fresh 实例 6 条中文查询 **0 结果**，且**每次空转 996ms**（不是快速失败）—— 它一个人把整条查询的 P50 抬到 1s 级；移除后结果数不变、P50 −33% | 低：唯一用途是中文补充，现已无贡献；若出口换回美国/回国可能恢复 | `settings.yml` 恢复备份 + `docker compose restart searxng`（或把 `disabled` 改回 `false`） |
| **`sogou wechat`**（建议移，或"保留观察"） | fresh 实例 6 条中文查询 **0 结果**（150ms 空转） | 中：它是 5.2 指定的**中文新闻主源**，移除后中文时效候选更依赖新的 `chinaso news`/`tiger news`；但**当前出口它一条都不给** | 同上；成本仅 150ms，若你想保守可先只移 `360search`（单这一项就有 −33% 延迟的大部分收益） |

### 5.2 新增

| 引擎 | 证据（6 条中文查询） | 额外配置 | 风险 | 回滚 |
| --- | --- | --- | --- | --- |
| **`chinaso news`**（首选） | **24 条，100% 带日期**，286ms；5.3 曾判"注册失败"，本次 fresh 注册成功 | 需覆盖 `inactive: false`（否则不注册） | 中：中文聚合源，内容质量需用 2-9 抽检复核；`time_range` 不支持（传了返回 0，属正常） | 删除该条目 + restart，或置 `disabled: true` |
| **`tiger news`**（备选） | **60 条，100% 带日期**，250ms | 需覆盖 `inactive: false` | 中：多语新闻源（非中文专用），中文质量需抽检 | 同上 |
| **`sina`**（可选） | 60 条，**无日期**，218ms，**支持 time_range** | 需覆盖 `inactive: false`（`json_engine`） | 中：无发布日期 ⇒ 对 5.2 时效无帮助，只增候选宽度；依赖其 JSON 接口稳定性 | 同上 |
| **`bilibili`**（**单独说明，本轮不建议默认加**） | 120 条，100% 带日期，476ms，支持 time_range | 无需额外配置 | **高**：**非新闻源**（视频站），6 条查询 120 条 = **20 条/查询全是同一站**；若不加限流会挤占 top5 | 同上 |

> 注：§4 的 `deployed16-2+3` 组合里 `+3` 用的是 `chinaso news`/`sina`/`bilibili`（口径与上一版一致）。
> 若按本节结论把 `bilibili` 换成 `tiger news`，出站路数不变（都是 +3），结果/日期覆盖只会更偏向中文新闻。

**`bilibili` 的适用场景（单独说明）**：它是**视频站**、不是新闻源。
唯一合理用法是「**中文长尾/需要视频内容时**」启用，并且**必须**依赖既有的
`rank_max_per_host=2`（同站限流）把单站洪水压到 2 条；否则它会用 20 条同站结果淹没候选池。
**不建议**把它放进通用/新闻路径的默认引擎集合。

### 5.3 保留（不动）

| 引擎 | 理由 |
| --- | --- |
| `google` | fresh 实例可用（59 条，time_range 正常）；现网 CAPTCHA 由 5.1 健康度冷却自愈 |
| `google news` | fresh 60 条但**无发布日期**；中文覆盖最全 ⇒ 保留（时效靠 URL/页面回补，5.2 已有的处理） |
| `yandex` | fresh 90 条，本轮中文侧主力（time_range day/week 均 15 条） |
| `naver` | fresh 75 条（time_range day=1 / week=13，week 档可用）⇒ 保留 |
| `yahoo` | fresh 42 条（time_range day=7 / week=7）⇒ 保留 |
| `fynd` | fresh 35 条（不支持 time_range）⇒ 保留（英文侧） |
| `brave` | 本轮 fresh 仍 `Suspended: too many requests`（0 条、11ms 快速失败）⇒ 保留（成本可忽略，历史上偶尔可用） |
| `duckduckgo news` | 英文新闻时效最好（本轮 12 条 100% 带日期） |
| `reloado` / `zapmeta` / `quark` | 中文侧 0 贡献（179/196/18ms）但**英文侧有用**（inventory 轮：reloado 2 查询 77 条）；保留 |
| `privacywall` / `yep` | 被拒但**成本仅 8ms**（SearXNG 快速失败）；保留以等其恢复 |
| `resulthunter` | 本轮被限流（`too many requests`），历史上是稳定主力；保留 |

## 6. 验收设计（供拍板实施）

**前置**：实施必须**另开一轮、由用户确认**；先备份 `searxng/settings.yml`、记录当前容器状态。

**对照口径**（改动前 vs 改动后，同一批查询、背靠背）：

| 维度 | 指标 | 通过标准 |
| --- | --- | --- |
| 相关性 | 同一批 **20 条 2-9 查询**（`scripts/relevance.py --no-cache` + agent 初评口径） | 达标查询数 **≥18/20**（宽松判），且**中文侧缺陷项 Q2 改善**（≥4/5） |
| 卫生度 | 覆盖率均值 / 同站冗余 / 聚合页 / 脚本不匹配 / 空内容 / 独立站点（5.3 口径） | 覆盖率 **不下降 >5%**；同站冗余 / 聚合页 / 脚本不匹配 / 空内容 **不增加**；独立站点不下降 |
| 时效性 | 5.2 口径（`news_check`：带 7 日内日期比例） | **≥80%**（门槛不变） |
| 延迟 / 成功率 | 闸门下 @5 与 @10（`scripts/loadtest.py`，RPM=0） | 延迟退化 **≤10%**；成功率 ≥95%（@5）/≥90%（@10） |
| 上游健康 | `/metrics` 的 `upstream_requests_total{result="error"}` 与 `/health` 的 `engines.cooling` | error **不增加**；cooling 不长期新增 |

**不得引入新的不达标项**：任一维度不达标即回滚（见 §7）。

**本轮测得的基线数字（实施轮直接对比用）**：

| 基线项 | 值 | 来源 |
| --- | --- | --- |
| 现网 16 引擎 · 中文查询 结果/查询 | 60 条 | §4 `deployed16` |
| 现网 16 引擎 · 带日期候选 | 26 条 / 12 样本（≈2.2/查询） | 同上 |
| 现网 16 引擎 · 延迟 P50 / max | **1024ms** / 1444ms（另一轮 1085ms，另含 1 个 20s 异常） | §4 |
| 预测改动后（16−2+3）· 结果 / 带日期 | 97 条 / 314 条 | §4 `deployed16-2+3` |
| 预测改动后 · 延迟 P50 | **789ms（−23%）** | §4 |
| 预测改动后 · 扇出 | 17 引擎（净 +1，+6%） | §4 结构说明 |

## 7. 实施与回滚（另开一轮）

1. **备份**：`cp searxng/settings.yml searxng/settings.yml.bak-<日期>`（或直接在分支上改，随 git 回滚）。
2. **改动**：只改 `searxng/settings.yml` 的 `use_default_settings.engines.keep_only` 与 `engines:` 列表
   （移除/新增条目；新增 `inactive` 的引擎必须显式 `inactive: false`）。
3. **生效**：`docker compose restart searxng`（**只重启 SearXNG**，应用不用重启）→ 等 `/healthz` 200。
4. **观察窗口**：至少 **1 小时**（或 100 次查询）：盯 `/health` 的 `engines.cooling`、
   `/metrics` 的 `upstream_requests_total{result="error"}`、`scripts/loadtest.py` 的延迟与成功率。
5. **回滚**：恢复备份文件 → `docker compose restart searxng` → 复跑验收（应回到基线）。

## 8. 原始数据与复现

| 内容 | 路径 |
| --- | --- |
| 现网 8 引擎复测（§2） | `docs/reports/engine-selection-deployed-retest-20260928.json` |
| **全新实例 20 引擎复测（§3 权威数据）** | `docs/reports/engine-selection-probe20-retest-20260928.json` |
| 扇出/收益实测（§4） | `docs/reports/engine-selection-fanout-round2-20260928.json`（表）＋ `engine-selection-fanout-round1-20260928.json`（交叉验证） |
| 探针配置（20 引擎 keep_only） | `docs/reports/engine-selection-probe20-settings-20260928.yml` |
| 探针脚本（已收敛为正式工具） | `scripts/engine_probe.py`（`retest` = 逐引擎隔离复测；`compare` = 同实例交错 A/B；`sweep` = 现网默认集合扫描） |
| ~~旧版 16 引擎复测~~（覆盖不全，已作废，仅留痕） | `docs/reports/engine-selection-probe16-partial-20260928.json` |

> 说明：**证据一律随代码留痕在 `docs/reports/`**；`data/measure/engine-selection-20260928/` 是同一批文件的
> 工作副本（`data/` 被 `.gitignore` 忽略，不入库）。

复现（**探针容器，不动现网**）：

```bash
# 1) 探针配置：keep_only = 现网 16 + 4 候选 = 20 个引擎，全部 inactive:false（见 probe20-settings.yml）
# 2) 起探针容器（8899，与现网 8888 隔离）
docker run -d --name searx-probe -p 127.0.0.1:8899:8080 \
  -v <仓库>/docs/reports/engine-selection-probe20-settings-20260928.yml:/etc/searxng/settings.yml:ro \
  -e SEARXNG_SECRET=probe-secret searxng/searxng:latest
# 3) 逐引擎复测（20 引擎 × 6 中文查询 + 2 次 time_range）
.venv/bin/python scripts/engine_probe.py retest http://127.0.0.1:8899 --label fresh20 \
  --engines resulthunter yandex naver privacywall google zapmeta yahoo fynd reloado yep brave quark \
  "duckduckgo news" "sogou wechat" "google news" 360search "chinaso news" sina bilibili "tiger news" \
  > docs/reports/engine-selection-probe20-retest-20260928.json
# 4) 扇出/收益（同实例交错 A/B）
.venv/bin/python scripts/engine_probe.py compare http://127.0.0.1:8899 --rounds 2 \
  --a "resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark,\
duckduckgo news,sogou wechat,google news,360search" \
  --b "...,chinaso news,sina,bilibili"
# 5) 用完即删
docker rm -f searx-probe
```

**局限**：

- 每引擎 6 条中文查询（比盘点轮的 2 条更公平，但仍不是全量；**候选源的最终取舍要用 §6 的 2-9 + 卫生度验收**）。
- 引擎可用性受**出口 IP 与时间**影响：5.2/5.3 的"美国出口"结论已不能直接沿用（本轮出口 = Singapore）；
  本报告只对"此刻"负责，换出口/换机房需复测。
- 探针是**全新实例（无历史处罚盒）**，与现网冷却状态不同 —— 这正是本报告要区分的点。
- §4 每档 n=12，**P95 只作趋势参考**；`deployed16` 另在另一轮出现 1 个 20s 级异常样本（1/24）。
- 扇出/延迟是**探针实例直连**数字，**不含**本服务的闸门/缓存/融合开销；实施轮必须按 §6 在闸门下重测。

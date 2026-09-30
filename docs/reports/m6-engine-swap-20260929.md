# M6 引擎集合优化 阶段 2：替换实施与验收（2026-09-29）

> **范围**：只改 `searxng/settings.yml`（单文件可回滚），**未动 `src/`**、未改闸门参数、未改排序逻辑、
> 未加 `sina` / `bilibili`。分支 `fix/m6-engine-swap-20260928`。
> 前置：阶段 1 报告 `docs/reports/m6-engine-selection-20260928.md`（现网复测 + 候选评估 + 替换方案）。

## 0. 结论摘要

**改了哪些引擎**（`searxng/settings.yml` 的 `keep_only` 与 `engines` 两处同步改动）：

| 动作 | 引擎 | 依据（阶段 1 实测） |
| --- | --- | --- |
| **移除** | `360search` | 6 条中文本地化查询 **0 结果**，且**每次空转 996ms**（不是快速失败）——它一个人把「默认集合查询」的 P50 抬到 1s 级 |
| **移除** | `sogou wechat` | 同一批查询 **0 结果**（150ms 空转）；5.2 定它为首选中文新闻源时测的是**美国出口**，现出口（新加坡）已失效 |
| **新增** | `chinaso news` | 探针实测 24 条、**100% 带发布日期**（286ms）；5.3 曾因本镜像注册失败而排除，2026-09-28 复核确认可注册（需显式 `inactive: false`） |
| **新增** | `tiger news` | 60 条、**100% 带发布日期**（250ms） |
| **保留（不删）** | `resulthunter` / `privacywall` / `yep` / `brave` / `quark` | 都是 0 结果但 **7-18ms 快速失败**，成本可忽略 —— 「0 结果」不是删除依据，**要看它是否占延迟** |

**硬门槛结果（5 项：4 通过 / 1 未通过）**：

| # | 硬门槛 | 结果 | 数字（改动后 vs 改动前，同一实例交错） |
| --- | --- | --- | --- |
| 1 | 结果数中位数不降 | ✅ | **54 → 54**（合计 623 → 628） |
| 2 | 延迟 P50/P95 退化 ≤10% | ✅ | P50 **927 → 704ms（−24%）**、P95 **1381 → 1223ms（−11%）** |
| 3 | upstream error 不高于基线、无新增 unresponsive | ✅ | 两次都是 **0 错误**；unresponsive 集合完全相同 `{brave, privacywall, resulthunter, yep}`，**无新增** |
| 4 | news + `time_range=day` 的 7 日内日期比例 ≥80% | ❌ | 改动前 **25/40 = 62%** → 改动后 **26/40 = 65%** ⇒ **未达标，且改动前就已未达标（非本轮引入）** |
| 5 | 20 条 2-9 达标占比 ≥90% | ✅ | **19/20 = 95%**（平均相关 4.70）；未达标仅 Q16（iPhone 17 Pro：2 条型号不符 + 1 条非 Pro 机型） |

**本轮最重要的发现（必须上报）**：

1. **产品路径（应用进程）看不到这次替换的效果**。`searxng/settings.yml` 决定的是「SearXNG 注册表里有哪些引擎」，
   而应用调用时**总是显式传 `engines=`**（`UTF8SEARCH_DEFAULT_ENGINES` 12 个 / `UTF8SEARCH_NEWS_ENGINES` 3 个，见 `.env`），
   这两个列表本轮按约束**没有改**。所以：新增的 `chinaso news` / `tiger news` **不会进入应用的检索路径**，
   被移除的两个引擎本来也不在应用的通用列表里（`360search` 不在 12 个里）。**本轮对产品路径是事实上的 no-op**，
   效果只体现在「SearXNG 默认集合查询」和「未来的配置空间」上。
   → 建议下一轮把 `.env` 的两个列表同步（见 §5.1），**需要你批准**（本轮非目标）。
2. **news 时效门槛（≥80%）在本轮之前就未达标**：改动前 62%、改动后 65%，
   把 `chinaso news`/`tiger news` 加进**新闻引擎列表**也不改善（仍 65%）——原因是这两个引擎**不支持 `time_range`**
   （探测：day/week 档均返回 0 条），而该门槛固定用 `time_range=day`。根因是新闻路径实际只有
   `duckduckgo news`（纯中文查询 0 条）+ `google news`（不给发布日期，靠 URL/页面回补）。

## 1. 改动内容

```diff
 use_default_settings.engines.keep_only:
     - "duckduckgo news"
-    - "sogou wechat"
     - "google news"
+    # 中文补充源（2026-09-28 实测采用，替换已失效的 360search / sogou wechat）
+    - "chinaso news"
+    - "tiger news"
-    - 360search

 engines:
-  - name: "sogou wechat"
-    disabled: false
-  - name: 360search
-    disabled: false
+  # inactive 引擎必须显式覆盖，否则 keep_only 也不会把它注册进来（5.3 踩过的坑）
+  - name: "chinaso news"
+    disabled: false
+    inactive: false
+  - name: "tiger news"
+    disabled: false
+    inactive: false
```

同时更新了文件头注释块：新增「2026-09-28 引擎集合替换」小节（每个动作的证据与理由），
并把 `chinaso news` 从「已实测剔除」名单里移出（那份结论是 5.3 时期的）。

**生效方式**：`docker compose restart searxng`（只重启 SearXNG，应用不用重启）。
重启后 `/config` 校验：**16 个引擎**，`360search`/`sogou wechat` 已消失、`chinaso news`/`tiger news` 已注册。

## 2. 验收协议（交错 A/B，现网新加坡出口）

- **A = 改动前**（`git show HEAD:searxng/settings.yml` 还原）、**B = 改动后**；每侧都 `docker compose restart searxng`
  后再测，保证两侧的实例状态对等（处罚盒被清空）。
- 序列：**A1 →（改）→ B1 →（还原）→ A2 →（改）→ B2**，最终停在 B。A1 是「长跑实例」的真实线上状态（另有参考价值）。
- 两把尺子：
  1. **`sweep`（默认集合）**：不传 `engines`，测 SearXNG 的 `keep_only` 集合——**这才是本次改动的直接对象**；
  2. **`compare`（显式列表）**：同一实例内逐条交错跑两套列表，用于量化「两个新中文源对显式引擎列表的贡献」
     （即 §5.1 建议方案的效果预估）。
- 工具：`scripts/engine_probe.py`（本阶段新增的正式工具，`retest` / `sweep` / `compare`）。

## 3. 结果

### 3.1 默认集合 A/B（6 条中文本地化查询 × 2 轮 = 每侧 12 样本）

| 轮次 | 引擎集合 | 结果中位 | 合计 | 带日期 | 延迟 P50 | P90 | P95 | max | 错误 | unresponsive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1（长跑实例） | 16（旧） | 59 | 707 | 2 | 1887ms | 2221 | 2378 | 2558 | 0 | brave12 google12 privacywall12 yep12 resulthunter1 |
| B1（重启后） | 16（新） | 54 | 610 | 2 | 857ms | 1101 | 1289 | 1506 | 0 | brave12 privacywall12 resulthunter12 yep12 |
| **A2（重启后）** | 16（旧） | **54** | **623** | 2 | **927ms** | 1040 | **1381** | 1796 | 0 | brave12 privacywall12 resulthunter12 yep12 |
| **B2（重启后）** | 16（新） | **54** | **628** | 2 | **704ms** | 1049 | **1223** | 1432 | 0 | brave12 privacywall12 resulthunter12 yep12 |

**判定用的对等比较是 A2 vs B2**（都在重启后、相隔约 30 秒）：
结果中位数 **54 → 54（不降）**、总计 623 → 628（+0.8%）、P50 **−24%**、P95 **−11%**、错误 0/0、**unresponsive 集合完全一致**。

> A1（1887ms）比 A2（927ms）慢一倍，且多出 `google` 12/12 不可用 —— 那是**长跑实例累计触发的 CAPTCHA 处罚盒**，
> 重启即消失。这印证了 5.1 的判断：引擎健康必须看「重启后的对等比较」，不能拿长跑实例的数字当基线。

### 3.2 显式引擎列表对比（量化两个新中文源）

同一实例（B 状态，16 个引擎都可用作显式列表）内逐条交错：

| 组 | 引擎列表 | 结果中位 | 合计 | **带日期** | 延迟 P50 | P90 | P95 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A（应用当前通用列表） | 12 个（`UTF8SEARCH_DEFAULT_ENGINES`） | 54 | 1206 | **4** | 963ms | 1018 | 1083 | 1105ms |
| B（+ 两个新中文源） | 14 个 | **68（+26%）** | **1541（+28%）** | **340（×85）** | **689ms（−28%）** | 991 | 1050（−3%） | **7724ms（1/24 样本）** |

（每侧 6 条中文查询 × 4 轮 = 24 样本；两轮的 12 样本版本见证据文件，P95 波动较大，n=24 更可信。）

**读法**：把两个新中文源加进**显式列表**后，结果数 +28%、**带发布日期候选从 4 条涨到 340 条**、P50 反而更快（−28%）、
P95 基本持平（−3%），但**尾部出现 1 个 7.7s 样本**（`国产 大模型 产业 动态 2026`，24 个样本里 1 个）。
这条曲线说明：新引擎对「显式列表」有实质召回收益，代价是**偶发尾延迟**（上游新闻源抖动），
应用侧还有 `search_timeout_limit`（默认 2.5s）兜底，实际影响要用 §5.1 的方案单独验一轮。

### 3.3 上游健康（upstream error / unresponsive / cooling）

- **错误**：4 个轮次全部 `0` 个非 200 响应。
- **unresponsive**：A2/B2 完全一致（`brave` / `privacywall` / `resulthunter` / `yep`，各 12/12 次）；
  B 侧**没有新增**任何不可用引擎；`google` 在 B 侧反而是**可用**的（12/12 有结果）。
- **应用 `/health`**：`engines.cooling = []`（**无新增长期冷却**），`searxng: ok`。
- 说明：SearXNG 自带的 `/metrics`（OpenMetrics，basic auth）**取不到样本行**（只有 HELP/TYPE），
  应用容器的镜像也**早于 M5**（无 `/metrics` 端点，`app.routes` 只有 `/search`/`/extract`/`/health`），
  因此本轮的「上游 error」以**响应体里的 `unresponsive_engines` + 应用 /health** 为准（逐条明细在 JSON 证据里）。
  → 部署镜像落后于 main 这一条记入遗留（见 §7）。

### 3.4 news 时效（`topic=news` + `time_range=day`，8 条中英新闻查询）

| 状态 | 7 日内日期比例 | 结论 |
| --- | --- | --- |
| **改动前（A）** | **25/40 = 62%** | ❌ 未达 80% |
| **改动后（B，现状）** | **26/40 = 65%** | ❌ 未达 80% |
| 改动后 + 把新引擎加进新闻列表（预估） | 26/40 = 65% | ❌ 未达 80%（仍不改善） |

**归因**：新闻路径固定 `time_range=day`，而 `chinaso news` / `tiger news` **不支持 `time_range`**（day/week 档返回 0 条，阶段 1 实测），
所以新增它们**修不了这条门槛**。真正拖后腿的查询：`最近一周 AI 行业动态`（1/5）、`美国 关税 最新政策`（0/5）、
`EU AI Act latest developments`（3/5）—— 都是纯中文/无日期源（`google news` 不给日期，靠 URL/页面回补）。
另注：该指标单跑漂移很大（M5 报告记录过 80/85/95/100% 的波动），单次运行只作参考。

### 3.5 2-9 相关性（20 条，agent 初评 + 同一判分口径）

- 采集：`scripts/relevance.py --depth basic --no-cache`（走本机 SearXNG，禁用缓存），**改动后**跑。
- 判分：**校准集先行**（6 条历史 ❌ 类条目 —— 京东 `iPhone8 参数`、京东 `苹果8x参数`、学校 COPPA 声明页、
  npm `nocache` 包、Homebrew `python@3.13` 公式页、砺算科技 7G100 —— **全部判 0，校准通过**），
  再按三档（明显/勉强/不相关，前两档计 1）盲评；判据①「聚合形态本身不等于不相关，只有『只是导航』才判 0」、
  判据②「判切题不判时新」。
- **结果：19/20 = 95%（门槛 90%）→ 通过**；平均相关 4.70。
  未达标：**Q16 iPhone 17 Pro 价格 参数（3/5）** —— 2 条京东 `iPhone8/苹果8x` 参数页（型号不符）+ 1 条 ZOL `iPhone 17 256GB`页（**非 Pro 机型**）。
- **敏感性披露**：宽松判（勉强相关=1）**19/20 = 95% 通过**；严格判（勉强相关=0）**16/20 = 80% 不通过** ——
  结论同样对「汇总/栏目形态是否算相关」高度敏感，口径沿用 2-9 已确立的判据。
- **归因**：改动前基线为 18/20（2026-09-28 同口径）。**这 1 条差异不能归给本轮替换** ——
  应用的通用引擎列表没有变化（§0 发现 1），属于上游结果漂移。

### 3.6 卫生度（**只报数，不作门槛** —— 聚合页口径尚未对齐，见 `docs/04` §8）

| 状态 | 覆盖率均值 | 独立站点均值 | 同站冗余 | 聚合页 | 脚本不匹配 | 空内容 |
| --- | --- | --- | --- | --- | --- | --- |
| 改动前（A，本次匹配测量） | 0.783 | 4.70 | 0 | 0 | 0 | 1 |
| **改动后（B）** | **0.755** | **4.55** | 0 | 0 | 0 | 1 |
| 参考：2026-09-28 基线 | 0.838 | 4.70 | 0 | 0 | 0 | 0 |

覆盖率 −3.6%、独立站点 −3.2%：与「应用路径未变」一致，属上游漂移（同一批查询两次采集本身就有波动）。

## 4. 硬门槛逐条判定（汇总）

| # | 门槛 | 判定 | 证据 |
| --- | --- | --- | --- |
| 1 | 结果数中位数不降 | ✅ 通过 | A2 54 → B2 54；合计 623 → 628 |
| 2 | 延迟 P50/P95 退化 ≤10% | ✅ 通过 | P50 927 → 704（−24%）、P95 1381 → 1223（−11%） |
| 3 | upstream error 不高于基线、无新增 unresponsive | ✅ 通过 | 0 错误；unresponsive 集合一致；`/health` cooling 空 |
| 4 | news + day 的 7 日内比例 ≥80% | ❌ **未通过** | 62% → 65%（**改动前已未达标**，且新引擎不支持 `time_range`，加进去也无改善） |
| 5 | 20 条 2-9 达标 ≥90% | ✅ 通过 | 19/20 = 95%（严格判 16/20 = 80%，敏感性已披露） |

**结论：未全过硬门槛** —— 唯一未通过项是 news 时效（既有问题，本轮不引入也不恶化），
且本轮替换对**产品路径是 no-op**（§0 发现 1），需要先决定 `.env` 是否同步，这条门槛才谈得上改善。

## 5. 关键发现与建议

### 5.1 建议：把两个新中文源接进产品路径（**本轮非目标，待批准**）

应用的引擎列表在 `.env`（服务器本地配置，不在 git 里），当前值：

```
UTF8SEARCH_DEFAULT_ENGINES=resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark
   # 12 个通用引擎（不含 360search，也没有任何 news 类目引擎）
UTF8SEARCH_NEWS_ENGINES=duckduckgo news,sogou wechat,google news
   # sogou wechat 已在 SearXNG 里移除 ⇒ 这一项现在是「悬空引用」（SearXNG 会静默丢弃它）
```

> 另注：`src/utf8_search/config.py` 里 `default_engines` 的**代码默认值**仍写着 `360search`
> （服务器被 `.env` 覆盖，所以现网不受影响）。改它属于 `src/` 改动，列入遗留。

建议改法（两者可分开评估）：

1. **必做（配置卫生）**：`UTF8SEARCH_NEWS_ENGINES` 去掉 `sogou wechat`（它已不在注册表里）。
2. **召回**：`UTF8SEARCH_NEWS_ENGINES=duckduckgo news,google news,chinaso news,tiger news`
   —— 对 `time_range` 空的新闻查询有用，**但不修 §3.4 的 day 档门槛**（那两个引擎不支持 `time_range`）。
3. **通用召回**：往 `UTF8SEARCH_DEFAULT_ENGINES` 追加 `chinaso news,tiger news`
   —— 实测收益：结果 +28%、带日期候选 ×85、P50 −28%、P95 持平，**代价是偶发 7.7s 尾延迟（1/24 样本）**。
   建议若要上，单独开一轮按 §6 口径复验（含 `search_timeout_limit` 下的端到端 P95）。
4. 修 news 时效门槛的更对症方向：找一个**支持 `time_range` 的中文新闻源**（阶段 1 的候选里只有 `bilibili` 支持且带日期，
   但它是视频站、会灌满候选池）或调大日期回补预算/页数；`sina` 支持 `time_range` 但**不带日期**，对时效无帮助。

### 5.2 其他发现

- **`sweep`（不传 `engines`）只跑通用类目**：`chinaso news`/`tiger news`/`duckduckgo news`/`google news`
  都是 news 类目引擎，**默认集合查询根本不会调用它们**（逐条来源只出现 fynd/naver/yahoo/yandex/resulthunter/google）。
  所以「在默认集合上验新增新闻引擎」是验不出来的——必须用显式列表（§3.2）或 `categories=news`。
- **部署镜像落后**：`utf8-search-app` 容器没有 `/metrics`（M5 新增），说明现网应用镜像早于 M5 合并点。
  本轮不受影响（只改 SearXNG 配置），但「上游错误率」类验收目前只能靠 `unresponsive_engines` 间接观测。

## 6. 回滚步骤

```bash
# 方式一（推荐，随 git）：把 searxng/settings.yml 回到替换前
git checkout <替换前的 commit> -- searxng/settings.yml
docker compose restart searxng

# 方式二（不改 git）：用备份文件覆盖后重启
cp searxng/settings.yml.bak-20260929 searxng/settings.yml
docker compose restart searxng

# 校验（应回到 16 个引擎且含 360search / sogou wechat）
curl -s http://127.0.0.1:8888/config | python -c "import json,sys; print(sorted(e['name'] for e in json.load(sys.stdin)['engines']))"

# 回滚后复跑本报告的验收命令（见 §8），应回到 A 侧数字
```

本轮替换**只影响 SearXNG 的引擎注册表**，应用无需重启；回滚同样只需重启 SearXNG。

## 7. 非目标与遗留（写入 `docs/04` §8）

- `.env` 的引擎列表同步（§5.1）——**需用户批准**，不在本轮。
- `src/utf8_search/config.py` 的 `default_engines` 代码默认值仍含已被移除的 `360search`（现网被 `.env` 覆盖，无实际影响）。
- news 时效门槛（≥80%）未达标，根因与可选修法见 §3.4 / §5.1。
- `sina` / `bilibili` 本轮不加（前者无日期、后者单站灌满），后续条件见阶段 1 报告 §5.2。
- 部署镜像落后于 main（缺 M5 `/metrics`），建议下次部署时一并更新。

## 8. 证据与复现

| 内容 | 路径 |
| --- | --- |
| 默认集合 A/B：A1 / A2 / B1 / B2 逐条明细 | `docs/reports/engine-swap-sweep-{A1,A2,B1,B2}-20260929.json` |
| 显式列表对比（n=12 / n=24） | `docs/reports/engine-swap-applist-compare-n{12,24}-20260929.json` |
| news 时效：改动前 / 改动后 / 加新引擎预估 | `docs/reports/engine-swap-news-{before,after,forecast}-20260929.md` |
| 2-9：改动后明细 / 速览 / 打分 / 判定 | `docs/reports/m2-9-after-engine-swap-20260929{,-brief,-scores,-scores-judge}.md` / `.csv` |
| 2-9：改动前明细（本次匹配测量，未判分） | `docs/reports/m2-9-before-engine-swap-20260929{,-brief}.md` |
| 卫生度 JSON（改动前 / 改动后） | `docs/reports/hygiene-{before,after}-swap.json` |

复现命令：

```bash
# 默认集合 A/B（改配置 + 重启前后各跑一次，--rounds 2）
.venv/bin/python scripts/engine_probe.py sweep http://127.0.0.1:8888 --label A2 --rounds 2 --out .../A2.json
docker compose restart searxng
.venv/bin/python scripts/engine_probe.py sweep http://127.0.0.1:8888 --label B2 --rounds 2 --out .../B2.json

# 显式列表对比（两个列表里的引擎必须都已注册）
.venv/bin/python scripts/engine_probe.py compare http://127.0.0.1:8888 --rounds 4 --a "<12 个通用引擎>" --b "<12 个 + chinaso news,tiger news>"

# news 时效 / 2-9（走应用流水线，禁用缓存）
.venv/bin/python scripts/news_check.py --no-cache --time-range day --out .../news-after.md
.venv/bin/python scripts/relevance.py --depth basic --no-cache --out docs/reports/m2-9-after-engine-swap-20260929.md --hygiene-out .../hygiene-after-swap.json
.venv/bin/python scripts/relevance.py --score-file docs/reports/m2-9-after-engine-swap-20260929-scores.csv
```

**局限**：每侧 12-24 个样本，P95 只作趋势；上游（免费引擎）分钟级漂移，A/B 只能靠交错/重启对等来抵消；
news 时效与 2-9 的采集各只跑了一次（未做配对），因此这两项的数字应与漂移幅度一起读。

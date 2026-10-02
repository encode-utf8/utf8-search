# 引擎列表落地到产品路径（.env）与复验（2026-09-30）
<!-- refs-policy: cleaned-2026-10-02 -->
> ⚠️ 引用提示：本文提到的部分过程明细已在 2026-10-02 仓库瘦身中清理（清单：`docs/reports/cleaned-files-20261002.txt`）；这些路径不是现存文件，需要时用 `git log --diff-filter=D -- <path>` 取回；规则见 `docs/reports/README.md`。

> **本轮只动部署与配置**：`src/` 未改、闸门参数未改、`searxng/settings.yml` 未动、人工项 3-9 未动。
> 改动面：服务器 `.env`（引擎列表）、仓库 `docker-compose.yml`（**接线缺口的最小修复**）、仓库 `.env.example`（口径说明）、
> 报告与 checklist。分支 `chore/engine-list-env-20260930`。

## 0. 摘要（先看结论）

| 目标 | 结果 |
| --- | --- |
| 把 `chinaso news` / `tiger news` 加进新闻引擎列表，移除悬空引用 `sogou wechat` | ✅ 已落地并**真正注入到容器**（见 §1 的关键发现） |
| 复验：结果中位数 / 带日期候选 / P50 / P95 / 尾延迟 | ⚠️ 结果中位与延迟达标（A 63→B 64；P50 730→741ms；P95 2371→1938ms）；**带日期候选 ×85 的预测未兑现**（本轮 ×6.3，且 7.7s 尾延迟**未复现**） |
| 复验：2-9 达标率 | ❌ **16/20 = 80%，低于 90% 门槛**（未达标 Q1/Q2/Q6/Q16）——上游结果明显漂移，且 `google` 当天在 CAPTCHA 处罚盒里 |
| 复验：**news 时效门槛（time_range=day，7 日内 ≥80%）= 本轮主目标** | ❌ **11/40 = 28%**，未达标；已拆解到「哪条查询 / 哪条路径 / 有无日期」（§4），**不是参数问题** |
| `/metrics` upstream/rejected | ✅ 容器 HTTP 路径 3 次请求全部 200、`requests_total{ok}=3`、**`rejected_total` 为空（0）**、无 error |
| `google news` 是否仍在 CAPTCHA | ⚠️ **仍在**（`Suspended: CAPTCHA`）⇒ 基线受污染，已做变体对照 + 冷却后补测（§3.5/§5） |

**本轮最重要的发现（容器从未收到 `.env`）**：现网 app 容器只被注入 4 个环境变量
（`SEARXNG_URL` / `API_KEYS` / `RATE_LIMIT_RPM` / `MCP_ALLOWED_HOSTS`），镜像里也没有 `.env`，
所以**其余约 40 项 `.env` 设置（含两个引擎列表）从来没有在容器里生效过** —— 容器一直在用 `config.py` 的代码默认值
（其 `default_engines` 还含已删除的 `360search`，`news_engines` 还含 `sogou wechat`）。
本轮按「引擎列表必须落地」的目标做了**最小接线**（compose 显式注入两个引擎列表），并把这个缺口记入遗留。

## 1. 改动

### 1.1 服务器 `.env`（仓库外，已备份）

```diff
-UTF8SEARCH_NEWS_ENGINES=duckduckgo news,sogou wechat,google news
+UTF8SEARCH_NEWS_ENGINES=duckduckgo news,google news,chinaso news,tiger news
 （上方注释同步更新：sogou wechat 在当前出口 0 结果且已从 SearXNG 删除；新增两个中文源的实测数字）
```

- 备份：`/root/deploy-backups-20260929/env.20260930-pre-engine-list.bak`（与改前 `.env` md5 一致 `f6bf9829…`，
  保留 09-29 那份 `env.bak`）；`UTF8SEARCH_DEFAULT_ENGINES` 本轮**未改**（仍是 12 个通用引擎）。

### 1.2 仓库 `docker-compose.yml`（接线缺口的最小修复）

```diff
     environment:
       - UTF8SEARCH_SEARXNG_URL=http://searxng:8080
       - UTF8SEARCH_API_KEYS=${UTF8SEARCH_API_KEYS:-}
       - UTF8SEARCH_RATE_LIMIT_RPM=${UTF8SEARCH_RATE_LIMIT_RPM:-60}
       - UTF8SEARCH_MCP_ALLOWED_HOSTS=${UTF8SEARCH_MCP_ALLOWED_HOSTS:-}
+      # 引擎列表必须显式注入（容器里没有 .env：镜像不打包、compose 也没挂载）
+      - UTF8SEARCH_DEFAULT_ENGINES=${UTF8SEARCH_DEFAULT_ENGINES:-resulthunter,yandex,...,quark}
+      - UTF8SEARCH_NEWS_ENGINES=${UTF8SEARCH_NEWS_ENGINES:-duckduckgo news,google news,chinaso news,tiger news}
```

> 为什么必须改 compose（而不是只改 `.env`）：`Settings` 的 `env_file=".env"` 是相对**工作目录**解析的，
> 容器工作目录 `/app` 下没有 `.env`；compose 的 `.env` 只用于**变量替换**，不会自动注入进容器。
> 只改 `.env` 再 `docker compose up -d --no-deps utf8-search`，容器里的值仍等于代码默认值
> （实测：重建后 `/health` 的 `active` 仍是 `…,360search,duckduckgo news,sogou wechat,google news`）。

### 1.3 仓库 `.env.example`

同步引擎列表口径 + 新增一段说明：**列表里的引擎名必须同时存在于 `searxng/settings.yml` 的 `keep_only` 与 `engines`**，
否则 SearXNG 静默丢弃（少数无效仍跑其余；全部无效会回退到默认引擎集合）。

### 1.4 生效方式

```bash
docker compose up -d --no-deps utf8-search     # env 变化必须 recreate（不能只 restart）
docker inspect utf8-search-app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep ENGINES
# UTF8SEARCH_DEFAULT_ENGINES=resulthunter,yandex,naver,privacywall,google,zapmeta,yahoo,fynd,reloado,yep,brave,quark
# UTF8SEARCH_NEWS_ENGINES=duckduckgo news,google news,chinaso news,tiger news
curl -s http://127.0.0.1:8000/health   # active 里已含 chinaso news / tiger news，且不再有 360search / sogou wechat
```

`searxng` / `caddy` 全程未重启未重建。

## 2. 结果数与日期候选（对照上一轮 ×85 预测）

### 2.1 通用引擎列表（与上一轮同法复跑，6 条中文查询 × 4 轮 = 24 样本）

| 组 | 引擎列表 | 结果中位 | 合计 | **带日期** | P50 | P90 | P95 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 12 个通用引擎 | 63 | 1493 | **18** | 730ms | 2211ms | 2371ms | 3869ms |
| B | + `chinaso news` `tiger news` | 64 | 1519 | **114（×6.3）** | 741ms | 1804ms | 1938ms | 2977ms |

**对照上一轮**：上一轮同法测得 A 带日期 4 条 → B 340 条（**×85**）、B 的 max 出现 **7.7s 尾延迟**。
本轮：A 18 → B 114（**×6.3**），**7.7s 尾延迟未复现**（B max 2.98s）。

**结论（如实写）**：带日期候选的**方向性收益仍在**（+96 条，且 A 侧基线本身也从 4 涨到 18），
但**×85 这个幅度不可复现**——两个工作日内同一测量相差 3 倍以上，说明 `chinaso news` 的返回量/延迟本身在漂移
（本轮诊断里它还出现过 `server API error`）。7.7s 尾延迟在 24 个样本里没再出现，**不是稳定触发**，
但样本量也不足以断言它不存在（上一轮是 24 个样本里 1 个）。

### 2.2 新闻引擎列表（8 条 news_check 查询，SearXNG 直连，无 time_range）

| 组 | 引擎列表 | 结果中位 | 合计 | 带日期 |
| --- | --- | --- | --- | --- |
| A | `duckduckgo news,google news`（改动前的等效集合） | 12 | 104 | 104 |
| B | 上面 + `chinaso news` `tiger news` | **19** | **138（+33%）** | **138** |

逐条看增益集中在中文查询（`美国 关税 最新政策` 4→14、`台风…` 26→36、`新能源汽车补贴政策` 0→10）；
两条中文查询（`2026年9月国内外重大新闻`、`最近一周AI行业动态`）**两个列表都返回 0** —— 这两条会走兜底源（见 §4）。

## 3. 门槛复验

### 3.1 2-9 相关性（20 条，agent 初评 + 校准集）

- 校准集（本次样本里的历史 ❌ 同类条目）**9 条全部判 0**（名侦探柯南动漫页、StackOverflow regex 页、
  京东 `iPhone8/苹果8x` 参数页 ×2、学校 COPPA 声明页、pandas 用法页、Homebrew 公式页、机场迎新页、日本开运日历页）⇒ 校准通过。
- **结果：16/20 = 80%，低于 90% 门槛 → 不通过**（平均相关 4.50）。
  未达标：**Q1（3/5，两条无关页）**、**Q2（3/5，动漫页 + regex 页）**、**Q6（3/5，pandas/公式页）**、**Q16（2/5，两条京东旧型号页）**。
- 敏感性：宽松判 16/20 = 80%；**严格判（勉强相关=0）14/20 = 70%**。
- **归因**：通用引擎列表本轮**没有改动**（12 个引擎与上一轮相同），所以这个下降是**上游漂移**，
  且当天 `google` 在 SearXNG 侧是 `Suspended: CAPTCHA`（§2.1 的 unresponsive 里 24/24 次），
  通用路径实际少了一个主力引擎。对比：09-29 同口径为 20/20、09-29（换引擎前）19/20。

### 3.2 卫生度（只报数，不作门槛）

| 指标 | 本轮 | 09-29 参照 |
| --- | --- | --- |
| 覆盖率均值 | 0.735 | 0.791 |
| 独立站点均值 | 4.75 | 4.55 |
| 同站冗余 / 聚合页 / 脚本不匹配 / 空内容 | 0 / 0 / 0 / **3** | 0 / 0 / 0 / 0 |

### 3.3 `/metrics`（容器 HTTP 路径）

容器在 10:35 由 env 变更**重建**，计数器从 0 起；随后经 HTTP 打 3 次搜索：
`utf8search_upstream_requests_total{result="ok"} = 3`、**`utf8search_upstream_rejected_total` 无任何样本（0 次拒绝）**、
无 `result="error"`。⇒ 引擎列表落地**没有引入错误、没有触发闸门拒绝**。

（脚本类复验 `relevance.py` / `news_check.py` / `engine_probe.py` 跑在宿主机进程内，不经过容器，因此不计入容器计数。）

### 3.4 尾延迟专项

- 上一轮 24 样本里出现 1 个 **7.7s**（查询 `国产 大模型 产业 动态 2026`）；本轮同法 24 样本 **未复现**（max 2.98s）。
- 触发条件无法确认：上一轮那条是 B 组（含 `chinaso news`/`sina`/`bilibili`）的偶发样本，
  本轮 B 组换成 `chinaso news`/`tiger news` 后未再出现 ⇒ 更像是**上游抖动**而非稳定触发；
  样本量（各 24）不足以给出频率上界。

### 3.5 `google news` 处罚盒状态与「污染」判定

- 现状：`google news` 与 `google` 在 SearXNG 侧都是 `Suspended: CAPTCHA`（问上游直接返回该状态；本轮多张证据里都有）。
- **变体对照（用来判断污染影响）**：把 `google news` 从新闻列表里拿掉重跑同一门槛 → **仍然是 11/40 = 28%，与含它完全一致**
  ⇒ `google news` 当前**贡献 0**，28% 是「当前真实状态」，不是被它拖累出来的假象；
  但「含 google news 的基线」确实**无法反映它健康时的水平**，所以按你的要求做**冷却后补测**（见 §5）。

## 4. news 时效门槛归因（逐条查询 × 路径 × 日期）

方法：`data/measure/engine-list-env-20260930/news_decompose.py`（进程内流水线，`topic=news`、`time_range=day`、
`max_results=5`、禁缓存），逐条打印**结果的来源引擎**与日期新鲜度。合计 **11/40 = 28%**（门槛 80%）。

| # | 查询 | 结果来自哪条路径 | 带日期情况 | 新鲜 |
| --- | --- | --- | --- | --- |
| 1 | 2026年9月 国内外重大新闻 | 新闻主源 **0 条**（`chinaso news` server API error + `google news` CAPTCHA）→ **兜底源（Bing）** | 5/5 **无日期** | 0/5 |
| 2 | 最近一周 AI 行业动态 | 同上（主源 0 条）→ **兜底源（Bing）** | 5/5 **无日期**（且结果离题：沃尔玛滤水器/世界杯页面） | 0/5 |
| 3 | 台风 最新消息 路径 | **新闻主源**（`chinaso news` 2 条 + `duckduckgo news` 3 条） | 5/5 有日期，但 8/37/371/80/29 天 | 0/5 |
| 4 | 美国 关税 最新政策 | **新闻主源**（`chinaso news` 2 + `duckduckgo news` 3） | 5/5 有日期，161/526/21/18/217 天 | 0/5 |
| 5 | latest news semiconductor… | **新闻主源**（全 `duckduckgo news`） | 5/5 有日期：6.6/1452/13/83/7 天 | **1/5** |
| 6 | OpenAI latest news | **新闻主源**（全 `duckduckgo news`） | 5/5 有日期，全部 ≤0.5 天 | **5/5** |
| 7 | 2026年 新能源汽车 补贴政策 | **新闻主源**（全 `chinaso news`） | 5/5 有日期，98/85/60/94/104 天 | 0/5 |
| 8 | EU AI Act latest developments | **新闻主源**（全 `duckduckgo news`） | 5/5 有日期，全部 ≤7 天 | **5/5** |

**结论（不盲调参数的依据）**：

1. **英文查询靠 `duckduckgo news` 达标**（第 6/8 条 100%，第 5 条 20%）；
2. **中文查询全线 0 新鲜**：`chinaso news` 能返回带日期的中文结果，但**索引偏旧**（本轮这几条是 18-217 天），
   `tiger news` 本轮**一条都没返回**，`google news` 在处罚盒里（且它本身也不给发布日期）；
   `sogou wechat`（唯一在 2026-09-24 美国出口测到「8/8 查询各 10 条、100% 带日期」的中文新闻源）已在当前出口失效并被移除。
3. **「把新源加进 `news_general_engine_list`（带 time_range 透传的那条路）」这条路走不通**：
   该路会把 `time_range=day` 透传给通用引擎，而 `chinaso news`/`tiger news` **不支持 `time_range`**
   （阶段 1 实测 day/week 档均返回 0 条）⇒ 加进去只会返回 0，不会增加新鲜候选。
   另外这两条中文查询（1/2）之所以走兜底源，是因为新闻主源直接 0 条，属于「主源无中文新鲜源」的同一个病根。
4. 因此**本轮不动参数**：门槛不达标的原因是**上游没有可用的中文新鲜新闻源**，不是排序/窗口/预算调参能解决的。

## 5. 冷却后补测（google news）

- 首测 2026-09-30 10:30、复测 10:39，状态均为 `Suspended: CAPTCHA`；变体对照已证明它当前贡献 0（§3.5）。
- **SearXNG 日志给出的关键事实**：`google` / `google news` 的最后一次上游 CAPTCHA 事件是
  **2026-09-30 02:31:43 / 02:34:26**，异常里写明 `SearxEngineCaptchaException … (suspended_time=3600)`，
  而 **8 小时后（10:39）引擎仍报 `Suspended: CAPTCHA`** ⇒ 处罚状态**没有自然过期**
  （期间只有探测、没有新的 CAPTCHA 日志，疑似 SearXNG 进程内状态未清理）。
- **补测结论（如实写）**：本轮的观察窗口内**无法完成**「冷却后补测」——按 `suspended_time=3600` 早该恢复却仍被挂起。
  可行路径两条，都需要你决定：
  1. **重启 SearXNG 立即清除处罚盒**（`docker compose restart searxng`，约 10 秒）——本轮约束是「searxng 不动」，
     **未执行**；批准后 1 分钟内即可补测：
     ```bash
     docker compose restart searxng && sleep 15
     .venv/bin/python scripts/news_check.py --no-cache --time-range day --out data/measure/engine-list-env-20260930/news-after-google-recovery.md
     ```
  2. 继续等待并保证期间不探测 `google`/`google news`（何时恢复不可预期）。
- 无论哪条，**§4 的归因不受影响**：中文查询的 0 新鲜来自 `chinaso news` 索引偏旧 + `tiger news` 无结果，
  与 `google news` 是否恢复无关（它即使恢复也不提供发布日期）。

## 6. 回滚

```bash
# ① 配置回退（服务器）：恢复引擎列表
cp /root/deploy-backups-20260929/env.20260930-pre-engine-list.bak .env
docker compose up -d --no-deps utf8-search        # env 变化要 recreate
curl -s http://127.0.0.1:8000/health | grep -o 'sogou wechat'   # 应重新出现（回退成功）

# ② 仓库回退：本分支只改了 compose 的 3 行 + .env.example，直接
git checkout main -- docker-compose.yml .env.example

# ③ 校验端口矩阵未变（app 只绑 127.0.0.1:8000；对外只有 80/443）
docker compose config | grep -A 3 'published'
```

**注意**：回滚 `docker-compose.yml` 后，容器会**再次丢失**两个引擎列表（回到代码默认值，含 `360search`/`sogou wechat` 悬空引用）。

## 7. 遗留（写入 `docs/04` §8）

1. **容器 env 注入缺口（重要）**：容器只收到 4 个变量，其余 ~40 项 `.env` 设置全部走代码默认值
   （含时效窗口、日期回补预算、rank 过滤参数、闸门参数等）。本轮只接了「两个引擎列表」这一条最小路径；
   建议单独一轮决定是否改为 `env_file: .env` 或挂载 `./.env:/app/.env:ro`（注意 `SEARXNG_URL` 已被 compose 显式覆盖，优先级正确）。
   **在修好之前，任何「改 .env 即生效」的结论对容器路径都不成立**（宿主机脚本路径是成立的）。
2. **中文新闻新鲜源缺失**：门槛 28% 的病根（§4）。可选方向：等 `google news` 冷却后复测（已做）、
   重新评估一个**支持 `time_range` 且带日期**的中文源（阶段 1 候选里只有 `bilibili` 满足，但它是视频站、需限流）、
   或明确把该门槛按「中文查询另设口径」处理 —— 需要产品侧决策，本轮不动。
3. **兜底源（Bing）会返回离题结果**：查询 2 的 top5 是沃尔玛滤水器/世界杯页面，且全部无日期（§4 第 2 行）。
   这会同时伤害 2-9 与时效两个门槛，建议单独排查兜底源的相关性校验。
4. **上一轮留下的红测试**（本轮开工时发现）：`tests/test_searxng_settings.py::test_local_settings_differs_only_by_proxy` 失败，
   原因是替换分支只改了 `searxng/settings.yml`、没同步 `searxng/settings.local.yml`（该文件仍含 `360search`/`sogou wechat`）。
   该测试要求两份文件除 `outgoing.proxies` 外逐行一致。**未自行修复**，待你确认（一行同步即可）。

## 8. 证据文件

| 内容 | 路径 |
| --- | --- |
| news 门槛（改动后）/ 变体（去掉 google news） | `docs/reports/engine-list-env-news-gate-after-20260930.md`、`engine-list-env-news-gate-no-google-20260930.md` |
| news 门槛拆解（逐条 + 来源引擎 + 日期） | `docs/reports/engine-list-env-news-decompose-20260930.txt`（§4 表；该次跑的是**不含 google news** 的列表，结果与含它完全一致，见 §3.5） |
| 新闻列表 A/B（8 条查询） | `docs/reports/engine-list-env-news-compare-20260930.json` |
| 通用列表 A/B 复跑（24 样本） | `docs/reports/engine-list-env-general-compare-20260930.json` |
| 2-9 明细 / 速览 / 打分 / 判定 | `docs/reports/m2-9-engine-list-env-20260930{,-brief,-scores,-scores-judge}.md/.csv` |
| 卫生度 JSON | `docs/reports/engine-list-env-hygiene-20260930.json` |
| `.env` 改前备份（仓库外） | `/root/deploy-backups-20260929/env.20260930-pre-engine-list.bak` |

---

## 附录 B：`google news` 冷却诊断（2026-09-30，已按批准 restart searxng 一次）

**要回答的问题**：`google` / `google news` 长期报 `Suspended: CAPTCHA`，是
**① SearXNG 进程内的本地冷却盒**（重启即消失，属运维问题）还是
**② Google 在 IP 层面拒绝本站出口**（重启也没用，属长期不可用）？

### B.1 重启前状态（10:44:14）

```
searxng 容器：Up 21 hours
日志里 google / google news 的 CAPTCHA 时间戳（suspended_time=3600）：
  2026-09-29 13:28:04 google     2026-09-29 14:33:03 google
  2026-09-29 15:38:03 google     2026-09-29 16:43:03 google
  2026-09-30 02:31:43 google     2026-09-30 02:34:26 google news
直问 SearXNG：
  google news  结果=0  unresponsive=[['google news', 'Suspended: CAPTCHA']]
  google       结果=0  unresponsive=[['google', 'Suspended: CAPTCHA']]
应用 /health cooling：privacywall(517s) / yep(517s) / google(1417s)
```

最后一次上游 CAPTCHA 事件是 **02:31/02:34**，按 `suspended_time=3600` 早该在 03:34 恢复，
但 10:44 仍被挂起 ⇒ 该处罚状态**不会自然过期**（与 §5 一致）。

### B.2 重启后立刻探针（`docker compose restart searxng`；caddy / app 未动）

```
10:44:2x  容器 Started（6s 后 /healthz=200）
第1次: 结果=12 带日期=0 耗时=650ms unresponsive=[]
第2次: 结果=12 带日期=0 耗时=366ms unresponsive=[]
第3次: 结果=12 带日期=0 耗时=254ms unresponsive=[]
重启后 5 分钟内的日志：无任何新的 google CAPTCHA 异常
对照 google（通用）：结果=10 带日期=0 unresponsive=[]
```

### B.3 结论

1. **是本地冷却盒，不是 IP 被封** —— 同一出口 IP，重启后**秒级**拿到 12 条 `google news` 结果（3/3 成功，
   254-650ms，无新 CAPTCHA 异常）⇒ **不需要**按「长期不可用」把它移除/降权，
   `docs/04` **不新增**「移除或降权 google news」条目；改为记一条运维动作：
   **引擎长期卡在 `Suspended: CAPTCHA` 时，重启 SearXNG 可立即清除本地处罚盒**。
2. **`google news` 依然不给发布日期**（12 条里 0 条带日期；通用 `google` 也 0 条）⇒ 它恢复的是**召回/覆盖**，
   对「7 日内日期比例」这个门槛**没有直接帮助**。
3. **冷却后补测（同一门槛命令，google news 已恢复）**：**24/40 = 60%**（此前 28%），仍低于 80%。
   失败形态从「带日期但过期」变成「**无日期**」：

   | 查询 | 结果 | 7 日内 | 过期 | 无日期 | 比例 |
   | --- | --- | --- | --- | --- | --- |
   | 2026年9月 国内外重大新闻 | 5 | 3 | 0 | 2 | 60% |
   | 最近一周 AI 行业动态 | 5 | 3 | 0 | 2 | 60% |
   | 台风 最新消息 路径 | 5 | 2 | 0 | 3 | 40% |
   | 美国 关税 最新政策 | 5 | 1 | 0 | 4 | 20% |
   | latest news semiconductor export controls | 5 | 3 | 0 | 2 | 60% |
   | OpenAI latest news | 5 | 5 | 0 | 0 | 100% |
   | 2026年 新能源汽车 补贴政策 | 5 | 2 | 0 | 3 | 40% |
   | EU AI Act latest developments | 5 | 5 | 0 | 0 | 100% |

   ⇒ 门槛的剩余差距变成**「无日期结果挤占 top5」**（`google news` 本身不给日期 + 日期回补没覆盖到），
   不再是「中文源全线拿不到结果」。这是**下一轮值得动手的方向**（提高日期回补命中 / 对无日期结果降权），
   本轮按「不盲调参数」只做记录。

证据：`docs/reports/engine-list-env-news-gate-google-recovery-20260930.md`（补测报告）；
探针命令与输出见上（B.1/B.2）。

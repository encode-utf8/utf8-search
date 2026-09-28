# 候选池 24 vs 40 对照明细（人工打分用）

- 生成时间：2026-09-28 17:43:58
- **数据来源**：**同一批候选切片而来** —— 每条查询只发**一次**上游请求（索取 40 条），再在本地取前 24 / 40 条分别排序。
- ⚠️ **不可与重新采集的结果混用**：本文件里的两列来自同一次采集；另跑一次脚本会得到不同的候选集。
- 打分模板：`pool24-scores.csv`（先填这份）、`pool40-scores.csv`（仅在必要时对照）
- 打分规则：scores 的 5 位依次对应排名 1-5，**非零即为相关**；门槛 20 条里 ≥18 条满足「相关 ≥4」。

## 怎么用（交付说明）

1. **先只填 `pool24-scores.csv`**（池 24 = 当前默认）——这份用于**关闭 2-9**（与 `docs/reports/m2-9-relevance-20260928.md` 是同一批 20 条查询，但采集批次不同，二者选一即可，别混填）。
2. **只有**当池 24 那份打出 **< 18/20**（未达 90% 门槛）时，才需要再填 `pool40-scores.csv` 做对照，看「把候选池从 24 放大到 40」能不能救回来。
3. 判定命令（不联网）：`.venv/bin/python scripts/relevance.py --score-file <填好的 csv>`

## 汇总

| 指标 | 池 24 | 池 40 |
| --- | --- | --- |
| 覆盖率均值 | 0.8474 | 0.8537 |
| 覆盖率最低 | 0.5625 | 0.4737 |
| 独立站点均值 | 4.6 | 4.7 |
| 排序耗时 P50 | 4.94 | 7.14 |
| 多留候选进 top5（条） | 0 | 20 |
| 进 top5 占槽位 | 0.0 | 20.0 |
| 至少进 1 条的查询占比 | 0.0 | 65.0 |
| top5 变化（条/查询） | 0.0 | 1.0 |

## 1. 2026年9月 国内外重大新闻

**池 24**（候选 24 条，覆盖 0.5895，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 中国外长王毅高度评价习近平主席访美 - 2026年9月27... | sputniknews.cn | 2026年9月23日至25日，中国国家主席习近平对美国进行国事访问。 行程结束之际，中共中央政治局委员、外交部长王毅向随行记者介绍此访情况，他指出，此访拓展中美关系新定位，开辟中美… | https://sputniknews.cn/20260927/1073398892.html |
| 2 | 2026年9月28日 · 每日推送20条 | brewpage.app | 2026年9月28日 每日推送（早6:00）. 广州日报媒重点实验室 · 申卉 · 工作日早报. 数据来源：微博热搜、抖音热榜、百度热搜、快手热榜、知乎热榜、B站热榜、中国青年报、… | https://brewpage.app/public/VVjvFZG9j1 |
| 3 | 【今日头条·每日新闻热点】2026年9月17日 国内外重大新闻20条 | toutiao.com | Sep 17, 2026 · 9月16日，香港特区政府公布《香港特别行政区经济和社会发展第一个五年规划（2026—2030年）》，明确经济发展取得新突破、持续提升国际竞争力与影响力… | https://www.toutiao.com/article/7686405497418760747/ |
| 4 | 2026时政热点:国内外时事政治汇总（9月1日）_华图教育 | huatu.com | Sep 1, 2026 · 2026时政热点:国内外时事政治汇总（9月1日） 一、全球 1、美国与伊朗冲突再度升级，美军袭击伊朗拉拉克岛，伊朗随后向约旦境内美军基地发动报复性打击，… | https://m.ah.huatu.com/2026/0901/3279749.html |
| 5 | 2026 年 9 月 26 日新闻速览：高铁、假期与明星动态\|国铁集团\|10部门\|纪念长征胜利90周年主题展览\|商务部\|龚俊\|贾乃亮\|戚薇\|京港高铁_新浪新闻 | sina.cn | 2 days ago — 2026 年 9 月 26 日新闻速览涵盖高铁开通、政策发布、灾害预警及娱乐活动，包括京港高铁雄商段等四条线路集中开通运营，10 部门联合促进房车消费，纪… | https://www.sina.cn/weibo/detail/5347294804182542.html |

**池 40**（候选 40 条，覆盖 0.4737，独立站点 5，新进 top5 4 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 对外经济贸易大学发布讣告：刘欢病逝 享年63岁 \| 文学城 | wenxuecity.com | 我们沉痛宣告：我校退休教师、全国家喻户晓的音乐家刘欢，于2026年9月25日上午9时52分在上海不幸病逝，享年63岁。他的离去，是我校的重大损失，也是中国音乐界的重大损失。 | https://www.wenxuecity.com/news/2026/09/25/126786284.html |
| 2 | 2026年9月27日重大事件汇总 – 轮子哥Blog | aisworld.cn | 9 hours ago · （说明）本篇汇总报道日为2026年9月27日（周日，中秋假期最后一天）。动笔前先行科技核验，就全球头部大模型的新世代正式发布或开放（OpenAI、Goo… | https://aisworld.cn/2026/09/28/2026%E5%B9%B49%E6%9C%8827%E6%97%A5%E9%87%8D%E5%A4… |
| 3 | 中国外长王毅高度评价习近平主席访美 - 2026年9月27... | sputniknews.cn | 2026年9月23日至25日，中国国家主席习近平对美国进行国事访问。 行程结束之际，中共中央政治局委员、外交部长王毅向随行记者介绍此访情况，他指出，此访拓展中美关系新定位，开辟中美… | https://sputniknews.cn/20260927/1073398892.html |
| 4 | 9月26日新闻早知道｜昨夜今晨·热点不容错过_腾讯新闻 | qq.com | 2 days ago — ▶ 习近平圆满结束对美国的国事访问当地时间9月25日下午，国家主席习近平结束对美国的国事访问返回北京。详情>>▶ 习近平和彭丽媛同美国总统特朗普夫妇茶叙当… | https://news.qq.com/rain/a/20260926A032ET00 |
| 5 | 2026年9月22日外交部发言人郭嘉昆主持例行记者会_中华人民共和国驻大韩民国大.... | china-embassy.gov.cn | 6일 전国家副主席韩正将于9月24日至26日赴纽约出席第81届联合国大会一般性辩论。与会期间，韩正副主席还将出席中方举办的全球发展倡议5周年高级别对话会，会见联合国秘书长、第81届… | https://kr.china-embassy.gov.cn/fyrth/202609/t20260922_12028748.htm |

## 2. 最近一周 AI 行业动态

**池 24**（候选 24 条，覆盖 0.5625，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | AI日报 - 每天三分钟关注AI行业趋势_AIbase | aibase.com | AI日报为您提供最新的人工智能行业资讯，每天仅需三分钟，全面掌握AI技术发展、行业动态和市场趋势。关注AI日报，紧跟未来科技步伐，获取独家分析与深度解读。 | https://www.aibase.com/zh/daily |
| 2 | AI行业发展一周动态 - 知乎 | zhihu.com | 2025年全球端侧AI市场规模将增至1.22万亿元年复合增长率达40%[2] · 2025年12月9日，谷歌公布智能眼镜Project Aura和Android XR系统关键细节，… | https://zhuanlan.zhihu.com/p/1983093760448542417 |
| 3 | AI消息周报 - 每周深度总结大模型、Agent 与 AI 工具变化 \| zglg.work | zglg.work | 郭震 AI 周报按周提炼 AI 日报和实时消息里的关键变化，整理大模型、AI Agent、开源工具、AI 编程工具、算力基础设施、产业应用和政策动态，保留来源线索、上下文链接、历史… | https://zglg.work/ai/weekly |
| 4 | AI周刊丨本周不可错过的AI行业动态（6.9-6.15） - 知乎 | zhihu.com | 科大讯飞在深圳举办智能交互产品升级发布会，主题为“交互领航智启新章”。 在发布会上，AIUI、机器人超脑、虚拟数字人与讯飞星辰四大开发平台亮相，展示软硬件协同优化成果。 ..."A… | https://zhuanlan.zhihu.com/p/1917647873308357987 |
| 5 | 每日AI资讯、热点、动态、融资、产品发布 \| AI工具集 | ai-bot.cn | August 10, 2023 — 面壁智能联合 OpenBMB 开源 ForgeStencil，全球首个 AI 驱动的 Stencil 全自动优化系统。ForgeStencil由… | https://ai-bot.cn/daily-ai-news/ |

**池 40**（候选 40 条，覆盖 0.5625，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | AI日报 - 每天三分钟关注AI行业趋势_AIbase | aibase.com | AI日报为您提供最新的人工智能行业资讯，每天仅需三分钟，全面掌握AI技术发展、行业动态和市场趋势。关注AI日报，紧跟未来科技步伐，获取独家分析与深度解读。 | https://www.aibase.com/zh/daily |
| 2 | AI行业发展一周动态 - 知乎 | zhihu.com | 2025年全球端侧AI市场规模将增至1.22万亿元年复合增长率达40%[2] · 2025年12月9日，谷歌公布智能眼镜Project Aura和Android XR系统关键细节，… | https://zhuanlan.zhihu.com/p/1983093760448542417 |
| 3 | AI消息周报 - 每周深度总结大模型、Agent 与 AI 工具变化 \| zglg.work | zglg.work | 郭震 AI 周报按周提炼 AI 日报和实时消息里的关键变化，整理大模型、AI Agent、开源工具、AI 编程工具、算力基础设施、产业应用和政策动态，保留来源线索、上下文链接、历史… | https://zglg.work/ai/weekly |
| 4 | AI周刊丨本周不可错过的AI行业动态（6.9-6.15） - 知乎 | zhihu.com | 科大讯飞在深圳举办智能交互产品升级发布会，主题为“交互领航智启新章”。 在发布会上，AIUI、机器人超脑、虚拟数字人与讯飞星辰四大开发平台亮相，展示软硬件协同优化成果。 ..."A… | https://zhuanlan.zhihu.com/p/1917647873308357987 |
| 5 | 每日AI资讯、热点、动态、融资、产品发布 \| AI工具集 | ai-bot.cn | August 10, 2023 — 面壁智能联合 OpenBMB 开源 ForgeStencil，全球首个 AI 驱动的 Stencil 全自动优化系统。ForgeStencil由… | https://ai-bot.cn/daily-ai-news/ |

## 3. latest news semiconductor export controls

**池 24**（候选 24 条，覆盖 0.72，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | What's the latest with semiconductor export controls? \| Reuters | reuters.com | 4 days ago · Anthony Rapa of Blank Rome LLP discusses recent developments in U.S. export c… | https://www.reuters.com/legal/legalindustry/whats-latest-with-semiconductor-expo… |
| 2 | What’s the Latest with Semiconductor Export Controls? | blankrome.com | 5 days ago · What's the Latest with Semiconductor Export Controls? - Blank Rome LLP | https://www.blankrome.com/news-and-events/whats-the-latest-with-semiconductor-ex… |
| 3 | China lashes out at latest U.S. export controls on chips | asahi.com | BEIJING--China on Saturday criticized the latest U.S. decision to tighten export controls … | https://www.asahi.com/ajw/articles/14738636 |
| 4 | Trump's AI chip export controls could go either way for Korea - Korea JoongAng Daily ,Kore… | koreajoongangdaily.com | 2025.05.14.Published May 14, 2025 - 6:36 p.m. Modified May 14, 2025 - 8:06 p.m.2025.05.14. | https://www.koreajoongangdaily.com/business/trumps-ai-chip-export-controls-could… |
| 5 | Reported Draft Rules Signal New Semiconductor Export Controls Framework | globaltradeandsanctionslaw.com | March 13, 2026 — On March 5, news outlets reported that the U.S. government is drafting ne… | https://www.globaltradeandsanctionslaw.com/reported-draft-rules-signal-new-semic… |

**池 40**（候选 40 条，覆盖 0.8，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | What's the latest with semiconductor export controls? \| Reuters | reuters.com | 4 days ago · Anthony Rapa of Blank Rome LLP discusses recent developments in U.S. export c… | https://www.reuters.com/legal/legalindustry/whats-latest-with-semiconductor-expo… |
| 2 | Biden’s Unprecedented Semiconductor Bet \| Carnegie Endowment for... | carnegieendowment.org | In issuing the latest round of export controls, President Joe Biden’s administration chose… | https://carnegieendowment.org/posts/2022/10/bidens-unprecedented-semiconductor-b… |
| 3 | What’s the Latest with Semiconductor Export Controls? | blankrome.com | 5 days ago · What's the Latest with Semiconductor Export Controls? - Blank Rome LLP | https://www.blankrome.com/news-and-events/whats-the-latest-with-semiconductor-ex… |
| 4 | Trump's AI chip export controls could go either way for Korea - Korea JoongAng Daily ,Kore… | koreajoongangdaily.com | 2025.05.14.Published May 14, 2025 - 6:36 p.m. Modified May 14, 2025 - 8:06 p.m.2025.05.14. | https://www.koreajoongangdaily.com/business/trumps-ai-chip-export-controls-could… |
| 5 | Reported Draft Rules Signal New Semiconductor Export Controls Framework | globaltradeandsanctionslaw.com | March 13, 2026 — On March 5, news outlets reported that the U.S. government is drafting ne… | https://www.globaltradeandsanctionslaw.com/reported-draft-rules-signal-new-semic… |

## 4. 台风 最新消息 路径

**池 24**（候选 24 条，覆盖 0.84，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 台风森拉克最新路径最有可能登陆哪里-抖音 | douyin.com | 超强台风森拉克将在13-14号，以17+风力重创美国关岛！ #超强台风 #台风森拉克 #台风最新消息台风实时路径 #最新天气预报 #台风最新消息. | https://www.douyin.com/shipin/7628796920739334182 |
| 2 | 2026年第19号台风紫檀最新消息路径实时更新- 杭州本地宝 | bendibao.com | 台风紫檀路径预报图. 台风紫檀大风预报图. 台风紫檀降雨预报图. 六、实时路径查询入口. 台风路径、强度、风雨影响将随时间动态变化，最新信息请以中央气象台官方发布为准。 | https://hz.bendibao.com/news/2026824/172470.shtm |
| 3 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | bendibao.com | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 4 | 超强台风“白海豚”最大风力达17级，8月5日夜间之前对我国海区无影响，中国.... | ycwb.com | 据中央气象台最新消息，今年第13号台风“白海豚”（超强台风级）的中心今天（8月1日）早晨5时位于日本东京东南方向大约2550公里的西北太平洋洋面上，就是北纬20.0度、东经158.… | https://news.ycwb.com/ikimvkctkj/content_54258026.htm |
| 5 | 中央气象台台风网 - typhoon.nmc.cn | nmc.cn | 台风路径实时发布系统是由中央气象台权威发布台风信息系统,系统可及时准确地提供最新最全的台风实时信息、预报路径,同时整合卫星云图、气象雷达、降雨等内容 | http://typhoon.nmc.cn/mobile.html |

**池 40**（候选 40 条，覆盖 0.8667，独立站点 4，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 台风森拉克最新路径最有可能登陆哪里-抖音 | douyin.com | 超强台风森拉克将在13-14号，以17+风力重创美国关岛！ #超强台风 #台风森拉克 #台风最新消息台风实时路径 #最新天气预报 #台风最新消息. | https://www.douyin.com/shipin/7628796920739334182 |
| 2 | 2026年第19号台风紫檀最新消息路径实时更新- 杭州本地宝 | bendibao.com | 台风紫檀路径预报图. 台风紫檀大风预报图. 台风紫檀降雨预报图. 六、实时路径查询入口. 台风路径、强度、风雨影响将随时间动态变化，最新信息请以中央气象台官方发布为准。 | https://hz.bendibao.com/news/2026824/172470.shtm |
| 3 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | bendibao.com | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 4 | 摩羯台风实时路径 \| TikTok | tiktok.com | #海南dou知道 #台风摩羯. 台风动态, 海南台风消息, 台风路径更新, 海口台风天气, 台风影响生活, 最新台风信息, 摩羯台风报道, 风浪增大现状, 海边天气变化, 台风. … | https://www.tiktok.com/discover/%E6%91%A9%E7%BE%AF%E5%8F%B0%E9%A3%8E%E5%AE%9E%E6… |
| 5 | 超强台风“白海豚”最大风力达17级，8月5日夜间之前对我国海区无影响，中国.... | ycwb.com | 据中央气象台最新消息，今年第13号台风“白海豚”（超强台风级）的中心今天（8月1日）早晨5时位于日本东京东南方向大约2550公里的西北太平洋洋面上，就是北纬20.0度、东经158.… | https://news.ycwb.com/ikimvkctkj/content_54258026.htm |

## 5. 美国 关税 最新政策

**池 24**（候选 24 条，覆盖 0.7467，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 2026 美国关税最新消息 — 中菲行国际物流集团 | dimerco.com | June 6, 2026 — 除232关税调整外，美国贸易代表办公室（USTR）还发布了一份《联邦公报》（Federal Register Notice），明确表明政府在7月24日… | https://cn.dimerco.com/us-tariff-update-2026/ |
| 2 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | edurew.com | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协… | https://www.edurew.com/html/03c79099206.html |
| 3 | 2026 美国关税新政深度解读：2 月 24 日起税率调整 + 清关实操指南，... | sohu.com | Feb 25, 2026 · 2026 年 2 月 24 日，美国关税新政正式落地实施，此次调整涉及旧关税取消、新关税上线、在途货清关规则、退税机制等多个核心问题，直接影响所有中国… | https://www.sohu.com/a/989760760_120987862 |
| 4 | 关税政策及其对全球贸易的影响 \| UPS Supply Chain Solutions - 美国 | ups.com | 根据第 122 条关税政策，自 2026年2月24日起，美国对所有国家的进口商品统一加征 10% 的关税。但是也存在几项豁免情形，例如符合美墨加协定认证的商品。更多信息可在此处查看… | https://www.ups.com/cn/zh/supplychain/resources/news-and-market-updates/2025-us-… |
| 5 | Temu 和 Shein... | 100ec.cn | 9 日起取消 Google 购物平台所有支出，并于 4 月 25 日因 “全球贸易规则和关税致运营费用上涨” 进行价格调整，Shein 也将在同日实施相同举措。 一、政策背景：特朗… | https://www.100ec.cn/detail--6648723.html |

**池 40**（候选 40 条，覆盖 0.8133，独立站点 5，新进 top5 2 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 2026 美国关税最新消息 — 中菲行国际物流集团 | dimerco.com | June 6, 2026 — 除232关税调整外，美国贸易代表办公室（USTR）还发布了一份《联邦公报》（Federal Register Notice），明确表明政府在7月24日… | https://cn.dimerco.com/us-tariff-update-2026/ |
| 2 | 如何查询美国最新关税政策？ - 知乎 | zhihu.com | 美国关税一直是外贸人比较关注的一个话题，它也一直在变，这里整理了美国关税政策发布的一些渠道，供有需要的外贸小伙伴参考。 美国贸易代表办公室 (USTR) | https://zhuanlan.zhihu.com/p/21672619612 |
| 3 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | edurew.com | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协… | https://www.edurew.com/html/03c79099206.html |
| 4 | 三年来首次下滑！关税政策正让美国经济经历“超出预期的糟糕” - 韩国最大的.... | joins.com | 2025.05.02.美国商务部4月30日公布最新数据显示，2025年第一季度，按年率计算，美国国内生产总值(GDP)环比萎缩0.3%，为2022年以来的首次收缩。这一最新数据的糟… | https://chinese.joins.com/news/articleView.html?idxno=119620 |
| 5 | 2026 美国关税新政深度解读：2 月 24 日起税率调整 + 清关实操指南，... | sohu.com | Feb 25, 2026 · 2026 年 2 月 24 日，美国关税新政正式落地实施，此次调整涉及旧关税取消、新关税上线、在途货清关规则、退税机制等多个核心问题，直接影响所有中国… | https://www.sohu.com/a/989760760_120987862 |

## 6. Python 3.13 新特性

**池 24**（候选 24 条，覆盖 1.0，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | python3.13 3.14 新特性 好好好 - 南鱼羁荒渡 - 博客园 | cnblogs.com | December 16, 2025 — Python 3.13 和 3.14 版本 带来了许多激动人心的改进，下面这个表格汇总了它们的核心新特性，可以帮助你快速了解这两个版本的主要… | https://www.cnblogs.com/nanyu/p/19356064 |
| 2 | Python 3.13 有什么新变化 — Python 3.13.1 文档 | sdx.cool | January 21, 2026 — Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive sh… | https://www.sdx.cool/index/python_docs/whatsnew/3.13.html |
| 3 | Python 3.13 有什么新变化 — Python 3.16.0a0 文档 | python.org | Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 PyPy 项目 的… | https://docs.python.org/zh-cn/dev/whatsnew/3.13.html |
| 4 | 【文章自荐】Python 3.13的7大类型注解新特性 · Issue #5255 · ruanyf/weekly · GitHub | github.com | 2024.09.30.https://medium.com/techtofreedom/7-new-typing-features-in-python-3-13-58caae5f2… | https://github.com/ruanyf/weekly/issues/5255 |
| 5 | Python 3.13 新特性与更新详解_python3.13新特性-CSDN博客 | csdn.net | 新版Python 3.13发布，官方...得注意的几大亮点包括：全新的交互式解释器、支持无全局解释器锁的实验性功能（PEP 703）、基本的即时编译器（PEP 744），以及对错误… | https://blog.csdn.net/qq254606826/article/details/144459740 |

**池 40**（候选 40 条，覆盖 1.0，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | python3.13 3.14 新特性 好好好 - 南鱼羁荒渡 - 博客园 | cnblogs.com | December 16, 2025 — Python 3.13 和 3.14 版本 带来了许多激动人心的改进，下面这个表格汇总了它们的核心新特性，可以帮助你快速了解这两个版本的主要… | https://www.cnblogs.com/nanyu/p/19356064 |
| 2 | Python 3.13 有什么新变化 — Python 3.13.1 文档 | sdx.cool | January 21, 2026 — Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive sh… | https://www.sdx.cool/index/python_docs/whatsnew/3.13.html |
| 3 | Python 3.13 有什么新变化 — Python 3.16.0a0 文档 | python.org | Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 PyPy 项目 的… | https://docs.python.org/zh-cn/dev/whatsnew/3.13.html |
| 4 | 【文章自荐】Python 3.13的7大类型注解新特性 · Issue #5255 · ruanyf/weekly · GitHub | github.com | 2024.09.30.https://medium.com/techtofreedom/7-new-typing-features-in-python-3-13-58caae5f2… | https://github.com/ruanyf/weekly/issues/5255 |
| 5 | 探索Python 3.13新特性：你不能错过的重要更新_python3.13 pep-CSDN博... | csdn.net | Python 3.13是Python编程语言的最新重大版本更新，它在2024年10月7日正式发布。这个版本带来了许多令人兴奋的新特性和优化，从全新的交互式解释器到实验性的免GIL模… | https://blog.csdn.net/exlink2012/article/details/154475484 |

## 7. MCP protocol specification 2026

**池 24**（候选 24 条，覆盖 1.0，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | The 2026-07-28 MCP Specification: A Stateless, Extensible ... | mcpservers.org | Jul 3, 2026 · A New Era for MCP On May 21, 2026, the Model Context Protocol team locked th… | https://blog.mcpservers.org/posts/mcp-spec-2026-07-28 |
| 2 | 다음 MCP 스펙 릴리즈(2026-07-28)의 주요 내용: Stateless 전환 및 공식 확장 도입 예.... | pytorch.kr | 2026.05.27.MCP 스펙 릴리즈 후보(The 2026-07-28 MCP Specification Release Candidate) 소개 Model Cont… | https://discuss.pytorch.kr/t/mcp-2026-07-28-stateless/10387 |
| 3 | Simplified AI Agent Protocol with MCP Specification 2026-07-28 | linkedin.com | The new Model Context Protocol specification (2026-07-28) eliminates the session-based des… | https://www.linkedin.com/posts/jokotagba-opemipo_the-protocol-connecting-ai-agen… |
| 4 | The 2026-07-28 Specification \| Model Context Protocol Blog | modelcontextprotocol.io | July 28, 2026 — The 2026-07-28 Model Context Protocol specification is out, bringing a sta… | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| 5 | The 2026-07-28 MCP Specification Release Candidate \| Model Context Protocol Blog | modelcontextprotocol.io | July 28, 2026 — The release candidate for the next Model Context Protocol (MCP) specificat… | https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ |

**池 40**（候选 40 条，覆盖 1.0，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | The 2026-07-28 MCP Specification: A Stateless, Extensible ... | mcpservers.org | Jul 3, 2026 · A New Era for MCP On May 21, 2026, the Model Context Protocol team locked th… | https://blog.mcpservers.org/posts/mcp-spec-2026-07-28 |
| 2 | 다음 MCP 스펙 릴리즈(2026-07-28)의 주요 내용: Stateless 전환 및 공식 확장 도입 예.... | pytorch.kr | 2026.05.27.MCP 스펙 릴리즈 후보(The 2026-07-28 MCP Specification Release Candidate) 소개 Model Cont… | https://discuss.pytorch.kr/t/mcp-2026-07-28-stateless/10387 |
| 3 | Simplified AI Agent Protocol with MCP Specification 2026-07-28 | linkedin.com | The new Model Context Protocol specification (2026-07-28) eliminates the session-based des… | https://www.linkedin.com/posts/jokotagba-opemipo_the-protocol-connecting-ai-agen… |
| 4 | The 2026-07-28 Specification \| Model Context Protocol Blog | modelcontextprotocol.io | July 28, 2026 — The 2026-07-28 Model Context Protocol specification is out, bringing a sta… | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| 5 | The New MCP Specification: What Security Teams Must Prepare For \| Akamai | akamai.com | June 25, 2026 — Following the release candidate published on May 21, 2026, the final speci… | https://www.akamai.com/blog/security-research/new-mcp-specification-security-tea… |

## 8. FastAPI 与 Django 性能对比

**池 24**（候选 24 条，覆盖 0.8182，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | python web框架哪家强？ Flask、Django、FastAPI对比_fastapi flask... | csdn.net | 对比Flask、Django和FastAPI三款python框架，Flask更适合新手上手。_fastapi flask django性能对比.Python使用总结之FastAPI… | https://blog.csdn.net/way311/article/details/139771390 |
| 2 | Python Web开发新时代：FastAPI vs Django性能对比 - 技术栈 | jishuzhan.net | Jan 12, 2026 · 在Python Web开发领域，Django作为老牌框架长期占据主导地位，而FastAPI作为后起之秀，凭借其出色的性能和现代化特性迅速崛起。本文将从… | https://jishuzhan.net/article/2010867478365782018 |
| 3 | Django 与 FastAPI 架构对比：学习路径指南Django 与 FastAPI... | juejin.cn | Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。 本文将详解如何对两者进行评估选择。 | https://juejin.cn/post/7565799761123786806 |
| 4 | Django 与 FastAPI 架构对比：学习路径指南 - 葡萄城技术团队 - Segme... | segmentfault.com | Oct 28, 2025 · Django 与 FastAPI 架构对比：学习路径指南 Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。本文将详解… | https://segmentfault.com/a/1190000047351357 |
| 5 | Django vs FastAPI：高并发场景下谁更胜一筹？（2025实战对比）-CSDN... | csdn.net | Oct 4, 2025 · 文章浏览阅读842次，点赞21次，收藏29次。深入解析Python Web框架对比2025趋势，聚焦Django与FastAPI在高并发场景下的性能差异… | https://blog.csdn.net/LearnFlow/article/details/152509413 |

**池 40**（候选 38 条，覆盖 0.8182，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | python web框架哪家强？ Flask、Django、FastAPI对比_fastapi flask... | csdn.net | 对比Flask、Django和FastAPI三款python框架，Flask更适合新手上手。_fastapi flask django性能对比.Python使用总结之FastAPI… | https://blog.csdn.net/way311/article/details/139771390 |
| 2 | Python Web开发新时代：FastAPI vs Django性能对比 - 技术栈 | jishuzhan.net | Jan 12, 2026 · 在Python Web开发领域，Django作为老牌框架长期占据主导地位，而FastAPI作为后起之秀，凭借其出色的性能和现代化特性迅速崛起。本文将从… | https://jishuzhan.net/article/2010867478365782018 |
| 3 | Django 与 FastAPI 架构对比：学习路径指南Django 与 FastAPI... | juejin.cn | Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。 本文将详解如何对两者进行评估选择。 | https://juejin.cn/post/7565799761123786806 |
| 4 | Django 与 FastAPI 架构对比：学习路径指南 - 葡萄城技术团队 - Segme... | segmentfault.com | Oct 28, 2025 · Django 与 FastAPI 架构对比：学习路径指南 Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。本文将详解… | https://segmentfault.com/a/1190000047351357 |
| 5 | Django vs FastAPI：高并发场景下谁更胜一筹？（2025实战对比）-CSDN... | csdn.net | Oct 4, 2025 · 文章浏览阅读842次，点赞21次，收藏29次。深入解析Python Web框架对比2025趋势，聚焦Django与FastAPI在高并发场景下的性能差异… | https://blog.csdn.net/LearnFlow/article/details/152509413 |

## 9. how does HTTP/3 QUIC work

**池 24**（候选 24 条，覆盖 0.9667，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | HTTP/3 Maintains a Consistent Connection ID | pubnub.com | How does HTTP/3 maintain a constant Connection ID? How does switching from 5G to Wi-Fi aff… | https://www.pubnub.com/blog/http3-and-quic-the-connection-id/ |
| 2 | HTTP/3 and QUIC, what do they mean for the web? \| Human Level | humanlevel.com | What is QUIC? How does it work? QUIC protocol characteristics: Brief history of QUIC. Curr… | https://www.humanlevel.com/en/blog/seo/http3-and-quic |
| 3 | [Illustration] How does HTTP/3 (HTTP over QUIC) work?... \| SEの道標 | nesuke.com | Change from HTTP/2 to HTTP/3. HTTP/3 has been decided to operate on a new protocol called … | https://milestone-of-se.nesuke.com/en/l7protocol/http/http3-over-quic/ |
| 4 | The Future of the Internet is here: QUIC Protocol and HTTP/3 \| Medium | medium.com | How does QUIC work? Unlike TCP, which uses a connection-oriented approach, QUIC uses a mul… | https://medium.com/@luisrodri/the-future-of-the-internet-is-here-quic-protocol-a… |
| 5 | What is HTTP and how does it work? Hypertext Transfer Protocol \| Definition from | techtarget.com | 2025.02.03.HTTP (Hypertext Transfer Protocol) is a set of rules that govern how informatio… | https://www.techtarget.com/whatis/definition/HTTP-Hypertext-Transfer-Protocol |

**池 40**（候选 35 条，覆盖 0.9，独立站点 5，新进 top5 2 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | HTTP/3 Maintains a Consistent Connection ID | pubnub.com | How does HTTP/3 maintain a constant Connection ID? How does switching from 5G to Wi-Fi aff… | https://www.pubnub.com/blog/http3-and-quic-the-connection-id/ |
| 2 | HTTP/3 and QUIC, what do they mean for the web? \| Human Level | humanlevel.com | What is QUIC? How does it work? QUIC protocol characteristics: Brief history of QUIC. Curr… | https://www.humanlevel.com/en/blog/seo/http3-and-quic |
| 3 | [Illustration] How does HTTP/3 (HTTP over QUIC) work?... \| SEの道標 | nesuke.com | Change from HTTP/2 to HTTP/3. HTTP/3 has been decided to operate on a new protocol called … | https://milestone-of-se.nesuke.com/en/l7protocol/http/http3-over-quic/ |
| 4 | How does reanalysis work? \| 3billion FAQ | 3billion.io | 고객지원 자주 묻는 질문과 답을 확인하세요 검사 결과 Q How does reanalysis work? If you agreed to the Reanalysis … | https://3billion.io/faq/item/how-does-reanalysis-work |
| 5 | QUIC \| HAProxy Technologies Glossary | haproxy.com | # How does QUIC work?HTTP/3 works at the application layer to unify functionality between … | https://www.haproxy.com/glossary/what-is-quic |

## 10. Rust async runtime tokio 原理

**池 24**（候选 24 条，覆盖 0.9143，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | Rust Async + Tokio 入門：非同步 Rust vs Python asyncio · 每日拍拍 | dailypypy.org | Rust：tokio::sync::mpsc. 八、底層原理：Python vs Rust 的非同步模型.features = ["full"] 會啟用所有功能（runtime、n… | https://dailypypy.org/learn/rust-async-tokio/ |
| 2 | Rust异步编程完全指南2026版：Tokio运行时原理与async-await底层机制... | csdn.net | Aug 10, 2026 · Rust异步编程完全指南2026版：Tokio运行时原理与async/await底层机制深度解析 一、为什么Rust需要异步编程 Rust的异步编程模… | https://blog.csdn.net/weixin_56622231/article/details/161893982 |
| 3 | 完整教程：深入Rust：Tokio多线程调度架构的原理、实践与性能优化 - c... | cnblogs.com | Nov 29, 2025 · 本文章目录深入Rust：Tokio多线程调度架构的原理、实践与性能优化一、先理清：Tokio多线程架构的核心目标二、核心架构拆解：三大组件的分工与协作… | https://www.cnblogs.com/clnchanpin/p/19285288 |
| 4 | Tokio 异步运行时原理剖析 \| DroneBlog | github.io | May 19, 2026 · Tokio 是 Rust 生态中最成熟的异步运行时之一，为高性能网络应用提供了事件驱动、非阻塞 I/O 的基础设施。本文从源码层面深入解析 Tokio… | https://oldoldtea.github.io/2026/05/12/tokio-async-runtime/ |
| 5 | Tokio Runtime 架构剖析：一个 Task 的诞生与旅程 | github.io | Jul 13, 2026 · 要回答这个问题，就得了解 Tokio Runtime 内部，看清它的运作机制，而不是停留在"会用 tokio::spawn “的层面。 如果你想知道这… | https://orangex-position0.github.io/posts/rust/tokio-runtime-architecture/ |

**池 40**（候选 40 条，覆盖 0.9143，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | Rust Async + Tokio 入門：非同步 Rust vs Python asyncio · 每日拍拍 | dailypypy.org | Rust：tokio::sync::mpsc. 八、底層原理：Python vs Rust 的非同步模型.features = ["full"] 會啟用所有功能（runtime、n… | https://dailypypy.org/learn/rust-async-tokio/ |
| 2 | Rust异步编程完全指南2026版：Tokio运行时原理与async-await底层机制... | csdn.net | Aug 10, 2026 · Rust异步编程完全指南2026版：Tokio运行时原理与async/await底层机制深度解析 一、为什么Rust需要异步编程 Rust的异步编程模… | https://blog.csdn.net/weixin_56622231/article/details/161893982 |
| 3 | 完整教程：深入Rust：Tokio多线程调度架构的原理、实践与性能优化 - c... | cnblogs.com | Nov 29, 2025 · 本文章目录深入Rust：Tokio多线程调度架构的原理、实践与性能优化一、先理清：Tokio多线程架构的核心目标二、核心架构拆解：三大组件的分工与协作… | https://www.cnblogs.com/clnchanpin/p/19285288 |
| 4 | Tokio 异步运行时原理剖析 \| DroneBlog | github.io | May 19, 2026 · Tokio 是 Rust 生态中最成熟的异步运行时之一，为高性能网络应用提供了事件驱动、非阻塞 I/O 的基础设施。本文从源码层面深入解析 Tokio… | https://oldoldtea.github.io/2026/05/12/tokio-async-runtime/ |
| 5 | Tokio Runtime 架构剖析：一个 Task 的诞生与旅程 | github.io | Jul 13, 2026 · 要回答这个问题，就得了解 Tokio Runtime 内部，看清它的运作机制，而不是停留在"会用 tokio::spawn “的层面。 如果你想知道这… | https://orangex-position0.github.io/posts/rust/tokio-runtime-architecture/ |

## 11. 2026年 新能源汽车 补贴政策

**池 24**（候选 24 条，覆盖 0.98，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | smzdm.com | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. … | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 2026年新能源汽车补贴政策全解读：国补地补与购置税减免一文看懂 · 酷... | toolcool.cn | Apr 28, 2026 · 2026年新能源汽车补贴政策迎来重大调整，国家以旧换新补贴最高2万元、地方配套补贴差异显著、购置税减免延续至2027年底。本文系统梳理国补金额、地方补… | https://toolcool.cn/zh/i/china-ev-subsidy-policy-2026-full-guide/ |
| 3 | 2026年新能源汽车补贴政策官方文件核心解读 - 今日头条 | toutiao.com | Feb 8, 2026 · 结论：2026年新能源汽车补贴政策核心为“购置税减半+技术门槛升级+精准补贴倾斜”，执行期为2026年1月1日至2027年12月31日，官方核心文件为《… | https://www.toutiao.com/article/7604391218893554214/ |
| 4 | 2026年新能源汽车补贴新政深度解读！福利攻略与申领指南 | sohu.com | Dec 15, 2025 · 2026年新能源汽车补贴新政推出，实施“购置税减半+以旧换新”叠加政策，聚焦技术升级与老旧淘汰，补贴上限3万元，推动 ... | https://news.sohu.com/a/965361554_122542760 |
| 5 | 国补出炉！ 电车油车补贴揭晓-有驾 | bdstatic.com | 好消息是，2026年的购车补贴政策终于出来了，不管是电车还是油车，补贴额度是多少？新能源汽车补贴政策. 咱们再来看看置换补贴这块儿。 新能源汽车的最高补贴是1.5万元，也就是购车价… | https://youjia-pc.bdstatic.com/article/9608259256117415955.html |

**池 40**（候选 40 条，覆盖 0.98，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | smzdm.com | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. … | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 2026年新能源汽车补贴政策官方文件核心解读 - 今日头条 | toutiao.com | Feb 8, 2026 · 结论：2026年新能源汽车补贴政策核心为“购置税减半+技术门槛升级+精准补贴倾斜”，执行期为2026年1月1日至2027年12月31日，官方核心文件为《… | https://www.toutiao.com/article/7604391218893554214/ |
| 3 | 2026年新能源汽车补贴政策全解读：国补地补与购置税减免一文看懂 · 酷... | toolcool.cn | Apr 28, 2026 · 2026年新能源汽车补贴政策迎来重大调整，国家以旧换新补贴最高2万元、地方配套补贴差异显著、购置税减免延续至2027年底。本文系统梳理国补金额、地方补… | https://toolcool.cn/zh/i/china-ev-subsidy-policy-2026-full-guide/ |
| 4 | 2026年新能源汽车补贴新政深度解读！福利攻略与申领指南 | sohu.com | Dec 15, 2025 · 2026年新能源汽车补贴新政推出，实施“购置税减半+以旧换新”叠加政策，聚焦技术升级与老旧淘汰，补贴上限3万元，推动 ... | https://news.sohu.com/a/965361554_122542760 |
| 5 | 国补出炉！ 电车油车补贴揭晓-有驾 | bdstatic.com | 好消息是，2026年的购车补贴政策终于出来了，不管是电车还是油车，补贴额度是多少？新能源汽车补贴政策. 咱们再来看看置换补贴这块儿。 新能源汽车的最高补贴是1.5万元，也就是购车价… | https://youjia-pc.bdstatic.com/article/9608259256117415955.html |

## 12. 数据出境安全评估办法 最新

**池 24**（候选 24 条，覆盖 0.8261，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 数据出境安全评估办法-搜了智采 | 51gpg.com | 数据出境安全评估办法.第三条 数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 | https://www.51gpg.com/notice/detail_76.html |
| 2 | 数据出境安全评估办法.docx - 墨天轮文档 | modb.pro | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 3 | 数据出境安全评估办法 数据出境安全评估 | cicpa.org.cn | 《数据出境安全评估办法》已经 2022 年 5 月 19 日国家互联网信息办公室 2022 年第 10 次室务会议审议通过,现予公布,自 2022 年 9 月 1 日起施行。 | https://www.cicpa.org.cn/ztzl1/hyxxhckzl/zcyxs/202208/P020220802389102775836.pdf |
| 4 | 中国网络安全审查“组合拳”学者:全面管制时代来临 - 美国之音中文网 您可靠.... | voachinese.com | 2022.07.22.中国国家互联网信息办公室(网信办)针对网络审查再祭出一系列新规，除自8月1日起要求境内各网络平台严格核实使用者的身分外，也发布《数据出境安全评估办法》，严格管… | https://www.voachinese.com/a/china-launches-security-review-on-cnki-the-country-… |
| 5 | 国家网信办发布《数据出境安全评估申报指南（第三版）》 | toutiao.com | Jun 27, 2025 · 中新网6月27日电 据中国网信网消息，为了指导和帮助数据处理者规范有序申报数据出境安全评估，国家互联网信息办公室编制了《数据出境安全评估申报指南 (第… | https://www.toutiao.com/article/7520599274888004150/ |

**池 40**（候选 38 条，覆盖 0.8261，独立站点 5，新进 top5 2 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 数据出境安全评估办法-搜了智采 | 51gpg.com | 数据出境安全评估办法.第三条 数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 | https://www.51gpg.com/notice/detail_76.html |
| 2 | 数据出境安全评估办法.docx - 墨天轮文档 | modb.pro | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 3 | 数据出境安全评估办法 数据出境安全评估 | cicpa.org.cn | 《数据出境安全评估办法》已经 2022 年 5 月 19 日国家互联网信息办公室 2022 年第 10 次室务会议审议通过,现予公布,自 2022 年 9 月 1 日起施行。 | https://www.cicpa.org.cn/ztzl1/hyxxhckzl/zcyxs/202208/P020220802389102775836.pdf |
| 4 | 解读数据出境安全评估办法：未通过评估企业或面临结构性影响 | oeeee.com | 数据出境安全相关评估办法曾三次征求意见. 自2016年网络安全法通过审议以来，国家网信办三次对数据出境安全相关的评估办法征求意见。2021年，《数据出境安全评估办法（征求意见稿）》… | https://m.mp.oeeee.com/a/BAAFRD000020220708701121.html |
| 5 | 数据出境安全评估办法-聚名集团-举报平台 | juming.cn | 第三条 数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 | http://aq.juming.cn/show/524.html |

## 13. EU AI Act compliance requirements

**池 24**（候选 24 条，覆盖 1.0，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance Guide 2026 \| Requirements, Timeline ... | ia-gouvernance.com | Complete guide to EU AI Act compliance. Requirements, deadlines, risk classifications, and… | https://www.ia-gouvernance.com/ai-act-compliance-guide.html |
| 2 | EU AI Act Compliance \| Microsoft Trust Center | microsoft.com | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restrict… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 3 | EU AI Act Compliance Guide 2026 - compliquest.com | compliquest.com | Mar 29, 2026 · What Is the EU AI Act? The Complete Guide to Requirements and Compliance in… | https://www.compliquest.com/en/blog/what-is-eu-ai-act-requirements-2026 |
| 4 | EU AI Act: Summary & Compliance Requirements - modelop.com | modelop.com | The Act places a strong emphasis on protecting fundamental rights by mandating human overs… | https://www.modelop.com/ai-governance/ai-regulations-standards/eu-ai-act |
| 5 | EU AI Act Compliance Guide \| Sinaptic.AI | sinaptic.ai | For providers and deployers of GPAI (including chatbots like ChatGPT), there are strict tr… | https://sinaptic.ai/articles/eu-ai-act-compliance |

**池 40**（候选 40 条，覆盖 1.0，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance Guide 2026 \| Requirements, Timeline ... | ia-gouvernance.com | Complete guide to EU AI Act compliance. Requirements, deadlines, risk classifications, and… | https://www.ia-gouvernance.com/ai-act-compliance-guide.html |
| 2 | EU AI Act Compliance \| Microsoft Trust Center | microsoft.com | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restrict… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 3 | EU AI Act Compliance Guide 2026 - compliquest.com | compliquest.com | Mar 29, 2026 · What Is the EU AI Act? The Complete Guide to Requirements and Compliance in… | https://www.compliquest.com/en/blog/what-is-eu-ai-act-requirements-2026 |
| 4 | EU AI Act: Summary & Compliance Requirements - modelop.com | modelop.com | The Act places a strong emphasis on protecting fundamental rights by mandating human overs… | https://www.modelop.com/ai-governance/ai-regulations-standards/eu-ai-act |
| 5 | EU AI Act Compliance Guide \| Aona AI | aona.ai | Key innovations include the creation of AI regulatory sandboxes, mandatory conformity asse… | https://aona.ai/compliance/regulations/eu-ai-act/ |

## 14. 个人所得税 专项附加扣除 标准

**池 24**（候选 24 条，覆盖 1.0，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 2025年个人所得税专项附加扣除标准 - 知乎 | zhihu.com | 个人所得税专项附加扣除标准 2025年最新版 1.婴幼儿照护:2000/月/人。 出生当月至年满3周岁前一个月，一方扣2000/月或各扣1000 ... | https://zhuanlan.zhihu.com/p/18104581377 |
| 2 | 三项个人所得税专项附加扣除标准提高了！一图了解政策要点 | chinatax.gov.cn | Sep 1, 2023 · 三项个人所得税专项附加扣除标准提高了！ 一图了解政策要点 2023年09月01日 来源：税务总局新媒体、中国税务报社 【字体： 大 中 小】 打印本页 … | https://www.chinatax.gov.cn/chinatax/n810341/n2340339/c5211397/content.html |
| 3 | 2026个税专项附加扣除标准！附确认填报流程_腾讯新闻 | qq.com | Dec 12, 2025 · 蓝字关注，回复“11”获取更多信息2026年度个人所得税专项附加扣除信息开始进行确认啦个税专项附加扣除怎么填报?个税专项附加扣除标准是多少 ... | https://news.qq.com/rain/a/20251212A076NW00 |
| 4 | 事关你的钱袋子，今起确认！ \| 每日经济新闻 | nbd.com.cn | 各个项目. 分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。税务部门提醒. 个人所得税专项… | https://m.nbd.com.cn/articles/2025-12-01/4162702.html |
| 5 | 月底截止，事关收入！ 抓紧确认 | gmw.cn | 个税专项附加扣除信息确认. 开始啦！ 纳税人可通过个人所得税App.3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元… | https://m.gmw.cn/2025-12/02/content_1304246592.htm |

**池 40**（候选 37 条，覆盖 1.0，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 2025年个人所得税专项附加扣除标准 - 知乎 | zhihu.com | 个人所得税专项附加扣除标准 2025年最新版 1.婴幼儿照护:2000/月/人。 出生当月至年满3周岁前一个月，一方扣2000/月或各扣1000 ... | https://zhuanlan.zhihu.com/p/18104581377 |
| 2 | 三项个人所得税专项附加扣除标准提高了！一图了解政策要点 | chinatax.gov.cn | Sep 1, 2023 · 三项个人所得税专项附加扣除标准提高了！ 一图了解政策要点 2023年09月01日 来源：税务总局新媒体、中国税务报社 【字体： 大 中 小】 打印本页 … | https://www.chinatax.gov.cn/chinatax/n810341/n2340339/c5211397/content.html |
| 3 | 2026个税专项附加扣除标准！附确认填报流程_腾讯新闻 | qq.com | Dec 12, 2025 · 蓝字关注，回复“11”获取更多信息2026年度个人所得税专项附加扣除信息开始进行确认啦个税专项附加扣除怎么填报?个税专项附加扣除标准是多少 ... | https://news.qq.com/rain/a/20251212A076NW00 |
| 4 | 月底截止，事关收入！ 抓紧确认 | gmw.cn | 个税专项附加扣除信息确认. 开始啦！ 纳税人可通过个人所得税App.3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元… | https://m.gmw.cn/2025-12/02/content_1304246592.htm |
| 5 | 事关你的钱袋子，今起确认！ \| 每日经济新闻 | nbd.com.cn | 各个项目. 分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。税务部门提醒. 个人所得税专项… | https://m.nbd.com.cn/articles/2025-12-01/4162702.html |

## 15. children privacy law COPPA update

**池 24**（候选 24 条，覆盖 0.88，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | FTC’s Strengthened Children’s Online Privacy Rules Now... - Lexology | lexology.com | This update marks the FTC’s first rulemaking effort since 2013, and just the second overal… | https://www.lexology.com/library/detail.aspx?g=740d7be8-21f1-4696-9a95-7ff7638d3… |
| 2 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for … | digiday.com | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (CO… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure… |
| 3 | COPPA Rule Update 2026: What Changed + Compliance Checklist | privacylawmap.com | Mar 29, 2026 · Where State Law Goes Past COPPA: All 20 In-Force Laws Every one of the 20 s… | https://privacylawmap.com/blog/coppa-rule-amendments-april-2026-compliance-check… |
| 4 | Senator Says Federal Law Protecting Children Online Needs Updating | wsj.com | 2021.10.01.Sen. Maria Cantwell (D., Wash.)—who chairs the powerful Commerce Committee—said… | https://www.wsj.com/livecoverage/facebook-hearing-live-updates/card/TwUpnUNNG7lh… |
| 5 | Privacy Policy - The Wheeler School - N-12 Coed Day School in Providence RI | wheelerschool.org | COPPA Statement The Children’s Online Privacy Protection Act (COPPA) is a federal law gove… | https://www.wheelerschool.org/privacy-policy/ |

**池 40**（候选 40 条，覆盖 0.92，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | COPPA Children's Privacy Lawyer \| Richt Law Firm | richtfirm.com | Free Speech Battles and Age-Appropriate Balance: Maryland and Connecticut Try Again for Yo… | https://richtfirm.com/coppa-childrens-privacy-lawyer/ |
| 2 | COPPA Rule Update 2026: What Changed + Compliance Checklist | privacylawmap.com | Mar 29, 2026 · Where State Law Goes Past COPPA: All 20 In-Force Laws Every one of the 20 s… | https://privacylawmap.com/blog/coppa-rule-amendments-april-2026-compliance-check… |
| 3 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for … | digiday.com | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (CO… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure… |
| 4 | FTC’s Strengthened Children’s Online Privacy Rules Now... - Lexology | lexology.com | This update marks the FTC’s first rulemaking effort since 2013, and just the second overal… | https://www.lexology.com/library/detail.aspx?g=740d7be8-21f1-4696-9a95-7ff7638d3… |
| 5 | Senator Says Federal Law Protecting Children Online Needs Updating | wsj.com | 2021.10.01.Sen. Maria Cantwell (D., Wash.)—who chairs the powerful Commerce Committee—said… | https://www.wsj.com/livecoverage/facebook-hearing-live-updates/card/TwUpnUNNG7lh… |

## 16. iPhone 17 Pro 价格 参数

**池 24**（候选 24 条，覆盖 0.7，独立站点 3，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | iPhone8手机参数 - 京东 | jd.com | 京东是国内专业的iPhone8手机参数网上购物商城，本频道提供iPhone8手机参数商品图片，iPhone8手机参数价格，iPhone8手机参数多少钱信息，为您选购提供全方位iPh… | https://www.jd.com/hprm/998728323d21c0c6f006.html |
| 2 | Apple iPhone 17 Pro - 全面参数、价格与评测 \| Kalvo | kalvo.com | Apple iPhone 17 Pro 图赏 常见问题解答 Apple iPhone 17 Pro 的售价是多少？ Apple iPhone 17 Pro 当前售价为 $849，实… | https://zh.kalvo.com/apple-iphone-17-pro-186083.html |
| 3 | 【苹果iPhone 17 Pro】最新报价_参数_图片_论坛_苹果iPhone 17 Pro系... | zol.com.cn | ZOL中关村在线提供苹果iPhone 17 Pro系列手机所有单品的型号、报价、配置、评测、行情、图片、论坛、点评、视频、驱动下载等内容,以及苹果iPhone 17 Pro系列手机… | https://detail.zol.com.cn/series/57/10918584_1.html |
| 4 | 【苹果iPhone 17 Pro 256GB】报价_参数_图片_论坛_Apple iPhone 17 Pr... | zol.com.cn | 评测 iPhone 18 Pro暗网曝光 苹果依旧“刀法精准” 评测 iPhone 18 系列前瞻：十项升级能否打动“钉子户”？ 评测 iPhone Air零售版全面评测 美丽小废… | https://detail.zol.com.cn/cell_phone/index2139584.shtml |
| 5 | 苹果8x参数 - 京东 | jd.com | Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus e二手手机A16详见质检报告 苹果 iPhone 8荣耀亲选LCHSE … | https://www.jd.com/hprm/9987d46c01cd9b8ab46f.html |

**池 40**（候选 40 条，覆盖 0.72，独立站点 4，新进 top5 2 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | iPhone8手机参数 - 京东 | jd.com | 京东是国内专业的iPhone8手机参数网上购物商城，本频道提供iPhone8手机参数商品图片，iPhone8手机参数价格，iPhone8手机参数多少钱信息，为您选购提供全方位iPh… | https://www.jd.com/hprm/998728323d21c0c6f006.html |
| 2 | Apple iPhone 17 Pro - 全面参数、价格与评测 \| Kalvo | kalvo.com | Apple iPhone 17 Pro 图赏 常见问题解答 Apple iPhone 17 Pro 的售价是多少？ Apple iPhone 17 Pro 当前售价为 $849，实… | https://zh.kalvo.com/apple-iphone-17-pro-186083.html |
| 3 | 【苹果iPhone 17 256GB】报价_参数_图片_论坛_Apple iPhone 17,苹果 17,iPhone17苹果手机报.... | zol.com.cn | 中关村在线为您提供苹果iPhone 17 256GB 手机最新报价，同时包括苹果iPhone 17 256GB图片、苹果iPhone 17 256GB参数、苹果iPhone 17 … | https://detail.zol.com.cn/cell_phone/index2139583.shtml |
| 4 | 小米(mi)手机REDMI Note17报价_参数_图片_视频_怎么样_问答-苏宁易购 | suning.com | 苏宁易购提供小米(mi)手机REDMI Note17最新价格，包括优质商家报价、参数、图片、视频、问答、评价、怎么样等详细信息。关注苏宁易购，为您购买REDMI Note17 流星… | https://www.suning.com/item/0010366446/000000012452805109.html |
| 5 | 【苹果iPhone 17 Pro】最新报价_参数_图片_论坛_苹果iPhone 17 Pro系... | zol.com.cn | ZOL中关村在线提供苹果iPhone 17 Pro系列手机所有单品的型号、报价、配置、评测、行情、图片、论坛、点评、视频、驱动下载等内容,以及苹果iPhone 17 Pro系列手机… | https://detail.zol.com.cn/series/57/10918584_1.html |

## 17. best noise cancelling headphones 2026 review

**池 24**（候选 24 条，覆盖 0.9667，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | tiktok.com | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best cheap noise-cancelling headphones 2026: expert-tested recommendations \| Wha | whathifi.com | All review verdicts are agreed upon by the team rather than an individual reviewer to elim… | https://www.whathifi.com/best-buys/best-cheap-noise-cancelling-headphones |
| 3 | 11 Best Noise-Canceling Headphones of 2026: Top Tested, Reviewed Picks | rollingstone.com | 2026.04.23.Still, for everyday listening, these headphones are some of the best on the mar… | https://www.rollingstone.com/product-recommendations/tech/best-noise-canceling-h… |
| 4 | Best Noise-Cancelling Headphones 2026: Minimise ambient noise | trustedreviews.com | Best Noise-Cancelling Headphones 2026: Noise Cancel Culture.Learn more about how we test h… | https://www.trustedreviews.com/best/best-noise-cancelling-headphones-3440212 |
| 5 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | whathifi.com | Best noise-cancelling headphones 2026 – 6 sensational pairs picked by our expert reviewers… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |

**池 40**（候选 31 条，覆盖 0.9667，独立站点 4，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | tiktok.com | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best cheap noise-cancelling headphones 2026: expert-tested recommendations \| Wha | whathifi.com | All review verdicts are agreed upon by the team rather than an individual reviewer to elim… | https://www.whathifi.com/best-buys/best-cheap-noise-cancelling-headphones |
| 3 | Best Noise-Cancelling Headphones 2026: Minimise ambient noise | trustedreviews.com | Best Noise-Cancelling Headphones 2026: Noise Cancel Culture.Learn more about how we test h… | https://www.trustedreviews.com/best/best-noise-cancelling-headphones-3440212 |
| 4 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | whathifi.com | Best noise-cancelling headphones 2026 – 6 sensational pairs picked by our expert reviewers… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |
| 5 | 11 Best Noise-Canceling Headphones of 2026: Top Tested, Reviewed Picks | rollingstone.com | 2026.04.23.Still, for everyday listening, these headphones are some of the best on the mar… | https://www.rollingstone.com/product-recommendations/tech/best-noise-canceling-h… |

## 18. 扫地机器人 推荐 性价比

**池 24**（候选 24 条，覆盖 0.9579，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 【26... | bilibili.com | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 石头P20 Max vs... \| 新浪网 | sina.com.cn | 石头P20 Max vs 同价位扫地机，谁才是性价比之王？ 3个维度硬核对比+FAQ.关键字 : 石头P20 Max 扫地机器人推荐 高性价比扫地机 同价位扫地机对比 2026年扫… | https://k.sina.com.cn/article_7879923199_1d5ae15ff06801jub0.html |
| 3 | 2026年扫地机器人推荐，全价位20＋款扫地机器人强强对比！_扫拖一体机... | smzdm.com | Jan 6, 2026 · 四、高性价比扫地机器人推荐 1.追觅S50 Pro 新推出的追觅S50 Pro再次让我眼前一亮，其性能配置可以说是25年同价位机型中最值得入手的一款。 … | https://post.smzdm.com/p/a3rzr5dn/ |
| 4 | 2026扫地机器人推荐：4款高性价比机型深度对比，懒人必看选购指南 | sohu.com | Sep 11, 2026 · 四、铭汇通全自动扫地机器人：百元级性价比之王，养宠入门首选 如果你预算特别紧张（甚至不到500元），但又想体验扫地机器人的便利，铭汇通这款值得一试。 … | https://www.sohu.com/a/1074826860_122645061 |
| 5 | 2026年扫地机器人推荐，全价位20＋款扫地机器人强强对比！ (石头/科沃... | zhihu.com | 快速选购区 后面科普内容比较长，我已经帮大家总结出几款高性价比的扫地机器，没时间的小伙伴可以直接选购。 追觅X60 Pro Steam 这次推出的追觅X60 Pro Steam配置… | https://www.zhihu.com/tardis/zm/art/504267054 |

**池 40**（候选 38 条，覆盖 0.9579，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 【26... | bilibili.com | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 石头P20 Max vs... \| 新浪网 | sina.com.cn | 石头P20 Max vs 同价位扫地机，谁才是性价比之王？ 3个维度硬核对比+FAQ.关键字 : 石头P20 Max 扫地机器人推荐 高性价比扫地机 同价位扫地机对比 2026年扫… | https://k.sina.com.cn/article_7879923199_1d5ae15ff06801jub0.html |
| 3 | 2026年扫地机器人推荐，全价位20＋款扫地机器人强强对比！_扫拖一体机... | smzdm.com | Jan 6, 2026 · 四、高性价比扫地机器人推荐 1.追觅S50 Pro 新推出的追觅S50 Pro再次让我眼前一亮，其性能配置可以说是25年同价位机型中最值得入手的一款。 … | https://post.smzdm.com/p/a3rzr5dn/ |
| 4 | 2026扫地机器人推荐：4款高性价比机型深度对比，懒人必看选购指南 | sohu.com | Sep 11, 2026 · 四、铭汇通全自动扫地机器人：百元级性价比之王，养宠入门首选 如果你预算特别紧张（甚至不到500元），但又想体验扫地机器人的便利，铭汇通这款值得一试。 … | https://www.sohu.com/a/1074826860_122645061 |
| 5 | 2026年扫地机器人推荐，全价位20＋款扫地机器人强强对比！ (石头/科沃... | zhihu.com | 快速选购区 后面科普内容比较长，我已经帮大家总结出几款高性价比的扫地机器，没时间的小伙伴可以直接选购。 追觅X60 Pro Steam 这次推出的追觅X60 Pro Steam配置… | https://www.zhihu.com/tardis/zm/art/504267054 |

## 19. RTX 5090 benchmark 价格

**池 24**（候选 24 条，覆盖 0.7667，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | NVIDIA GeForce RTX 5090 — 价格、规格与跑分 | hardwarerk.com | Sep 1, 2026 · NVIDIA GeForce RTX 5090 现在多少钱？ 截至 2026-09-15，NVIDIA GeForce RTX 5090 的最低观测价格… | https://hardwarerk.com/zh-CN/gpu/rtx-5090 |
| 2 | GeForce RTX 5090 价格（美国） — 历史价格、优惠与规格 | gpuprix.com | Jul 25, 2026 · GeForce RTX 5090 在 美国 的价格历史：当前最低 $6,795 USD，12 个月最低 $1,300 USD，12 个月中位数 $3,… | https://gpuprix.com/zh/us/gpus/geforce-rtx-5090 |
| 3 | 5090显卡国内价格 - 爱企查 | baidu.com | Sep 21, 2026 · 中国市场上 RTX 5090 显卡价格目前分化明显，官方指导价与现货市场价差距巨大。RTX 5090D 中国特供版官网起售价为16499 元，而标准版… | https://aiqicha.baidu.com/details/ugknowledge?id=206279f6bc15d9a5219986c8c086c5e… |
| 4 | GeForce RTX 5090 价格与二手行情：能部署哪些大模型？ | vramglass.com | 1 day ago · GeForce RTX 5090 租用价格 GeForce RTX 5090 在优云智算按需租用每小时 ¥3.15，每天用 8 小时约 ¥766/月。 买一… | https://vramglass.com/zh/gpu/rtx-5090 |
| 5 | A thorough insight into technical specs and benchmarks of RTX 5090. | technical.city | Synthetic benchmark performance of GeForce RTX 5090. The combined score is measured on a 0… | https://technical.city/en/gpu/GeForce-RTX-5090 |

**池 40**（候选 40 条，覆盖 0.8333，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | NVIDIA GeForce RTX 5090 — 价格、规格与跑分 | hardwarerk.com | Sep 1, 2026 · NVIDIA GeForce RTX 5090 现在多少钱？ 截至 2026-09-15，NVIDIA GeForce RTX 5090 的最低观测价格… | https://hardwarerk.com/zh-CN/gpu/rtx-5090 |
| 2 | GeForce RTX 5090 价格（美国） — 历史价格、优惠与规格 | gpuprix.com | Jul 25, 2026 · GeForce RTX 5090 在 美国 的价格历史：当前最低 $6,795 USD，12 个月最低 $1,300 USD，12 个月中位数 $3,… | https://gpuprix.com/zh/us/gpus/geforce-rtx-5090 |
| 3 | 5090显卡国内价格 - 爱企查 | baidu.com | Sep 21, 2026 · 中国市场上 RTX 5090 显卡价格目前分化明显，官方指导价与现货市场价差距巨大。RTX 5090D 中国特供版官网起售价为16499 元，而标准版… | https://aiqicha.baidu.com/details/ugknowledge?id=206279f6bc15d9a5219986c8c086c5e… |
| 4 | GeForce RTX 5090 价格与二手行情：能部署哪些大模型？ | vramglass.com | 1 day ago · GeForce RTX 5090 租用价格 GeForce RTX 5090 在优云智算按需租用每小时 ¥3.15，每天用 8 小时约 ¥766/月。 买一… | https://vramglass.com/zh/gpu/rtx-5090 |
| 5 | RTX 5090 来了，性能飙升 70%，价格逼近 2 万 - 36氪 | 36kr.com | 没关系。 一句话总结：RTX 5090 的整体性能预计比 RTX 4090 提升 70% 左右，其光栅化性能预计提高 60%，光线追踪性能提高 2.5倍，计算能力提升 2 倍。 | https://www.36kr.com/p/2991033083964421 |

## 20. 国产显卡 摩尔线程 最新型号

**池 24**（候选 24 条，覆盖 0.713，独立站点 5，新进 top5 0 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 国产显卡品牌摩尔线程发新卡 单卡48GB显存_凤凰网 | ifeng.com | 国产显卡品牌摩尔线程，终于又要发新显卡了。这张显卡的具体型号为MTT S4000，规格方面非常不错。 国产显卡品牌摩尔线程发新卡 单卡48GB显存. | https://i.ifeng.com/c/8VfiImHtDxn |
| 2 | 新GPU、新AI卡、新显卡全来了？摩尔线程MDC最新爆料汇总 | sohu.com | Dec 17, 2025 · 近两年摩尔集中精力在搞AI智算卡和千卡万卡中心，同时，消费级显卡产品线却迟迟没有更新。 S80 至今已发布两年多，每个月还在更新驱动，支持Direct… | https://www.sohu.com/a/966178550_627777 |
| 3 | MTTS70显卡多少钱_摩尔线程MTTS70国产显卡售价及参数-硬件之家 | yingjianzhijia.com | 摩尔线程MTTS70国产显卡售价及参数. 发售价格：2499元. 品牌：摩尔线程. 型号：MTTS70. 显卡核心：春晓. 核心频率：1.6GHz. | https://www.yingjianzhijia.com/zhishi/76390.html |
| 4 | 摩尔线程： 国产GPU黑马突破算力封锁 最新芯片性能追平英伟达 | toutiao.com | Dec 18, 2025 · 国产GPU迎来里程碑突破！ 摩尔线程今日正式发布第三代GPU芯片MTT S4000 ，采用全新架构设计 ，AI算力性能达到英伟达A100水平的85% … | https://www.toutiao.com/article/7585174075341816339/ |
| 5 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | mydrivers.com | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |

**池 40**（候选 38 条，覆盖 0.7217，独立站点 5，新进 top5 1 条）

| 排名 | 标题 | 域名 | 摘要 | URL |
| --- | --- | --- | --- | --- |
| 1 | 国产显卡品牌摩尔线程发新卡 单卡48GB显存_凤凰网 | ifeng.com | 国产显卡品牌摩尔线程，终于又要发新显卡了。这张显卡的具体型号为MTT S4000，规格方面非常不错。 国产显卡品牌摩尔线程发新卡 单卡48GB显存. | https://i.ifeng.com/c/8VfiImHtDxn |
| 2 | 新GPU、新AI卡、新显卡全来了？摩尔线程MDC最新爆料汇总 | sohu.com | Dec 17, 2025 · 近两年摩尔集中精力在搞AI智算卡和千卡万卡中心，同时，消费级显卡产品线却迟迟没有更新。 S80 至今已发布两年多，每个月还在更新驱动，支持Direct… | https://www.sohu.com/a/966178550_627777 |
| 3 | MTTS70显卡多少钱_摩尔线程MTTS70国产显卡售价及参数-硬件之家 | yingjianzhijia.com | 摩尔线程MTTS70国产显卡售价及参数. 发售价格：2499元. 品牌：摩尔线程. 型号：MTTS70. 显卡核心：春晓. 核心频率：1.6GHz. | https://www.yingjianzhijia.com/zhishi/76390.html |
| 4 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | mydrivers.com | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |
| 5 | 首款国产游戏显卡摩尔线程MTTS80上架,售价2999元－win7之家 | win7zhijia.cn | 首款国产游戏显卡摩尔线程MTTS80上架,售价2999元. 2022-11-11 09:13.据官方介绍，MTT S80 是国内首款支持 Windows 环境和 DirectX 图… | https://www.win7zhijia.cn/win10jc/win10_50648.html |


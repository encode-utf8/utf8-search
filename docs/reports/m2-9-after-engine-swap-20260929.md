# 相关性抽检报告（验收项 2-9）

- 生成时间：2026-09-29 13:13:03
- 深度模式：basic，每条取前 5 条
- 查询构成：20 条中英混合，覆盖 新闻 / 技术 / 政策 / 商品 各 5 条
- **采集缓存状态**：已禁用缓存（`--no-cache`），全部为本次实时采集

## 打分规则（先读这三条）

1. **门槛**：20 条查询里，满足「top5 中相关条数 ≥ 4」的查询数要 **≥ 18 条**（即 ≥ 90%）。
2. **scores 的 5 位依次对应排名 1-5**（第 1 位 = 排名第 1 的结果），逐位填 0/1。
3. **非零数字一律视为「相关」**（填 1 最规范；填 2 或其它非零值同样按相关计）。

- 判定命令：`python scripts/relevance.py --score-file m2-9-after-engine-swap-20260929-scores.csv`
- 通过标准（脚本口径）：top5 中相关数 ≥ 4 的查询占比 ≥ 90%
- 速览版（不带正文字数/发布时间/URL）：`m2-9-after-engine-swap-20260929-brief.md`

## 1. [新闻] 2026年9月 国内外重大新闻

引擎：searxng；失败引擎：privacywall, resulthunter, yep
卫生度：覆盖 0.46（最低 0.42） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | “平平”和“福双”前驻亚特兰大动物园 中国与美恢复“熊猫外交” | www.rfi.fr | 146 | 2026-09-27T09:47:57 | 发表时间： 27/09/2026 - 10:01更改时间： 28/09/2026 - 14:02. 6 分钟 浏览时间.此外，今年早些时候，由于日本首相暗示若发生针对台湾的袭击日本可能会进行军事干预，… | https://www.rfi.fr/cn/%E4%B8%AD%E5%9B%BD/20260927-%E4%B8%A4%E5%8F%AA%E5%A4%A7%E7%86%8A%E7%8C%AB%E5%90%AF%E7%A8%8B%E5%89%8D%E5%BE%80%E4%BA%9A%E7%89%B9%E5%85%B0%E5%A4%A7%E5%8A%A8%E7%89%A9%E5%9B%AD-%E4%B8%AD%E5%9B%BD%E4%B8%8E%E7%BE%8E%E6%81%A2%E5%A4%8D-%E7%86%8A%E7%8C%AB%E5%A4%96%E4%BA%A4 |
| 2 | 2026 年 9 月 26 日新闻速览：高铁、假期与明星动... | www.sina.cn | 96 | 2026-09-26T07:11:00 | 2026 年 9 月 26 日新闻速览涵盖高铁开通、政策发布、灾害预警及娱乐活动，包括京港高铁雄商段等四条线路集中开通运营，10 部门联合促进房车消费，纪念长征胜利 90 周年展览开放，... | https://www.sina.cn/weibo/detail/5347294804182542.html |
| 3 | 美国之音中文网新闻 - 美国之音中文网 | www.voachinese.com | 154 | 2026-09-26T15:15:15 | 唐纳德·特朗普总统在结束接待中国国家主席习近平对美国进行的三天国事访问之际表示，美国展示了实力以及与中国的友谊。这次在华盛顿举行的美中元首峰会在星期五(9月25日)结束。特朗普宣布今年还会与习近平有两… | https://www.voachinese.com/z/1739 |
| 4 | 商务部召开例行新闻发布会（2026年9月3日） | www.mofcom.gov.cn | 78 | - | 3 Sept 2026 · 9月2日,习近平主席与埃及总统塞西举行会谈,就深化双边关系和拓展各领域务实合作达成广泛共识,为下阶段中埃经贸关系发展指明了方向。 | https://www.mofcom.gov.cn/xwfbzt/2026/swbzklxxwfbh2026n9y3r/index.html |
| 5 | SBS一周大事件（2026年9月18日） | www.sbs.com.au | 230 | 2026-09-18 | 2주 전澳大利亚政府公布重大移民政策改革方案；中国出入境新规生效，公民出境或需接受面谈；美联储无视总统特朗普降息要求，三年内首次加息；欧盟委员会主席提议让加拿大成为欧盟首个“联席成员”。 欢迎下载应用… | https://www.sbs.com.au/language/chinese/zh-hans/podcast-episode/weekly-news-wrap-20260918/qw26jpdga |

## 2. [新闻] 最近一周 AI 行业动态

引擎：searxng；失败引擎：-
卫生度：覆盖 0.39（最低 0.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | AI行业发展一周动态 - 知乎专栏 | zhuanlan.zhihu.com | 91 | - | 26 Dec 2025 · 一、 市场运行与行业趋势. 火山引擎发布豆包大模型运营数据及企业级智能体平台[1][2]. 豆包日均Tokens使用量突破50万亿，居中国第一、全球第三。 | https://zhuanlan.zhihu.com/p/1987970291440304627 |
| 2 | AI行业发展一周动态 - 知乎 | zhuanlan.zhihu.com | 139 | - | 2025年全球端侧AI市场规模将增至1.22万亿元年复合增长率达40%[2] · 2025年12月9日，谷歌公布智能眼镜Project Aura和Android XR系统关键细节，理想汽车发布首款AI… | https://zhuanlan.zhihu.com/p/1983093760448542417 |
| 3 | 每日AI资讯、热点、动态、融资、产品发布 - AI工具集 | ai-bot.cn | 201 | - | 面壁智能联合 OpenBMB 开源 ForgeStencil，全球首个 AI 驱动的 Stencil 全自动优化系统。ForgeStencil由 Kernel Agent 与 App Agent 双智… | https://ai-bot.cn/daily-ai-news/ |
| 4 | 每周必知5件AI大事 | www.aiposthub.com | 102 | - | OpenAI 估值突破5000 億美元，成為全球最貴未上市公司；Sora 2 + 社交影片App 正式登場；開發者大會釋出Apps SDK 與AgentKit，讓ChatGPT 蛻變為AI 經濟作業系… | https://www.aiposthub.com/weekly-ai-news-top5/ |
| 5 | nocache - npm | www.npmjs.com | 210 | - | Middleware to destroy caching. Latest version: 4.0.0, last published: 3 years ago. Start using nocac… | https://www.npmjs.com/package/nocache |

## 3. [新闻] latest news semiconductor export controls

引擎：searxng；失败引擎：-
卫生度：覆盖 0.64（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | What's the latest with semiconductor export controls? \| Reuters | www.reuters.com | 153 | 2026-09-23 | 6 days ago · Anthony Rapa of Blank Rome LLP discusses recent developments in U.S. export controls on… | https://www.reuters.com/legal/legalindustry/whats-latest-with-semiconductor-export-controls--pracin-2026-09-23/ |
| 2 | Semiconductor Latest News \| SIA \| Semiconductor Industry... | www.semiconductors.org | 179 | - | Latest News. Press Release: 09/04/26.Chip Design and R&DEnvironment, Health & SafetyExport Control a… | https://www.semiconductors.org/news-events/latest-news/ |
| 3 | China lashes out at latest U.S. export controls on chips | www.asahi.com | 200 | - | BEIJING--China on Saturday criticized the latest U.S. decision to tighten export controls that would… | https://www.asahi.com/ajw/articles/14738636 |
| 4 | Semiconductor Export Controls in 2026: Dual-Use Risk, Re-export... | frilinglaw.com | 186 | - | This article explains semiconductor export controls in 2026, with special focus on dual-use risk, re… | https://frilinglaw.com/blog/semiconductor-export-controls |
| 5 | SIA Statement on New Export Controls - Semiconductor Industry Association | www.semiconductors.org | 222 | - | 2022.10.07.WASHINGTON—Oct. 7, 2022—The Semiconductor Industry Association (SIA) today released the f… | http://www.semiconductors.org/sia-statement-on-new-export-controls/ |

## 4. [新闻] 台风 最新消息 路径

引擎：searxng；失败引擎：brave
卫生度：覆盖 0.77（最低 0.47） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 3

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026年台风红霞最新消息（附实时路径查询入口）- 泉州本地宝 | m.qz.bendibao.com | 74 | - | 2026年台风红霞最新消息（附实时路径查询入口）.2026年台风红霞最新消息（附实时路径查询入口）. 台风“红霞”最新实时路径查询入口：中央气象台. | https://m.qz.bendibao.com/news/38203.shtm |
| 2 | 刚刚！ 台风“丹娜丝”路径有变！ 或在福建浙江登陆 | c.m.163.com | 60 | - | 注意！ 90度拐弯. 台风“丹娜丝”路径有变化. 或在闽浙沿海登陆. 台风最新消息. 中央气象台消息. 7月5日13时. | https://c.m.163.com/news/a/K3NE3U0Q0550IMZX.html?spss=sps_sem |
| 3 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | gz.bendibao.com | 120 | - | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级，台风级或强台风级）… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 4 | 舒力基 - 中央气象台台风网 | typhoon.nmc.cn | 77 | - | 台风路径实时发布系统是由中央气象台权威发布台风信息 ... 台风“舒力基”最新位置：北纬23.6度， 东经127.1度，中心附近最大风力11级. 触屏版. | https://typhoon.nmc.cn/web.html |
| 5 | 台风路径预报 | m.nmc.cn | 54 | - | 台风快讯与报文. 台风路径预报. 台风公报. 台风预警.台风综合信息. 台风海洋. 台风路径预报. 麦德姆. | https://m.nmc.cn/publish/typhoon/probability-img3.html |

## 5. [新闻] 美国 关税 最新政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.65（最低 0.47） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 关税，突发！美国宣布：豁免！ - 证券时报 | www.stcn.com | 82 | - | 6 Sept 2025 · 美国关税政策迎来重大调整。 据最新消息，美国总统特朗普宣布，从全球国别关税中豁免石墨、钨、铀、金条等金属产品，同时将硅产品纳入征税清单。 | https://www.stcn.com/article/detail/3325589.html |
| 2 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | www.edurew.com | 161 | - | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协会近日表示，根据最新… | https://www.edurew.com/html/03c79099206.html |
| 3 | Temu 和 Shein... | www.100ec.cn | 102 | - | 9 日起取消 Google 购物平台所有支出，并于 4 月 25 日因 “全球贸易规则和关税致运营费用上涨” 进行价格调整，Shein 也将在同日实施相同举措。 一、政策背景：特朗普政府关税新政及其影… | https://www.100ec.cn/detail--6648723.html |
| 4 | 一文读懂特朗普最新关税措施：他宣布的最新全球关税将如何 ... | www.bbc.com | 96 | - | 22 Feb 2026 · 新的15%关税将从2月24日美国东部时间凌晨12点01分（格林威治时间上午5点01分）开始，对所有进口到美国的商品征税，无论商品来自哪个国家。 白宫官员告诉 ... | https://www.bbc.com/zhongwen/articles/c20zp13zgjro/simp |
| 5 | 美国进口关税追踪器- 当前税率和状态 - Zonos | zonos.com | 78 | - | 美国小额关税豁免自2025年8月29日起暂停。这意味着进入美国的每项进口都将产生关税。价值少于800美元的邮政货物必须预先支付关税- 截至2026年 ... | https://zonos.com/zh/docs/guides/us-tariff-changes |

## 6. [技术] Python 3.13 新特性

引擎：searxng；失败引擎：-
卫生度：覆盖 0.68（最低 0.38） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 好学编程：Python 3.13 这些新特性你一定要知道！ | zhuanlan.zhihu.com | 102 | - | 16 Dec 2024 · Python 3.13 已于2024 年10 月7 日正式发布。作为Python 的最新版本，它带来了多项令人振奋的新特性和改进。本文好学编程将为你详细介绍这些重要更新 .… | https://zhuanlan.zhihu.com/p/12824443094 |
| 2 | 【Python 3.13】新特性解读，重大改进建议升级：JIT编译、免GIL | blog.csdn.net | 109 | - | 26 Nov 2024 · 1. 提升交互式解释器(REPL)体验 · 彩色提示符: 更直观的交互体验。 · 简化命令: REPL专属命令不再需要括号调用，例如exit、clear、help等。 · … | https://blog.csdn.net/weixin_42212872/article/details/144067816 |
| 3 | Python 3.13 有什么新变化— Python 3.16.0a0 文档 | docs.python.org | 99 | - | Python 3.13 Python 编程语言的一个稳定发布版，包含多项针对语言、实现和标准库的改变。 最大的变化包括一个新的交互式解释器，对于在自由线程模式 (PEP 703) 下运行以及 ... | https://docs.python.org/zh-cn/dev/whatsnew/3.13.html |
| 4 | Python 3.13 的最佳新功能 | www.reddit.com | 102 | - | 7 Oct 2024 · Python 3.13 的最佳新功能 · 块级编辑，这对于经常编写代码或大量使用REPL 的人来说是一个巨大的解脱 · 智能粘贴：现在粘贴代码块直接就能用 · 智能复制： .… | https://www.reddit.com/r/Python/comments/1fyeo1g/python_313s_best_new_features/?tl=zh-hans |
| 5 | python@3.13 | formulae.brew.sh | 47 | - | Formula JSON API: /api/formula/python@3.13.json | https://formulae.brew.sh/formula/python@3.13 |

## 7. [技术] MCP protocol specification 2026

引擎：searxng；失败引擎：-
卫生度：覆盖 0.90（最低 0.75） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 다음 MCP 스펙 릴리즈(2026-07-28)의 주요 내용: Stateless 전환 및 공식 확장 도입 예.... | discuss.pytorch.kr | 222 | - | 2026.05.27.MCP 스펙 릴리즈 후보(The 2026-07-28 MCP Specification Release Candidate) 소개 Model Context Protoc… | https://discuss.pytorch.kr/t/mcp-2026-07-28-stateless/10387 |
| 2 | The 2026-07-28 Specification \| Model Context Protocol Blog | blog.modelcontextprotocol.io | 222 | - | 2026.07.28.The 2026-07-28 Model Context Protocol specification is out, bringing a stateless protocol… | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| 3 | Specification - What is the Model Context Protocol (MCP)? | modelcontextprotocol.io | 279 | - | 5일 전You are viewing an older version (2026-07-28) of the specification. View the latest version (lat… | https://modelcontextprotocol.io/specification/2026-07-28 |
| 4 | Specification and documentation for the Model Context Protocol | github.com | 159 | - | MCP protocol schema; Official MCP documentation. The schema is defined in TypeScript first, but made… | https://github.com/modelcontextprotocol/modelcontextprotocol |
| 5 | MCP goes stateless — and Postman's ready \| Postman Blog | blog.postman.com | 238 | - | The next Model Context Protocol specification (2026-07-28) lands on July 28. Postman’s MCP Inspector… | https://blog.postman.com/mcp-goes-stateless-and-postmans-ready/ |

## 8. [技术] FastAPI 与 Django 性能对比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.78（最低 0.64） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Flask、Django与FastAPI：全面比较与实战指南 - 知乎专栏 | zhuanlan.zhihu.com | 94 | - | 11 Mar 2024 · 性能对比 FastAPI通常提供最佳性能,特别是在利用其异步功能时。 Flask适合轻量级应用,性能适中。 Django由于其全包式的特性,可能在性能上略逊一筹 | https://zhuanlan.zhihu.com/p/686300460 |
| 2 | Django 与 FastAPI 架构对比：学习路径指南Django 与 FastAPI... | juejin.cn | 59 | - | Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。 本文将详解如何对两者进行评估选择。 | https://juejin.cn/post/7565799761123786806 |
| 3 | 下一代Python Web 框架？FastAPI 全面解析与实战对比 - 稀土掘金 | juejin.cn | 105 | - | 6 Aug 2025 · 3、关键维度深度对比 ; 性能, 依赖WSGI 服务器，性能良好但非顶尖。 基于ASGI，异步原生支持，性能极高（与Node.js/Go 比肩）。 ; 开发效率, 灵活但需自… | https://juejin.cn/post/7535277686312091686 |
| 4 | FastAPI 与 Django：2026 年最佳 Python 框架 | www.lastingdynamics.com | 79 | - | FastAPI vs Django for Startups（MVP）.FastAPI 与 Django 的主要区别. 性能比较. 异步功能. 开发人员体验. | https://www.lastingdynamics.com/zh/blog/fastapi-vs-django/ |
| 5 | Django 和FastAPI 的区别：全面对比与选择指南原创 - CSDN博客 | blog.csdn.net | 98 | - | 4 May 2025 · 【摘要】在Python生态中，Django与FastAPI代表了两种截然不同的开发哲学：全栈框架的厚重与API优先的敏捷。本文从性能、生态、安全等八大维度深度剖析 ... | https://blog.csdn.net/yuntongliangda/article/details/147689885 |

## 9. [技术] how does HTTP/3 QUIC work

引擎：searxng；失败引擎：-
卫生度：覆盖 0.80（最低 0.67） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | QUIC Protocol: How It Works, HTTP/3, and Enterprise Security | www.zscaler.com | 277 | - | QUIC Protocol Explained: How It Works, Why It's Faster Than TCP, and What It Means for Enterprise Se… | https://www.zscaler.com/blogs/product-insights/quic-secure-communication-protocol-shaping-future-of-internet |
| 2 | The Future of the Internet is here: QUIC Protocol and HTTP/3 \| Medium | medium.com | 266 | - | How does QUIC work? Unlike TCP, which uses a connection-oriented approach, QUIC uses a multiplexed s… | https://medium.com/@luisrodri/the-future-of-the-internet-is-here-quic-protocol-and-http-3-d7061adf424f |
| 3 | What Are QUIC and HTTP/3? - F5 | www.f5.com | 266 | - | HTTP/3, based on QUIC, is the third major version of the Hypertext Transfer Protocol (HTTP) and was … | https://www.f5.com/glossary/quic-http3 |
| 4 | How QUIC Works: From UDP Packets to HTTP/3 | www.linkedin.com | 228 | - | QUIC = transport protocol. HTTP/3 = HTTP mapping that uses QUIC. Other application protocols can use… | https://www.linkedin.com/pulse/how-quic-works-from-udp-packets-http3-chengfa-wang-lqlsc |
| 5 | HTTP/3 is Fast! - Request Metrics 🦥 | requestmetrics.com | 304 | - | 2025.02.19.HTTP/3 promises speed and efficiency, but does it actually deliver? In our latest article… | https://requestmetrics.com/web-performance/http3-is-fast/ |

## 10. [技术] Rust async runtime tokio 原理

引擎：searxng；失败引擎：-
卫生度：覆盖 0.74（最低 0.57） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Rust Async + Tokio 入門：非同步 Rust vs Python asyncio · 每日拍拍 | dailypypy.org | 106 | - | Rust：tokio::sync::mpsc. 八、底層原理：Python vs Rust 的非同步模型.features = ["full"] 會啟用所有功能（runtime、net、time、sy… | https://dailypypy.org/learn/rust-async-tokio/ |
| 2 | Tokio 任务调度原理分析 - Rust Magazine | rustmagazine.org | 101 | - | async Future 是Rust 中实现异步的基础,代表一个异步执行的计算任务, 。Tokio 是社区内使用最为广泛的异步运行时,它内部采用各种措施来保证Future 被公平、及时的调度执行 ..… | https://rustmagazine.org/issue-4/how-tokio-schedule-tasks-zh/ |
| 3 | 理解tokio的核心(1): runtime - Rust入门秘籍 | rust-book.junmajinlong.com | 152 | - | 要使用tokio，需要先创建它提供的异步运行时环境(Runtime)，然后在这个Runtime中执行异步任务。 使用 tokio::runtime 创建Runtime：. use tokio; ...… | https://rust-book.junmajinlong.com/ch100/01_understand_tokio_runtime.html |
| 4 | 理解tokio的核心(1): runtime - Rust入門祕籍 | shihyu.github.io | 85 | - | 要使用tokio，需要先創建它提供的異步運行時環境(Runtime)，然後在這個Runtime中執行異步任務。 使用 tokio::runtime 創建Runtime：. | https://shihyu.github.io/rust_hacks/ch100/01_understand_tokio_runtime.html |
| 5 | Async Rust: async/await and the Tokio Runtime — LabHub Blog | labhub.hopto.org | 106 | - | Introduction — Why Async Rust Is DifferentA Future Is a Lazy State MachineThe Executor and Runtime —… | https://labhub.hopto.org/blog/2026-06-29-rust-async-tokio?lang=en |

## 11. [政策] 2026年 新能源汽车 补贴政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.91（最低 0.85） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | post.smzdm.com | 139 | - | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. 新能源汽车补贴政策延… | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 别光顾着过年，快来买车 625亿元“国补”已经发放 - OFweek新能源汽车网 | nev.ofweek.com | 75 | - | 从2025年末开始，国内汽车消费市场便进入了政策切换的过渡期——原有的新能源汽车购置税免征政策、汽车以旧换新补贴政策逐步收尾，而2026年新的政策尚. | https://nev.ofweek.com/2026-02/ART-71000-8420-30681174.html |
| 3 | 多地加码购车补贴 重庆首次将“电驴”纳入购新政策范围 _ 东方财富网 - 财经.... | finance.eastmoney.com | 138 | - | 2026.08.03.多地为促进汽车消费正在陆续推出购车消费补贴。8月1日，西安市发布汽车消费补贴政策，个人消费者购买纳入《减免车辆购置税的新能源汽车车型目录》的新能源乘用车，按照购车发票价格的2%给… | https://finance.eastmoney.com/a/202608033829764288.html |
| 4 | 2026年4月汽车国补置换2万元申请全攻略：手把手教你领到国家补贴 | www.zhihu.com | 72 | - | 2026年，国家继续实施汽车以旧换新补贴政策，也就是大家常说的“国补”。补贴金额： · 买新能源车 → 按新车销售价格的12%补贴，最高2万元. | https://www.zhihu.com/tardis/jm/art/2033119484798616793 |
| 5 | qdzb07b20260116C | epaper.qingdaonews.com | 77 | - | 2026 年伊始新一轮购车国补新政正式落地实施。 此次新政不仅对补贴模式进行了优化还 同步调整了新能源汽车购置税优惠政策形成“国补+税补”的双重让利格局。 | https://epaper.qingdaonews.com/qdzb/resfile/2026-01-16/A07/qdzb-20260116-A07.pdf |

## 12. [政策] 数据出境安全评估办法 最新

引擎：searxng；失败引擎：-
卫生度：覆盖 0.83（最低 0.83） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 数据出境安全评估办法.docx - 墨天轮文档 | www.modb.pro | 70 | - | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 2 | 《数据出境安全评估办法》主要制度和常见误解 | www.secrss.com | 78 | - | 14 Jul 2022 · 2022年7月7日,国家互联网信息办公室发布《数据出境安全评估办法》(下称“《出境评估办法》”),并将于2022年9月1日施行。 | https://www.secrss.com/articles/44687 |
| 3 | 数据出境安全评估办法 - 百度百科 | baike.baidu.com | 83 | - | 《数据出境安全评估办法》是为了规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，根据《中华人民共和国网络安全法》、《 ... | https://baike.baidu.com/item/%E6%95%B0%E6%8D%AE%E5%87%BA%E5%A2%83%E5%AE%89%E5%85%A8%E8%AF%84%E4%BC%B0%E5%8A%9E%E6%B3%95/59030537 |
| 4 | [PDF] 数据出境安全评估办法 | openresearch-repository.anu.edu.au | 78 | - | 7 Jul 2022 · 第三条数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合,防范数据出境安全风险,保障数据依法有序自由 流动。 | https://openresearch-repository.anu.edu.au/bitstreams/7bba4ac6-0ee2-4890-b90c-f586f63de6e8/download |
| 5 | 以安全促发展——《数据出境安全评估办法》解读- 金杜律师事务所 | www.kingandwood.com | 92 | - | 7 Jul 2022 · 2022年7月7日，《数据出境安全评估办法》正式颁布，这意味着，我国数据出境安全评估制度在效力上，从概念的制度向实践的制度迈出了重要的一步。本文在回顾 ... | https://www.kingandwood.com/cn/zh/insights/latest-thinking/promoting-development-with-security-interpretation-of-measures-for-security-assessment-of-data-exports.html |

## 13. [政策] EU AI Act compliance requirements

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance Requirements - LinkedIn | www.linkedin.com | 160 | - | The EU AI Act compliance requirements are a set of rules and procedures that organizations must foll… | https://www.linkedin.com/top-content/artificial-intelligence/eu-ai-initiatives/eu-ai-act-compliance-requirements/ |
| 2 | EU AI Act Compliance \| Microsoft Trust Center | www.microsoft.com | 162 | - | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restricted Use Pol… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 3 | EU AI Act Compliance: What You Need to Know | www.sai360.com | 156 | - | SAI360 helps organizations take a practical, structured approach to meeting the requirements of the … | https://www.sai360.com/regulations/eu-ai-act |
| 4 | EU AI Act: Summary & Compliance Requirements - ModelOp | www.modelop.com | 161 | - | The Act places a strong emphasis on protecting fundamental rights by mandating human oversight of AI… | https://www.modelop.com/ai-governance/ai-regulations-standards/eu-ai-act |
| 5 | How to Achieve EU AI Act Compliance and Build Trustworthy AI | secureframe.com | 163 | - | 11 Sept 2025 · The EU AI Act sets strict requirements for high-risk AI, from risk assessments and da… | https://secureframe.com/blog/eu-ai-act-compliance |

## 14. [政策] 个人所得税 专项附加扣除 标准

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 七项个人所得税专项附加扣除政策要点（2025年3月） - 税屋 | www.shui5.cn | 87 | - | 个人所得税专项附加扣除,是指个人所得税法规定的子女教育 … 扣除标准 2019年度-2022年度:1000元/月/每个子女(定额扣除) 除标准的100%扣除 标准的50%扣除 | https://www.shui5.cn/article/9c/122307.html |
| 2 | 国务院关于提高个人所得税有关专项附加扣除标准的通知_税务_中国政府网 | www.gov.cn | 79 | - | 为进一步减轻家庭生育养育和赡养老人的支出负担，依据《中华人民共和国个人所得税法》有关规定，国务院决定，提高3岁以下婴幼儿照护等三项个人所得税专项附加扣除标准。 | https://www.gov.cn/zhengce/content/202308/content_6901206.htm |
| 3 | 月底截止，事关收入！ 抓紧确认 | m.gmw.cn | 91 | - | 个税专项附加扣除信息确认. 开始啦！ 纳税人可通过个人所得税App.3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。 | https://m.gmw.cn/2025-12/02/content_1304246592.htm |
| 4 | 事关你的钱袋子，今起确认！ \| 每日经济新闻 | m.nbd.com.cn | 97 | - | 各个项目. 分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。税务部门提醒. 个人所得税专项附加扣除信息. | https://m.nbd.com.cn/articles/2025-12-01/4162702.html |
| 5 | 月底截止，事关收入！ 抓紧确认_腾讯新闻 | news.qq.com | 102 | - | 本月底，2025年度个人所得税专项附加扣除信息确认将截止。各个项目分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000… | https://news.qq.com/rain/a/20241229A04S4300 |

## 15. [政策] children privacy law COPPA update

引擎：searxng；失败引擎：-
卫生度：覆盖 0.84（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for kids plan | digiday.com | 221 | - | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (COPPA) and w… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure-against-facebooks-instagram-for-kids-plan/ |
| 2 | Children and Teens' Online Privacy Protection Act (COPPA 2.0) | www.termsfeed.com | 196 | - | It is an update to the Children’s Online Privacy Protection Act (COPPA). COPPA 2.0 takes a stricter … | https://www.termsfeed.com/blog/coppa-2-children-teens-online-privacy-protection-act/ |
| 3 | COPPA: Children's Online Privacy Protection Act Guide 2026 | usercentrics.com | 148 | - | COPPA protects the online privacy of children under 13 in the U.S. Learn what the law requires, what… | https://usercentrics.com/knowledge-hub/childrens-online-privacy-protection-act-coppa/ |
| 4 | Privacy Policy - The Wheeler School - N-12 Coed Day School in Providence RI | www.wheelerschool.org | 158 | - | COPPA Statement The Children’s Online Privacy Protection Act (COPPA) is a federal law governing the … | https://www.wheelerschool.org/privacy-policy/ |
| 5 | COPPA Sample Clauses \| Law Insider | www.lawinsider.com | 158 | - | The COPPA clause is designed to ensure compliance with the Children’s Online Privacy Protection Act,… | https://www.lawinsider.com/clause/coppa |

## 16. [商品] iPhone 17 Pro 价格 参数

引擎：searxng；失败引擎：-
卫生度：覆盖 0.72（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 3

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | iPhone8手机参数 - 京东 | www.jd.com | 131 | - | 京东是国内专业的iPhone8手机参数网上购物商城，本频道提供iPhone8手机参数商品图片，iPhone8手机参数价格，iPhone8手机参数多少钱信息，为您选购提供全方位iPhone8手机参数怎么… | https://www.jd.com/hprm/998728323d21c0c6f006.html |
| 2 | Apple iPhone 17 Pro - 全面参数、价格与评测\| Kalvo | zh.kalvo.com | 99 | - | 9 Sept 2025 · Apple iPhone 17 Pro 当前售价为$849，实际成交价可能随时间调整。 Apple iPhone 17 Pro 的上市时间是什么时候？ Apple ... | https://zh.kalvo.com/apple-iphone-17-pro-186083.html |
| 3 | 【苹果iPhone 17 256GB】报价_参数_图片_论坛_Apple iPhone 17,苹果 17,iPhone17苹果手机报.... | detail.zol.com.cn | 181 | - | 中关村在线为您提供苹果iPhone 17 256GB 手机最新报价，同时包括苹果iPhone 17 256GB图片、苹果iPhone 17 256GB参数、苹果iPhone 17 256GB评测行情、… | https://detail.zol.com.cn/cell_phone/index2139583.shtml |
| 4 | 参数_图片_苹果iPhone 17 Pro手机报价 | detail.zol.com.cn | 121 | - | 苹果iPhone 17 Pro · 京东商城. Apple/苹果iPhone 17 Pro 256GB 银色支持移动联通电信5G 双卡双待手机. ￥ 8999. 去购买 · 【政府补贴10%仅江苏用】… | https://detail.zol.com.cn/cell_phone/index2139584.shtml |
| 5 | 苹果8x参数 - 京东 | www.jd.com | 259 | - | Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus e二手手机A16详见质检报告 苹果 iPhone 8荣耀亲选LCHSE X5s蓝牙耳机无线入… | https://www.jd.com/hprm/9987d46c01cd9b8ab46f.html |

## 17. [商品] best noise cancelling headphones 2026 review

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | www.tiktok.com | 234 | - | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise-cancellin… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best Noise-Cancelling Headphones 2026: Minimise ambient noise | www.trustedreviews.com | 253 | - | Best Noise-Cancelling Headphones 2026: Noise Cancel Culture.Learn more about how we test headphones.… | https://www.trustedreviews.com/best/best-noise-cancelling-headphones-3440212 |
| 3 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | www.whathifi.com | 208 | - | 24 Jul 2026 · The Sony WH-1000XM6 are our pick as the best noise cancelling headphones overall – the… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |
| 4 | Best Noise Cancelling Headphones Review: Top Picks 2026 ... | www.techcityng.com | 120 | - | 17 Mar 2026 · 1. Sony WH-1000XM5 — Best overall for ANC and features ・ 2. Bose QuietComfort Ultra ・ … | https://www.techcityng.com/best-noise-cancelling-headphones-review-top-picks-2026-guide/ |
| 5 | Best Noise Cancelling Headphones 2026 (50+ Tested!) | recordingnow.com | 163 | - | Best Overall: Sony 1000X THE COLLEXION · See our Full Sony 1000X THE COLLEXION Review on YouTube bel… | https://recordingnow.com/blog/best-noise-cancelling-headphones/ |

## 18. [商品] 扫地机器人 推荐 性价比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.88（最低 0.68） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 【26... | www.bilibili.com | 102 | - | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人选购攻略！ 10:3… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 推荐一些性价比高的扫地机器人\|清洁 - 新浪 | www.sina.cn | 106 | - | 2 days ago · 2026年想买高性价比扫地机器人，可重点关注米家H40（约1749元）、Mova P50（约1999元）和追觅S40增强版（约3230元）这几款，其中米家H40和Mova P… | https://www.sina.cn/gc/article/nitfanv5117762.html |
| 3 | 扫地机器人选购指南：3款高性价比机型推荐 - Joybuy | m.joybuy.co.uk | 97 | - | Lubluelu SL60D 扫地机器人 · 性价比极高，尤其是在当前的清仓活动期间。 · 精准的LDS 激光导航，实现系统化清洁。 · 4000 Pa 的可靠吸力，并带有地毯自动识别增压功能。 | https://m.joybuy.co.uk/blog/robot-vacuum-buying-guide-2026/td0Bwfw6 |
| 4 | 2026年扫地机器人推荐（9月更新） - 知乎专栏 | zhuanlan.zhihu.com | 87 | - | 如果你想要极致的清洁体验，野树最推荐、也是性价比最高的，就是科沃斯T80S Pro的上下水版本，不仅能够无限复洗复拖、实现真正的拖地自由，还能解决自动添加清洁液功能的 ... | https://zhuanlan.zhihu.com/p/139666607 |
| 5 | 扫地机哪个牌子好？ 求推荐一个性价比高的? - 知乎 | www.zhihu.com | 71 | - | 租房两年，前后换两台扫地机踩大坑，终于挖到 MOVA 这个性价比牌子，P70S 水箱版千元出头，功能对标两三千机型，预算 2000 内闭眼冲。 | https://www.zhihu.com/tardis/jm/ans/2066203690583773200 |

## 19. [商品] RTX 5090 benchmark 价格

引擎：searxng；失败引擎：-
卫生度：覆盖 0.50（最低 0.50） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB Benchmark and Specs - GPU comparison | www.gpu-monkey.com | 152 | - | Benchmark results and tests of the GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB in 3DMark an… | https://www.gpu-monkey.com/en/gpu-gigabyte_aorus_geforce_rtx_5090_xtreme_waterforce_wb |
| 2 | NVIDIA GeForce RTX 5090 Review: Pushing Boundaries with AI Acceleration - Storag | www.storagereview.com | 161 | - | The Procyon AI Text Generation Benchmark Benchmark simplifies AI LLM performance testing by offering… | https://www.storagereview.com/review/nvidia-geforce-rtx-5090-review-pushing-boundaries-with-ai-acceleration |
| 3 | A thorough insight into technical specs and benchmarks of RTX 5090. | technical.city | 107 | - | Synthetic benchmark performance of GeForce RTX 5090. The combined score is measured on a 0-100 point… | https://technical.city/en/gpu/GeForce-RTX-5090 |
| 4 | PassMark - GeForce RTX 5090 - Price performance comparison | www.videocardbenchmark.net | 162 | - | Price and performance details for the GeForce RTX 5090 can be found below. This is made using thousa… | https://www.videocardbenchmark.net/gpu.php?gpu=GeForce+RTX+5090&id=5725 |
| 5 | ASUS Details GeForce RTX 5090 and 5080 Pricing | www.techporn.ph | 160 | - | ASUS has officially launched the highly anticipated GeForce RTX 5090 and 5080 graphics cards in the … | https://www.techporn.ph/asus-details-geforce-rtx-5090-and-5080-pricing/ |

## 20. [商品] 国产显卡 摩尔线程 最新型号

引擎：searxng；失败引擎：-
卫生度：覆盖 0.60（最低 0.43） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 国产显卡品牌摩尔线程发新卡 单卡48GB显存_凤凰网 | i.ifeng.com | 74 | - | 国产显卡品牌摩尔线程，终于又要发新显卡了。这张显卡的具体型号为MTT S4000，规格方面非常不错。 国产显卡品牌摩尔线程发新卡 单卡48GB显存. | https://i.ifeng.com/c/8VfiImHtDxn |
| 2 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | news.mydrivers.com | 36 | - | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |
| 3 | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU... | m.ithome.com | 42 | - | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU 快速迭代. | https://m.ithome.com/html/663833.htm |
| 4 | 砺算科技 7g100 国产显卡开启预约，12GB 售 3299... \| 知乎 | www.zhihu.com | 108 | - | 因此7G100和之前的国产显卡如S80、JH920等有显著不同，它是拿下了微软WHQL认证（要通过微软实验室一系列稳定与兼容性测试）的！另外目前生产的仅有3风扇型号，单卡长度达到29.4cm，因此要注… | https://www.zhihu.com/tardis/jm/ans/2040860622385061977 |
| 5 | 摩尔线程（MooreThreads）MTT S80 8K高清 16G大显存 国产游戏独立显卡【图片 价格 品牌 报价】-京东 | item.jd.com | 90 | - | 摩尔线程（MooreThreads）MTT S80 8K高清 16G大显存 国产游戏独立显卡图片、价格、品牌样样齐全！【京东正品行货，全国配送，心动不如行动，立即购买享受更多优惠哦 | https://item.jd.com/10065360417210.html |

## 卫生度汇总（M5-5.3，客观指标）

| 指标 | 值 | 含义 |
| --- | --- | --- |
| 结果总数 | 100 | 20 条查询的 top-N 合计 |
| 查询词覆盖率（加权） | 0.755 | 越高说明结果越贴题 |
| 同站冗余 | 0 | 同一可注册域超出上限的条数 |
| 聚合页 | 0 | 站点首页/栏目页这类「只是导航」的结果 |
| 非中英文脚本 | 0 | 中文查询下混入的俄语/韩语等标题 |
| 空内容 | 1 | 摘要不足 40 字、对 LLM 无价值 |
| 平均独立站点数 | 4.5 | 来源分散度 |


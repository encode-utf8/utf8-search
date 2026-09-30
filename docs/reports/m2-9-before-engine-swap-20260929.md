# 相关性抽检报告（验收项 2-9）

- 生成时间：2026-09-29 13:15:04
- 深度模式：basic，每条取前 5 条
- 查询构成：20 条中英混合，覆盖 新闻 / 技术 / 政策 / 商品 各 5 条
- **采集缓存状态**：已禁用缓存（`--no-cache`），全部为本次实时采集

## 打分规则（先读这三条）

1. **门槛**：20 条查询里，满足「top5 中相关条数 ≥ 4」的查询数要 **≥ 18 条**（即 ≥ 90%）。
2. **scores 的 5 位依次对应排名 1-5**（第 1 位 = 排名第 1 的结果），逐位填 0/1。
3. **非零数字一律视为「相关」**（填 1 最规范；填 2 或其它非零值同样按相关计）。

- 判定命令：`python scripts/relevance.py --score-file m2-9-before-swap-scores.csv`
- 通过标准（脚本口径）：top5 中相关数 ≥ 4 的查询占比 ≥ 90%
- 速览版（不带正文字数/发布时间/URL）：`m2-9-before-swap-brief.md`

## 1. [新闻] 2026年9月 国内外重大新闻

引擎：searxng；失败引擎：brave, privacywall, yep
卫生度：覆盖 0.49（最低 0.37） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | “平平”和“福双”前驻亚特兰大动物园 中国与美恢复“熊猫外交” | www.rfi.fr | 146 | 2026-09-27T09:47:57 | 发表时间： 27/09/2026 - 10:01更改时间： 28/09/2026 - 14:02. 6 分钟 浏览时间.此外，今年早些时候，由于日本首相暗示若发生针对台湾的袭击日本可能会进行军事干预，… | https://www.rfi.fr/cn/%E4%B8%AD%E5%9B%BD/20260927-%E4%B8%A4%E5%8F%AA%E5%A4%A7%E7%86%8A%E7%8C%AB%E5%90%AF%E7%A8%8B%E5%89%8D%E5%BE%80%E4%BA%9A%E7%89%B9%E5%85%B0%E5%A4%A7%E5%8A%A8%E7%89%A9%E5%9B%AD-%E4%B8%AD%E5%9B%BD%E4%B8%8E%E7%BE%8E%E6%81%A2%E5%A4%8D-%E7%86%8A%E7%8C%AB%E5%A4%96%E4%BA%A4 |
| 2 | 商务部召开例行新闻发布会（2026年9月3日） | www.mofcom.gov.cn | 91 | - | 3 Sept 2026 · 9月2日，习近平主席与埃及总统塞西举行会谈，就深化双边关系和拓展各领域务实合作达成广泛共识，为下阶段中埃经贸关系发展指明了方向。在两国元首见证下， ... | https://www.mofcom.gov.cn/xwfbzt/2026/swbzklxxwfbh2026n9y3r/index.html |
| 3 | 美国之音中文网新闻 - 美国之音中文网 | www.voachinese.com | 814 | - | 3 days ago — 唐纳德·特朗普总统在结束接待中国国家主席习近平对美国进行的三天国事访问之际表示，美国展示了实力以及与中国的友谊。这次在华盛顿举行的美中元首峰会在星期五(9月25日)结束。特朗… | https://www.voachinese.com/z/1739 |
| 4 | 【2026年9月の開運日カレンダー】一粒万倍日・吉日一覧｜開運待ち受け（スマホ壁紙）を変えるタイミング✨ | www.hana-pla.com | 100 | - | 2026年9月の開運日カレンダーと、開運待ち受け（スマホ壁紙）を取り入れるタイミングをまとめました。 一粒万倍日や寅の日、巳の日、辰の日、新月、満月、大安など、2026年9月の縁起が良いとされる日・吉 | https://www.hana-pla.com/wallpaper/luckyday-calendar202609/ |
| 5 | SBS一周大事件（2026年9月18日） | www.sbs.com.au | 230 | 2026-09-18 | 2주 전澳大利亚政府公布重大移民政策改革方案；中国出入境新规生效，公民出境或需接受面谈；美联储无视总统特朗普降息要求，三年内首次加息；欧盟委员会主席提议让加拿大成为欧盟首个“联席成员”。 欢迎下载应用… | https://www.sbs.com.au/language/chinese/zh-hans/podcast-episode/weekly-news-wrap-20260918/qw26jpdga |

## 2. [新闻] 最近一周 AI 行业动态

引擎：searxng；失败引擎：-
卫生度：覆盖 0.47（最低 0.19） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | AI行业发展一周动态 - 知乎专栏 | zhuanlan.zhihu.com | 91 | - | 26 Dec 2025 · 一、 市场运行与行业趋势. 火山引擎发布豆包大模型运营数据及企业级智能体平台[1][2]. 豆包日均Tokens使用量突破50万亿，居中国第一、全球第三。 | https://zhuanlan.zhihu.com/p/1987970291440304627 |
| 2 | AI行业发展一周动态 - 知乎 | zhuanlan.zhihu.com | 268 | - | 2025年全球端侧AI市场规模将增至1.22万亿元年复合增长率达40%[2] · 2025年12月9日，谷歌公布智能眼镜Project Aura和Android XR系统关键细节，理想汽车发布首款AI… | https://zhuanlan.zhihu.com/p/1983093760448542417 |
| 3 | 每日AI资讯、热点、动态、融资、产品发布 \| AI工具集 | ai-bot.cn | 422 | - | August 10, 2023 — 面壁智能联合 OpenBMB 开源 ForgeStencil，全球首个 AI 驱动的 Stencil 全自动优化系统。ForgeStencil由 Kernel Ag… | https://ai-bot.cn/daily-ai-news/ |
| 4 | 资讯合集 - 前沿观澜 官方站 | www.uijae.com | 178 | - | AI监管企业实践测评：从「被动合规」到「主动治理」的真实体验 ; 作为一家中型金融科技公司的合规负责人，我每天最头疼的不是业务增长，而是如何应对层出不穷的AI监管要求。直到我们部署了「智盾AI治理平台… | https://www.uijae.com/%E7%81%AB%E9%94%85%E9%94%85%E5%85%B7%E4%BB%80%E4%B9%88%E6%9D%90%E8%B4%A8%E5%A5%BD/ |
| 5 | 每周必知5件AI大事 | www.aiposthub.com | 102 | - | OpenAI 估值突破5000 億美元，成為全球最貴未上市公司；Sora 2 + 社交影片App 正式登場；開發者大會釋出Apps SDK 與AgentKit，讓ChatGPT 蛻變為AI 經濟作業系… | https://www.aiposthub.com/weekly-ai-news-top5/ |

## 3. [新闻] latest news semiconductor export controls

引擎：searxng；失败引擎：-
卫生度：覆盖 0.64（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | What's the latest with semiconductor export controls? \| Reuters | www.reuters.com | 153 | 2026-09-23 | 6 days ago · Anthony Rapa of Blank Rome LLP discusses recent developments in U.S. export controls on… | https://www.reuters.com/legal/legalindustry/whats-latest-with-semiconductor-export-controls--pracin-2026-09-23/ |
| 2 | China lashes out at latest U.S. export controls on chips | www.asahi.com | 200 | - | BEIJING--China on Saturday criticized the latest U.S. decision to tighten export controls that would… | https://www.asahi.com/ajw/articles/14738636 |
| 3 | Semiconductor Export Controls in 2026: Dual-Use Risk, Re-export... | frilinglaw.com | 186 | - | This article explains semiconductor export controls in 2026, with special focus on dual-use risk, re… | https://frilinglaw.com/blog/semiconductor-export-controls |
| 4 | Trump's AI chip export controls could go either way for Korea - Korea JoongAng Daily ,Korean news in Engl.... | www.koreajoongangdaily.com | 90 | - | 2025.05.14.Published May 14, 2025 - 6:36 p.m. Modified May 14, 2025 - 8:06 p.m.2025.05.14. | https://www.koreajoongangdaily.com/business/trumps-ai-chip-export-controls-could-go-either-way-for-korea/12444537 |
| 5 | Joint Advisory: Export controls on advanced semiconductor and ... | www.mti.gov.sg | 161 | - | 4 Apr 2025 · In recent years, several countries have imposed unilateral export controls on advanced … | https://www.mti.gov.sg/newsroom/joint-advisory--export-controls-on-advanced-semiconductor-and-artificial-intelligence--ai--technologies/ |

## 4. [新闻] 台风 最新消息 路径

引擎：searxng；失败引擎：-
卫生度：覆盖 0.80（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026年台风红霞最新消息（附实时路径查询入口）- 泉州本地宝 | m.qz.bendibao.com | 74 | - | 2026年台风红霞最新消息（附实时路径查询入口）.2026年台风红霞最新消息（附实时路径查询入口）. 台风“红霞”最新实时路径查询入口：中央气象台. | https://m.qz.bendibao.com/news/38203.shtm |
| 2 | 刚刚！ 台风“丹娜丝”路径有变！ 或在福建浙江登陆 | c.m.163.com | 60 | - | 注意！ 90度拐弯. 台风“丹娜丝”路径有变化. 或在闽浙沿海登陆. 台风最新消息. 中央气象台消息. 7月5日13时. | https://c.m.163.com/news/a/K3NE3U0Q0550IMZX.html?spss=sps_sem |
| 3 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | gz.bendibao.com | 120 | - | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级，台风级或强台风级）… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 4 | 热带低压 - 台风网- 中央气象台 | typhoon.nmc.cn | 374 | - | 3 weeks ago — 舒力基 · 台风“舒力基”最新位置：北纬26.9度， 东经131.2度，中心附近最大风力15级 · 触屏版 · 24 小 时 警 戒 线 · 48 小 时 警 戒 线 · … | https://typhoon.nmc.cn/web.html |
| 5 | 台风“红霞”即将生成 最新路径预判 | sdxw.iqilu.com | 57 | - | 石流等次生灾害。 台风“红霞”即将生成. 或于本周登陆粤闽沿海. 中央气象台7月23日10时继续发布热带低压预报： | https://sdxw.iqilu.com/w/article/YS0yMS0xNzMxNTMyNg.html |

## 5. [新闻] 美国 关税 最新政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.73（最低 0.53） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026 美国关税最新消息 — 中菲行国际物流集团 | cn.dimerco.com | 987 | - | June 6, 2026 — 除232关税调整外，美国贸易代表办公室（USTR）还发布了一份《联邦公报》（Federal Register Notice），明确表明政府在7月24日第122条款（Sec… | https://cn.dimerco.com/us-tariff-update-2026/ |
| 2 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | www.edurew.com | 161 | - | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协会近日表示，根据最新… | https://www.edurew.com/html/03c79099206.html |
| 3 | 关税政策及其对全球贸易的影响 \| UPS Supply Chain Solutions - 美国 | www.ups.com | 868 | - | 根据第 122 条关税政策，自 2026年2月24日起，美国对所有国家的进口商品统一加征 10% 的关税。但是也存在几项豁免情形，例如符合美墨加协定认证的商品。更多信息可在此处查看。"根据要求，UPS… | https://www.ups.com/cn/zh/supplychain/resources/news-and-market-updates/2025-us-tariffs-impact-global-trade |
| 4 | Temu 和 Shein... | www.100ec.cn | 102 | - | 9 日起取消 Google 购物平台所有支出，并于 4 月 25 日因 “全球贸易规则和关税致运营费用上涨” 进行价格调整，Shein 也将在同日实施相同举措。 一、政策背景：特朗普政府关税新政及其影… | https://www.100ec.cn/detail--6648723.html |
| 5 | 一文读懂特朗普最新关税措施：他宣布的最新全球关税将如何 ... | www.bbc.com | 96 | - | 22 Feb 2026 · 新的15%关税将从2月24日美国东部时间凌晨12点01分（格林威治时间上午5点01分）开始，对所有进口到美国的商品征税，无论商品来自哪个国家。 白宫官员告诉 ... | https://www.bbc.com/zhongwen/articles/c20zp13zgjro/simp |

## 6. [技术] Python 3.13 新特性

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Python 3.13 有什么新变化 — Python 3.13.1 文档 | www.sdx.cool | 734 | - | January 21, 2026 — Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 … | https://www.sdx.cool/index/python_docs/whatsnew/3.13.html |
| 2 | Python 3.13 有什么新变化 — Python 3.16.0a0 文档 | docs.python.org | 725 | - | Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 PyPy 项目 的代码。 当使用从交互… | https://docs.python.org/zh-cn/dev/whatsnew/3.13.html |
| 3 | 【Python 3.13】新特性解读，重大改进建议升级：JIT编译、免GIL | blog.csdn.net | 109 | - | 26 Nov 2024 · 1. 提升交互式解释器(REPL)体验 · 彩色提示符: 更直观的交互体验。 · 简化命令: REPL专属命令不再需要括号调用，例如exit、clear、help等。 · … | https://blog.csdn.net/weixin_42212872/article/details/144067816 |
| 4 | 好学编程：Python 3.13 这些新特性你一定要知道！ - 知乎 | zhuanlan.zhihu.com | 703 | - | Python 3.13 终于支持禁用全局解释器锁（GIL）了！这意味着你的多线程 Python 程序可以充分利用多核处理器的优势。虽然目前仍处于实验阶段，但这无疑是一个激动人心的突破。"Python … | https://zhuanlan.zhihu.com/p/12824443094 |
| 5 | Python 3.13 来了！更效率、更优雅-腾讯云开发者社区-腾讯云 | cloud.tencent.com | 549 | - | October 12, 2024 — 在早期版本引入的强大类型系统基础上，Python 3.13 将引入七个新的类型特性，有望提高代码的可靠性和开发人员的工作效率。"在本文中，我们将尝试这些令人兴奋的… | https://cloud.tencent.com/developer/article/2457400 |

## 7. [技术] MCP protocol specification 2026

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 다음 MCP 스펙 릴리즈(2026-07-28)의 주요 내용: Stateless 전환 및 공식 확장 도입 예.... | discuss.pytorch.kr | 222 | - | 2026.05.27.MCP 스펙 릴리즈 후보(The 2026-07-28 MCP Specification Release Candidate) 소개 Model Context Protoc… | https://discuss.pytorch.kr/t/mcp-2026-07-28-stateless/10387 |
| 2 | The 2026-07-28 Specification \| Model Context Protocol Blog | blog.modelcontextprotocol.io | 1201 | - | July 28, 2026 — The 2026-07-28 Model Context Protocol specification is out, bringing a stateless pro… | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| 3 | Model Context Protocol Specification Version Timeline - Version-by-Version Changes and Adoption Milestones \| hidekazu-konishi.com | hidekazu-konishi.com | 1198 | - | August 20, 2026 — In the current specification, 2026-07-28, there is no negotiation handshake: every… | https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html |
| 4 | The 2026-07-28 MCP Specification Release Candidate \| Model Context Protocol Blog | blog.modelcontextprotocol.io | 1201 | - | July 28, 2026 — The release candidate for the next Model Context Protocol (MCP) specification is now… | https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ |
| 5 | New Enterprise-Ready MCP Specification Brings New Security Challenges - SecurityWeek | www.securityweek.com | 1193 | - | June 26, 2026 — On July 28, 2026, it will transition to a new version: MCP 2026-07-28, allowing a 12… | https://www.securityweek.com/new-enterprise-ready-mcp-specification-brings-new-security-challenges/ |

## 8. [技术] FastAPI 与 Django 性能对比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.76（最低 0.64） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Python Web框架：Django、Flask和FastAPI巅峰对决-阿里云开发者社区 | developer.aliyun.com | 111 | - | September 19, 2023 — 本文深入对比 Django、Flask 与 FastAPI 三大 Python Web 框架，剖析各自在全能性、灵活性与异步高性能方面的特点，为您的项目技术选… | https://developer.aliyun.com/article/1331205 |
| 2 | WEB框架对比——Django、Flask、FastAPI - ''竹先森゜ - 博客园 | www.cnblogs.com | 739 | - | May 7, 2021 — 社区活跃程度——Django ... 的社区目前还比较小，因为它相对较新。 · 性能。在性能方面——FastAPI 是领跑者，因为它是面向速度的，其次是 Flask，最后是… | https://www.cnblogs.com/zhuminghui/p/14741536.html |
| 3 | Django框架：优缺点、实用场景及与Flask、FastAPI的对比-腾讯云开发者社区-腾讯云 | cloud.tencent.com | 471 | - | 速度相对较慢：Django是一个重量级框架，在处理大量请求时，性能可能受到影响。"Django是一个使用Python语言编写的高级Web框架，它提供了快速开发、可重用和可维护的Web应用程序所需的一切… | https://cloud.tencent.com/developer/article/2294156 |
| 4 | Django，Flask ，FastAPI 怎么选？-腾讯云开发者社区 - Tencent | cloud.tencent.com | 93 | - | 29 Apr 2021 · Python三大Web框架对比：Django适合大型商业项目，功能完善但稍重；Flask轻量灵活，适合快速原型开发；FastAPI高性能异步，专为API设计。 | https://cloud.tencent.com/developer/article/1819808 |
| 5 | FastAPI 与 Django：2026 年最佳 Python 框架 | www.lastingdynamics.com | 79 | - | FastAPI vs Django for Startups（MVP）.FastAPI 与 Django 的主要区别. 性能比较. 异步功能. 开发人员体验. | https://www.lastingdynamics.com/zh/blog/fastapi-vs-django/ |

## 9. [技术] how does HTTP/3 QUIC work

引擎：searxng；失败引擎：-
卫生度：覆盖 0.83（最低 0.67） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | The Future of the Internet is here: QUIC Protocol and HTTP/3 \| Medium | medium.com | 266 | - | How does QUIC work? Unlike TCP, which uses a connection-oriented approach, QUIC uses a multiplexed s… | https://medium.com/@luisrodri/the-future-of-the-internet-is-here-quic-protocol-and-http-3-d7061adf424f |
| 2 | What is HTTP and how does it work? Hypertext Transfer Protocol \| Definition from | www.techtarget.com | 526 | - | 2025.02.03.HTTP (Hypertext Transfer Protocol) is a set of rules that govern how information will be … | https://www.techtarget.com/whatis/definition/HTTP-Hypertext-Transfer-Protocol |
| 3 | Hypertext Transfer Protocol Version 3 (HTTP/3) | www.ietf.org | 1188 | - | February 2, 2021 — Multiplexing of requests is performed using the QUIC stream abstraction, describe… | https://www.ietf.org/archive/id/draft-ietf-quic-http-34.html |
| 4 | HTTP/3 is Fast! - Request Metrics 🦥 | requestmetrics.com | 304 | - | 2025.02.19.HTTP/3 promises speed and efficiency, but does it actually deliver? In our latest article… | https://requestmetrics.com/web-performance/http3-is-fast/ |
| 5 | How QUIC Works: From UDP Packets to HTTP/3 | www.linkedin.com | 228 | - | QUIC = transport protocol. HTTP/3 = HTTP mapping that uses QUIC. Other application protocols can use… | https://www.linkedin.com/pulse/how-quic-works-from-udp-packets-http3-chengfa-wang-lqlsc |

## 10. [技术] Rust async runtime tokio 原理

引擎：searxng；失败引擎：-
卫生度：覆盖 0.66（最低 0.57） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Tokio 任务调度原理分析 - Rust Magazine | rustmagazine.org | 101 | - | async Future 是Rust 中实现异步的基础,代表一个异步执行的计算任务, 。Tokio 是社区内使用最为广泛的异步运行时,它内部采用各种措施来保证Future 被公平、及时的调度执行 ..… | https://rustmagazine.org/issue-4/how-tokio-schedule-tasks-zh/ |
| 2 | 理解tokio的核心(1): runtime - Rust入门秘籍 | rust-book.junmajinlong.com | 1198 | - | Rust · Coal · Navy · Ayu · 理解tokio核心(1): runtime · 创建tokio Runtime · async main · 多个runtime共存 · 进入ru… | https://rust-book.junmajinlong.com/ch100/01_understand_tokio_runtime.html |
| 3 | 理解tokio的核心(1): runtime - Rust入門祕籍 | shihyu.github.io | 85 | - | 要使用tokio，需要先創建它提供的異步運行時環境(Runtime)，然後在這個Runtime中執行異步任務。 使用 tokio::runtime 創建Runtime：. | https://shihyu.github.io/rust_hacks/ch100/01_understand_tokio_runtime.html |
| 4 | How to Use Tokio for Async Runtime in Rust | oneuptime.com | 1173 | - | February 1, 2026 — Before diving into code, let us understand what Tokio actually does. Rust has asy… | https://oneuptime.com/blog/post/2026-02-01-rust-tokio-async-runtime/view |
| 5 | Practical Guide to Async Rust and Tokio \| by Oleg Kubrakov \| Medium | medium.com | 1196 | - | December 2, 2024 — Tokio implements a cooperative event loop, which means Tokio tasks should volunta… | https://medium.com/@OlegKubrakov/practical-guide-to-async-rust-and-tokio-99e818c11965 |

## 11. [政策] 2026年 新能源汽车 补贴政策

引擎：searxng；失败引擎：resulthunter
卫生度：覆盖 0.89（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | post.smzdm.com | 139 | - | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. 新能源汽车补贴政策延… | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 别光顾着过年，快来买车 625亿元“国补”已经发放 - OFweek新能源汽车网 | nev.ofweek.com | 75 | - | 从2025年末开始，国内汽车消费市场便进入了政策切换的过渡期——原有的新能源汽车购置税免征政策、汽车以旧换新补贴政策逐步收尾，而2026年新的政策尚. | https://nev.ofweek.com/2026-02/ART-71000-8420-30681174.html |
| 3 | 2026年4月汽车国补置换2万元申请全攻略：手把手教你领到国家补贴 | www.zhihu.com | 72 | - | 2026年，国家继续实施汽车以旧换新补贴政策，也就是大家常说的“国补”。补贴金额： · 买新能源车 → 按新车销售价格的12%补贴，最高2万元. | https://www.zhihu.com/tardis/jm/art/2033119484798616793 |
| 4 | qdzb07b20260116C | epaper.qingdaonews.com | 77 | - | 2026 年伊始新一轮购车国补新政正式落地实施。 此次新政不仅对补贴模式进行了优化还 同步调整了新能源汽车购置税优惠政策形成“国补+税补”的双重让利格局。 | https://epaper.qingdaonews.com/qdzb/resfile/2026-01-16/A07/qdzb-20260116-A07.pdf |
| 5 | 2026年汽车以旧换新政策落地：新能源车最高补2万元 | www.ccn.com.cn | 93 | - | 5 Jan 2026 · 具体而言，在报废更新场景下，购买新能源车可获车价12%的补贴，封顶2万元；购买传统燃油车可获车价10%的补贴，封顶1.5万元。在置换更新场景下，新能源车 ... | https://www.ccn.com.cn/Content/2026/01-05/1847019380.html |

## 12. [政策] 数据出境安全评估办法 最新

引擎：searxng；失败引擎：-
卫生度：覆盖 0.83（最低 0.83） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 解读数据出境安全评估办法：未通过评估企业或面临结构性影响 | m.mp.oeeee.com | 98 | - | 数据出境安全相关评估办法曾三次征求意见. 自2016年网络安全法通过审议以来，国家网信办三次对数据出境安全相关的评估办法征求意见。2021年，《数据出境安全评估办法（征求意见稿）》向社会征求意见。 | https://m.mp.oeeee.com/a/BAAFRD000020220708701121.html |
| 2 | 数据出境安全评估办法.docx - 墨天轮文档 | www.modb.pro | 70 | - | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 3 | 《数据出境安全评估办法》主要制度和常见误解 | www.secrss.com | 78 | - | 14 Jul 2022 · 2022年7月7日,国家互联网信息办公室发布《数据出境安全评估办法》(下称“《出境评估办法》”),并将于2022年9月1日施行。 | https://www.secrss.com/articles/44687 |
| 4 | 数据出境安全评估办法 - 百度百科 | baike.baidu.com | 83 | - | 《数据出境安全评估办法》是为了规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，根据《中华人民共和国网络安全法》、《 ... | https://baike.baidu.com/item/%E6%95%B0%E6%8D%AE%E5%87%BA%E5%A2%83%E5%AE%89%E5%85%A8%E8%AF%84%E4%BC%B0%E5%8A%9E%E6%B3%95/59030537 |
| 5 | [PDF] 数据出境安全评估办法 | openresearch-repository.anu.edu.au | 78 | - | 7 Jul 2022 · 第三条数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合,防范数据出境安全风险,保障数据依法有序自由 流动。 | https://openresearch-repository.anu.edu.au/bitstreams/7bba4ac6-0ee2-4890-b90c-f586f63de6e8/download |

## 13. [政策] EU AI Act compliance requirements

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance Requirements - LinkedIn | www.linkedin.com | 160 | - | The EU AI Act compliance requirements are a set of rules and procedures that organizations must foll… | https://www.linkedin.com/top-content/artificial-intelligence/eu-ai-initiatives/eu-ai-act-compliance-requirements/ |
| 2 | EU AI Act Compliance \| Microsoft Trust Center | www.microsoft.com | 162 | - | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restricted Use Pol… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 3 | EU AI Act: Summary & Compliance Requirements - ModelOp | www.modelop.com | 161 | - | The Act places a strong emphasis on protecting fundamental rights by mandating human oversight of AI… | https://www.modelop.com/ai-governance/ai-regulations-standards/eu-ai-act |
| 4 | EU AI Act Compliance: What You Need to Know | www.sai360.com | 156 | - | SAI360 helps organizations take a practical, structured approach to meeting the requirements of the … | https://www.sai360.com/regulations/eu-ai-act |
| 5 | EU AI Act Compliance Guide \| Aona AI | aona.ai | 160 | - | Key innovations include the creation of AI regulatory sandboxes, mandatory conformity assessments fo… | https://aona.ai/compliance/regulations/eu-ai-act/ |

## 14. [政策] 个人所得税 专项附加扣除 标准

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 七项个人所得税专项附加扣除政策要点（2025年3月） - 税屋 | www.shui5.cn | 102 | - | 七项个人所得税专项附加扣除政策要点（2025年3月） ; 扣除标准, 2022年度：1000元/月/每个子女（定额扣除） 自2023年1月1日起：2000元/月/每个子女（定额扣除） ; 扣除主体 .… | https://www.shui5.cn/article/9c/122307.html |
| 2 | 国务院关于提高个人所得税有关专项附加扣除标准的通知_税务_中国政府网 | www.gov.cn | 79 | - | 为进一步减轻家庭生育养育和赡养老人的支出负担，依据《中华人民共和国个人所得税法》有关规定，国务院决定，提高3岁以下婴幼儿照护等三项个人所得税专项附加扣除标准。 | https://www.gov.cn/zhengce/content/202308/content_6901206.htm |
| 3 | 月底截止，事关收入！ 抓紧确认 | m.gmw.cn | 91 | - | 个税专项附加扣除信息确认. 开始啦！ 纳税人可通过个人所得税App.3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。 | https://m.gmw.cn/2025-12/02/content_1304246592.htm |
| 4 | 事关你的钱袋子，今起确认！ \| 每日经济新闻 | m.nbd.com.cn | 97 | - | 各个项目. 分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。税务部门提醒. 个人所得税专项附加扣除信息. | https://m.nbd.com.cn/articles/2025-12-01/4162702.html |
| 5 | 国务院印发《个人所得税专项附加扣除暂行办法》 - 市财政局 | www.huaihua.gov.cn | 204 | - | 2018.12.23.新华社北京12月22日电 国务院日前印发《个人所得税专项附加扣除暂行办法》（以下简称《办法》），自2019年1月1日起施行。 《办法》指出，个人所得税专项附加扣除，是指个人所得税… | https://www.huaihua.gov.cn/czj/c100738/201812/3209b912c78742bc934904841c4c89eb.shtml |

## 15. [政策] children privacy law COPPA update

引擎：searxng；失败引擎：-
卫生度：覆盖 0.84（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for kids plan | digiday.com | 221 | - | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (COPPA) and w… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure-against-facebooks-instagram-for-kids-plan/ |
| 2 | Privacy Policy - The Wheeler School - N-12 Coed Day School in Providence RI | www.wheelerschool.org | 158 | - | COPPA Statement The Children’s Online Privacy Protection Act (COPPA) is a federal law governing the … | https://www.wheelerschool.org/privacy-policy/ |
| 3 | What is COPPA? The Children's Online Privacy Protection Act | ed.link | 154 | - | The Children's Online Privacy Protection Act, or COPPA, is a U.S. federal law that protects the pers… | https://ed.link/community/coppa/ |
| 4 | Updates to COPPA (and what it means for your business) - Yoti | www.yoti.com | 254 | - | The Children’s Online Privacy Protection Act of 1998 (COPPA), is a US federal law.The updated regula… | https://www.yoti.com/blog/age-assurance-for-coppa/ |
| 5 | What Is Data Privacy Compliance? | www.paloaltonetworks.com | 159 | - | The Children's Online Privacy Protection Act (COPPA) is a US federal law enacted in 1998 to protect … | https://www.paloaltonetworks.com/cyberpedia/data-privacy-compliance |

## 16. [商品] iPhone 17 Pro 价格 参数

引擎：searxng；失败引擎：-
卫生度：覆盖 0.64（最低 0.40） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | iPhone8手机参数 - 京东 | www.jd.com | 131 | - | 京东是国内专业的iPhone8手机参数网上购物商城，本频道提供iPhone8手机参数商品图片，iPhone8手机参数价格，iPhone8手机参数多少钱信息，为您选购提供全方位iPhone8手机参数怎么… | https://www.jd.com/hprm/998728323d21c0c6f006.html |
| 2 | Apple iPhone 17 Pro - 全面参数、价格与评测\| Kalvo | zh.kalvo.com | 121 | - | 9 Sept 2025 · 售价 $849 £930 €1,048.49 … 厚度 8.8 mm (0.35 英寸) 重量 206 g (7.27 oz) Apple iPhone 17 Pro 当前… | https://zh.kalvo.com/apple-iphone-17-pro-186083.html |
| 3 | 参数_图片_苹果iPhone 17 Pro手机报价 | detail.zol.com.cn | 121 | - | 苹果iPhone 17 Pro · 京东商城. Apple/苹果iPhone 17 Pro 256GB 银色支持移动联通电信5G 双卡双待手机. ￥ 8999. 去购买 · 【政府补贴10%仅江苏用】… | https://detail.zol.com.cn/cell_phone/index2139584.shtml |
| 4 | 苹果8x参数 - 京东 | www.jd.com | 259 | - | Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus e二手手机A16详见质检报告 苹果 iPhone 8荣耀亲选LCHSE X5s蓝牙耳机无线入… | https://www.jd.com/hprm/9987d46c01cd9b8ab46f.html |
| 5 | iPhone 17 Pro_百度百科 | baike.baidu.com | 100 | - | iPhone 17 Pro是苹果公司于北京时间2025年9月10日发布的智能手机产品，售价8999元起。iPhone 17 Pro采用了全新横向大矩阵摄像头设计。采用一体成型的航空级铝合金机身 ... | https://baike.baidu.com/item/iPhone%2017%20Pro/65333654 |

## 17. [商品] best noise cancelling headphones 2026 review

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | www.tiktok.com | 234 | - | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise-cancellin… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best Noise Cancelling Headphones Review: Top Picks 2026 ... | www.techcityng.com | 120 | - | 17 Mar 2026 · 1. Sony WH-1000XM5 — Best overall for ANC and features ・ 2. Bose QuietComfort Ultra ・ … | https://www.techcityng.com/best-noise-cancelling-headphones-review-top-picks-2026-guide/ |
| 3 | Best Noise-Cancelling Headphones 2026: Minimise ambient noise | www.trustedreviews.com | 253 | - | Best Noise-Cancelling Headphones 2026: Noise Cancel Culture.Learn more about how we test headphones.… | https://www.trustedreviews.com/best/best-noise-cancelling-headphones-3440212 |
| 4 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | www.whathifi.com | 257 | - | Best noise-cancelling headphones 2026 – 6 sensational pairs picked by our expert reviewers.All of th… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |
| 5 | Best cheap noise-cancelling headphones 2026: expert-tested recommendations \| Wha | www.whathifi.com | 154 | - | All review verdicts are agreed upon by the team rather than an individual reviewer to eliminate any … | https://www.whathifi.com/best-buys/best-cheap-noise-cancelling-headphones |

## 18. [商品] 扫地机器人 推荐 性价比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.94（最低 0.89） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 【26... | www.bilibili.com | 102 | - | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人选购攻略！ 10:3… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 石头P20 Max vs... \| 新浪网 | k.sina.com.cn | 95 | - | 石头P20 Max vs 同价位扫地机，谁才是性价比之王？ 3个维度硬核对比+FAQ.关键字 : 石头P20 Max 扫地机器人推荐 高性价比扫地机 同价位扫地机对比 2026年扫地机选购. | https://k.sina.com.cn/article_7879923199_1d5ae15ff06801jub0.html |
| 3 | 推荐一些性价比高的扫地机器人\|清洁 - 新浪 | www.sina.cn | 106 | - | 2 days ago · 2026年想买高性价比扫地机器人，可重点关注米家H40（约1749元）、Mova P50（约1999元）和追觅S40增强版（约3230元）这几款，其中米家H40和Mova P… | https://www.sina.cn/gc/article/nitfanv5117762.html |
| 4 | 扫地机器人选购指南：3款高性价比机型推荐 - Joybuy | m.joybuy.co.uk | 97 | - | Lubluelu SL60D 扫地机器人 · 性价比极高，尤其是在当前的清仓活动期间。 · 精准的LDS 激光导航，实现系统化清洁。 · 4000 Pa 的可靠吸力，并带有地毯自动识别增压功能。 | https://m.joybuy.co.uk/blog/robot-vacuum-buying-guide-2026/td0Bwfw6 |
| 5 | 2026年扫地机器人推荐（9月更新） - 知乎专栏 | zhuanlan.zhihu.com | 87 | - | 如果你想要极致的清洁体验，野树最推荐、也是性价比最高的，就是科沃斯T80S Pro的上下水版本，不仅能够无限复洗复拖、实现真正的拖地自由，还能解决自动添加清洁液功能的 ... | https://zhuanlan.zhihu.com/p/139666607 |

## 19. [商品] RTX 5090 benchmark 价格

引擎：searxng；失败引擎：-
卫生度：覆盖 0.50（最低 0.50） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB Benchmark and Specs - GPU comparison | www.gpu-monkey.com | 152 | - | Benchmark results and tests of the GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB in 3DMark an… | https://www.gpu-monkey.com/en/gpu-gigabyte_aorus_geforce_rtx_5090_xtreme_waterforce_wb |
| 2 | A thorough insight into technical specs and benchmarks of RTX 5090. | technical.city | 107 | - | Synthetic benchmark performance of GeForce RTX 5090. The combined score is measured on a 0-100 point… | https://technical.city/en/gpu/GeForce-RTX-5090 |
| 3 | NVIDIA GeForce RTX 5090 Review: Pushing Boundaries with AI Acceleration - Storag | www.storagereview.com | 161 | - | The Procyon AI Text Generation Benchmark Benchmark simplifies AI LLM performance testing by offering… | https://www.storagereview.com/review/nvidia-geforce-rtx-5090-review-pushing-boundaries-with-ai-acceleration |
| 4 | PassMark - GeForce RTX 5090 - Price performance comparison | www.videocardbenchmark.net | 162 | - | Price and performance details for the GeForce RTX 5090 can be found below. This is made using thousa… | https://www.videocardbenchmark.net/gpu.php?gpu=GeForce+RTX+5090&id=5725 |
| 5 | ASUS Details GeForce RTX 5090 and 5080 Pricing | www.techporn.ph | 160 | - | ASUS has officially launched the highly anticipated GeForce RTX 5090 and 5080 graphics cards in the … | https://www.techporn.ph/asus-details-geforce-rtx-5090-and-5080-pricing/ |

## 20. [商品] 国产显卡 摩尔线程 最新型号

引擎：searxng；失败引擎：-
卫生度：覆盖 0.63（最低 0.43） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 国产显卡品牌摩尔线程发新卡 单卡48GB显存_凤凰网 | i.ifeng.com | 74 | - | 国产显卡品牌摩尔线程，终于又要发新显卡了。这张显卡的具体型号为MTT S4000，规格方面非常不错。 国产显卡品牌摩尔线程发新卡 单卡48GB显存. | https://i.ifeng.com/c/8VfiImHtDxn |
| 2 | MTTS70显卡多少钱_摩尔线程MTTS70国产显卡售价及参数-硬件之家 | www.yingjianzhijia.com | 74 | - | 摩尔线程MTTS70国产显卡售价及参数. 发售价格：2499元. 品牌：摩尔线程. 型号：MTTS70. 显卡核心：春晓. 核心频率：1.6GHz. | https://www.yingjianzhijia.com/zhishi/76390.html |
| 3 | 砺算科技 7g100 国产显卡开启预约，12GB 售 3299... \| 知乎 | www.zhihu.com | 108 | - | 因此7G100和之前的国产显卡如S80、JH920等有显著不同，它是拿下了微软WHQL认证（要通过微软实验室一系列稳定与兼容性测试）的！另外目前生产的仅有3风扇型号，单卡长度达到29.4cm，因此要注… | https://www.zhihu.com/tardis/jm/ans/2040860622385061977 |
| 4 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | news.mydrivers.com | 36 | - | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |
| 5 | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU... | m.ithome.com | 42 | - | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU 快速迭代. | https://m.ithome.com/html/663833.htm |

## 卫生度汇总（M5-5.3，客观指标）

| 指标 | 值 | 含义 |
| --- | --- | --- |
| 结果总数 | 100 | 20 条查询的 top-N 合计 |
| 查询词覆盖率（加权） | 0.783 | 越高说明结果越贴题 |
| 同站冗余 | 0 | 同一可注册域超出上限的条数 |
| 聚合页 | 0 | 站点首页/栏目页这类「只是导航」的结果 |
| 非中英文脚本 | 0 | 中文查询下混入的俄语/韩语等标题 |
| 空内容 | 1 | 摘要不足 40 字、对 LLM 无价值 |
| 平均独立站点数 | 4.7 | 来源分散度 |


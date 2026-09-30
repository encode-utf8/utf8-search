# 相关性抽检报告（验收项 2-9）

- 生成时间：2026-09-30 15:27:43
- 深度模式：basic，每条取前 5 条
- 查询构成：20 条中英混合，覆盖 新闻 / 技术 / 政策 / 商品 各 5 条
- **采集缓存状态**：已禁用缓存（`--no-cache`），全部为本次实时采集

## 打分规则（先读这三条）

1. **门槛**：20 条查询里，满足「top5 中相关条数 ≥ 4」的查询数要 **≥ 18 条**（即 ≥ 90%）。
2. **scores 的 5 位依次对应排名 1-5**（第 1 位 = 排名第 1 的结果），逐位填 0/1。
3. **非零数字一律视为「相关」**（填 1 最规范；填 2 或其它非零值同样按相关计）。

- 判定命令：`python scripts/relevance.py --score-file m2-9-relevance-hardening-20260930-scores.csv`
- 通过标准（脚本口径）：top5 中相关数 ≥ 4 的查询占比 ≥ 90%
- 速览版（不带正文字数/发布时间/URL）：`m2-9-relevance-hardening-20260930-brief.md`

## 1. [新闻] 2026年9月 国内外重大新闻

引擎：searxng；失败引擎：brave, google, privacywall
卫生度：覆盖 0.49（最低 0.37） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 扩大军事足迹 中老两军班根机场联合保障和训练中心挂牌运行 | www.rfi.fr | 94 | 2026-09-29T14:18:22 | 电邮新闻头条新闻就在您的每日新闻信里. 订阅.蒙古国总理尼·乌其日勒（Prime Minister of Mongolia Nyam-Osor Uchral）2026年9月27日访问日本. | https://www.rfi.fr/cn/%E4%BA%9A%E6%B4%B2/20260929-%E6%89%A9%E5%A4%A7%E5%86%9B%E4%BA%8B%E8%B6%B3%E8%BF%B9-%E4%B8%AD%E8%80%81%E4%B8%A4%E5%86%9B%E7%8F%AD%E6%A0%B9%E6%9C%BA%E5%9C%BA%E8%81%94%E5%90%88%E4%BF%9D%E9%9A%9C%E5%92%8C%E8%AE%AD%E7%BB%83%E4%B8%AD%E5%BF%83%E6%8C%82%E7%89%8C%E8%BF%90%E8%A1%8C |
| 2 | 从台海到日本，习近平试图“撬动”特朗普的亚太立场 - 纽约时报中文网 | cn.nytimes.com | 66 | 2026-09-28T01:32:52 | 2026年9月28日. 中国领导人习近平和特朗普总统周四在白宫举行的欢迎仪式上。他从事新闻工作已超过20年。 翻译：纽约时报中文网. | https://cn.nytimes.com/china/20260928/summit-xi-trump-taiwan-japan/ |
| 3 | 重要新闻_中华人民共和国外交部 | www.fmprc.gov.cn | 225 | - | 韩正会见联合国秘书长古特雷斯 出席全球发展倡议5周年高级别对话会 宣读习近平主席贺信并致辞（2026-09-26）"李强出席2026年世界技能大会开幕式并致辞（2026-09-23）""韩正会见联合国… | https://www.fmprc.gov.cn/zyxw/ |
| 4 | 2026年9月学期新生迎新 – 仁川国际机场 | www.jbsc.ac.kr | 0 | - |  | https://www.jbsc.ac.kr/portal/liuxue_chn/bbs/view.do?menuId=M0195000500000000&boardSeq=81432 |
| 5 | 美国之音中文网新闻 - 美国之音中文网 | www.voachinese.com | 814 | - | 4 days ago — 唐纳德·特朗普总统在结束接待中国国家主席习近平对美国进行的三天国事访问之际表示，美国展示了实力以及与中国的友谊。这次在华盛顿举行的美中元首峰会在星期五(9月25日)结束。特朗… | https://www.voachinese.com/z/1739 |

## 2. [新闻] 最近一周 AI 行业动态

引擎：searxng；失败引擎：-
卫生度：覆盖 0.50（最低 0.31） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 滴滴代操（都市版） - 短剧视频在线观看 \| 黄果短剧 | 679.kmexvuoz.cc | 62 | 2026-09-30T05:04:05 | 首页 AI成人短剧 AI成人漫剧 AI换脸 AI魔改 专题 排行榜 黄果吃瓜 回家的路 黄果短剧APP 个人中心.最近浏览. | https://679.kmexvuoz.cc/video/1189/ |
| 2 | AI行业发展一周动态 - 知乎 | zhuanlan.zhihu.com | 268 | - | 2025年全球端侧AI市场规模将增至1.22万亿元年复合增长率达40%[2] · 2025年12月9日，谷歌公布智能眼镜Project Aura和Android XR系统关键细节，理想汽车发布首款AI… | https://zhuanlan.zhihu.com/p/1983093760448542417 |
| 3 | AI周刊丨本周不可错过的AI行业动态（6.9-6.15） - 知乎 | zhuanlan.zhihu.com | 585 | - | 科大讯飞在深圳举办智能交互产品升级发布会，主题为“交互领航智启新章”。 在发布会上，AIUI、机器人超脑、虚拟数字人与讯飞星辰四大开发平台亮相，展示软硬件协同优化成果。 ..."AI周刊丨本周不可错过… | https://zhuanlan.zhihu.com/p/1917647873308357987 |
| 4 | 每日AI资讯、热点、动态、融资、产品发布 \| AI工具集 | ai-bot.cn | 422 | - | August 10, 2023 — 面壁智能联合 OpenBMB 开源 ForgeStencil，全球首个 AI 驱动的 Stencil 全自动优化系统。ForgeStencil由 Kernel Ag… | https://ai-bot.cn/daily-ai-news/ |
| 5 | 资讯合集 - 前沿观澜 官方站 | www.uijae.com | 178 | - | AI监管企业实践测评：从「被动合规」到「主动治理」的真实体验 ; 作为一家中型金融科技公司的合规负责人，我每天最头疼的不是业务增长，而是如何应对层出不穷的AI监管要求。直到我们部署了「智盾AI治理平台… | https://www.uijae.com/%E7%81%AB%E9%94%85%E9%94%85%E5%85%B7%E4%BB%80%E4%B9%88%E6%9D%90%E8%B4%A8%E5%A5%BD/ |

## 3. [新闻] latest news semiconductor export controls

引擎：searxng；失败引擎：yep
卫生度：覆盖 0.72（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Silicon-level intelligence for the AI hardware trade — from wafer to rack. | diesignal.com | 214 | 2026-09-29T14:03:37 | China Responds to US Semiconductor Export Controls, OECD Report. China has hit back at US semiconduc… | https://diesignal.com/ |
| 2 | China may allow tech giants to buy new... \| Digital Watch Observatory | dig.watch | 279 | 2026-09-28T21:45:47 | The MIIT’s willingness to encourage the purchase of RTX Pro 5500 chips and the easing of restriction… | https://dig.watch/updates/china-may-allow-new-nvidia-chips |
| 3 | Articles for “Chip Export News” | exportcompliancedaily.com | 1201 | - | The Information Technology Industry Council (ITI) and four other industry groups called on Congress … | https://exportcompliancedaily.com/topic/chip_export_news |
| 4 | Insight into the U.S. Semiconductor Export Controls Update | www.csis.org | 169 | - | The Scholl Chair team analyzes the latest update to U.S. advanced semiconductor export controls, whi… | https://www.csis.org/analysis/insight-us-semiconductor-export-controls-update |
| 5 | China lashes out at latest U.S. export controls on chips | www.asahi.com | 200 | - | BEIJING--China on Saturday criticized the latest U.S. decision to tighten export controls that would… | https://www.asahi.com/ajw/articles/14738636 |

## 4. [新闻] 台风 最新消息 路径

引擎：searxng；失败引擎：-
卫生度：覆盖 0.77（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 刚刚！ 台风“丹娜丝”路径有变！ 或在福建浙江登陆 | c.m.163.com | 60 | - | 注意！ 90度拐弯. 台风“丹娜丝”路径有变化. 或在闽浙沿海登陆. 台风最新消息. 中央气象台消息. 7月5日13时. | https://c.m.163.com/news/a/K3NE3U0Q0550IMZX.html?spss=sps_sem |
| 2 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | gz.bendibao.com | 120 | - | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级，台风级或强台风级）… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 3 | 超强台风“白海豚”最大风力达17级，8月5日夜间之前对我国海区无影响，中国.... | news.ycwb.com | 202 | - | 据中央气象台最新消息，今年第13号台风“白海豚”（超强台风级）的中心今天（8月1日）早晨5时位于日本东京东南方向大约2550公里的西北太平洋洋面上，就是北纬20.0度、东经158.8度，中心附近最大风… | https://news.ycwb.com/ikimvkctkj/content_54258026.htm |
| 4 | 热带低压 - 台风网- 中央气象台 | typhoon.nmc.cn | 373 | - | 6 days ago — 舒力基 · 台风“舒力基”最新位置：北纬28.9度， 东经135.0度，中心附近最大风力10级 · 触屏版 · 24 小 时 警 戒 线 · 48 小 时 警 戒 线 · 最… | https://typhoon.nmc.cn/web.html |
| 5 | 2026年第18... | m.nj.bendibao.com | 84 | - | 导语 2026年第18号台风沙德尔于8月19日生成，“沙德尔”巅峰强度有可能达到超强台风级，但后期路径变数较大，具体路径详见正文。的天气影响、活动取消或延期提示等消息。 | https://m.nj.bendibao.com/news/182606.shtm |

## 5. [新闻] 美国 关税 最新政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.83（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026 美国关税最新消息 — 中菲行国际物流集团 | cn.dimerco.com | 987 | - | June 6, 2026 — 除232关税调整外，美国贸易代表办公室（USTR）还发布了一份《联邦公报》（Federal Register Notice），明确表明政府在7月24日第122条款（Sec… | https://cn.dimerco.com/us-tariff-update-2026/ |
| 2 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | www.edurew.com | 161 | - | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协会近日表示，根据最新… | https://www.edurew.com/html/03c79099206.html |
| 3 | 特朗普为何突然出台重大关税豁免？ “特别适用于中国产品” | www.jfdaily.com | 68 | - | 最新豁免的出台，终结了美国出台“对等关税”后的“狂野一周”，也被视为美国政府关税政策的“180度大转弯”，再次凸显其贸易政策的混乱本质。 | https://www.jfdaily.com/wx/detail.do?id=892234 |
| 4 | 三年来首次下滑！关税政策正让美国经济经历“超出预期的糟糕” - 韩国最大的.... | chinese.joins.com | 212 | - | 2025.05.02.美国商务部4月30日公布最新数据显示，2025年第一季度，按年率计算，美国国内生产总值(GDP)环比萎缩0.3%，为2022年以来的首次收缩。这一最新数据的糟糕程度超出市场预期，… | https://chinese.joins.com/news/articleView.html?idxno=119620 |
| 5 | 关税政策及其对全球贸易的影响 \| UPS Supply Chain Solutions - 美国 | www.ups.com | 868 | - | 根据第 122 条关税政策，自 2026年2月24日起，美国对所有国家的进口商品统一加征 10% 的关税。但是也存在几项豁免情形，例如符合美墨加协定认证的商品。更多信息可在此处查看。"根据要求，UPS… | https://www.ups.com/cn/zh/supplychain/resources/news-and-market-updates/2025-us-tariffs-impact-global-trade |

## 6. [技术] Python 3.13 新特性

引擎：searxng；失败引擎：-
卫生度：覆盖 0.82（最低 0.50） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Python 3.13 有什么新变化 — Python 3.13.1 文档 | www.sdx.cool | 734 | - | January 21, 2026 — Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 … | https://www.sdx.cool/index/python_docs/whatsnew/3.13.html |
| 2 | Python 3.13 有什么新变化 — Python 3.16.0a0 文档 | docs.python.org | 725 | - | Python 3.13 及以后的版本有两年的完整支持，另加三年的安全修正。 · Python 现在默认会使用新的 interactive shell，它基于来自 PyPy 项目 的代码。 当使用从交互… | https://docs.python.org/zh-cn/dev/whatsnew/3.13.html |
| 3 | 好学编程：Python 3.13 这些新特性你一定要知道！ - 知乎 | zhuanlan.zhihu.com | 703 | - | Python 3.13 终于支持禁用全局解释器锁（GIL）了！这意味着你的多线程 Python 程序可以充分利用多核处理器的优势。虽然目前仍处于实验阶段，但这无疑是一个激动人心的突破。"Python … | https://zhuanlan.zhihu.com/p/12824443094 |
| 4 | Python 3.13：新版本发布，一些重要更新 - 知乎 | zhuanlan.zhihu.com | 1015 | - | Python 3.13 中新的实验性 JIT 编译器使用了一种名为复制和修补(copy-and-patch)的新算法。这种编译技术背后的基本思想：为目标 CPU 找到一个具有预编译机器代码的合适模板，… | https://zhuanlan.zhihu.com/p/2297580514 |
| 5 | [アップデート] AWS Lambda で Python 3.13... | dev.classmethod.jp | 78 | - | 情報が古い可能性がありますので、ご注意ください。 いわさです。 先日、AWS SAM CLI にて Python 3.13 サポートがアナウンスされました。 | https://dev.classmethod.jp/articles/aws_lambda_support_python313/ |

## 7. [技术] MCP protocol specification 2026

引擎：searxng；失败引擎：resulthunter
卫生度：覆盖 0.95（最低 0.75） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 다음 MCP 스펙 릴리즈(2026-07-28)의 주요 내용: Stateless 전환 및 공식 확장 도입 예.... | discuss.pytorch.kr | 222 | - | 2026.05.27.MCP 스펙 릴리즈 후보(The 2026-07-28 MCP Specification Release Candidate) 소개 Model Context Protoc… | https://discuss.pytorch.kr/t/mcp-2026-07-28-stateless/10387 |
| 2 | The 2026-07-28 Specification \| Model Context Protocol Blog | blog.modelcontextprotocol.io | 222 | - | 2026.07.28.The 2026-07-28 Model Context Protocol specification is out, bringing a stateless protocol… | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| 3 | MCP, 세션 지우고 HTTP 인프라 위로… 2026-07-28 spec 확정 - Insights | insights.marvin-42.com | 329 | - | 2026.07.30.agent tool 서버를 띄울 때 붙어 다니던 sticky session 부담이 MCP 정식 spec에서 사라진다. Model Context Protocol … | https://insights.marvin-42.com/articles/mcp-http-2026-07-28-spec |
| 4 | With a stateless makeover, new MCP spec targets enterprise scale | arstechnica.com | 174 | - | 2026.07.30.New MCP specification addresses the main barrier to enterprise adoption Plus, a new polic… | https://arstechnica.com/ai/2026/07/with-a-stateless-makeover-new-mcp-spec-targets-enterprise-scale/ |
| 5 | The 2026-07-28 MCP Specification Release Candidate \| Model Context Protocol Blog | blog.modelcontextprotocol.io | 159 | - | MCP Apps (SEP-1865) lets servers ship interactive HTML interfaces that hosts render in a sandboxed i… | https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ |

## 8. [技术] FastAPI 与 Django 性能对比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.71（最低 0.55） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | python web框架哪家强？ Flask、Django、FastAPI对比_fastapi flask... | blog.csdn.net | 101 | - | 对比Flask、Django和FastAPI三款python框架，Flask更适合新手上手。_fastapi flask django性能对比.Python使用总结之FastAPI和Flask框架对比… | https://blog.csdn.net/way311/article/details/139771390 |
| 2 | Django 与 FastAPI 架构对比：学习路径指南Django 与 FastAPI... | juejin.cn | 59 | - | Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。 本文将详解如何对两者进行评估选择。 | https://juejin.cn/post/7565799761123786806 |
| 3 | FastAPI 与 Django：2026 年最佳 Python 框架 | www.lastingdynamics.com | 79 | - | FastAPI vs Django for Startups（MVP）.FastAPI 与 Django 的主要区别. 性能比较. 异步功能. 开发人员体验. | https://www.lastingdynamics.com/zh/blog/fastapi-vs-django/ |
| 4 | 2026年Django vs Flask vs FastAPI ： 该选哪个 \| [ Mecanik Dev ] | mecanik.dev | 62 | - | 本指南深入对比Django、Flask和FastAPI，涵盖性能、生态系统、学习曲线，以及根据实际构建内容应该选择哪个框架。 | https://mecanik.dev/zh-cn/posts/python-web-framework-comparison-2026-django-vs-flask-vs-fastapi/ |
| 5 | Django框架：优缺点、实用场景及与Flask、FastAPI... | cloud.tencent.com | 56 | - | 在本文中，我们将探讨Django的get和post请求、优缺点、实用场景以及与Flask、FastAPI的对比。 | https://cloud.tencent.com/developer/article/2294156 |

## 9. [技术] how does HTTP/3 QUIC work

引擎：searxng；失败引擎：-
卫生度：覆盖 0.93（最低 0.83） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HTTP/3 Maintains a Consistent Connection ID | www.pubnub.com | 151 | - | How does HTTP/3 maintain a constant Connection ID? How does switching from 5G to Wi-Fi affect HTTP/3… | https://www.pubnub.com/blog/http3-and-quic-the-connection-id/ |
| 2 | [Illustration] How does HTTP/3 (HTTP over QUIC) work?... \| SEの道標 | milestone-of-se.nesuke.com | 174 | - | Change from HTTP/2 to HTTP/3. HTTP/3 has been decided to operate on a new protocol called QUIC. QUIC… | https://milestone-of-se.nesuke.com/en/l7protocol/http/http3-over-quic/ |
| 3 | The Future of the Internet is here: QUIC Protocol and HTTP/3 \| Medium | medium.com | 266 | - | How does QUIC work? Unlike TCP, which uses a connection-oriented approach, QUIC uses a multiplexed s… | https://medium.com/@luisrodri/the-future-of-the-internet-is-here-quic-protocol-and-http-3-d7061adf424f |
| 4 | How QUIC works \| HTTP/3 explained | http3-explained.haxx.se | 224 | - | HTTP/3 explained. README. English. Why QUIC. Process. Protocol features.Without explaining the exact… | https://http3-explained.haxx.se/en/quic |
| 5 | What Are QUIC and HTTP/3? \| F5 | www.f5.com | 266 | - | HTTP/3, based on QUIC, is the third major version of the Hypertext Transfer Protocol (HTTP) and was … | https://www.f5.com/glossary/quic-http3 |

## 10. [技术] Rust async runtime tokio 原理

引擎：searxng；失败引擎：-
卫生度：覆盖 0.86（最低 0.71） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Tokio 运行时 - 深度解析 | atcfu.com | 107 | - | Tokio 运行时. 深度解析 Rust 异步运行时核心原理. 正确 async fn good() { tokio::time::sleep(. Duration::from_secs(1) ).a… | https://atcfu.com/ai-articles/tokio-runtime/ |
| 2 | Rust Async + Tokio 入門：非同步 Rust vs Python asyncio · 每日拍拍 | dailypypy.org | 106 | - | Rust：tokio::sync::mpsc. 八、底層原理：Python vs Rust 的非同步模型.features = ["full"] 會啟用所有功能（runtime、net、time、sy… | https://dailypypy.org/learn/rust-async-tokio/ |
| 3 | Tokio：Rust 高并发异步运行时的实战指南——IO 密集型项目深度剖析 | rs.bifuba.com | 113 | - | 原理：Tokio Streams 组合 IO 操作，merge 多个源。 代码： use tokio::net::UdpSocket; use tokio_stream::{self as strea… | https://rs.bifuba.com/tokio-rusts-practical-guide-to-highly-concurrent-asynchronous-runtimes-in-depth-analysis-of-io-intensive-projects |
| 4 | 13｜独立王国：初步了解Rust异步并发编程-Rust... | time.geekbang.org | 128 | - | async rust.文章介绍了async函数和块的定义方式，以及异步运行时的作用和原理。 此外，还详细介绍了基于tokio runtime的代码范例，包括文件的读写操作、定时器操作等。 通过文章，读… | https://time.geekbang.org/column/article/725837 |
| 5 | 理解tokio的核心(1): runtime - Rust入门秘籍 | rust-book.junmajinlong.com | 94 | - | 创建tokio Runtime. async main.阻塞当前线程，等待异步任务的完成 thread::sleep(std::time::Duration::from_secs(10)) | https://rust-book.junmajinlong.com/ch100/01_understand_tokio_runtime.html |

## 11. [政策] 2026年 新能源汽车 补贴政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.87（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | post.smzdm.com | 139 | - | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. 新能源汽车补贴政策延… | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 国补出炉！ 电车油车补贴揭晓-有驾 | youjia-pc.bdstatic.com | 95 | - | 好消息是，2026年的购车补贴政策终于出来了，不管是电车还是油车，补贴额度是多少？新能源汽车补贴政策. 咱们再来看看置换补贴这块儿。 新能源汽车的最高补贴是1.5万元，也就是购车价格的8%。 | https://youjia-pc.bdstatic.com/article/9608259256117415955.html |
| 3 | 别光顾着过年，快来买车 625亿元“国补”已经发放 - OFweek新能源汽车网 | nev.ofweek.com | 75 | - | 从2025年末开始，国内汽车消费市场便进入了政策切换的过渡期——原有的新能源汽车购置税免征政策、汽车以旧换新补贴政策逐步收尾，而2026年新的政策尚. | https://nev.ofweek.com/2026-02/ART-71000-8420-30681174.html |
| 4 | qdzb07b20260116C | epaper.qingdaonews.com | 77 | - | 2026 年伊始新一轮购车国补新政正式落地实施。 此次新政不仅对补贴模式进行了优化还 同步调整了新能源汽车购置税优惠政策形成“国补+税补”的双重让利格局。 | https://epaper.qingdaonews.com/qdzb/resfile/2026-01-16/A07/qdzb-20260116-A07.pdf |
| 5 | 8月多地优化汽车消费政策 地方购车补贴持续落地 _ 东方财富网 - 财经首页 ,东.... | finance.eastmoney.com | 199 | - | 2026.08.02.进入8月，多地调整汽车消费政策，变化集中在简化申领流程、增加地方购车补贴和明确资金配额等方面。7月30日，济南市商务局发布公告，自8月1日起，消费者申领汽车报废更新或置换更新补贴… | https://finance.eastmoney.com/a/202608023829105787.html |

## 12. [政策] 数据出境安全评估办法 最新

引擎：searxng；失败引擎：-
卫生度：覆盖 0.74（最低 0.43） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 筑牢数据出境安全防线，《数据出境安全评估办法》正式实施-安全KER... | www.anquanke.com | 94 | - | 《办法》具体内容包括： 数据出境安全评估原则. 坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 申报数据出境安全评估的触发条件. | https://www.anquanke.com/post/id/279455 |
| 2 | 数据出境安全评估办法.docx - 墨天轮文档 | www.modb.pro | 70 | - | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 3 | 合规及跨境数据传输联合白皮书2024 | www.pwccn.com | 80 | - | 国家网信办受理后将统一开展数据 出境安全评估工作开展实质审查并出具结论完成数 据出境安全评估。在通过安全评估后企业仍需要对数据出境进行持续的 评估监管。 04. | https://www.pwccn.com/zh/issues/cybersecurity-and-data-privacy/joint-white-paper-on-compliance-cross-border-data-transfers-may2024.pdf |
| 4 | 中国网络安全审查“组合拳”学者:全面管制时代来临 - 美国之音中文网 您可靠.... | www.voachinese.com | 195 | - | 2022.07.22.中国国家互联网信息办公室(网信办)针对网络审查再祭出一系列新规，除自8月1日起要求境内各网络平台严格核实使用者的身分外，也发布《数据出境安全评估办法》，严格管控数据跨国流通，更对… | https://www.voachinese.com/a/china-launches-security-review-on-cnki-the-country-s-leading-academic-research-database-0722222/6666367.html |
| 5 | [每日信息流] 2025-06-07 · Issue #97 · yiliufeng168/picker · GitHub | github.com | 206 | - | 2025.06.07.密码加密存储与其他敏感信息的安全处理 国家密码管理局：征集国家密码科学基金第二批项目指南建议 《网络交易平台规则监督管理办法》公开征求意见（附全文）... 《2024-2025中… | https://github.com/yiliufeng168/picker/issues/97 |

## 13. [政策] EU AI Act compliance requirements

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance \| Microsoft Trust Center | www.microsoft.com | 162 | - | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restricted Use Pol… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 2 | EU AI Act Compliance Guide \| Aona AI | aona.ai | 160 | - | Key innovations include the creation of AI regulatory sandboxes, mandatory conformity assessments fo… | https://aona.ai/compliance/regulations/eu-ai-act/ |
| 3 | EU AI Act Compliance Guide \| Sinaptic.AI | sinaptic.ai | 162 | - | For providers and deployers of GPAI (including chatbots like ChatGPT), there are strict transparency… | https://sinaptic.ai/articles/eu-ai-act-compliance |
| 4 | EU AI Act Compliance: What You Need to Know | www.sai360.com | 156 | - | SAI360 helps organizations take a practical, structured approach to meeting the requirements of the … | https://www.sai360.com/regulations/eu-ai-act |
| 5 | How different stakeholders are thinking about EU AI Act compliance \| IAPP | iapp.org | 160 | - | ITIC argues in its EU AI policy priorities that member states and the Commission need to coordinate … | https://iapp.org/news/a/how-different-stakeholders-are-thinking-about-eu-ai-act-compliance |

## 14. [政策] 个人所得税 专项附加扣除 标准

引擎：searxng；失败引擎：-
卫生度：覆盖 0.99（最低 0.96） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 你可能有一笔“退款”！ 马上截止，尽快确认 | m.gmw.cn | 100 | - | 按照什么标准扣除？ 七项个人所得税专项附加扣除，都是按照什么标准进行扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个婴幼儿（子女）每月2000元。 赡养老人专项附加扣除标准为每月3000元。 | https://m.gmw.cn/2025-12/28/content_1304282511.htm |
| 2 | 国务院关于提高个人所得税有关专项附加扣除标准的通知_税务_中国政府网 | www.gov.cn | 79 | - | 为进一步减轻家庭生育养育和赡养老人的支出负担，依据《中华人民共和国个人所得税法》有关规定，国务院决定，提高3岁以下婴幼儿照护等三项个人所得税专项附加扣除标准。 | https://www.gov.cn/zhengce/content/202308/content_6901206.htm |
| 3 | 提高个人所得税3岁以下婴幼儿照护、子女教育、赡养老人专项附加扣除标准的.... | www.xjkel.gov.cn | 214 | - | 2023.09.13.问：提高个人所得税3岁以下婴幼儿照护、子女教育、赡养老人专项附加扣除标准的具体规定是什么？ 答：根据国务院发布的《关于提高个人所得税有关专项附加扣除标准的通知》（国发〔2023〕… | https://www.xjkel.gov.cn/xjkrls/c117543/202309/fc10821a7adf4eb7adceb9646df21b87.shtml |
| 4 | 国务院印发《个人所得税专项附加扣除暂行办法》 - 市财政局 | www.huaihua.gov.cn | 204 | - | 2018.12.23.新华社北京12月22日电 国务院日前印发《个人所得税专项附加扣除暂行办法》（以下简称《办法》），自2019年1月1日起施行。 《办法》指出，个人所得税专项附加扣除，是指个人所得税… | https://www.huaihua.gov.cn/czj/c100738/201812/3209b912c78742bc934904841c4c89eb.shtml |
| 5 | 月底截止，事关收入！ 抓紧确认_腾讯新闻 | news.qq.com | 102 | - | 本月底，2025年度个人所得税专项附加扣除信息确认将截止。各个项目分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000… | https://news.qq.com/rain/a/20241229A04S4300 |

## 15. [政策] children privacy law COPPA update

引擎：searxng；失败引擎：-
卫生度：覆盖 0.84（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Children and Teens' Online Privacy Protection Act (COPPA 2.0) | www.termsfeed.com | 196 | - | It is an update to the Children’s Online Privacy Protection Act (COPPA). COPPA 2.0 takes a stricter … | https://www.termsfeed.com/blog/coppa-2-children-teens-online-privacy-protection-act/ |
| 2 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for kids plan | digiday.com | 221 | - | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (COPPA) and w… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure-against-facebooks-instagram-for-kids-plan/ |
| 3 | Senator Says Federal Law Protecting Children Online Needs Updating | www.wsj.com | 222 | - | 2021.10.01.Sen. Maria Cantwell (D., Wash.)—who chairs the powerful Commerce Committee—said the big p… | https://www.wsj.com/livecoverage/facebook-hearing-live-updates/card/TwUpnUNNG7lhv25M7F8I |
| 4 | Privacy Policy - The Wheeler School - N-12 Coed Day School in Providence RI | www.wheelerschool.org | 158 | - | COPPA Statement The Children’s Online Privacy Protection Act (COPPA) is a federal law governing the … | https://www.wheelerschool.org/privacy-policy/ |
| 5 | What is COPPA? The Children's Online Privacy Protection Act | ed.link | 154 | - | The Children's Online Privacy Protection Act, or COPPA, is a U.S. federal law that protects the pers… | https://ed.link/community/coppa/ |

## 16. [商品] iPhone 17 Pro 价格 参数

引擎：searxng；失败引擎：-
卫生度：覆盖 0.46（最低 0.30） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 苹果8x参数 - 京东 | www.jd.com | 259 | - | Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus e二手手机A16详见质检报告 苹果 iPhone 8荣耀亲选LCHSE X5s蓝牙耳机无线入… | https://www.jd.com/hprm/9987d46c01cd9b8ab46f.html |
| 2 | iPhone 17 Pro and 17 Pro Max online in Saudi Arabia | redsea.com | 101 | - | Explore iPhone, the world’s most powerful personal device. Check out iPhone 17 Pro, iPhone 17 Pro Ma… | https://redsea.com/en/iphone-17-pro |
| 3 | Apple unveils iPhone 17 Pro and iPhone 17 Pro Max - Apple | www.apple.com | 265 | - | “iPhone 17 Pro is by far the most powerful iPhone we’ve ever made, with a stunning new design rebuil… | https://www.apple.com/newsroom/2025/09/apple-unveils-iphone-17-pro-and-iphone-17-pro-max/ |
| 4 | Apple iPhone 17 Pro Max | www.wirefly.com | 152 | - | Apple iPhone 17 Pro Max phone. Read reviews of the Apple iPhone 17 Pro Max and shop online. Apple iP… | https://www.wirefly.com/product/apple-iphone-17-pro-max |
| 5 | 【苹果iPhone 17 256GB】报价_参数_图片_论坛_Apple iPhone 17,苹果 17,iPhone17苹果手机报.... | detail.zol.com.cn | 181 | - | 中关村在线为您提供苹果iPhone 17 256GB 手机最新报价，同时包括苹果iPhone 17 256GB图片、苹果iPhone 17 256GB参数、苹果iPhone 17 256GB评测行情、… | https://detail.zol.com.cn/cell_phone/index2139583.shtml |

## 17. [商品] best noise cancelling headphones 2026 review

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | www.tiktok.com | 234 | - | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise-cancellin… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best noise-cancelling headphones – the top earphones... \| Ideal Home | www.idealhome.co.uk | 191 | - | Best noise-cancelling headphones 2026. Sony WH-1000XM3 headphones with Ideal Home approved logo.4. L… | https://www.idealhome.co.uk/buying-guide-reviews/best-noise-cancelling-headphones-231575 |
| 3 | The 5 Best Noise Cancelling Earbuds of 2026 - RTINGS.com | www.rtings.com | 247 | - | Compare Results Table Tool Review List Review Index Graph Review Pipeline Vote Custom Ratings.918 He… | https://www.rtings.com/headphones/reviews/best/noise-cancelling-earbuds |
| 4 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | www.whathifi.com | 257 | - | Best noise-cancelling headphones 2026 – 6 sensational pairs picked by our expert reviewers.All of th… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |
| 5 | Best cheap noise-cancelling headphones 2026: expert-tested recommendations \| Wha | www.whathifi.com | 154 | - | All review verdicts are agreed upon by the team rather than an individual reviewer to eliminate any … | https://www.whathifi.com/best-buys/best-cheap-noise-cancelling-headphones |

## 18. [商品] 扫地机器人 推荐 性价比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.84（最低 0.63） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 【26... | www.bilibili.com | 102 | - | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人选购攻略！ 10:3… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 石头P20 Max vs... \| 新浪网 | k.sina.com.cn | 95 | - | 石头P20 Max vs 同价位扫地机，谁才是性价比之王？ 3个维度硬核对比+FAQ.关键字 : 石头P20 Max 扫地机器人推荐 高性价比扫地机 同价位扫地机对比 2026年扫地机选购. | https://k.sina.com.cn/article_7879923199_1d5ae15ff06801jub0.html |
| 3 | 智能拖地机器人推荐【TOP10】机器人拖把 \| 美国好物推荐 | yycams.com | 160 | - | 拖地机器人推荐【TOP10】机器人拖把.6. 性价比最高的2合一拖地机器人 ILIFE V8s 2-in-1 Mopping Robot Vacuum8. 最智能的拖地机器人 Roborock S6 … | https://yycams.com/best-robot-mops/ |
| 4 | 米家扫拖机器人评测 米家的性价比从未让人失望-电子发烧友网 | m.elecfans.com | 66 | - | 还有一点不同是，命名上扫地变成了扫拖，米家三年磨一剑推出了其扫地机器人的全新升级版：扫拖机器人。六、总结：米家的性价比从未让人失望. | https://m.elecfans.com/article/1052310.html |
| 5 | 想给父母买个扫地机器人，求推荐 - V2EX | www.v2ex.com | 50 | - | 想给父母买个扫地机器人，求推荐.@GT7 #2 现在的扫地机器人谁还不带拖地功能啊？ ethsol. | https://www.v2ex.com/t/1008824 |

## 19. [商品] RTX 5090 benchmark 价格

引擎：searxng；失败引擎：-
卫生度：覆盖 0.50（最低 0.50） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Qwen Image 2.1 RTX 5090 benchmark: 500 W was 3.6% slower | stableyogi.com | 125 | 2026-09-27T16:04:14 | Qwen Image 2.1 BF16 RTX 5090 power limit benchmark chart showing ComfyUI speed, average power draw, … | https://stableyogi.com/blog/rtx-5090-qwen-image-2-1-power-limit-benchmark |
| 2 | GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB Benchmark and Specs - GPU comparison | www.gpu-monkey.com | 152 | - | Benchmark results and tests of the GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB in 3DMark an… | https://www.gpu-monkey.com/en/gpu-gigabyte_aorus_geforce_rtx_5090_xtreme_waterforce_wb |
| 3 | GeForce RTX 5090 D V2 [in 1 benchmark] | technical.city | 161 | - | This section provides details about the physical dimensions of GeForce RTX 5090 D V2 and its compati… | https://technical.city/en/video/GeForce-RTX-5090-D-V2?search=RTX+5090+benchmark+%E4%BB%B7%E6%A0%BC+site%3Atechnical.city&safe=0 |
| 4 | NVIDIA GeForce RTX 5090 Review: Pushing Boundaries with AI Acceleration - Storag | www.storagereview.com | 161 | - | The Procyon AI Text Generation Benchmark Benchmark simplifies AI LLM performance testing by offering… | https://www.storagereview.com/review/nvidia-geforce-rtx-5090-review-pushing-boundaries-with-ai-acceleration |
| 5 | The MOST POWERFUL Gaming PC EVER! RTX 5090... - YouTube | www.youtube.com | 167 | - | This RTX 5090 Founders Edition PC Build uses the Ryzen 7 9800x3d and Montech King 65 Pro!59 Founders… | https://www.youtube.com/watch?v=mlIyNH-joaE |

## 20. [商品] 国产显卡 摩尔线程 最新型号

引擎：searxng；失败引擎：-
卫生度：覆盖 0.63（最低 0.61） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MTTS70显卡多少钱_摩尔线程MTTS70国产显卡售价及参数-硬件之家 | www.yingjianzhijia.com | 74 | - | 摩尔线程MTTS70国产显卡售价及参数. 发售价格：2499元. 品牌：摩尔线程. 型号：MTTS70. 显卡核心：春晓. 核心频率：1.6GHz. | https://www.yingjianzhijia.com/zhishi/76390.html |
| 2 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | news.mydrivers.com | 36 | - | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |
| 3 | 2499元现货！摩尔线程MTT S70国产游戏显卡开卖 | diy.zol.com.cn | 115 | - | 摩尔线程MTT S70国产游戏显卡开卖.这款显卡是S80显卡的精简版，继续推动国产显卡普及，基于7nm工艺春晓GPU核心，配备3584个MUSA核心，频率1.6GHz，浮点性能11.2TFLOPS，G… | https://diy.zol.com.cn/819/8195169.html |
| 4 | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU... | m.ithome.com | 42 | - | 国产显卡厂商摩尔线程宣布完成 15 亿元 B 轮融资，加速多功能 GPU 快速迭代. | https://m.ithome.com/html/663833.htm |
| 5 | 主动接受市场检验，就是摩尔线程的最大优势\|显卡\|大众_网易订阅 | www.163.com | 90 | - | 让AI触手可及，摩尔线程还在发力. 就在5月18日晚间，摩尔线程在北京中关村召开2026产品发布会。首先，从算力基础设施来看，摩尔线程公布了夸娥（KUAE）万卡算力集群的最新情况。 | https://www.163.com/dy/article/KT8C935L0511BE1V.html |

## 卫生度汇总（M5-5.3，客观指标）

| 指标 | 值 | 含义 |
| --- | --- | --- |
| 结果总数 | 100 | 20 条查询的 top-N 合计 |
| 查询词覆盖率（加权） | 0.773 | 越高说明结果越贴题 |
| 同站冗余 | 0 | 同一可注册域超出上限的条数 |
| 聚合页 | 0 | 站点首页/栏目页这类「只是导航」的结果 |
| 非中英文脚本 | 0 | 中文查询下混入的俄语/韩语等标题 |
| 空内容 | 2 | 摘要不足 40 字、对 LLM 无价值 |
| 平均独立站点数 | 4.8 | 来源分散度 |


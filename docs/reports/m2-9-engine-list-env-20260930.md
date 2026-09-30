# 相关性抽检报告（验收项 2-9）

- 生成时间：2026-09-30 10:37:01
- 深度模式：basic，每条取前 5 条
- 查询构成：20 条中英混合，覆盖 新闻 / 技术 / 政策 / 商品 各 5 条
- **采集缓存状态**：已禁用缓存（`--no-cache`），全部为本次实时采集

## 打分规则（先读这三条）

1. **门槛**：20 条查询里，满足「top5 中相关条数 ≥ 4」的查询数要 **≥ 18 条**（即 ≥ 90%）。
2. **scores 的 5 位依次对应排名 1-5**（第 1 位 = 排名第 1 的结果），逐位填 0/1。
3. **非零数字一律视为「相关」**（填 1 最规范；填 2 或其它非零值同样按相关计）。

- 判定命令：`python scripts/relevance.py --score-file m2-9-engine-list-env-20260930-scores.csv`
- 通过标准（脚本口径）：top5 中相关数 ≥ 4 的查询占比 ≥ 90%
- 速览版（不带正文字数/发布时间/URL）：`m2-9-engine-list-env-20260930-brief.md`

## 1. [新闻] 2026年9月 国内外重大新闻

引擎：searxng；失败引擎：brave, google, privacywall, resulthunter, yep
卫生度：覆盖 0.42（最低 0.37） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 特朗普推出AI... - RFI - 法国国际广播电台 | www.rfi.fr | 64 | 2026-09-29T19:15:09 | 美国总统特朗普 2026年9月27日 © Nathan Howard / Reuters.电邮新闻头条新闻就在您的每日新闻信里. | https://www.rfi.fr/cn/%E6%94%BF%E6%B2%BB/20260929-%E7%89%B9%E6%9C%97%E6%99%AE%E6%8E%A8%E5%87%BAai%E6%94%BF%E5%BA%9C%E6%9C%8D%E5%8A%A1%E7%BD%91%E7%AB%99-%E7%A7%B0%E7%BE%8E%E5%9B%BD%E9%A2%86%E5%85%88%E4%B8%AD%E5%9B%BD-%E4%B8%8D%E6%84%BF%E5%85%B1%E5%90%8C%E5%8F%91%E5%B1%95ai%E6%8A%80%E6%9C%AF |
| 2 | 从台海到日本，习近平试图“撬动”特朗普的亚太立场 - 纽约时报中文网 | cn.nytimes.com | 66 | 2026-09-28T01:32:52 | 2026年9月28日. 中国领导人习近平和特朗普总统周四在白宫举行的欢迎仪式上。他从事新闻工作已超过20年。 翻译：纽约时报中文网. | https://cn.nytimes.com/china/20260928/summit-xi-trump-taiwan-japan/ |
| 3 | 受贿2.63亿余元，彭晓春一审被判死缓 | www.guancha.cn | 72 | 2026-09-29T09:34:19 | 据央视新闻消息，2026年9月29日，广东省佛山市中级人民法院一审公开宣判广西壮族自治区政协原党组成员、副主席彭晓春受贿一案，对被告人彭晓春以. | https://www.guancha.cn/ZhengZhi/2026_09_29_902678.shtml |
| 4 | 2026年9月学期新生迎新 – 仁川国际机场 | www.jbsc.ac.kr | 0 | - |  | https://www.jbsc.ac.kr/portal/liuxue_chn/bbs/view.do?menuId=M0195000500000000&boardSeq=81432 |
| 5 | 【2026年9月の開運日カレンダー】一粒万倍日・吉日一覧｜開運待ち受け（スマホ壁紙）を変えるタイミング✨ | www.hana-pla.com | 100 | - | 2026年9月の開運日カレンダーと、開運待ち受け（スマホ壁紙）を取り入れるタイミングをまとめました。 一粒万倍日や寅の日、巳の日、辰の日、新月、満月、大安など、2026年9月の縁起が良いとされる日・吉 | https://www.hana-pla.com/wallpaper/luckyday-calendar202609/ |

## 2. [新闻] 最近一周 AI 行业动态

引擎：searxng；失败引擎：-
卫生度：覆盖 0.28（最低 0.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 特朗普推出AI... - RFI - 法国国际广播电台 | www.rfi.fr | 99 | 2026-09-29T19:15:09 | 就在特朗普宣布America.gov上线前几天，他与习近平在华盛顿会面后，美中同意建立“超级智能”（Super Intelligence）对话机制，讨论AI风险与效益，并建立处理AI事故的双边沟通. | https://www.rfi.fr/cn/%E6%94%BF%E6%B2%BB/20260929-%E7%89%B9%E6%9C%97%E6%99%AE%E6%8E%A8%E5%87%BAai%E6%94%BF%E5%BA%9C%E6%9C%8D%E5%8A%A1%E7%BD%91%E7%AB%99-%E7%A7%B0%E7%BE%8E%E5%9B%BD%E9%A2%86%E5%85%88%E4%B8%AD%E5%9B%BD-%E4%B8%8D%E6%84%BF%E5%85%B1%E5%90%8C%E5%8F%91%E5%B1%95ai%E6%8A%80%E6%9C%AF |
| 2 | 行业动态 - 惠利玛 | ai.valimart.net | 71 | - | 摘要：惠利玛 VALIMART 推出 Vali 服装 AI设计平台，实现从AI辅助服装打版与放码、工装风服装设计到多平台一键适配的全自动闭环。 | https://ai.valimart.net/news/industry/ |
| 3 | 名侦探柯南：30号杀人事件免费观看-在线观看蓝光无修 - Omofun动漫 | www.omofuna.com | 27 | - | 最近观看 清空. 暂无观看记录. avatar 登录. | https://www.omofuna.com/anime/d86c9dcbf741288720446bce.html |
| 4 | 资讯合集 - 前沿观澜 官方站 | www.uijae.com | 178 | - | AI监管企业实践测评：从「被动合规」到「主动治理」的真实体验 ; 作为一家中型金融科技公司的合规负责人，我每天最头疼的不是业务增长，而是如何应对层出不穷的AI监管要求。直到我们部署了「智盾AI治理平台… | https://www.uijae.com/%E7%81%AB%E9%94%85%E9%94%85%E5%85%B7%E4%BB%80%E4%B9%88%E6%9D%90%E8%B4%A8%E5%A5%BD/ |
| 5 | regex - Adding ?nocache=1 to every url (including the assets like... | stackoverflow.com | 215 | - | Jul 12, 2016 · Alright, this is due to the pain that godaddy gives me by implementing their own cach… | https://stackoverflow.com/questions/38333569/adding-nocache-1-to-every-url-including-the-assets-like-stylesheet-behind-the |

## 3. [新闻] latest news semiconductor export controls

引擎：searxng；失败引擎：-
卫生度：覆盖 0.64（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | China may allow tech giants to buy new... \| Digital Watch Observatory | dig.watch | 279 | 2026-09-28T21:45:47 | The MIIT’s willingness to encourage the purchase of RTX Pro 5500 chips and the easing of restriction… | https://dig.watch/updates/china-may-allow-new-nvidia-chips |
| 2 | China lashes out at latest U.S. export controls on chips | www.asahi.com | 200 | - | BEIJING--China on Saturday criticized the latest U.S. decision to tighten export controls that would… | https://www.asahi.com/ajw/articles/14738636 |
| 3 | Trump's AI chip export controls could go either way for Korea - Korea JoongAng Daily ,Korean news in Engl.... | www.koreajoongangdaily.com | 90 | - | 2025.05.14.Published May 14, 2025 - 6:36 p.m. Modified May 14, 2025 - 8:06 p.m.2025.05.14. | https://www.koreajoongangdaily.com/business/trumps-ai-chip-export-controls-could-go-either-way-for-korea/12444537 |
| 4 | China Lashes Out at Latest US Export Controls on Chips - VOA | www.voanews.com | 215 | - | 2022.10.08.FILE - Employees wearing protective equipment work at a semiconductor production facility… | https://www.voanews.com/a/china-lashes-out-at-latest-us-export-controls-on-chips/6781565.html |
| 5 | China Vows to Resolutely Defend its Interests following US Further... | en.tmtpost.com | 269 | - | China firmly opposes the United States' latest control measures on semiconductor export, a spokesper… | https://en.tmtpost.com/post/7364060 |

## 4. [新闻] 台风 最新消息 路径

引擎：searxng；失败引擎：-
卫生度：覆盖 0.76（最低 0.47） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026年台风红霞最新消息（附实时路径查询入口）- 泉州本地宝 | m.qz.bendibao.com | 74 | - | 2026年台风红霞最新消息（附实时路径查询入口）.2026年台风红霞最新消息（附实时路径查询入口）. 台风“红霞”最新实时路径查询入口：中央气象台. | https://m.qz.bendibao.com/news/38203.shtm |
| 2 | 刚刚！ 台风“丹娜丝”路径有变！ 或在福建浙江登陆 | c.m.163.com | 60 | - | 注意！ 90度拐弯. 台风“丹娜丝”路径有变化. 或在闽浙沿海登陆. 台风最新消息. 中央气象台消息. 7月5日13时. | https://c.m.163.com/news/a/K3NE3U0Q0550IMZX.html?spss=sps_sem |
| 3 | 2026广州台风最新消息_广州台风实时路径\|登陆时间地点-广州本地宝 | gz.bendibao.com | 120 | - | 登陆时间＋地点 ; 预计，“红霞”将以每小时20-25公里的速度向西偏北方向移动，强度逐渐加强，将于今天夜间至26日早晨在香港到广东陆丰一带沿海登陆（35-42米/秒，12-14级，台风级或强台风级）… | http://gz.bendibao.com/news/zhuantitaifeng/ |
| 4 | 台风路径预报 | m.nmc.cn | 54 | - | 台风快讯与报文. 台风路径预报. 台风公报. 台风预警.台风综合信息. 台风海洋. 台风路径预报. 麦德姆. | https://m.nmc.cn/publish/typhoon/probability-img3.html |
| 5 | 台风“红霞”即将生成 最新路径预判 | sdxw.iqilu.com | 57 | - | 石流等次生灾害。 台风“红霞”即将生成. 或于本周登陆粤闽沿海. 中央气象台7月23日10时继续发布热带低压预报： | https://sdxw.iqilu.com/w/article/YS0yMS0xNzMxNTMyNg.html |

## 5. [新闻] 美国 关税 最新政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.76（最低 0.60） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 特朗普为何突然出台重大关税豁免？ “特别适用于中国产品” | www.jfdaily.com | 68 | - | 最新豁免的出台，终结了美国出台“对等关税”后的“狂野一周”，也被视为美国政府关税政策的“180度大转弯”，再次凸显其贸易政策的混乱本质。 | https://www.jfdaily.com/wx/detail.do?id=892234 |
| 2 | 外媒：关税或将致美国日用品全面涨价-运城晚报 | www.edurew.com | 161 | - | 针对美国最新公布的关税政策，英国广播公司、美联社等报道称，美新关税政策将推高美国民众几乎所有日用品的价格，尤其是服装、食品等，损害美国消费者和企业的利益。 报道称，美国服装与鞋类协会近日表示，根据最新… | https://www.edurew.com/html/03c79099206.html |
| 3 | 三年来首次下滑！关税政策正让美国经济经历“超出预期的糟糕” - 韩国最大的.... | chinese.joins.com | 212 | - | 2025.05.02.美国商务部4月30日公布最新数据显示，2025年第一季度，按年率计算，美国国内生产总值(GDP)环比萎缩0.3%，为2022年以来的首次收缩。这一最新数据的糟糕程度超出市场预期，… | https://chinese.joins.com/news/articleView.html?idxno=119620 |
| 4 | 被重锤的东南亚，不敢“报复” - 华尔街见闻 | wallstreetcn.com | 94 | - | 特朗普的关税政策对依赖东南亚供应链的美国企业造成了重大打击。 根据《纽约时报》的报道，美国商业人士如Patrick Soong已经在考虑将生产从泰国和越南转移到关税较低的菲律宾（17%）。 | https://wallstreetcn.com/articles/3744646 |
| 5 | 青瓦台密切关注美国全球关税政策最新动向 | www.newspim.com | 172 | 2026-07-22 | 2026.07.22.纽斯频通讯社首尔7月22日电 韩国总统府青瓦台22日表示，随着美国对全球实施的10%关税措施期限临近，韩国政府正密切关注相关政策动向，并将通过政府间磋商机制与美方保持沟通。青瓦台… | https://www.newspim.com/news/view/20260722000265 |

## 6. [技术] Python 3.13 新特性

引擎：searxng；失败引擎：-
卫生度：覆盖 0.53（最低 0.38） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | zywscq - V2EX | www.v2ex.com | 90 | - | 求推荐油管频道，适合吃饭时候作为电子榨菜的国内后端就业现在什么行情？ Java 还是最佳技能吗？Python 的类型提示越来越复杂了： Python3.13 又引入了类型注解新特性 | https://www.v2ex.com/member/zywscq |
| 2 | Python pandas 中loc函数的意思及用法，及跟iloc的区别-CSDN博客 | blog.csdn.net | 79 | - | Ubuntu python matplotlib 3篇. VMware虚拟机skills 1篇.C++面向对象三大特性 5篇. Python正则表达式 1篇. | https://blog.csdn.net/u014712482/article/details/85080864 |
| 3 | python@3.13 | formulae.brew.sh | 47 | - | Formula JSON API: /api/formula/python@3.13.json | https://formulae.brew.sh/formula/python@3.13 |
| 4 | Python 3.13 Debuts With New Interactive Interpreter & Experimental JIT | www.phoronix.com | 153 | - | Following a last minute delay due to a performance regression, Python 3.13 stable is out today as th… | https://www.phoronix.com/news/Python-3.13-Released |
| 5 | WSL2のUbuntuでPython 3.13をソースからビルドし、venv... | zenn.dev | 73 | - | インストール後、実行ファイルは /usr/local/bin/python3.13 (および対応する pip3.13 など) として配置されます。 | https://zenn.dev/exmedia/articles/python-venv-on-wsl2 |

## 7. [技术] MCP protocol specification 2026

引擎：searxng；失败引擎：-
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
卫生度：覆盖 0.65（最低 0.55） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Django 与 FastAPI 架构对比：学习路径指南Django 与 FastAPI... | juejin.cn | 59 | - | Django 提供模板系统及全栈功能，而 FastAPI 主打异步性能与类型安全。 本文将详解如何对两者进行评估选择。 | https://juejin.cn/post/7565799761123786806 |
| 2 | FastAPI 与 Django：2026 年最佳 Python 框架 | www.lastingdynamics.com | 79 | - | FastAPI vs Django for Startups（MVP）.FastAPI 与 Django 的主要区别. 性能比较. 异步功能. 开发人员体验. | https://www.lastingdynamics.com/zh/blog/fastapi-vs-django/ |
| 3 | 2026年Django vs Flask vs FastAPI ： 该选哪个 \| [ Mecanik Dev ] | mecanik.dev | 62 | - | 本指南深入对比Django、Flask和FastAPI，涵盖性能、生态系统、学习曲线，以及根据实际构建内容应该选择哪个框架。 | https://mecanik.dev/zh-cn/posts/python-web-framework-comparison-2026-django-vs-flask-vs-fastapi/ |
| 4 | Django框架：优缺点、实用场景及与Flask、FastAPI... | cloud.tencent.com | 56 | - | 在本文中，我们将探讨Django的get和post请求、优缺点、实用场景以及与Flask、FastAPI的对比。 | https://cloud.tencent.com/developer/article/2294156 |
| 5 | WEB框架对比——Django、Flask、FastAPI - ''竹先森゜ - 博客园 | www.cnblogs.com | 102 | - | 软件包丰富程度——Django 具有使代码可重用的大多数软件包，是一个完整的 Web 开发框架，而 Flask 和 FastAPI 是用于构建网站的简约框架，很多功能比如用户系统，后台管. 理要自己实… | https://www.cnblogs.com/zhuminghui/p/14741536.html |

## 9. [技术] how does HTTP/3 QUIC work

引擎：searxng；失败引擎：-
卫生度：覆盖 0.93（最低 0.83） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HTTP/3 Maintains a Consistent Connection ID | www.pubnub.com | 151 | - | How does HTTP/3 maintain a constant Connection ID? How does switching from 5G to Wi-Fi affect HTTP/3… | https://www.pubnub.com/blog/http3-and-quic-the-connection-id/ |
| 2 | [Illustration] How does HTTP/3 (HTTP over QUIC) work?... \| SEの道標 | milestone-of-se.nesuke.com | 174 | - | Change from HTTP/2 to HTTP/3. HTTP/3 has been decided to operate on a new protocol called QUIC. QUIC… | https://milestone-of-se.nesuke.com/en/l7protocol/http/http3-over-quic/ |
| 3 | The Future of the Internet is here: QUIC Protocol and HTTP/3 \| Medium | medium.com | 266 | - | How does QUIC work? Unlike TCP, which uses a connection-oriented approach, QUIC uses a multiplexed s… | https://medium.com/@luisrodri/the-future-of-the-internet-is-here-quic-protocol-and-http-3-d7061adf424f |
| 4 | What Are QUIC and HTTP/3? \| F5 | www.f5.com | 266 | - | HTTP/3, based on QUIC, is the third major version of the Hypertext Transfer Protocol (HTTP) and was … | https://www.f5.com/glossary/quic-http3 |
| 5 | How QUIC works \| HTTP/3 explained | http3-explained.haxx.se | 224 | - | HTTP/3 explained. README. English. Why QUIC. Process. Protocol features.Without explaining the exact… | https://http3-explained.haxx.se/en/quic |

## 10. [技术] Rust async runtime tokio 原理

引擎：searxng；失败引擎：-
卫生度：覆盖 0.74（最低 0.57） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Tokio 运行时 - 深度解析 | atcfu.com | 107 | - | Tokio 运行时. 深度解析 Rust 异步运行时核心原理. 正确 async fn good() { tokio::time::sleep(. Duration::from_secs(1) ).a… | https://atcfu.com/ai-articles/tokio-runtime/ |
| 2 | Rust Async + Tokio 入門：非同步 Rust vs Python asyncio · 每日拍拍 | dailypypy.org | 106 | - | Rust：tokio::sync::mpsc. 八、底層原理：Python vs Rust 的非同步模型.features = ["full"] 會啟用所有功能（runtime、net、time、sy… | https://dailypypy.org/learn/rust-async-tokio/ |
| 3 | 理解tokio的核心(1): runtime - Rust入门秘籍 | rust-book.junmajinlong.com | 94 | - | 创建tokio Runtime. async main.阻塞当前线程，等待异步任务的完成 thread::sleep(std::time::Duration::from_secs(10)) | https://rust-book.junmajinlong.com/ch100/01_understand_tokio_runtime.html |
| 4 | Why Tokio Isn’t Just an Async Runtime — It’s an Entire Concurrency Framework \| by Aayush Tiwari | medium.com | 215 | - | 2025.09.24.Why Tokio Isn’t Just an Async Runtime — It’s an Entire Concurrency Framework A Surprising… | https://medium.com/@aayush71727/why-tokio-isnt-just-an-async-runtime-it-s-an-entire-concurrency-framework-c4e8b505a627 |
| 5 | Topics \| Tokio - An asynchronous Rust runtime | tokio.rs | 140 | - | Tokio is a runtime for writing reliable asynchronous applications with Rust. It provides async I/O, … | https://tokio.rs/tokio/topics?search=Rust+async+runtime+tokio+%E5%8E%9F%E7%90%86+site%3Atokio.rs&safe=0 |

## 11. [政策] 2026年 新能源汽车 补贴政策

引擎：searxng；失败引擎：-
卫生度：覆盖 0.93（最低 0.85） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 新能源汽车补贴退坡，是“精准扶持”还是“福利缩水”？ 1000+... | post.smzdm.com | 139 | - | 4. 2026年初新能源汽车补贴新政解读. 知乎. 5. 重磅！ 新能源汽车补贴政策调整，市场格局或变. 微信公众号. 6. 2026年新能源车补贴政策曝光！ 微信公众号.16. 新能源汽车补贴政策延… | https://post.smzdm.com/p/a82e37rn/ |
| 2 | 国补出炉！ 电车油车补贴揭晓-有驾 | youjia-pc.bdstatic.com | 95 | - | 好消息是，2026年的购车补贴政策终于出来了，不管是电车还是油车，补贴额度是多少？新能源汽车补贴政策. 咱们再来看看置换补贴这块儿。 新能源汽车的最高补贴是1.5万元，也就是购车价格的8%。 | https://youjia-pc.bdstatic.com/article/9608259256117415955.html |
| 3 | 别光顾着过年，快来买车 625亿元“国补”已经发放 - OFweek新能源汽车网 | nev.ofweek.com | 75 | - | 从2025年末开始，国内汽车消费市场便进入了政策切换的过渡期——原有的新能源汽车购置税免征政策、汽车以旧换新补贴政策逐步收尾，而2026年新的政策尚. | https://nev.ofweek.com/2026-02/ART-71000-8420-30681174.html |
| 4 | 多地加码购车补贴 重庆首次将“电驴”纳入购新政策范围 _ 东方财富网 - 财经.... | finance.eastmoney.com | 138 | - | 2026.08.03.多地为促进汽车消费正在陆续推出购车消费补贴。8月1日，西安市发布汽车消费补贴政策，个人消费者购买纳入《减免车辆购置税的新能源汽车车型目录》的新能源乘用车，按照购车发票价格的2%给… | https://finance.eastmoney.com/a/202608033829764288.html |
| 5 | 2026年4月汽车国补置换2万元申请全攻略：手把手教你领到国家补贴 | www.zhihu.com | 72 | - | 2026年，国家继续实施汽车以旧换新补贴政策，也就是大家常说的“国补”。补贴金额： · 买新能源车 → 按新车销售价格的12%补贴，最高2万元. | https://www.zhihu.com/tardis/jm/art/2033119484798616793 |

## 12. [政策] 数据出境安全评估办法 最新

引擎：searxng；失败引擎：-
卫生度：覆盖 0.82（最低 0.70） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 数据出境安全评估办法-搜了智采 | www.51gpg.com | 76 | - | 数据出境安全评估办法.第三条 数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 | https://www.51gpg.com/notice/detail_76.html |
| 2 | 数据出境安全评估办法.docx - 墨天轮文档 | www.modb.pro | 70 | - | 规范数据出境活动，保护个人信息权益，维护国家安全和社会公共利益，促进数据跨境安全、自由流动，制定的管理办法。数据出境安全评估办法.docx. | https://www.modb.pro/doc/70005 |
| 3 | 数据出境安全评估办法-聚名集团-举报平台 | aq.juming.cn | 65 | - | 第三条 数据出境安全评估坚持事前评估和持续监督相结合、风险自评估与安全评估相结合，防范数据出境安全风险，保障数据依法有序自由流动。 | http://aq.juming.cn/show/524.html |
| 4 | 合规及跨境数据传输联合白皮书2024 | www.pwccn.com | 80 | - | 国家网信办受理后将统一开展数据 出境安全评估工作开展实质审查并出具结论完成数 据出境安全评估。在通过安全评估后企业仍需要对数据出境进行持续的 评估监管。 04. | https://www.pwccn.com/zh/issues/cybersecurity-and-data-privacy/joint-white-paper-on-compliance-cross-border-data-transfers-may2024.pdf |
| 5 | 中国网络安全审查“组合拳”学者:全面管制时代来临 - 美国之音中文网 您可靠.... | www.voachinese.com | 195 | - | 2022.07.22.中国国家互联网信息办公室(网信办)针对网络审查再祭出一系列新规，除自8月1日起要求境内各网络平台严格核实使用者的身分外，也发布《数据出境安全评估办法》，严格管控数据跨国流通，更对… | https://www.voachinese.com/a/china-launches-security-review-on-cnki-the-country-s-leading-academic-research-database-0722222/6666367.html |

## 13. [政策] EU AI Act compliance requirements

引擎：searxng；失败引擎：-
卫生度：覆盖 1.00（最低 1.00） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EU AI Act Compliance \| Microsoft Trust Center | www.microsoft.com | 162 | - | Microsoft has incorporated “prohibited practices” into our internal, company-wide Restricted Use Pol… | https://www.microsoft.com/en-au/trust-center/compliance/eu-ai-act |
| 2 | EU AI Act Compliance: What You Need to Know | www.sai360.com | 156 | - | SAI360 helps organizations take a practical, structured approach to meeting the requirements of the … | https://www.sai360.com/regulations/eu-ai-act |
| 3 | EU AI Act Compliance Guide \| Sinaptic.AI | sinaptic.ai | 162 | - | For providers and deployers of GPAI (including chatbots like ChatGPT), there are strict transparency… | https://sinaptic.ai/articles/eu-ai-act-compliance |
| 4 | How different stakeholders are thinking about EU AI Act compliance \| IAPP | iapp.org | 160 | - | ITIC argues in its EU AI policy priorities that member states and the Commission need to coordinate … | https://iapp.org/news/a/how-different-stakeholders-are-thinking-about-eu-ai-act-compliance |
| 5 | We Thought Our AI Product Was Ready for Europe... - D2i Technology | d2itechnology.com | 257 | - | European AI Act Compliance refers to meeting the requirements of the EU’s risk-based AI regulation. … | https://d2itechnology.com/blogs/we-thought-our-ai-product-was-ready-for-europe-until-we-learned-about-the-european-ai-act/ |

## 14. [政策] 个人所得税 专项附加扣除 标准

引擎：searxng；失败引擎：-
卫生度：覆盖 0.99（最低 0.96） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 月底截止，事关收入！ 抓紧确认 | m.gmw.cn | 91 | - | 个税专项附加扣除信息确认. 开始啦！ 纳税人可通过个人所得税App.3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。 | https://m.gmw.cn/2025-12/02/content_1304246592.htm |
| 2 | 国务院关于提高个人所得税有关专项附加扣除标准的通知_税务_中国政府网 | www.gov.cn | 79 | - | 为进一步减轻家庭生育养育和赡养老人的支出负担，依据《中华人民共和国个人所得税法》有关规定，国务院决定，提高3岁以下婴幼儿照护等三项个人所得税专项附加扣除标准。 | https://www.gov.cn/zhengce/content/202308/content_6901206.htm |
| 3 | 提高个人所得税3岁以下婴幼儿照护、子女教育、赡养老人专项附加扣除标准的.... | www.xjkel.gov.cn | 214 | - | 2023.09.13.问：提高个人所得税3岁以下婴幼儿照护、子女教育、赡养老人专项附加扣除标准的具体规定是什么？ 答：根据国务院发布的《关于提高个人所得税有关专项附加扣除标准的通知》（国发〔2023〕… | https://www.xjkel.gov.cn/xjkrls/c117543/202309/fc10821a7adf4eb7adceb9646df21b87.shtml |
| 4 | 事关你的钱袋子，今起确认！ \| 每日经济新闻 | m.nbd.com.cn | 97 | - | 各个项目. 分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000元。税务部门提醒. 个人所得税专项附加扣除信息. | https://m.nbd.com.cn/articles/2025-12-01/4162702.html |
| 5 | 月底截止，事关收入！ 抓紧确认_腾讯新闻 | news.qq.com | 102 | - | 本月底，2025年度个人所得税专项附加扣除信息确认将截止。各个项目分别按照什么标准扣除？ 3岁以下婴幼儿照护、子女教育专项附加扣除标准为每个子女每月2000元。 赡养老人专项附加扣除标准为每月3000… | https://news.qq.com/rain/a/20241229A04S4300 |

## 15. [政策] children privacy law COPPA update

引擎：searxng；失败引擎：-
卫生度：覆盖 0.84（最低 0.80） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Cheat Sheet: Children’s privacy law update adds pressure against Facebook’s Instagram for kids plan | digiday.com | 221 | - | Below is an overview of the bill updating the Children’s Online Privacy Protection Act (COPPA) and w… | https://digiday.com/media/cheat-sheet-childrens-privacy-law-update-adds-pressure-against-facebooks-instagram-for-kids-plan/ |
| 2 | Senator Says Federal Law Protecting Children Online Needs Updating | www.wsj.com | 222 | - | 2021.10.01.Sen. Maria Cantwell (D., Wash.)—who chairs the powerful Commerce Committee—said the big p… | https://www.wsj.com/livecoverage/facebook-hearing-live-updates/card/TwUpnUNNG7lhv25M7F8I |
| 3 | Children and Teens' Online Privacy Protection Act (COPPA 2.0) | www.termsfeed.com | 196 | - | It is an update to the Children’s Online Privacy Protection Act (COPPA). COPPA 2.0 takes a stricter … | https://www.termsfeed.com/blog/coppa-2-children-teens-online-privacy-protection-act/ |
| 4 | Privacy Policy - The Wheeler School - N-12 Coed Day School in Providence RI | www.wheelerschool.org | 158 | - | COPPA Statement The Children’s Online Privacy Protection Act (COPPA) is a federal law governing the … | https://www.wheelerschool.org/privacy-policy/ |
| 5 | COPPA Updates: What Parents Should Know in 2026 - The Policy Circle | www.thepolicycircle.org | 205 | - | On April 22, 2026, updates to the Children’s Online Privacy Protection Act (COPPA) officially went i… | https://www.thepolicycircle.org/coppa-updates-2026-parents-guide/ |

## 16. [商品] iPhone 17 Pro 价格 参数

引擎：searxng；失败引擎：-
卫生度：覆盖 0.52（最低 0.30） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | iPhone8手机参数 - 京东 | www.jd.com | 131 | - | 京东是国内专业的iPhone8手机参数网上购物商城，本频道提供iPhone8手机参数商品图片，iPhone8手机参数价格，iPhone8手机参数多少钱信息，为您选购提供全方位iPhone8手机参数怎么… | https://www.jd.com/hprm/998728323d21c0c6f006.html |
| 2 | 【苹果iPhone 17 256GB】报价_参数_图片_论坛_Apple iPhone 17,苹果 17,iPhone17苹果手机报.... | detail.zol.com.cn | 181 | - | 中关村在线为您提供苹果iPhone 17 256GB 手机最新报价，同时包括苹果iPhone 17 256GB图片、苹果iPhone 17 256GB参数、苹果iPhone 17 256GB评测行情、… | https://detail.zol.com.cn/cell_phone/index2139583.shtml |
| 3 | 苹果8x参数 - 京东 | www.jd.com | 259 | - | Apple【95新】苹果17/16/15/14/13/12/11/X系列pro max mini plus e二手手机A16详见质检报告 苹果 iPhone 8荣耀亲选LCHSE X5s蓝牙耳机无线入… | https://www.jd.com/hprm/9987d46c01cd9b8ab46f.html |
| 4 | iPhone 17 Pro and 17 Pro Max online in Saudi Arabia | redsea.com | 101 | - | Explore iPhone, the world’s most powerful personal device. Check out iPhone 17 Pro, iPhone 17 Pro Ma… | https://redsea.com/en/iphone-17-pro |
| 5 | Apple unveils iPhone 17 Pro and iPhone 17 Pro Max - Apple | www.apple.com | 265 | - | “iPhone 17 Pro is by far the most powerful iPhone we’ve ever made, with a stunning new design rebuil… | https://www.apple.com/newsroom/2025/09/apple-unveils-iphone-17-pro-and-iphone-17-pro-max/ |

## 17. [商品] best noise cancelling headphones 2026 review

引擎：searxng；失败引擎：-
卫生度：覆盖 0.93（最低 0.83） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Best Noise Cancelling Headphones 2026 Review \| TikTok | www.tiktok.com | 234 | - | Best headphones in 2026 #techtok #apple #airpodspro2 AirPods Pro 2 review 2026: best noise-cancellin… | https://www.tiktok.com/discover/best-noise-cancelling-headphones-2026-review |
| 2 | Best noise-cancelling headphones 2026 – tested by our in-house review experts \| | www.whathifi.com | 257 | - | Best noise-cancelling headphones 2026 – 6 sensational pairs picked by our expert reviewers.All of th… | https://www.whathifi.com/best-buys/headphones/best-noise-cancelling-headphones |
| 3 | Best cheap noise-cancelling headphones 2026: expert-tested recommendations \| Wha | www.whathifi.com | 154 | - | All review verdicts are agreed upon by the team rather than an individual reviewer to eliminate any … | https://www.whathifi.com/best-buys/best-cheap-noise-cancelling-headphones |
| 4 | The 5 Best Noise Cancelling Headphones of 2026 - RTINGS.com | www.rtings.com | 153 | - | 2026.06.26.The Sony WH-1000XM6 are the best noise cancelling headphones we've tested. These premium … | https://www.rtings.com/headphones/reviews/best/by-feature/noise-cancelling |
| 5 | 8 Best Noise Cancelling Headphones (August 2026) Honest Reviews | www.theclassicalshop.net | 233 | - | Detailed Reviews of the Best Noise Cancelling Headphones 2026.Choosing the best noise cancelling hea… | https://www.theclassicalshop.net/best-noise-cancelling-headphones-2026/ |

## 18. [商品] 扫地机器人 推荐 性价比

引擎：searxng；失败引擎：-
卫生度：覆盖 0.83（最低 0.63） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 【26... | www.bilibili.com | 102 | - | 【2026年1月扫地机器人推荐】不同品牌的扫地机器人到底该怎么选？ 哪个价位选哪款？ 一期视频帮你解决选购问题！【26年扫地机器人推荐-性价比篇】值得买的型号就只有这些，扫地机器人选购攻略！ 10:3… | https://www.bilibili.com/video/BV1btfZBxEYB/ |
| 2 | 石头P20 Max vs... \| 新浪网 | k.sina.com.cn | 95 | - | 石头P20 Max vs 同价位扫地机，谁才是性价比之王？ 3个维度硬核对比+FAQ.关键字 : 石头P20 Max 扫地机器人推荐 高性价比扫地机 同价位扫地机对比 2026年扫地机选购. | https://k.sina.com.cn/article_7879923199_1d5ae15ff06801jub0.html |
| 3 | 智能拖地机器人推荐【TOP10】机器人拖把 \| 美国好物推荐 | yycams.com | 160 | - | 拖地机器人推荐【TOP10】机器人拖把.6. 性价比最高的2合一拖地机器人 ILIFE V8s 2-in-1 Mopping Robot Vacuum8. 最智能的拖地机器人 Roborock S6 … | https://yycams.com/best-robot-mops/ |
| 4 | 想给父母买个扫地机器人，求推荐 - V2EX | www.v2ex.com | 50 | - | 想给父母买个扫地机器人，求推荐.@GT7 #2 现在的扫地机器人谁还不带拖地功能啊？ ethsol. | https://www.v2ex.com/t/1008824 |
| 5 | 内蒙古扫地机推荐：性价比高、应用广泛-内蒙古永佳商贸有限责任公司 | www.nmgqj.cn | 87 | - | 当提到内蒙古扫地机，我们往往会想到性价比高、功能广泛的产品。 这些扫地机通过..技术和设计，为用户带来了极大的便利。 无论是家庭清洁还是商业场所的维护，这些扫地机都能够胜任。 | http://www.nmgqj.cn/789/2324482.html |

## 19. [商品] RTX 5090 benchmark 价格

引擎：searxng；失败引擎：-
卫生度：覆盖 0.50（最低 0.50） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 0 · 独立站点 4

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB Benchmark and Specs - GPU comparison | www.gpu-monkey.com | 152 | - | Benchmark results and tests of the GIGABYTE AORUS GeForce RTX 5090 XTREME WATERFORCE WB in 3DMark an… | https://www.gpu-monkey.com/en/gpu-gigabyte_aorus_geforce_rtx_5090_xtreme_waterforce_wb |
| 2 | NVIDIA GeForce RTX 5090 Review: Pushing Boundaries with AI Acceleration - Storag | www.storagereview.com | 161 | - | The Procyon AI Text Generation Benchmark Benchmark simplifies AI LLM performance testing by offering… | https://www.storagereview.com/review/nvidia-geforce-rtx-5090-review-pushing-boundaries-with-ai-acceleration |
| 3 | A thorough insight into technical specs and benchmarks of RTX 5090. | technical.city | 107 | - | Synthetic benchmark performance of GeForce RTX 5090. The combined score is measured on a 0-100 point… | https://technical.city/en/gpu/GeForce-RTX-5090 |
| 4 | ASUS Details GeForce RTX 5090 and 5080 Pricing | www.techporn.ph | 160 | - | ASUS has officially launched the highly anticipated GeForce RTX 5090 and 5080 graphics cards in the … | https://www.techporn.ph/asus-details-geforce-rtx-5090-and-5080-pricing/ |
| 5 | GeForce RTX 5090 D [in 1 benchmark] | technical.city | 158 | - | This section provides details about the physical dimensions of GeForce RTX 5090 D and its compatibil… | https://technical.city/en/video/GeForce-RTX-5090-D |

## 20. [商品] 国产显卡 摩尔线程 最新型号

引擎：searxng；失败引擎：-
卫生度：覆盖 0.68（最低 0.61） · 同站冗余 0 · 聚合页 0 · 脚本不匹配 0 · 空内容 1 · 独立站点 5

| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 国产显卡品牌摩尔线程发新卡 单卡48GB显存_凤凰网 | i.ifeng.com | 74 | - | 国产显卡品牌摩尔线程，终于又要发新显卡了。这张显卡的具体型号为MTT S4000，规格方面非常不错。 国产显卡品牌摩尔线程发新卡 单卡48GB显存. | https://i.ifeng.com/c/8VfiImHtDxn |
| 2 | MTTS70显卡多少钱_摩尔线程MTTS70国产显卡售价及参数-硬件之家 | www.yingjianzhijia.com | 74 | - | 摩尔线程MTTS70国产显卡售价及参数. 发售价格：2499元. 品牌：摩尔线程. 型号：MTTS70. 显卡核心：春晓. 核心频率：1.6GHz. | https://www.yingjianzhijia.com/zhishi/76390.html |
| 3 | 摩尔线程显卡能玩什么游戏-抖音 | www.douyin.com | 62 | - | 摩尔线程7月驱动更新！ DX12游戏性能提升，可以玩明末渊虚之 #摩尔线程 #明末渊虚之羽 #驱动更新 #国产显卡 #显卡. | https://www.douyin.com/shipin/7587973921086736399 |
| 4 | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害--快科技--科技.... | news.mydrivers.com | 36 | - | 疑摩尔线程S90首曝！2年前的国产显卡 玩游戏竟然比RTX4060还厉害 | https://news.mydrivers.com/1/1064/1064120.htm |
| 5 | 2499元现货！摩尔线程MTT S70国产游戏显卡开卖 | diy.zol.com.cn | 115 | - | 摩尔线程MTT S70国产游戏显卡开卖.这款显卡是S80显卡的精简版，继续推动国产显卡普及，基于7nm工艺春晓GPU核心，配备3584个MUSA核心，频率1.6GHz，浮点性能11.2TFLOPS，G… | https://diy.zol.com.cn/819/8195169.html |

## 卫生度汇总（M5-5.3，客观指标）

| 指标 | 值 | 含义 |
| --- | --- | --- |
| 结果总数 | 100 | 20 条查询的 top-N 合计 |
| 查询词覆盖率（加权） | 0.735 | 越高说明结果越贴题 |
| 同站冗余 | 0 | 同一可注册域超出上限的条数 |
| 聚合页 | 0 | 站点首页/栏目页这类「只是导航」的结果 |
| 非中英文脚本 | 0 | 中文查询下混入的俄语/韩语等标题 |
| 空内容 | 3 | 摘要不足 40 字、对 LLM 无价值 |
| 平均独立站点数 | 4.8 | 来源分散度 |


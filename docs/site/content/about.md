# 关于与已知限制

本站由 `scripts/build_docs_site.py` 从仓库文档生成（单一来源，避免文档漂移），
生成物是自包含的 `docs/site/index.html`：无 CDN、无外部脚本、无后端。

## 内容来源

| 页面 | 来源 |
| --- | --- |
| 客户端接入指南 | `docs/03-客户端接入指南.md` |
| 客户端配置包 | `docs/reports/20260930-p4-3-9-client-config-pack.md` |
| 自部署与运维 | `docs/05-服务器部署手册.md` |
| 报告索引（证据与政策） | `docs/reports/README.md` |

## 已知限制（如实告知）

* **中文新闻时效**：免费中文新鲜源不可得（评估见报告索引），中文 news 场景可能返回
  `degraded=true` + `degraded_reason="freshness_unverified"` —— 这是如实降级，不是故障；
* **主题相关性**：极少数查询（如上游池内没有切题候选）会返回 `degraded_reason="no_relevant_results"`
  （已知上游限制，不硬凑结果）；
* **Tavily 兼容差异**：`answer` 恒 `null`、图片字段恒空、`score` 量纲不同、`usage.credits` 恒 0 —— 属有意保留，
  详见「客户端接入指南」的 Tavily 兼容章节；
* **限流与闸门**：429 分两类（RPM 限流 / 上游闸门过载），`Retry-After` 形态不同，排查见「客户端配置包」故障对照表。

## 版本快照（2026-10-03）

* 线上应用镜像：`258749c7a318`；8 条需求 **7 达标 / 1 有明确限制 / 0 未做**；
* 2-9 相关性按登记口径线上 3 轮 **19/19/19**（中位 19、最低 19）；
* 自检 `scripts/mcp_selfcheck.py` **24/24**；
* 详细证据与遗留清单见 `docs/reports/m6-project-acceptance-20260930.md` 与报告索引。

## 站点自检

```bash
# 生成（幂等；提交前先跑）
.venv/bin/python scripts/build_docs_site.py
# 校验生成物是否为最新（CI/测试用，落后则 exit 1）
.venv/bin/python scripts/build_docs_site.py --check
```

# M6 Tavily 兼容性逐字段核对与补齐（2026-09-28）

- 分支：`feature/m6-tavily-compat`（基于 `main` @ `726d0b7`）
- 对照依据（**留档、可复核，不凭记忆**）：
  - [`tavily-official-search-20260928.md`](tavily-official-search-20260928.md)：官方 `/search` 的请求/响应/错误
    字段清单（从官方 OpenAPI schema 逐字提取）＋官方 Python SDK 的错误解析代码（2026-09-28 抓取）；
  - [`tavily-search-response-example-20260928.json`](tavily-search-response-example-20260928.json)：官方示例响应（测试 fixture）。
- 官方来源：<https://docs.tavily.com/documentation/api-reference/endpoint/search>、<https://docs.tavily.com/documentation/api-reference/endpoint/extract>、`tavily-python`（GitHub）。

## 0. 结论摘要

- **可直接补齐的（本轮已补）**：`results[].favicon`、`results[].images[]`、`results[].id`、
  顶层 `auto_parameters`、顶层 `usage`（`include_usage=true` 时）、`/extract` 的 `results[].images`、
  REST 错误体补 `error`；`response_time` / `request_id` / `answer` / `images` / `include_usage` 本就有。
- **语义不同（写清，不硬凑）**：`answer`（不自带 LLM，恒 null）、图片相关（不做图片搜索，恒空）、
  `score`（本地融合分，量纲与 Tavily 不同）、`usage.credits`（免费，恒 0）、
  未实现的 Tavily 请求参数（接受但忽略）。
- **会导致客户端报错的**：核对后**没有**「必崩」项 —— 官方 SDK 不校验成功响应、错误体有 try/except 兜底；
  唯一有风险的是「按字段遍历」时缺 `results[].images/favicon/id` 与顶层 `usage/auto_parameters`，
  已按「可直接补齐」处理。

## 1. 请求字段对照

| 字段 | 我方 `/v1/search` | Tavily | 差异 | 影响 |
| --- | --- | --- | --- | --- |
| `query` | ✅ 必填 | ✅ 必填 | 无 | — |
| `search_depth` | ✅ `basic`/`advanced`/`deep` | ✅ 含 `fast`/`ultra-fast` 等 | **取值集不同**（我们没有 fast/ultra-fast；`deep` 是我们特有的深度抓取） | 传非我方取值 → 422；Tavily 客户端默认 `basic`，实际风险低（见 §4） |
| `max_results` | ✅ 1-20 | ✅ 上限更高 | 上限不同 | 传 >20 → 422 |
| `topic` | ✅ `general`/`news` | ✅ 同 | 无 | — |
| `time_range` | ✅ `day`/`week`/`month`/`year` | ✅ 同 | 无 | — |
| `days` | ✅ 保留（内部换算 `time_range`） | ⛔ 当前文档无（改用 `start_date`/`end_date`） | 我方多支持（超集） | 无 |
| `include_answer` | ✅（`answer` 恒 `null`） | ✅ 生成 LLM 答案 | **语义不同** | 客户端拿到 `null` 而非答案，已在文档写明 |
| `include_raw_content` | ✅ | ✅ | 无 | — |
| `include_images` | ✅（顶层 `images` 恒空、`results[].images` 恒空） | ✅ 返回图片 | **语义不同**（不做图片搜索） | 不崩，拿到空数组 |
| `include_usage` | ✅ 本轮新增 | ✅ | **语义不同**（本服务免费，`credits` 恒 0） | 超集 |
| `include_domains` / `exclude_domains` | ✅ | ✅ | 无 | — |
| Key 传法 | ✅ `body.api_key` / `Authorization: Bearer` / `X-API-Key` | ✅ `Authorization: Bearer`（+ 旧式 body） | 我方多支持两种（超集） | 无 |
| `chunks_per_source`、`start_date`、`end_date`、`include_published_date`、`filter_by_published_date`、`include_image_descriptions`、`include_favicon`、`include_domains_mode`、`country`、`language`、`filter_by_language`、`auto_parameters`、`exact_match`、`safe_search` | ⚠️ **接受但忽略**（`extra="ignore"`） | ✅ 生效 | **未实现** | **不会报错**（不会被 422 拒绝），但也没有效果；`language` 我们固定 `all`（中英兼顾）——需在客户端预期里写明 |

> 请求侧的关键兼容点：**未知字段一律忽略**，所以直接替换 `base_url` 的 Tavily 客户端不会因为多传参数而失败。

## 2. 响应字段对照

| 字段 | 我方 | Tavily | 差异 | 影响 |
| --- | --- | --- | --- | --- |
| `query` | ✅ | ✅ | 无 | — |
| `answer` | ⚠️ 恒 `null`（`include_answer=false` 时按 Tavily 习惯**不返回该键**） | ✅ 生成答案 | **语义不同** | 需要答案的客户端拿不到内容 |
| `images`（顶层） | ⚠️ 恒 `[]`（`include_images=false` 时不返回该键） | ✅ 图片列表 | **语义不同** | 不崩 |
| `results[].title` / `.url` / `.content` | ✅ | ✅ | 无 | — |
| `results[].score` | ✅ | ✅ | **量纲不同**（我们是本地融合分） | 只适合相对排序，不可与 Tavily 分数横向比较 |
| `results[].raw_content` | ✅（`include_raw_content=false` 时为 `null`） | ✅（同条件出现） | 无 | — |
| `results[].published_date` | ✅（可能为 `null`；支持 URL/页面回补） | ✅ | 覆盖度不同 | 我们尽力回补，仍可能缺 |
| `results[].favicon` | ✅ **本轮补齐**（恒 `null`） | ✅ | **语义不同**（不采集 favicon） | 不崩 |
| `results[].images[]` | ✅ **本轮补齐**（恒 `[]`） | ✅ `{url, description}` | **语义不同**（不做图片搜索） | 不崩 |
| `results[].id` | ✅ **本轮补齐**（`<request_id>-<序号>`） | ✅ 不透明短 id | 格式不同、用途相同 | 可用于去重/引用 |
| `response_time` | ✅ number | ✅ schema 是 **number**（官方“示例响应”里误写成字符串 `"1.67"`） | 无（我们与 schema 一致） | — |
| `auto_parameters` | ✅ **本轮补齐**（回显实际生效的 `topic`/`search_depth`） | ✅（官方说明「仅 `auto_parameters=true` 时出现」） | **超集**（我们恒给） | 不崩 |
| `usage` | ✅ **本轮补齐**（仅 `include_usage=true` 时 `{"credits": 0}`） | ✅ 计费信息 | **语义不同**（免费服务） | 不崩 |
| `request_id` | ✅ | ✅ | 无 | — |
| 我方额外字段 | `engine`、`cached`、`depth`、`pages_read`、`engines_used`、`failed_engines`、`degraded`、`degraded_reason`、`follow_up_questions` | ⛔ | 超集 | 客户端忽略即可；**不改动**它们 |

### 2.1 `/extract` 对照

| 字段 | 我方 | Tavily | 差异 |
| --- | --- | --- | --- |
| 请求 `urls` / `format` | ✅（另支持 `max_chars`） | ✅（另有 `query`/`chunks_per_source`/`extract_depth`/`include_images`/`include_favicon`/`timeout`/`include_usage`，我们忽略） | 未实现项忽略、不报错 |
| `results[].url` / `.raw_content` | ✅ | ✅ | 无 |
| `results[].images` | ✅ **本轮补齐**（恒 `[]`） | ✅ | 语义不同（不做图片提取） |
| `results[].title` / `.chars` | ✅ 额外 | ⛔ | 超集 |
| `failed_results[].url` / `.error` | ✅ 完全一致 | ✅ | 无 |
| `response_time` / `request_id` | ✅ | ✅ | 无 |

## 3. 错误码与限流语义对照

| 场景 | 我方 | Tavily | 差异与影响 |
| --- | --- | --- | --- |
| 鉴权失败 | **401** `{"detail": "<str>", "error": "<str>"}` | **401** `{"detail": {"error": "<str>"}}` | 形状不同（我们**不改** `detail` 的字符串类型）：官方 SDK 的 `body.get("detail", {}).get("error")` 会走到它自己的 `try/except` 兜底 → **不崩**，但消息为空串；我们额外给的顶层 `error` 让消息可读（测试断言了这一点） |
| 限流 | **429** + **`Retry-After`** | **429**（文档未列 `Retry-After`） | 我们多给 `Retry-After`（超集） |
| 请求体校验失败 | **422** `{"detail": [ ... ]}`（FastAPI 默认） | **422** `{"detail": [ ... ]}`（官方示例同形） | 一致 |
| 参数语义非法（如非法 topic） | **422**（Pydantic 校验） | **400** | 状态码不同：官方 SDK 对 422 走 `raise_for_status()` → `requests.HTTPError`，而不是 `BadRequestError`；**均为异常、不会静默成功**，已在 §4 记为已知差异 |
| 套餐/额度 | 不产生 | **432/433/403** | 语义不同（本服务免费，无套餐） |
| 服务端错误 | **500** `{"detail": "Internal Server Error"}` | **500** `{"detail": {"error": "Internal Server Error"}}` | 同 401 的形状差异 |
| 超时 | 上游 `search_timeout_limit+3`（默认 5.5s）×1 次重试；闸门排队上限 4.0s | SDK 侧 `timeout` 参数 | Tavily 的 `timeout` 请求参数我们忽略；客户端应使用自己的 HTTP 超时 |

## 4. 本轮补齐项（只加不改）

| 文件 | 变更 |
| --- | --- |
| `src/utf8_search/models.py` | `ResultImage`；`SearchResult` 增 `favicon`/`images`/`id`；`SearchResponse` 增 `auto_parameters`/`usage`；`SearchRequest` 增 `include_usage`；`ExtractItem` 增 `images` |
| `src/utf8_search/core/pipeline.py` | 结果级 `id = <request_id>-<序号>`；`auto_parameters` 回显实际生效参数；`include_usage=true` 时给 `usage={"credits": 0}`（缓存复用路径同样重新盖章，避免 id 与 request_id 不一致） |
| `src/utf8_search/server/http_api.py` | 请求体增 `include_usage`；新增 `HTTPException` 处理器：错误体保留 `detail`（原样、字符串）并**追加**顶层 `error`；`/mcp` 中间件的错误体同样补齐 |
| `src/utf8_search/server/mcp_server.py` | `web_search` 增 `include_usage`，与 REST 同一套字段 |

**没有改动**任何既有字段的名称、类型或语义（`detail` 仍是字符串、`score`/`answer`/`images` 等语义不变，
只做新增字段与新增顶层 `error`）。

## 5. 回归测试

`tests/test_tavily_compat.py`（8 条，全部离线）：

1. **官方示例响应能被我们的模型直接解析**（`SearchResponse.model_validate(官方示例)`，含字符串 `response_time` 的兼容）；
2. **我们的 REST 响应覆盖官方示例里的每个字段路径**（含 `results[].images[].url` 这种嵌套路径；
   空数组按「字段存在」判定，因为我们不做图片搜索）；
3. **MCP 工具输出与 REST 同一套字段**；
4. **官方 SDK 的错误解析写法能解析我们的 401/429**（不抛、分类正确、`Retry-After` 存在、顶层 `error` 可读）；
5. 422 校验错误的 `detail` 是列表（与 Tavily 官方示例同形）；
6. **真实 pipeline 会给结果盖章** `id=<request_id>-<序号>` 并回显 `auto_parameters`/`usage`；
7. `/extract` 的 `results[].images` 与 `failed_results[].{url,error}` 与官方一致。

离线全量：`pytest -q -m "not net"` → **264 passed, 4 deselected**。

## 6. 有意保留的差异（与理由）

1. **`answer` 恒 null**：本服务不自带 LLM（需求第 8 条只要求 Tavily 兼容替换，不含答案生成）。
2. **图片相关字段恒空**：不做图片搜索/图片提取；补字段是为了「按字段遍历的客户端不 KeyError」。
3. **`score` 量纲不同**：本地融合分（引擎权重 + 时效 + 去重），不是 Tavily 的排序分。
4. **`usage.credits` 恒 0**：免费服务不计费；给字段是为了客户端计费代码不必分支。
5. **未实现的 Tavily 请求参数「接受但忽略」而不是报错**：直接替换 `base_url` 的客户端不应因为多传参数而失败；
   需要严格过滤的客户端请自行传 `time_range`/`include_domains` 等我们已实现的参数。
6. **`detail` 保持字符串**（不改成 Tavily 的 `detail.error` 对象）：这是既有字段语义，改了会打断老客户端；
   官方 SDK 对此有兜底、不会崩，且我们补了顶层 `error`。
7. **非法参数的 422 vs Tavily 的 400**：保持 FastAPI 默认校验语义（422 + 列表型 `detail`，与 Tavily 的 422 同形）。

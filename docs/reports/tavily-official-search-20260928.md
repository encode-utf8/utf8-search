# Tavily 官方 `/search` 字段清单（留档，2026-09-28 抓取）

> **来源**：<https://docs.tavily.com/documentation/api-reference/endpoint/search>（官方 Mintlify 文档，
> 2026-09-28 抓取）。本文件从该页面的 OpenAPI schema 与示例代码块**逐字提取**，不凭记忆；
> 示例响应原样存为 [`tavily-search-response-example-20260928.json`](tavily-search-response-example-20260928.json)
> （该文档内容本身不含密钥，无需脱敏）。

## 1. 请求字段（POST /search body）

| 字段 | 类型 | 官方说明（摘） |
| --- | --- | --- |
| `query` | string | **必填**；查询词 |
| `search_depth` | string | 延迟/相关性的取舍，也决定 `results[].content` 的生成方式（basic/advanced/…） |
| `chunks_per_source` | integer | 从每个来源抽取的内容片段数（每段最多 500 字符） |
| `max_results` | integer | 返回结果条数上限 |
| `topic` | string | 搜索类目；`news` 适合实时更新 |
| `time_range` | string | 相对当前日期的回溯窗口，按发布/更新时间过滤 |
| `start_date` | string | 只返回该日期之后的结果 |
| `end_date` | string | 只返回该日期之前的结果 |
| `include_published_date` | boolean | 每条结果附带 `published_date` |
| `filter_by_published_date` | boolean | 剔除发布日期落在窗口外的结果 |
| `include_images` | boolean | 顶层 `images`（查询相关图片）+ 每条结果的 `images` |
| `include_image_descriptions` | boolean | 图片附带描述文本（需 `include_images=true`） |
| `include_favicon` | boolean | 每条结果附带 favicon URL |
| `include_domains` | array | 只保留这些域名（最多 300 个） |
| `exclude_domains` | array | 排除这些域名（最多 150 个） |
| `include_domains_mode` | string | `include_domains` 的施加方式（restrict 等） |
| `country` | string | 偏向特定国家的内容 |
| `language` | string | 偏向特定语言（ISO 639-1） |
| `filter_by_language` | boolean | 严格过滤语言而不只是加权 |
| `auto_parameters` | boolean | 由 Tavily 自动推断参数（会多花 credit） |
| `exact_match` | boolean | 只返回包含精确引号短语的结果 |
| `include_usage` | boolean | 响应里附带 credit 用量信息 |
| `safe_search` | boolean | 过滤成人/不安全内容（fast/ultra-fast 不支持） |

## 2. 响应字段

| 字段 | 类型 | 官方说明（摘） |
| --- | --- | --- |
| `query` | string | 实际执行的查询 |
| `answer` | string | LLM 生成的简短回答；**仅当 `include_answer=true` 时出现** |
| `images` | array | 查询相关图片；`include_image_descriptions=true` 时每项含 `{url, description}` |
| `results[].title` | string | 结果标题 |
| `results[].url` | string | 结果 URL |
| `results[].content` | string | 结果短描述 |
| `results[].score` | number | 相关性分数 |
| `results[].raw_content` | string | 清洗后的正文；**仅当 `include_raw_content=true` 时给出** |
| `results[].published_date` | string | Tavily 估计的发布/更新时间 |
| `results[].favicon` | string | 结果站点 favicon |
| `results[].images[].url` / `.description` | array / string | 该结果内嵌图片（`include_images=true` 时） |
| `results[].id` | string | 结果唯一标识 |
| `response_time` | **number** | 请求耗时（秒）——注意文档“示例响应”里写成字符串 `"1.67"`，但 **schema 类型是 number** |
| `auto_parameters` | object | 自动推断出的参数；官方说明「仅 `auto_parameters=true` 时出现」 |
| `usage` | object | credit 用量（`include_usage` 相关） |
| `request_id` | string | 请求唯一 id，可提供给客服排查 |

## 3. 错误响应（官方示例代码块）

| HTTP | 官方示例体 | 说明 |
| --- | --- | --- |
| 400 | `{"detail": {"error": "<400 Bad Request, (e.g Invalid topic...)>"}}` | 参数非法（如 topic 不在 general/news） |
| 401 | `{"detail": {"error": "Unauthorized: missing or invalid API key."}}` | 缺少/无效 Key |
| 422 | `{"detail": [{"type": "string_type", "loc": ["body","query"], "msg": "...", "input": []}]}` | 请求体校验失败（FastAPI 风格列表） |
| 429 | `{"detail": {"error": "Your request has been blocked due to excessive requests..."}}` | 频率超限 |
| 432 / 433 | `{"detail": {"error": "<432 Custom Forbidden Error ...>"}}` | 套餐/额度上限（官方 Python SDK 把 403/432/433 一起映射为 `ForbiddenError`） |
| 500 | `{"detail": {"error": "Internal Server Error"}}` | 服务端错误 |

## 4. 官方 Python SDK 的关键行为（`tavily-python`，2026-09-28 抓取 `tavily/tavily.py`）

```python
def _handle_error_response(self, response) -> None:
    body = None
    try:
        body = response.json()
    except Exception:
        body = None
    ...
    detail = ""
    if isinstance(body, dict):
        try:
            detail = body.get("detail", {}).get("error", None) or ""
        except Exception:
            detail = ""          # ← detail 不是 dict 时静默兜底，不抛

    if response.status_code == 429:      raise UsageLimitExceededError(detail)
    elif response.status_code in [403, 432, 433]: raise ForbiddenError(detail)
    elif response.status_code == 401:    raise InvalidAPIKeyError(detail)
    elif response.status_code == 400:    raise BadRequestError(detail)
    else:                                raise response.raise_for_status()
```

要点：

1. **成功响应不做 schema 校验**（`return response.json()`），所以多字段/少字段都不会让它崩；
2. 错误体只从 `detail.error` 取消息，且**取不到时静默兜底为空串**；
3. 未被列举的状态码（例如 422）走 `raise_for_status()` → `requests.HTTPError`；
4. `search()` 的 `timeout` 超时会抛 SDK 自己的 `TimeoutError`。

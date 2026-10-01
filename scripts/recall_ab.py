"""P7 证据：drop_stale=True（P5）会不会伤召回？

对同一批 20 条 2-9 查询，跑两次流水线：
  * before = 把 `apply_recency` 包一层强制 `drop_stale=False`（模拟 P5 之前的行为）；
  * after  = 当前代码（命中时间意图时 drop_stale=True）。
记录每条查询**返回的结果条数**与是否命中时间意图，输出对照表 + JSON。

只读、不写产品数据（禁用缓存），不改任何配置。

用法（脚本自带 40 次上游请求，单并发；改代码/参数做 A/B 时的"受控回放"工具）：

    .venv/bin/python scripts/recall_ab.py

说明：脚本会 import `scripts/relevance.py` 的 20 条固定查询（`QUERIES`），
所以必须在仓库根目录下运行；明细 JSON 写到 `data/recall-ab.json`（`data/` 被 gitignore，
报告引用的是脚本 stdout 里的对照表）。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from relevance import QUERIES  # noqa: E402
from utf8_search.config import Settings  # noqa: E402
from utf8_search.core import pipeline as pipeline_mod  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.rank.recency import has_recency_intent  # noqa: E402

OUT = REPO / "data" / "recall-ab.json"


async def run_all(*, force_no_drop_stale: bool) -> list[int]:
    original = pipeline_mod.apply_recency
    if force_no_drop_stale:
        def patched(results, **kwargs):  # noqa: ANN001, ANN003
            kwargs["drop_stale"] = False
            return original(results, **kwargs)

        pipeline_mod.apply_recency = patched  # type: ignore[assignment]
    settings = Settings().model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    counts: list[int] = []
    try:
        for _category, query in QUERIES:
            response = await pipeline.search(
                SearchRequest(query=query, max_results=5, depth="basic")
            )
            counts.append(len(response.results))
    finally:
        await pipeline.close()
        pipeline_mod.apply_recency = original  # type: ignore[assignment]
    return counts


async def main() -> int:
    before = await run_all(force_no_drop_stale=True)
    after = await run_all(force_no_drop_stale=False)
    rows = []
    for index, (_category, query) in enumerate(QUERIES):
        rows.append({
            "id": index + 1,
            "query": query,
            "recency_intent": has_recency_intent(query),
            "count_before": before[index],
            "count_after": after[index],
            "delta": after[index] - before[index],
        })
    print(f"{'#':>3} {'意图':<5}{'before':>7}{'after':>7}{'delta':>7}  查询")
    for row in rows:
        print(f"{row['id']:>3} {'是' if row['recency_intent'] else '否':<5}"
              f"{row['count_before']:>7}{row['count_after']:>7}{row['delta']:>+7}  {row['query'][:40]}")
    intent_rows = [r for r in rows if r["recency_intent"]]
    decreased = [r for r in rows if r["delta"] < 0]
    print(f"\n命中时间意图的查询 {len(intent_rows)} 条；条数下降的查询 {len(decreased)} 条"
          f"（{[(r['id'], r['delta']) for r in decreased] or '无'}）")
    print(f"合计返回条数：before {sum(before)} → after {sum(after)}（{sum(after) - sum(before):+d}）")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("明细:", OUT)
    return 0


raise SystemExit(asyncio.run(main()))

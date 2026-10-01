"""规则 A/B 的召回对照（固定候选集）：同一批 20 条查询、同一份候选池，比对两种规则口径下的
**返回条数**与 **top5 是否逐位一致**（与 scripts/replay_pool.py 同一套"固定候选"思路）。

用法：

    .venv/bin/python scripts/rule_recall_ab.py --out data/measure/t7/rule-ab.json

当前用途（T7 第 0 步 ②）：`has_item_like_content` 收紧「聚合页实质内容豁免」（T6 规则①）的召回对照 ——
before = 旧 `is_aggregator_page`（有实质内容即豁免），after = 新（有实质内容 **且** 像条目才豁免）；
两侧都把「内容农场」规则关掉，以隔离规则①的影响。只读、不改任何配置。
"""

from __future__ import annotations

import argparse
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
from utf8_search.rank import diversity as div  # noqa: E402


def _old_is_aggregator_page(result):  # noqa: ANN001 - SearchResult
    """T6 之前的判据：形态像栏目页 **且** 没有实质内容 → 聚合页（不做条目感检查）。"""
    return div.looks_like_column(result) and not div.has_substantive_content(result)


async def main() -> int:
    parser = argparse.ArgumentParser(description="固定候选集的规则 A/B 召回对照")
    parser.add_argument("--out", default="", help="JSON 输出路径")
    args = parser.parse_args()

    settings = Settings().model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    captured: dict[int, list] = {}
    current = {"id": 0}
    original_apply = pipeline_mod.apply_rank_filters

    def wrapper(results, **kwargs):  # noqa: ANN001, ANN003
        captured[current["id"]] = list(results)
        return original_apply(results, **kwargs)

    pipeline_mod.apply_rank_filters = wrapper  # type: ignore[assignment]
    rows: list[dict] = []
    original_agg = div.is_aggregator_page
    original_farm = div.is_content_farm
    try:
        for index, (category, query) in enumerate(QUERIES, 1):
            current["id"] = index
            await pipeline.search(SearchRequest(query=query, max_results=5, depth="basic"))
    finally:
        await pipeline.close()
        pipeline_mod.apply_rank_filters = original_apply  # type: ignore[assignment]

    def run_arm(pool, query, *, before: bool):  # noqa: ANN001
        div.is_aggregator_page = _old_is_aggregator_page if before else original_agg  # type: ignore[assignment]
        div.is_content_farm = lambda *_a, **_k: False  # type: ignore[assignment]
        try:
            kept, _stats = div.apply_rank_filters(
                list(pool),
                query=query,
                max_results=5,
                max_per_host=settings.rank_max_per_host,
                min_query_coverage=settings.rank_min_query_coverage,
                drop_aggregator_pages=settings.rank_drop_aggregator_pages,
                drop_script_mismatch=settings.rank_drop_script_mismatch,
            )
            kept = div.apply_form_penalty(kept)[:5]
        finally:
            div.is_aggregator_page = original_agg  # type: ignore[assignment]
            div.is_content_farm = original_farm  # type: ignore[assignment]
        return kept

    print(f"{'#':>3} {'before':>7}{'after':>7}{'delta':>7}  top5一致  查询")
    for index, (category, query) in enumerate(QUERIES, 1):
        pool = captured.get(index, [])
        before = run_arm(pool, query, before=True)
        after = run_arm(pool, query, before=False)
        same = [r.url for r in before] == [r.url for r in after]
        rows.append({
            "id": index,
            "category": category,
            "query": query,
            "pool_size": len(pool),
            "before_count": len(before),
            "after_count": len(after),
            "delta": len(after) - len(before),
            "top5_identical": same,
            "before_titles": [r.title for r in before],
            "after_titles": [r.title for r in after],
        })
        print(f"{index:>3} {len(before):>7}{len(after):>7}{len(after) - len(before):>+7}  {'是' if same else '否 ⚠️'}      {query[:34]}")
    changed = [row["id"] for row in rows if not row["top5_identical"] or row["delta"] != 0]
    print(f"\n返回条数变化 / top5 变化的查询：{changed or '无'}")
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("明细:", path)
    return 0


raise SystemExit(asyncio.run(main()))

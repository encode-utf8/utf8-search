"""按「受控回放」固定候选集，逐条诊断指定查询的坏结果与原因。

用法（单并发、禁缓存；与 `scripts/recall_ab.py` 同一套受控回放思路）：

    .venv/bin/python scripts/diag_candidates.py 6 16 --out data/diag-q6-q16.json

对每个查询打印**候选池**（rank 过滤前的全部候选）里每一条的信号：
形态（首页/栏目/聚合页）、正文实质度、规格 token 匹配级别与 missing、
混杂型号页、查询词覆盖率，以及它是否进入最终 top5（进第几名）。
只读、不改任何配置。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
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
from utf8_search.rank import spec_tokens as spec_mod  # noqa: E402
from utf8_search.rank.diversity import (  # noqa: E402
    has_substantive_content,
    is_aggregator_page,
    looks_like_column,
    query_coverage,
)


def modifier_exact_check(query: str, *, title: str, content: str, url: str) -> dict:
    """诊断用：修饰词在结果里是否有「未被其它修饰词延长」的精确出现（与产品同口径：只看标题+URL）。"""
    tokens = [t for t in spec_mod.extract_spec_tokens(query) if spec_mod._MODIFIER_RE.fullmatch(t)]
    haystack = " ".join(part for part in (title, url) if part).lower()
    out: dict[str, dict] = {}
    for token in tokens:
        occurrences = [m.start() for m in re.finditer(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack)]
        exact = False
        extended_by: list[str] = []
        for pos in occurrences:
            following = haystack[pos + len(token) : pos + len(token) + 16]
            nxt = spec_mod._MODIFIER_FOLLOW_RE.match(following)
            if nxt and spec_mod._MODIFIER_RE.fullmatch(nxt.group(1)):
                extended_by.append(nxt.group(1))
            else:
                exact = True
        out[token] = {"occurrences": len(occurrences), "exact_standalone": exact, "extended_by": sorted(set(extended_by))}
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description="受控回放：指定查询的候选集逐条诊断")
    parser.add_argument("ids", nargs="+", type=int, help="QUERIES 的 1-based 编号")
    parser.add_argument("--out", default="", help="JSON 输出路径")
    args = parser.parse_args()

    captured: dict[str, list] = {}
    original = pipeline_mod.apply_rank_filters

    def wrapper(results, **kwargs):  # noqa: ANN001, ANN003
        captured["pool"] = list(results)
        kept, stats = original(results, **kwargs)
        captured["kept"] = list(kept)
        captured["stats"] = dict(stats)
        return kept, stats

    pipeline_mod.apply_rank_filters = wrapper  # type: ignore[assignment]
    settings = Settings().model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    report: dict[str, object] = {"queries": []}
    try:
        for qid in args.ids:
            category, query = QUERIES[qid - 1]
            response = await pipeline.search(SearchRequest(query=query, max_results=5, depth="basic"))
            pool = captured.get("pool", [])
            final_urls = [r.url for r in response.results]
            tokens = spec_mod.extract_spec_tokens(query)
            rows = []
            for candidate in pool:
                match = spec_mod.match_spec_tokens(
                    tokens,
                    title=candidate.title or "",
                    content=(candidate.content or "")[:500],
                    url=candidate.url or "",
                )
                rows.append({
                    "title": (candidate.title or "")[:90],
                    "url": candidate.url,
                    "content_len": len(candidate.content or ""),
                    "substantive": has_substantive_content(candidate),
                    "looks_like_column": looks_like_column(candidate),
                    "aggregator_page": is_aggregator_page(candidate),
                    "spec_level": match.level,
                    "spec_missing": list(match.missing),
                    "mixed_model_page": spec_mod.is_mixed_model_page(candidate.title, candidate.content),
                    "coverage": round(query_coverage(query, candidate), 3),
                    "modifier_check": modifier_exact_check(
                        query, title=candidate.title or "", content=candidate.content or "", url=candidate.url or ""
                    ),
                    "final_rank": (final_urls.index(candidate.url) + 1) if candidate.url in final_urls else None,
                })
            report["queries"].append({
                "id": qid,
                "category": category,
                "query": query,
                "spec_tokens": tokens,
                "pool_size": len(pool),
                "final_top5": [{"rank": i + 1, "title": (r.title or "")[:90], "url": r.url} for i, r in enumerate(response.results)],
                "rank_stats": captured.get("stats", {}),
                "candidates": rows,
            })
            print(f"== {qid}. [{category}] {query}  pool={len(pool)}  final={len(response.results)}")
            for row in rows:
                flag = f"top{row['final_rank']}" if row["final_rank"] else "-----"
                print(
                    f"  {flag} spec={row['spec_level']:<7} cov={row['coverage']:<5} "
                    f"subst={int(row['substantive'])} col={int(row['looks_like_column'])} agg={int(row['aggregator_page'])} "
                    f"mixed={int(row['mixed_model_page'])} mod={row['modifier_check']} {row['title'][:50]} | {row['url'][:70]}"
                )
    finally:
        await pipeline.close()
        pipeline_mod.apply_rank_filters = original  # type: ignore[assignment]

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("明细:", path)
    return 0


raise SystemExit(asyncio.run(main()))

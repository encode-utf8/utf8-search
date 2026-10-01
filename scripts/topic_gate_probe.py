"""主题相关性闸门探针：跑登记口径的 20 条查询，同时产出「明细速览」与「降级/池内切题候选」统计。

用法（单并发、禁缓存；与 `scripts/relevance.py` 同一套采集口径）：

    .venv/bin/python scripts/topic_gate_probe.py --out data/measure/t10/run1.md

输出：
* `--out` 指定的 Markdown（与 relevance.py 的 `-brief.md` 同格式，可直接用于判分）；
* 同名 `-gate.json`：逐条 `degraded_reason` / 池内切题候选数（`on_topic_candidates`）/
  `no_relevant_results` 标志 / top5 标题。
只读，不改配置。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from relevance import QUERIES  # noqa: E402
from utf8_search.config import Settings  # noqa: E402
from utf8_search.core import pipeline as pipeline_mod  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.rank.diversity import count_on_topic_candidates  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="主题相关性闸门探针（20 条登记查询）")
    parser.add_argument("--out", required=True, help="Markdown 明细输出路径")
    args = parser.parse_args()

    captured: dict[str, list] = {}
    current = {"query": ""}
    original = pipeline_mod.apply_rank_filters

    def wrapper(results, **kwargs):  # noqa: ANN001, ANN003
        captured[current["query"]] = list(results)
        return original(results, **kwargs)

    pipeline_mod.apply_rank_filters = wrapper  # type: ignore[assignment]
    settings = Settings().model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    rows: list[dict] = []
    try:
        for index, (category, query) in enumerate(QUERIES, 1):
            current["query"] = query
            response = await pipeline.search(SearchRequest(query=query, max_results=5, depth="basic"))
            pool = captured.get(query, [])
            rows.append({
                "id": index,
                "category": category,
                "query": query,
                "degraded": response.degraded,
                "degraded_reason": response.degraded_reason,
                "pool_size": len(pool),
                "on_topic_candidates": count_on_topic_candidates(query, pool),
                "no_relevant_results": bool(
                    response.degraded_reason and "no_relevant_results" in response.degraded_reason.split(",")
                ),
                "results": [
                    {"title": item.title or "", "url": item.url or "", "content": (item.content or "")[:120]}
                    for item in response.results
                ],
            })
    finally:
        await pipeline.close()
        pipeline_mod.apply_rank_filters = original  # type: ignore[assignment]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 主题相关性闸门探针（20 条登记查询）",
        "",
        f"- 采集：{datetime.now().astimezone().isoformat(timespec='seconds')}；单并发、禁缓存",
        "- 打分：非零即为相关；门槛 20 条里 ≥18 条满足「相关 ≥4」",
        "",
    ]
    for row in rows:
        lines += [f"## {row['id']}. [{row['category']}] {row['query']}", "",
                  f"- degraded_reason: `{row['degraded_reason']}`；池内切题候选 {row['on_topic_candidates']}/{row['pool_size']}", "",
                  "| 打勾位 | 标题 | 域名 | 摘要 |", "| --- | --- | --- | --- |"]
        for rank, item in enumerate(row["results"][:5], 1):
            url = item["url"]
            domain = url.split("/")[2] if url.startswith("http") else ""
            snippet = (item["content"] or "").replace("\n", " ")[:80]
            lines.append(f"| {rank} | {item['title'][:70]} | {domain} | {snippet} |")
        lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    gate_path = out.with_name(out.stem + "-gate.json")
    gate_path.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    flagged = [row["id"] for row in rows if row["no_relevant_results"]]
    print(f"写入 {out} 与 {gate_path}；no_relevant_results = {flagged or '无'}")
    return 0


raise SystemExit(asyncio.run(main()))

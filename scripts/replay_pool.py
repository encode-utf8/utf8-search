"""固定候选集的 before/after 对拍：把 dump 出来的候选池重新过一遍**当前代码**的排序层。

配合 `scripts/diag_candidates.py --dump-pool`：

    # 1) 抓一次候选池（受控回放，禁缓存）
    .venv/bin/python scripts/diag_candidates.py 2 3 --dump-pool data/measure/t6-pool.json
    # 2) 同一份候选池，分别用「改动前 / 改动后」的代码各跑一遍，逐位对比 top5
    PYTHONPATH=/tmp/t6-before/src .venv/bin/python scripts/replay_pool.py data/measure/t6-pool.json --out /tmp/before.json
    PYTHONPATH=/opt/utf8-search/src  .venv/bin/python scripts/replay_pool.py data/measure/t6-pool.json --out /tmp/after.json
    diff <(python -m json.tool /tmp/before.json) <(python -m json.tool /tmp/after.json) && echo IDENTICAL

只做排序层复算（`apply_rank_filters` + `apply_form_penalty`），不联网、不写产品数据。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 代码版本切换（2026-10-02 T15 修正）：脚本默认用**自己所在仓库**的 `src`，
# 因此"改前/改后对拍"必须显式指定 `REPLAY_SRC=<另一个 worktree>/src`，
# 不能只靠 `PYTHONPATH` —— 早期用它做过对拍，两侧其实都加载了同一份代码（结论无效，已在 T15 报告更正）。
REPO = Path(__file__).resolve().parents[1]
_SRC = Path(os.environ.get("REPLAY_SRC", str(REPO / "src")))
sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(REPO / "scripts"))

from relevance import QUERIES  # noqa: E402
from utf8_search.config import Settings  # noqa: E402
from utf8_search.models import SearchResult  # noqa: E402
from utf8_search.rank.diversity import apply_form_penalty, apply_rank_filters  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="固定候选集的排序层复算（before/after 对拍）")
    parser.add_argument("pool", help="diag_candidates.py --dump-pool 的产物")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--out", default="", help="结果 JSON（不写则打印）")
    args = parser.parse_args()

    pools = json.loads(Path(args.pool).read_text(encoding="utf-8"))
    settings = Settings()
    out: dict[str, list[dict]] = {}
    for qid, dump in pools.items():
        category, query = QUERIES[int(qid) - 1]
        results = [SearchResult.model_validate(item) for item in dump]
        kept, _stats = apply_rank_filters(
            results,
            query=query,
            max_results=args.max_results,
            max_per_host=settings.rank_max_per_host,
            min_query_coverage=settings.rank_min_query_coverage,
            drop_aggregator_pages=settings.rank_drop_aggregator_pages,
            drop_script_mismatch=settings.rank_drop_script_mismatch,
        )
        kept = apply_form_penalty(kept)[: args.max_results]
        out[qid] = [
            {"rank": index + 1, "title": (item.title or "")[:80], "url": item.url}
            for index, item in enumerate(kept)
        ]
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print("written:", args.out)
    else:
        print(text)
    return 0


raise SystemExit(main())

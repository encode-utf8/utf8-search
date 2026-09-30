"""引擎探针：单引擎公平复测 + 引擎集合交错 A/B + 现网默认集合扫描（只读上游，不改任何配置）。

用途（M6 引擎集合优化，见 `docs/reports/m6-engine-selection-20260928.md`）：

1) 逐引擎隔离复测——用**中文本地化查询**判断某引擎是「真的不可用」还是「探针查询不合适」：

       python scripts/engine_probe.py retest http://127.0.0.1:8899 \
           --engines 360search "sogou wechat" "chinaso news" --out data/measure/retest.json

2) 集合交错 A/B——同一个实例内逐条交错跑两套显式引擎列表，抵消上游漂移。
   注意：**引擎名必须在实例的 `keep_only` 里注册**，否则 SearXNG 会静默丢弃
   （见 checklist 第 6 条），所以跨配置对比要用 `sweep` + 重启，而不是 `compare`。

       python scripts/engine_probe.py compare http://127.0.0.1:8899 \
           --a "google,yandex" --b "google,yandex,chinaso news" --rounds 2

3) 现网默认集合扫描——不传 `engines`，测「实例当前 keep_only 集合」的真实表现，
   用于**改动前后**（改 `searxng/settings.yml` + 重启）的交错 A/B：

       python scripts/engine_probe.py sweep http://127.0.0.1:8888 --label A --rounds 1 \
           --out data/measure/swap-A1.json

输出：屏幕上给汇总表，同时把逐条明细写 JSON（便于报告引用与复算）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from searxng_dates import (  # noqa: E402 - 同目录小工具，见 scripts/searxng_dates.py
    DATE_TRUST_INDEX_ONLY,
    DATE_TRUST_NO_DATE,
    DATE_TRUST_TRUSTED,
    DATE_TRUST_UNKNOWN,
    classify_date_trust,
    year_clues,
)


def missing_engines(requested: list[str], registered: list[str]) -> list[str]:
    """返回 `requested` 里**未注册**的引擎（纯函数，便于单测）。

    为什么必须校验：SearXNG 对 `engines=` 里未注册的名字是**静默丢弃**的 ——
    少数名字无效时只跑其余引擎；**全部无效时会回退到默认引擎集合**。
    2026-09-30 就因此造过一条假结论（`engines=sina` 实际跑的是默认集合，
    却把 90/90 带日期的结果记到了 sina 头上），所以探针在发查询前必须先把关。
    """
    known = {name.strip() for name in registered if name and name.strip()}
    return [name for name in requested if name and name not in known]


async def assert_engines_registered(client: httpx.AsyncClient, base: str, engines: list[str]) -> None:
    """校验点名的引擎确实注册在目标实例里；未注册直接报错退出（并打印可用引擎列表）。"""
    response = await client.get(base.rstrip("/") + "/config", timeout=30.0)
    response.raise_for_status()
    registered = sorted(
        item.get("name", "") for item in (response.json().get("engines") or [])
    )
    missing = missing_engines(engines, registered)
    if not missing:
        return
    print(
        "❌ 以下引擎未注册在本实例（SearXNG 会静默丢弃，全部无效时还会回退默认集合，结论会失真）："
        f"{missing}\n   本实例可用引擎（{len(registered)}）：{', '.join(registered)}",
        file=sys.stderr,
    )
    raise SystemExit(2)


# 中文本地化查询：政策 / 地方政策 / 地方新闻 / 产业动态 / 商品评测 ×2
QUERY_SETS: dict[str, list[str]] = {
    "zh": [
        "2026年 新能源汽车 补贴政策",
        "四川省 数字经济 扶持 政策 申报 条件",
        "深圳 地铁 新线路 开通 最新",
        "国产 大模型 产业 动态 2026",
        "扫地机器人 推荐 性价比 2026",
        "折叠屏 手机 参数 对比 2026",
    ],
    "en": [
        "US tariff policy latest",
        "EU AI Act compliance requirements",
        "best noise cancelling headphones 2026",
        "MCP protocol specification 2026",
        "open source LLM benchmark 2026",
        "semiconductor export controls news",
    ],
}


# --------------------------------------------------------------------- 工具


def percentile(values: list[float], q: float) -> float:
    """线性插值分位数（样本少时比最近秩更稳）。"""
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


async def query_once(
    client: httpx.AsyncClient,
    base: str,
    query: str,
    *,
    engines: str | None = None,
    time_range: str | None = None,
    language: str = "all",
) -> dict[str, object]:
    """发一次 `/search`，返回结果数 / 带日期数 / 延迟 / unresponsive。"""
    params: dict[str, object] = {"q": query, "format": "json", "pageno": 1, "language": language}
    if engines:
        params["engines"] = engines
    if time_range:
        params["time_range"] = time_range
    started = time.perf_counter()
    try:
        resp = await client.get(base.rstrip("/") + "/search", params=params, timeout=90.0)
        ms = (time.perf_counter() - started) * 1000
        if resp.status_code != 200:
            return {"query": query, "time_range": time_range or "", "status": resp.status_code,
                    "results": 0, "with_date": 0, "unresponsive": [], "ms": round(ms)}
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — 探针要如实记录任何异常
        return {"query": query, "time_range": time_range or "", "status": None, "results": 0,
                "with_date": 0, "unresponsive": [], "ms": None, "error": str(exc)[:120]}
    results = payload.get("results") or []
    unresponsive = [
        item[0] if isinstance(item, (list, tuple)) and item else str(item)
        for item in (payload.get("unresponsive_engines") or [])
    ]
    return {
        "query": query,
        "time_range": time_range or "",
        "status": 200,
        "results": len(results),
        "with_date": sum(1 for item in results if item.get("publishedDate") or item.get("published_date")),
        "unresponsive": unresponsive,
        "engines_of_results": sorted({e for item in results for e in (item.get("engines") or [])}),
        # 逐条明细（供「日期可信度抽检」比对上报日期与内容年份线索）
        "items": [
            {
                "url": item.get("url") or "",
                "title": item.get("title") or "",
                "date": item.get("publishedDate") or item.get("published_date"),
                "text": " ".join(
                    str(part) for part in (item.get("title"), item.get("content"), item.get("url")) if part
                ),
            }
            for item in results[:20]
        ],
        "ms": round(ms),
    }


def summarize(rows: list[dict[str, object]], engines: list[str], label: str, rounds: int) -> str:
    """把逐条明细压成一行汇总（缺样本不参与延迟统计）。"""
    ms = [r["ms"] for r in rows if r.get("ms") is not None]
    res = [r["results"] for r in rows]
    dated = sum(r["with_date"] for r in rows)
    unresponsive: dict[str, int] = {}
    for row in rows:
        for name in row.get("unresponsive") or []:
            unresponsive[name] = unresponsive.get(name, 0) + 1
    errors = sum(1 for r in rows if r.get("status") != 200)
    head = (
        f"{label:<28} rounds={rounds} n={len(rows):<3} "
        f"结果中位={int(statistics.median(res)):<4} 合计={sum(res):<5} 带日期={dated:<4} "
        f"延迟 P50={int(percentile(ms, 0.5))}ms P90={int(percentile(ms, 0.9))}ms "
        f"P95={int(percentile(ms, 0.95))}ms max={int(max(ms)) if ms else 0}ms 错误={errors}"
    )
    tail = f"  engines={len(engines) if engines else 'default'} unresponsive={unresponsive or '{}'}"
    return head + tail


# --------------------------------------------------------------------- 子命令


async def cmd_retest(args: argparse.Namespace) -> int:
    """逐引擎隔离复测：每引擎跑全部查询 + time_range(day/week) 探测。"""
    queries = QUERY_SETS[args.query_set]
    rows: list[dict[str, object]] = []
    async with httpx.AsyncClient(trust_env=False) as client:
        # 先校验引擎确实注册：否则「点名一个没注册的引擎」会被 SearXNG 静默丢弃/回退默认集合，
        # 把默认集合的结果记到它头上（2026-09-30 踩过这个坑）
        await assert_engines_registered(client, args.base, args.engines)
        for engine in args.engines:
            for query in queries:
                rows.append(await query_once(client, args.base, query, engines=engine))
            for tr in ("day", "week"):
                rows.append(await query_once(client, args.base, queries[0], engines=engine, time_range=tr))
    print(f"# retest {args.base} query_set={args.query_set} engines={len(args.engines)}")
    # 逐引擎汇总（按明细顺序切块：每引擎 查询数 + 2 条 time_range）
    step = len(queries) + 2
    for index, engine in enumerate(args.engines):
        chunk = rows[index * step : (index + 1) * step]
        main = [r for r in chunk if not r["time_range"]]
        tr = {r["time_range"]: r["results"] for r in chunk if r["time_range"]}
        dated = sum(r["with_date"] for r in main)
        ms = [r["ms"] for r in chunk if r.get("ms") is not None]
        unreason = sorted({u for r in chunk for u in (r.get("unresponsive") or [])})
        print(
            f"{engine:<18} 结果={sum(r['results'] for r in main):<4} 带日期={dated:<4} "
            f"time_range(day/week)={tr.get('day', 0)}/{tr.get('week', 0)} "
            f"P50={int(statistics.median(ms)) if ms else -1}ms 原因={unreason or '-'}"
        )
    _write(args.out, {"label": args.label, "base": args.base, "mode": "retest",
                      "query_set": args.query_set, "rows": rows})
    return 0


async def cmd_sweep(args: argparse.Namespace) -> int:
    """扫描实例当前默认引擎集合（不传 engines），用于跨重启的改动前后对照。"""
    queries = QUERY_SETS[args.query_set]
    engines = [e.strip() for e in (args.engines or "").split(",") if e.strip()]
    rows: list[dict[str, object]] = []
    async with httpx.AsyncClient(trust_env=False) as client:
        if engines:
            await assert_engines_registered(client, args.base, engines)
        for _ in range(args.rounds):
            for query in queries:
                row = await query_once(client, args.base, query, engines=args.engines or None)
                row["engines"] = args.engines or ""
                rows.append(row)
    print(summarize(rows, engines, args.label or "sweep", args.rounds))
    printed = sorted({name for r in rows for name in (r.get("unresponsive") or [])})
    if printed:
        print(f"  不可用引擎: {printed}")
    _write(args.out, {"label": args.label, "base": args.base, "mode": "sweep",
                      "query_set": args.query_set, "engines": args.engines or "",
                      "rounds": args.rounds, "rows": rows})
    return 0


async def cmd_compare(args: argparse.Namespace) -> int:
    """同一实例内逐条交错跑 A/B 两套引擎列表（引擎必须都已注册）。"""
    queries = QUERY_SETS[args.query_set]
    configs = [("A", args.a), ("B", args.b)]
    rows: list[dict[str, object]] = []
    async with httpx.AsyncClient(trust_env=False) as client:
        requested = [e.strip() for _label, value in configs for e in value.split(",") if e.strip()]
        await assert_engines_registered(client, args.base, requested)
        for _ in range(args.rounds):
            for query in queries:
                for label, engines in configs:
                    row = await query_once(client, args.base, query, engines=engines)
                    row["config"] = label
                    row["engines"] = engines
                    rows.append(row)
    for label, engines in configs:
        sub = [r for r in rows if r["config"] == label]
        print(summarize(sub, [e.strip() for e in engines.split(",") if e.strip()], label, args.rounds))
    _write(args.out, {"label": args.label, "base": args.base, "mode": "compare",
                      "query_set": args.query_set, "a": args.a, "b": args.b,
                      "rounds": args.rounds, "rows": rows})
    return 0


async def cmd_dates(args: argparse.Namespace) -> int:
    """日期可信度抽检：每引擎抽 ≥N 条，比对「上报日期」与「内容里的年份线索」。

    这是 2026-09-30「假绿」事故的加固项：`yandex` 会把索引日期当发布日期上报
    （2017 年的旧政策被标成当天），只看"7 日内比例"会被骗过去。判定逻辑在
    `scripts/searxng_dates.py`（纯函数，另有单测）。
    """
    queries = QUERY_SETS[args.query_set]
    rows: list[dict[str, object]] = []
    async with httpx.AsyncClient(trust_env=False) as client:
        await assert_engines_registered(client, args.base, args.engines)
        for engine in args.engines:
            items: list[dict[str, object]] = []
            for query in queries:
                if len([i for i in items if i.get("date")]) >= args.min_samples:
                    break
                row = await query_once(client, args.base, query, engines=engine, time_range=args.time_range or None)
                items.extend(row.get("items") or [])
            verdict, stats = classify_date_trust(items)
            rows.append({"engine": engine, "verdict": verdict, **stats.to_dict()})
            flag = "  ⚠️ 索引日期污染" if stats.year_conflict else ""
            print(
                f"{engine:<18} 判定={verdict:<14} 样本={stats.total:<3} 带日期={stats.dated:<3} "
                f"年份冲突={stats.year_conflict}（{stats.conflict_ratio:.0%}）"
                f" 同日最多={stats.same_day_max}{flag}"
            )
            for detail in (stats.detail or []):
                if detail.get("year_conflict"):
                    print(f"    ↳ 污染样例：上报 {detail['reported_date']}，内容年份 {detail['content_years']}"
                          f" {str(detail['title'])[:46]}")
    _write(args.out, {"mode": "dates", "base": args.base, "query_set": args.query_set,
                      "time_range": args.time_range or "", "rows": rows})
    return 0


def _write(path: str, payload: dict[str, object]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  明细已写入 {target}")


# --------------------------------------------------------------------- CLI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SearXNG 引擎探针（只读）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("base", help="SearXNG 地址，如 http://127.0.0.1:8888")
        p.add_argument("--query-set", default="zh", choices=sorted(QUERY_SETS), help="查询集（默认 zh）")
        p.add_argument("--out", default="", help="逐条明细 JSON 输出路径")
        p.add_argument("--label", default="", help="标签，写进 JSON 便于区分轮次")

    retest = sub.add_parser("retest", help="逐引擎隔离复测（含 time_range 探测）")
    common(retest)
    retest.add_argument("--engines", nargs="+", required=True, help="被测引擎名（空格分隔）")
    retest.set_defaults(func=cmd_retest)

    sweep = sub.add_parser("sweep", help="扫描实例当前默认引擎集合（跨重启对照用）")
    common(sweep)
    sweep.add_argument("--rounds", type=int, default=1, help="每个查询跑几轮（默认 1）")
    sweep.add_argument("--engines", default="", help="可选：显式引擎列表（默认不传，用实例默认集合）")
    sweep.set_defaults(func=cmd_sweep)

    compare = sub.add_parser("compare", help="同实例内交错 A/B 两套引擎列表")
    common(compare)
    compare.add_argument("--a", required=True, help="A 组引擎列表（逗号分隔）")
    compare.add_argument("--b", required=True, help="B 组引擎列表（逗号分隔）")
    compare.add_argument("--rounds", type=int, default=2, help="每个查询跑几轮（默认 2）")
    compare.set_defaults(func=cmd_compare)

    dates = sub.add_parser("dates", help="日期可信度抽检（上报日期 vs 内容年份线索）")
    common(dates)
    dates.add_argument("--engines", nargs="+", required=True, help="被测引擎名（空格分隔）")
    dates.add_argument("--min-samples", type=int, default=5, help="每条引擎至少要凑到几条带日期样本")
    dates.add_argument("--time-range", default="", help="可选：传给 SearXNG 的 time_range（day/week/…）")
    dates.set_defaults(func=cmd_dates)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())

"""T17：把「中新网滚动新闻 RSS」当**额外候选来源**的收益上限测量（只测不判、零现网改动）。

做法（固定候选池回放）：
  1) 拉一次 RSS（robots 校验 + 单请求 + 3s 超时），冻结为「最新一批」候选（30 条）；
  2) 每轮跑登记口径的 20 条 2-9 查询（`--no-cache`、单并发）：
       捕获 pipeline `_collect_hits` 的原始 hits（= 现有候选池）；
       before = `_rank_hits(hits)`；after = `_rank_hits(hits + RSS hits)`（同一套融合/排序/过滤）；
  3) 再对中文 news 组（topic=news + time_range=day）同法对比「7 日内日期比例」；
  4) 每轮输出 JSON，并把 before/after 的 top5 明细写成 Markdown（供判分）。

只读：不改产品代码、不动配置；RSS 只拉 1 次 + robots 1 次。
用法：`.venv/bin/python scripts/zh_rss_pool_ab.py --rounds 3 --out-dir docs/reports`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from relevance import QUERIES  # noqa: E402
from news_check import QUERIES as NEWS_QUERIES  # noqa: E402
from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.models import SearchResult  # noqa: E402
from utf8_search.providers.base import SearchHit  # noqa: E402
from utf8_search.rank.diversity import query_coverage  # noqa: E402

RSS_URL = "https://www.chinanews.com.cn/rss/scroll-news.xml"
UA = "utf8-search/0.1 (rss-pool-evaluation; +https://github.com/encode-utf8/utf8-search)"
FRESH_DAYS = 7
ZH_NEWS_QUERIES = [q for q in NEWS_QUERIES if re.search(r"[\u4e00-\u9fff]", q)]


def _robots_allows(robots_text: str, path: str) -> bool:
    """极简 robots 判定：任一 Disallow 前缀命中即视为不允许（保守）。"""
    for line in robots_text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line.lower().startswith("disallow:"):
            continue
        prefix = line.split(":", 1)[1].strip()
        if prefix and (path.startswith(prefix) or prefix == "/"):
            return False
    return True


async def fetch_rss(client: httpx.AsyncClient) -> tuple[list[SearchHit], dict]:
    parts = urlsplit(RSS_URL)
    robots = await client.get(f"{parts.scheme}://{parts.netloc}/robots.txt", timeout=3.0)
    allowed = _robots_allows(robots.text, parts.path)
    if not allowed:
        raise SystemExit(f"robots.txt 不允许抓取 {parts.path}，按约定终止")
    resp = await client.get(RSS_URL, timeout=3.0)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    hits: list[SearchHit] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        published = None
        if pub:
            try:
                published = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                published = None
        if title and link:
            hits.append(SearchHit(title=title, url=link, snippet=desc, engine="rss:chinanews",
                                  published_date=published))
    meta = {"robots_allows": allowed, "http_status": resp.status_code, "items": len(hits),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    return hits, meta


def _fresh_within(date_str: str | None, *, now: datetime, days: int = FRESH_DAYS) -> bool:
    if not date_str:
        return False
    try:
        text = date_str.replace("Z", "+00:00")
        value = datetime.fromisoformat(text)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return timedelta(0) <= now - value.astimezone(timezone.utc) <= timedelta(days=days)


def admit_rss(query: str, rss_hits: list[SearchHit], *, min_coverage: float) -> list[SearchHit]:
    """产品口径的准入过滤：覆盖率 ≥ `rank_min_query_coverage`（默认 0.34）的 RSS 条目才会成为候选。

    不做这一步的「全量注入」会引入**评分伪影**（新 engine 组参与 RRF/归一化，把不相关条目顶进 top5），
    不能代表产品行为 —— 在产品里这些条目会被同一条 `low_coverage` 判据剔除。
    """
    admitted = []
    for hit in rss_hits:
        probe = SearchResult(title=hit.title, url=hit.url, content=hit.snippet or "")
        if query_coverage(query, probe) >= min_coverage:
            admitted.append(hit)
    return admitted


async def run_round(
    pipeline: SearchPipeline, rss_hits: list[SearchHit], round_no: int, *, min_coverage: float
) -> dict:
    captured: dict[str, tuple] = {}
    original = pipeline._collect_hits  # noqa: SLF001

    async def capture(request):  # noqa: ANN001
        result = await original(request)
        captured[request.query] = result
        return result

    pipeline._collect_hits = capture  # type: ignore[method-assign]  # noqa: SLF001
    now = datetime.now(timezone.utc)
    rows = []
    try:
        for index, (category, query) in enumerate(QUERIES, 1):
            request = SearchRequest(query=query, max_results=5, depth="basic")
            await pipeline.search(request)                      # 只用来触发一次采集（结果与 before 同源）
            hits = captured[query][0]
            admitted = admit_rss(query, rss_hits, min_coverage=min_coverage)
            before = (await pipeline._rank_hits(list(hits), request))[:5]  # noqa: SLF001
            after = (await pipeline._rank_hits(list(hits) + list(admitted), request))[:5]  # noqa: SLF001
            rows.append({
                "id": index, "category": category, "query": query,
                "rss_admitted": len(admitted),
                "top5_changed": [r.url for r in before] != [r.url for r in after],
                "before": [{"title": r.title, "url": r.url, "date": r.published_date} for r in before],
                "after": [{"title": r.title, "url": r.url, "date": r.published_date} for r in after],
                "before_fresh_share": round(sum(_fresh_within(r.published_date, now=now) for r in before) / max(len(before), 1), 3),
                "after_fresh_share": round(sum(_fresh_within(r.published_date, now=now) for r in after) / max(len(after), 1), 3),
            })
        news_rows = []
        for index, query in enumerate(ZH_NEWS_QUERIES, 1):
            request = SearchRequest(query=query, max_results=5, depth="basic", topic="news", time_range="day")
            await pipeline.search(request)
            hits = captured[query][0]
            admitted = admit_rss(query, rss_hits, min_coverage=min_coverage)
            before = (await pipeline._rank_hits(list(hits), request))[:5]  # noqa: SLF001
            after = (await pipeline._rank_hits(list(hits) + list(admitted), request))[:5]  # noqa: SLF001
            news_rows.append({
                "id": index, "query": query,
                "rss_admitted": len(admitted),
                "before": {"n": len(before), "fresh": sum(_fresh_within(r.published_date, now=now) for r in before)},
                "after": {"n": len(after), "fresh": sum(_fresh_within(r.published_date, now=now) for r in after)},
                "rss_in_after": sum(1 for r in after if "chinanews.com.cn" in (r.url or "")),
            })
    finally:
        pipeline._collect_hits = original  # type: ignore[method-assign]  # noqa: SLF001
    return {"round": round_no, "queries": rows, "zh_news": news_rows}


async def main() -> int:
    parser = argparse.ArgumentParser(description="中文 RSS 作为额外候选源的收益上限测量")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--out-dir", default="docs/reports")
    parser.add_argument("--min-coverage", type=float, default=0.34,
                        help="RSS 条目准入的查询词覆盖率门槛（产品同款 rank_min_query_coverage=0.34）")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as client:
        rss_hits, rss_meta = await fetch_rss(client)

    settings = Settings().model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    rounds = []
    try:
        for round_no in range(1, args.rounds + 1):
            rounds.append(await run_round(pipeline, rss_hits, round_no, min_coverage=args.min_coverage))
            print(f"round {round_no} done", flush=True)
    finally:
        await pipeline.close()

    payload = {"rss": rss_meta, "min_coverage": args.min_coverage, "rss_hits": [h.to_dict() for h in rss_hits],
               "zh_news_queries": ZH_NEWS_QUERIES, "rounds": rounds}
    out = out_dir / "zh-rss-pool-benefit-20261002.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# T17：中文 RSS 作为额外候选来源——before/after 明细", "",
             f"- RSS: {RSS_URL}（{rss_meta['items']} 条，robots_allows={rss_meta['robots_allows']}）", ""]
    for rnd in rounds:
        lines += [f"## round {rnd['round']}", ""]
        for row in rnd["queries"]:
            if not row["top5_changed"]:
                continue
            lines += [f"### Q{row['id']} {row['query']}（top5 变化）", "",
                      "| 位 | before | after |", "| --- | --- | --- |"]
            for i in range(5):
                b = row["before"][i]["title"] if i < len(row["before"]) else "—"
                a = row["after"][i]["title"] if i < len(row["after"]) else "—"
                lines.append(f"| {i+1} | {b[:60]} | {a[:60]} |")
            lines.append("")
        lines += [f"### round {rnd['round']} 中文 news 组", "",
                  "| 查询 | before 7日内/条 | after 7日内/条 | after 含RSS |",
                  "| --- | --- | --- | --- |"]
        for row in rnd["zh_news"]:
            lines.append(f"| {row['query']} | {row['before']['fresh']}/{row['before']['n']} | "
                         f"{row['after']['fresh']}/{row['after']['n']} | {row['rss_in_after']} |")
        lines.append("")
    (out_dir / "zh-rss-pool-benefit-20261002-detail.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("written:", out)
    return 0


raise SystemExit(asyncio.run(main()))

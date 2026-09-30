"""运维巡检：/health + /metrics + 磁盘/数据目录阈值，结构化日志 + 非零退出码。

设计给 cron 用（每 5 分钟一次，见 `docs/05-服务器部署手册.md` §运维巡检）：

* **服务不可达**：/health 非 200 或超时；
* **上游错误**：`utf8search_upstream_requests_total{result="error"}` > 0（与阈值一起看）；
* **闸门拒绝异常增长**：`rejected_total` 相比上次快照的增量 > `--max-rejected-delta`（默认 200）；
* **磁盘**：根分区与项目 `data/` 目录占用超过阈值（默认 85% / 5 GiB）；
* 通知通道留接口：`OPS_ALERT_WEBHOOK` / `OPS_ALERT_TOKEN` 环境变量，**未配置时只记日志**。

用法：
    .venv/bin/python scripts/ops_check.py                    # 单次巡检
    .venv/bin/python scripts/ops_check.py --base-url http://127.0.0.1:8000
    .venv/bin/python scripts/ops_check.py --json             # 也是结构化输出（便于管道）

退出码：0 = 全部通过；1 = 有告警（cron 可据此发邮件/接监控）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LOG = REPO / "data" / "ops-check.log"
STATE = REPO / "data" / "ops-check-state.json"


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def api_key() -> str:
    env = os.environ.get("UTF8SEARCH_API_KEYS", "")
    if env:
        return env.split(",")[0].strip()
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("UTF8SEARCH_API_KEYS="):
                return line.split("=", 1)[1].split(",")[0].strip()
    return ""


def parse_metrics(text: str) -> dict[str, float]:
    """抽出巡检关心的几条序列（无标签聚合 + 带标签两类）。"""
    values: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        name, _, raw = line.partition(" ")
        try:
            value = float(raw)
        except ValueError:
            continue
        values[name] = values.get(name, 0.0) + value
    return values


def check_disk(path: Path, *, max_used_ratio: float, max_data_bytes: int) -> list[str]:
    problems: list[str] = []
    usage = shutil.disk_usage(path)
    ratio = usage.used / usage.total if usage.total else 0.0
    if ratio > max_used_ratio:
        problems.append(f"磁盘占用 {ratio:.1%} > 阈值 {max_used_ratio:.0%}（{path}）")
    data_dir = REPO / "data"
    if data_dir.exists():
        size = sum(p.stat().st_size for p in data_dir.rglob("*") if p.is_file())
        if size > max_data_bytes:
            problems.append(f"data/ 占用 {size / 2**30:.2f} GiB > 阈值 {max_data_bytes / 2**30:.2f} GiB")
    return problems


def notify(problems: list[str], payload: dict) -> str:
    """通知通道接口：未配置 webhook 时只返回 'log-only'。"""
    url = os.environ.get("OPS_ALERT_WEBHOOK", "").strip()
    if not url or not problems:
        return "log-only"
    token = os.environ.get("OPS_ALERT_TOKEN", "").strip()
    try:
        with httpx.Client(trust_env=False, timeout=8.0) as client:
            client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"} if token else {})
        return "sent"
    except Exception as exc:  # noqa: BLE001 - 通知失败不能影响巡检结论
        return f"failed: {exc}"


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description="utf8-search 运维巡检")
    parser.add_argument("--base-url", default=os.environ.get("OPS_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--max-rejected-delta", type=int, default=200)
    parser.add_argument("--max-used-ratio", type=float, default=0.85)
    parser.add_argument("--max-data-gib", type=float, default=5.0)
    parser.add_argument("--json", action="store_true", help="把巡检结果以 JSON 打到 stdout")
    args = parser.parse_args()

    started = time.perf_counter()
    problems: list[str] = []
    snapshot: dict[str, object] = {"ts": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url}
    key = api_key()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    with httpx.Client(trust_env=False, timeout=10.0) as client:
        try:
            health = client.get(f"{args.base_url.rstrip('/')}/health", headers=headers)
            snapshot["health_status"] = health.status_code
            if health.status_code != 200:
                problems.append(f"/health 返回 {health.status_code}")
            else:
                body = health.json()
                snapshot["searxng"] = body.get("searxng")
                cooling = [c.get("engine") for c in (body.get("engines") or {}).get("cooling") or []]
                snapshot["cooling"] = cooling
        except Exception as exc:  # noqa: BLE001
            problems.append(f"/health 不可达：{exc}")
        try:
            metrics = client.get(f"{args.base_url.rstrip('/')}/metrics", headers=headers)
            if metrics.status_code != 200:
                problems.append(f"/metrics 返回 {metrics.status_code}")
            else:
                values = parse_metrics(metrics.text)
                errors = values.get('utf8search_upstream_requests_total{result="error"}', 0.0)
                rejected = sum(v for k, v in values.items() if k.startswith("utf8search_upstream_rejected_total"))
                ok_count = values.get('utf8search_upstream_requests_total{result="ok"}', 0.0)
                snapshot.update({"upstream_error": errors, "rejected_total": rejected, "requests_ok": ok_count})
                if errors > 0:
                    problems.append(f"上游错误计数非 0：result=error {errors:.0f}")
                previous = {}
                if STATE.exists():
                    try:
                        previous = json.loads(STATE.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        previous = {}
                delta = rejected - float(previous.get("rejected_total", rejected))
                snapshot["rejected_delta"] = delta
                if delta > args.max_rejected_delta:
                    problems.append(f"闸门拒绝数增量异常：+{delta:.0f} > {args.max_rejected_delta}")
                STATE.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"/metrics 不可达：{exc}")
    problems.extend(check_disk(REPO, max_used_ratio=args.max_used_ratio,
                               max_data_bytes=int(args.max_data_gib * 2**30)))
    snapshot["problems"] = problems
    snapshot["duration_ms"] = round((time.perf_counter() - started) * 1000)
    status = "ALERT" if problems else "OK"
    line = json.dumps({"level": status, **snapshot}, ensure_ascii=False)
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    channel = notify(problems, snapshot)
    if args.json:
        print(line)
    else:
        print(f"[{status}] health={snapshot.get('health_status')} "
              f"error={snapshot.get('upstream_error')} rejected={snapshot.get('rejected_total')} "
              f"冷却引擎={snapshot.get('cooling')} 通知={channel}")
        for problem in problems:
            print(f"  ⚠️ {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

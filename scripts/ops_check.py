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
import csv
import json
import os
import re
import shutil
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LOG = REPO / "data" / "ops-check.log"
STATE = REPO / "data" / "ops-check-state.json"
SNAPSHOT_CSV = REPO / "data" / "ops-metrics-snapshot.csv"
BACKUP_GLOB = os.environ.get("OPS_BACKUP_GLOB", "/var/backups/utf8-search/deploy-backups-*")
# 备份产物后缀：P3（2026-09-30）之后默认是加密包 `.tar.gz.enc`；旧的明文包是 `.tar.gz`，两种都要认。
# 曾经的缺陷：这里只 glob 了 `*.tar.gz` ⇒ 加密备份上线后每 5 分钟误报「未找到任何备份产物」。
BACKUP_ARTIFACT_GLOBS = ("utf8-search-backup-*.tar.gz", "utf8-search-backup-*.tar.gz.enc")
# SHA256SUMS 与产物必须**同目录**，且 mtime 相差不超过这个窗口（否则可能是"新校验和配旧包"）
BACKUP_PAIR_TOLERANCE_SEC = 3600


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


def cert_days(host: str, port: int = 443, *, timeout: float = 8.0) -> tuple[float, str]:
    """连接目标端口并读回证书，返回 (剩余天数, notAfter ISO)。仅看日期，不做链校验。"""
    from cryptography import x509  # 本地依赖，随 pyproject 安装

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket_create(host, port, timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    certificate = x509.load_der_x509_certificate(der)
    not_after = certificate.not_valid_after_utc
    return (not_after - datetime.now(timezone.utc)).total_seconds() / 86400, not_after.isoformat()


def socket_create(host: str, port: int, timeout: float):
    import socket

    return socket.create_connection((host, port), timeout=timeout)


def check_backup(backup_dir: str, *, max_age_hours: float) -> tuple[list[str], dict[str, object]]:
    """最近一次 backup.sh 产物是否新鲜。

    判据（2026-09-30 P6 修正）：
    * 产物后缀认**两种**：`utf8-search-backup-*.tar.gz`（明文）与 `utf8-search-backup-*.tar.gz.enc`（P3 起的默认加密包）；
    * `SHA256SUMS` 必须与产物**同目录**，且两者 mtime 相差 ≤ `BACKUP_PAIR_TOLERANCE_SEC`（避免"新校验和 + 旧包"被当成新鲜）；
    * 新鲜度取该 pair 里**较新**的 mtime，超过 `max_age_hours` 即告警。
    """
    problems: list[str] = []
    info: dict[str, object] = {}
    import glob

    dirs = [Path(p) for p in glob.glob(backup_dir)] or ([Path(backup_dir)] if Path(backup_dir).exists() else [])
    newest: tuple[float, Path, Path] | None = None
    for directory in dirs:
        sums_files = list(directory.glob("SHA256SUMS"))
        artifacts = [p for pattern in BACKUP_ARTIFACT_GLOBS for p in directory.glob(pattern)]
        for artifact in artifacts:
            for sums in sums_files:
                if abs(artifact.stat().st_mtime - sums.stat().st_mtime) > BACKUP_PAIR_TOLERANCE_SEC:
                    continue  # 同目录但不同龄：不认这一对
                stamp = max(artifact.stat().st_mtime, sums.stat().st_mtime)
                if newest is None or stamp > newest[0]:
                    newest = (stamp, directory, artifact)
    if newest is None:
        problems.append(
            f"未找到任何有效备份产物（{backup_dir}：需要 utf8-search-backup-*.tar.gz[.enc] "
            f"且与同目录 SHA256SUMS 同龄 ≤ {BACKUP_PAIR_TOLERANCE_SEC // 60} 分钟）"
        )
        return problems, info
    age_hours = (time.time() - newest[0]) / 3600
    info["backup_dir"] = str(newest[1])
    info["backup_artifact"] = newest[2].name
    info["backup_age_hours"] = round(age_hours, 2)
    if age_hours > max_age_hours:
        problems.append(f"最近一次备份已 {age_hours:.1f} 小时（> {max_age_hours:.0f}h）：{newest[1]}")
    return problems, info


def append_snapshot(path: Path, row: dict[str, object]) -> None:
    """把关键指标快照成一行 CSV（用于积累坏日样本）。"""
    header = ["ts", "health_status", "upstream_error", "rejected_queue_full", "rejected_timeout",
              "requests_ok", "probe_results"]
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        if new_file:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in header})


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
    parser.add_argument("--cert-host", default=os.environ.get("OPS_CERT_HOST", ""),
                        help="证书检查的主机名（默认取 OPS_CERT_HOST；未配置则跳过证书检查）")
    parser.add_argument("--cert-port", type=int, default=443)
    parser.add_argument("--cert-min-days", type=float, default=30.0,
                        help="证书剩余天数低于该值告警（Let's Encrypt 90 天有效，30 天是续期预警线）")
    parser.add_argument("--cert-skip", action="store_true", help="跳过证书检查（内网/离线环境）")
    parser.add_argument("--backup-glob", default=BACKUP_GLOB,
                        help="备份目录 glob（默认取 OPS_BACKUP_GLOB 或 /var/backups/utf8-search/deploy-backups-*）")
    parser.add_argument("--backup-max-hours", type=float, default=48.0, help="最近备份的最大允许年龄（小时）")
    parser.add_argument("--snapshot-csv", default=str(SNAPSHOT_CSV), help="指标快照 CSV 路径")
    parser.add_argument("--no-probe-search", action="store_true",
                        help="不做探针搜索（默认做一次唯一查询，用于记录结果条数）")
    parser.add_argument("--json", action="store_true", help="把巡检结果以 JSON 打到 stdout")
    args = parser.parse_args()

    started = time.perf_counter()
    problems: list[str] = []
    snapshot: dict[str, object] = {"ts": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url}
    queue_full = 0.0
    timeout_rejected = 0.0
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
                queue_full = values.get('utf8search_upstream_rejected_total{reason="queue_full"}', 0.0)
                timeout_rejected = values.get('utf8search_upstream_rejected_total{reason="timeout"}', 0.0)
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
        # 1.5) 探针搜索：记录结果条数（坏日样本的"结果中位数"口径：每 5 分钟一条）
        if not args.no_probe_search and key:
            try:
                probe = client.post(
                    f"{args.base_url.rstrip('/')}/v1/search",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"query": f"ops probe {datetime.now(timezone.utc).strftime('%H%M%S')}",
                          "max_results": 5, "search_depth": "basic"},
                    timeout=30.0,
                )
                payload = probe.json()
                snapshot["probe_results"] = len(payload.get("results") or [])
                snapshot["probe_status"] = probe.status_code
            except Exception as exc:  # noqa: BLE001
                problems.append(f"探针搜索失败：{exc}")
    # 2) 证书剩余天数（遗留 #5：续期依赖 80/443 放行，必须能提前发现）
    if not args.cert_skip and not args.cert_host:
        snapshot["cert_skipped"] = "OPS_CERT_HOST 未配置"
        print("注意：未配置 OPS_CERT_HOST，证书检查已跳过（cron 里应显式设置）")
    elif not args.cert_skip:
        try:
            days, not_after = cert_days(args.cert_host, args.cert_port)
            snapshot["cert_days"] = round(days, 1)
            snapshot["cert_not_after"] = not_after
            if days < args.cert_min_days:
                problems.append(
                    f"证书剩余 {days:.1f} 天（< {args.cert_min_days:.0f} 天，到期 {not_after}）："
                    f"{args.cert_host}:{args.cert_port}"
                )
        except Exception as exc:  # noqa: BLE001
            problems.append(f"证书检查失败（{args.cert_host}:{args.cert_port}）：{exc}")
    # 3) 最近一次备份是否新鲜（backup.sh 产物）
    backup_problems, backup_info = check_backup(args.backup_glob, max_age_hours=args.backup_max_hours)
    snapshot.update(backup_info)
    problems.extend(backup_problems)
    problems.extend(check_disk(REPO, max_used_ratio=args.max_used_ratio,
                               max_data_bytes=int(args.max_data_gib * 2**30)))
    # 4) 指标快照 CSV（坏日样本）
    append_snapshot(Path(args.snapshot_csv), {
        "ts": snapshot["ts"],
        "health_status": snapshot.get("health_status", ""),
        "upstream_error": snapshot.get("upstream_error", ""),
        "rejected_queue_full": queue_full,
        "rejected_timeout": timeout_rejected,
        "requests_ok": snapshot.get("requests_ok", ""),
        "probe_results": snapshot.get("probe_results", ""),
    })
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

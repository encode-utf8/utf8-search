"""引用完整性检查：确保「非 gitignore 文件」里出现的路径引用都可核实。

背景：2026-10-02 仓库瘦身清理了 204 个过程明细文件，但 checklist §8 与部分历史报告
仍以纯文本提到它们（Markdown 链接扫描扫不到）。本脚本把这类引用显式化：

规则（只看 git 跟踪 + 未忽略的文本文件）：
1. Markdown 链接 `](path)` 必须能解析到现存文件；
2. 文本里的路径引用（`docs/reports/...` 或带扩展名的仓库内路径）必须：
   - 指向现存文件；或
   - 命中 `docs/reports/cleaned-files-20261002.txt` 的已清理清单，且**该文件带标记**
     `<!-- refs-policy: cleaned-2026-10-02 -->`（表示"历史引用、不可当现存路径用"）；
3. `data/` 属于 gitignore 范围（工程约定不保证留存），本脚本只统计不判错。

实现约束（防 CPU 事故）：不展开花括号、单遍正则、单文件 ≤512KB、token ≤200 字符、
纯集合/前缀匹配 —— 全仓库扫描应在 1 秒级完成。

用法：
    .venv/bin/python scripts/check_refs.py          # 有违规时 exit 1
    .venv/bin/python scripts/check_refs.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

MARKER = "refs-policy: cleaned-2026-10-02"
CLEANED_LIST = "docs/reports/cleaned-files-20261002.txt"
TEXT_EXT = {".md", ".csv", ".json", ".py", ".yml", ".yaml", ".sh", ".txt", ".toml"}
MAX_FILE_BYTES = 512_000
MAX_TOKEN = 200

TOKEN_RE = re.compile(r"(?:docs|scripts|tests|src|searxng|data)/[A-Za-z0-9_./@{},+\-]{1," + str(MAX_TOKEN) + r"}")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")
DOC_NUM_RE = re.compile(r"^docs/\d{2}(?:-\d{2})?$")
CONTAINER_PATHS = {"searxng/searx/settings.yml"}  # searxng 容器内路径，不是仓库文件


def _sh(*args: str, cwd: Path) -> list[str]:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    # -z 由调用方传入；这里统一按 NUL 切，避免中文路径被 git 加引号转义。
    return [x for x in out.stdout.split("\0") if x]


def repo_files(root: Path) -> list[str]:
    """git 跟踪 + 未忽略的未跟踪文件（即"不在 gitignore 范围内"的全部文件）。"""
    tracked = _sh("ls-files", "-z", cwd=root)
    untracked = _sh("ls-files", "--others", "--exclude-standard", "-z", cwd=root)
    return sorted(set(tracked) | set(untracked))


def load_cleaned(root: Path) -> set[str]:
    p = root / CLEANED_LIST
    if not p.exists():
        return set()
    return {line.strip() for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def has_policy_marker(text: str) -> bool:
    return MARKER in text


def extract_tokens(text: str) -> list[str]:
    """提取候选路径 token（有界；不做任何花括号展开）。"""
    out = []
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0).rstrip(".,;:)`'\"")
        if tok:
            out.append(tok)
    return out


def is_enforced(token: str, root: Path) -> bool:
    """只强制检查两类：docs/reports/ 下的引用；带扩展名的仓库内路径。"""
    if token.startswith("data/"):
        return False
    if token in CONTAINER_PATHS:
        return False
    if token.startswith("docs/reports/"):
        return True
    if DOC_NUM_RE.match(token):
        return True
    return Path(token).suffix.lower() in TEXT_EXT


def token_status(token: str, root: Path, exists: set[str], cleaned: set[str]) -> tuple[str, str]:
    """返回 (status, detail)：ok / cleaned-ok / cleaned-no-marker / missing。"""
    if DOC_NUM_RE.match(token):
        spec = token.split("/")[1]
        nums = [spec[:2]] if len(spec) == 2 else [f"{n:02d}" for n in range(int(spec[:2]), int(spec[3:]) + 1)]
        # docs/00 是文档集的占位编号（实际从 01 开始），白名单放行；其余编号必须有对应文件。
        ok = all(nn == "00" or any(p.startswith(f"docs/{nn}-") for p in exists) for nn in nums)
        return ("ok", "") if ok else ("missing", "docs 序号引用无对应文件")
    if token.endswith("/"):
        return ("ok", "dir") if (root / token).is_dir() else ("missing", "目录不存在")
    if "{" in token or token.endswith("-") or (Path(token).suffix == "" and token.startswith("docs/reports/")):
        prefix = token.split("{", 1)[0]
        base_prefix = prefix.rsplit("/", 1)[-1]
        if len(base_prefix) < 3:
            return ("missing", f"引用过短，无法判定：{prefix}")
        hit_exists = any(p.startswith(prefix) for p in exists)
        hit_cleaned = any(p.startswith(prefix) for p in cleaned)
        if hit_exists or hit_cleaned:
            return ("ok", "pattern")
        return ("missing", f"花括号模式前缀无匹配：{prefix}")
    if token in exists:
        return ("ok", "")
    if token in cleaned:
        return ("cleaned-ok", "历史引用（文件已按 2026-10-02 瘦身清理）")
    return ("missing", "既不是现存文件，也不在已清理清单")


def check_file(rel: str, root: Path, exists: set[str], cleaned: set[str],
               cleaned_names: dict[str, str]) -> list[dict]:
    p = root / rel
    try:
        if p.suffix.lower() not in TEXT_EXT or p.stat().st_size > MAX_FILE_BYTES:
            return []
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    marked = has_policy_marker(text)
    problems: list[dict] = []
    seen: set[tuple[str, str]] = set()

    if p.suffix.lower() == ".md":
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (p.parent / clean).resolve()
            if not resolved.exists():
                key = ("link", target)
                if key not in seen:
                    seen.add(key)
                    problems.append({"file": rel, "ref": target, "reason": "Markdown 链接指向不存在的文件"})

    for token in extract_tokens(text):
        if not is_enforced(token, root):
            continue
        status, detail = token_status(token, root, exists, cleaned)
        if status == "ok":
            continue
        if status == "cleaned-ok" and marked:
            continue
        key = (token, status)
        if key in seen:
            continue
        seen.add(key)
        if status == "cleaned-ok":
            reason = "引用了已清理文件，但本文缺少标记 <!-- refs-policy: cleaned-2026-10-02 -->"
        else:
            reason = f"引用了不存在的文件（{detail}）"
        problems.append({"file": rel, "ref": token, "reason": reason})
    # 裸文件名（反引号里不带目录前缀，如 `m29-t19-...-brief.md`）：命中已清理清单同样要求标记。
    for content in BACKTICK_RE.findall(text):
        c = content.strip()
        if not c or " " in c or c.startswith(("http://", "https://", "git ", "python ", "docker ")):
            continue
        # 只把"像文件名/文件模式"的反引号内容当引用，避免 `engine` 这类普通词误报。
        if len(c) < 8 or not any(ch in c for ch in ".{*") and not c[-1].isdigit():
            continue
        prefix = c.split("{", 1)[0]
        if len(prefix) < 6 or "/" in prefix:
            continue
        if not any(name.startswith(prefix) for name in cleaned_names):
            continue
        if marked:
            continue
        key = (c, "cleaned-bare")
        if key in seen:
            continue
        seen.add(key)
        problems.append({"file": rel, "ref": c,
                         "reason": "裸文件名命中已清理清单，但本文缺少标记 <!-- refs-policy: cleaned-2026-10-02 -->"})
    return problems


def run(root: Path) -> dict:
    t0 = time.time()
    files = [f for f in repo_files(root) if (root / f).exists()]
    cleaned = load_cleaned(root)
    cleaned_names = {Path(p).name: p for p in cleaned}
    exists = set(files)
    problems: list[dict] = []
    data_refs = 0
    for rel in files:
        if rel == CLEANED_LIST:
            continue
        p = root / rel
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        data_refs += sum(1 for t in extract_tokens(text) if t.startswith("data/"))
        problems.extend(check_file(rel, root, exists, cleaned, cleaned_names))
    return {
        "scanned_files": len(files),
        "cleaned_registry": len(cleaned),
        "data_refs_ignored": data_refs,
        "violations": problems,
        "elapsed_s": round(time.time() - t0, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="非忽略文件引用完整性检查")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", default="")
    args = parser.parse_args()
    result = run(Path(args.root).resolve())
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"扫描 {result['scanned_files']} 个非忽略文件；已清理清单 {result['cleaned_registry']} 项；"
          f"data/ 引用 {result['data_refs_ignored']} 处（gitignore 范围，只统计）；"
          f"{result['elapsed_s']}s")
    if not result["violations"]:
        print("OK：所有可强制的路径引用都可核实")
        return 0
    print(f"发现 {len(result['violations'])} 处违规：")
    for v in result["violations"][:100]:
        print(f"  - {v['file']}: {v['ref']} —— {v['reason']}")
    if len(result["violations"]) > 100:
        print(f"  ... 其余 {len(result['violations']) - 100} 处见 --json 输出")
    return 1


if __name__ == "__main__":
    sys.exit(main())

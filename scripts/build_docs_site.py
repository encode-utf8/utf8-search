#!/usr/bin/env python3
"""使用说明站生成器：把仓库里的 Markdown 生成自包含的 `docs/site/index.html`。

设计约束：
* 纯前端：生成物内联 CSS/JS/搜索索引，不引用任何 CDN 或外部脚本/字体/图片；
* 单一来源：内容来自 `docs/03`、P4 客户端配置包、`docs/05` 与本站自有的两份说明页；
* 确定性：同样输入必然生成同样输出（不含时间戳），`--check` 可校验提交物是否过期；
* 零依赖：只用标准库（Markdown 子集渲染器足够覆盖仓库文档的用法）。

用法：
    .venv/bin/python scripts/build_docs_site.py        # 生成 docs/site/index.html
    .venv/bin/python scripts/build_docs_site.py --check  # 过期则 exit 1（测试/CI 用）
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_PATH = REPO / "docs/site/index.html"

PAGES = [
    {"id": "home", "title": "快速开始", "group": "开始", "source": "docs/site/content/home.md"},
    {"id": "clients", "title": "客户端接入指南", "group": "接入", "source": "docs/03-客户端接入指南.md"},
    {"id": "client-pack", "title": "客户端配置包（复制即用）", "group": "接入",
     "source": "docs/reports/20260930-p4-3-9-client-config-pack.md"},
    {"id": "deploy", "title": "自部署与运维", "group": "自部署", "source": "docs/05-服务器部署手册.md"},
    {"id": "about", "title": "关于与已知限制", "group": "关于", "source": "docs/site/content/about.md"},
]

INLINE_RE = re.compile(r"(`[^`]+`)|(\[[^\]]+\]\([^)\s]+\))|(\*\*[^*]+\*\*)")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")


def slugify(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text).strip().lower()
    out: list[str] = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "section"


def link_map() -> dict[str, str]:
    return {str((REPO / p["source"]).resolve()): f"#page-{p['id']}" for p in PAGES}


def resolve_href(url: str, page_id: str, links: dict[str, str], src_dir: Path) -> str | None:
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    if url.startswith("#"):
        return f"#page-{page_id}--{slugify(url[1:])}"
    target = (src_dir / url).resolve()
    return links.get(str(target))


def render_inline(text: str, page_id: str, links: dict[str, str], src_dir: Path) -> str:
    parts: list[str] = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        parts.append(html.escape(text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("`"):
            parts.append("<code>" + html.escape(tok[1:-1]) + "</code>")
        elif tok.startswith("["):
            label, url = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)", tok).groups()
            href = resolve_href(url, page_id, links, src_dir)
            if href is None:
                parts.append('<span class="repo-ref" title="仓库内文件（不在本站，见仓库对应路径）">'
                             + render_inline(label, page_id, links, src_dir) + "</span>")
            else:
                extra = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
                parts.append(f'<a href="{html.escape(href, quote=True)}"{extra}>'
                             + render_inline(label, page_id, links, src_dir) + "</a>")
        else:
            parts.append("<strong>" + render_inline(tok[2:-2], page_id, links, src_dir) + "</strong>")
        pos = m.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def _cells(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|") and not raw.endswith("\\|"):
        raw = raw[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", raw)]


def _is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", line)) and "-" in line


def _render_list(items: list[tuple[int, bool, str]], page_id: str,
                 links: dict[str, str], src_dir: Path) -> str:
    out: list[str] = []
    stack: list[tuple[int, str]] = []
    for level, ordered, text in items:
        tag = "ol" if ordered else "ul"
        while stack and level < stack[-1][0]:
            out.append(f"</{stack.pop()[1]}>")
        if not stack or level > stack[-1][0]:
            out.append(f"<{tag}>")
            stack.append((level, tag))
        elif stack[-1][1] != tag:
            out.append(f"</{stack.pop()[1]}>")
            out.append(f"<{tag}>")
            stack.append((level, tag))
        out.append("<li>" + render_inline(text, page_id, links, src_dir) + "</li>")
    while stack:
        out.append(f"</{stack.pop()[1]}>")
    return "".join(out)


def md_to_html(md: str, page_id: str, links: dict[str, str], src_dir: Path) -> tuple[str, list[tuple[str, str]]]:
    """返回 (body_html, headings[(anchor, title)])。支持仓库文档用到的 Markdown 子集。"""
    lines = md.replace("\r\n", "\n").split("\n")
    # 去掉源文件的一级标题（页面标题由清单提供）
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines) and lines[idx].startswith("# "):
        lines = lines[idx + 1:]

    out: list[str] = []
    headings: list[tuple[str, str]] = []
    used: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if line.lstrip().startswith("```"):
            lang = line.strip().strip("`").strip()
            buf: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            slug = slugify(title)
            n = used.get(slug, 0)
            used[slug] = n + 1
            anchor = f"page-{page_id}--{slug}" + (f"-{n}" if n else "")
            headings.append((anchor, title))
            out.append(f'<h{level} id="{anchor}">' + render_inline(title, page_id, links, src_dir) + f"</h{level}>")
            i += 1
            continue

        if re.match(r"^\s*(?:-{3,}|\*{3,})\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            out.append("<blockquote><p>" +
                       render_inline(" ".join(x for x in buf if x), page_id, links, src_dir) +
                       "</p></blockquote>")
            continue

        if "|" in line and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            header = _cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                rows.append(_cells(lines[i]))
                i += 1
            th = "".join("<th>" + render_inline(c, page_id, links, src_dir) + "</th>" for c in header)
            trs = "".join("<tr>" + "".join("<td>" + render_inline(c, page_id, links, src_dir) + "</td>"
                                           for c in row) + "</tr>" for row in rows)
            out.append(f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>")
            continue

        if LIST_RE.match(line):
            items: list[tuple[int, bool, str]] = []
            while i < len(lines):
                lm = LIST_RE.match(lines[i])
                if not lm:
                    break
                indent = len(lm.group(1))
                level = 0 if indent < 2 else (1 if indent < 4 else 2)
                text = lm.group(3).strip()
                j = i + 1
                while (j < len(lines) and lines[j].strip()
                       and not LIST_RE.match(lines[j])
                       and not lines[j].lstrip().startswith(("```", ">", "#"))
                       and not (("|" in lines[j]) and (j + 1 < len(lines) and _is_table_sep(lines[j + 1])))
                       and re.match(r"^\s{2,}\S", lines[j])):
                    text += " " + lines[j].strip()
                    j += 1
                items.append((level, lm.group(2)[0].isdigit(), text))
                i = j
            out.append(_render_list(items, page_id, links, src_dir))
            continue

        buf = [line.strip()]
        i += 1
        while (i < len(lines) and lines[i].strip() and not HEADING_RE.match(lines[i])
               and not lines[i].lstrip().startswith(("```", ">"))
               and not LIST_RE.match(lines[i])
               and not (("|" in lines[i]) and (i + 1 < len(lines) and _is_table_sep(lines[i + 1])))):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + render_inline(" ".join(buf), page_id, links, src_dir) + "</p>")

    return "\n".join(out), headings


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def build_search_index(page_id: str, page_title: str, body: str) -> list[dict]:
    entries = []
    chunks = re.split(r"(?=<h[23] )", body)
    first = chunks[0]
    text = _strip_tags(first)
    if text:
        entries.append({"page": page_id, "anchor": f"page-{page_id}", "title": page_title, "text": text[:1500]})
    for chunk in chunks[1:]:
        m = re.match(r'<h[23] id="([^"]+)">(.*?)</h[23]>', chunk)
        if not m:
            continue
        entries.append({"page": page_id, "anchor": m.group(1),
                        "title": _strip_tags(m.group(2)), "text": _strip_tags(chunk)[:1500]})
    return entries


def build_site() -> str:
    links = link_map()
    nav_groups: dict[str, list[dict]] = {}
    sections: list[str] = []
    search_index: list[dict] = []
    for p in PAGES:
        src = REPO / p["source"]
        body, _ = md_to_html(src.read_text(encoding="utf-8"), p["id"], links, src.parent)
        sections.append(f'<section class="page" id="page-{p["id"]}">\n'
                        f'<h1>{html.escape(p["title"])}</h1>\n{body}\n</section>')
        search_index.extend(build_search_index(p["id"], p["title"], body))
        nav_groups.setdefault(p["group"], []).append(p)

    nav = "".join(
        f'<div class="nav-group"><div class="nav-title">{html.escape(g)}</div>'
        + "".join(f'<a class="nav-link" href="#page-{p["id"]}">{html.escape(p["title"])}</a>' for p in items)
        + "</div>"
        for g, items in nav_groups.items())

    index_json = json.dumps(search_index, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("__NAV__", nav).replace("__CONTENT__", "\n".join(sections)) \
                   .replace("__INDEX__", index_json)


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>utf8-search 使用说明</title>
<meta name="description" content="utf8-search 的使用说明：快速开始、客户端接入、配置包、自部署与已知限制。">
<style>
:root{--bg:#f7f8fa;--card:#fff;--fg:#1f2328;--muted:#59636e;--line:#d8dee4;--accent:#0b6bcb;--code:#f2f4f7}
@media (prefers-color-scheme: dark){:root{--bg:#0f1216;--card:#171b21;--fg:#e6e9ee;--muted:#9aa4b0;--line:#2a313a;--accent:#5aa7ff;--code:#11151a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{position:sticky;top:0;z-index:10;display:flex;gap:16px;align-items:center;padding:10px 18px;background:var(--card);border-bottom:1px solid var(--line)}
.brand{font-weight:700;white-space:nowrap}
.search{position:relative;flex:1;max-width:560px}
.search input{width:100%;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:14px}
.results{position:absolute;top:110%;left:0;right:0;max-height:50vh;overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:8px;display:none}
.results a{display:block;padding:8px 12px;border-bottom:1px solid var(--line);text-decoration:none;color:var(--fg)}
.results a:hover{background:var(--bg)}
.results .sec{color:var(--muted);font-size:12px}
.layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:24px;max-width:1200px;margin:0 auto;padding:20px 18px 60px}
nav{position:sticky;top:64px;align-self:start;max-height:calc(100vh - 90px);overflow:auto}
.nav-title{font-size:12px;color:var(--muted);margin:14px 0 4px;letter-spacing:.08em}
.nav-link{display:block;padding:6px 10px;border-radius:6px;color:var(--fg);text-decoration:none;font-size:14px}
.nav-link:hover{background:var(--card)}
main{min-width:0}
.page{display:none;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:28px 30px}
.page.active{display:block}
h1{font-size:26px;margin:0 0 18px}
h2{font-size:20px;margin:30px 0 10px;padding-top:6px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:22px 0 8px}
a{color:var(--accent)}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.92em}
pre{position:relative;background:var(--code);border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow:auto}
pre code{background:none;padding:0}
.copy{position:absolute;top:6px;right:6px;border:1px solid var(--line);background:var(--card);color:var(--muted);border-radius:6px;font-size:12px;padding:2px 8px;cursor:pointer}
.table-wrap{overflow:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--accent);background:var(--bg);border-radius:0 8px 8px 0}
.repo-ref{border-bottom:1px dashed var(--muted);cursor:help}
footer{max-width:1200px;margin:0 auto;padding:0 18px 40px;color:var(--muted);font-size:13px}
@media (max-width:860px){.layout{grid-template-columns:1fr}nav{position:static;max-height:none}.page{padding:20px 16px}}
</style>
</head>
<body>
<header>
  <div class="brand">utf8-search 说明</div>
  <div class="search">
    <input id="q" type="search" placeholder="搜索：429 / degraded / 客户端 / 证书 …" autocomplete="off">
    <div class="results" id="results"></div>
  </div>
</header>
<div class="layout">
  <nav>__NAV__</nav>
  <main>__CONTENT__</main>
</div>
<footer>由 <code>scripts/build_docs_site.py</code> 从仓库 Markdown 生成（单一来源）。纯静态页：无 CDN、无外部脚本、无后端。</footer>
<script>
const INDEX = __INDEX__;
const pages = [...document.querySelectorAll('.page')];
function show(id){
  pages.forEach(p=>p.classList.toggle('active', p.id===id));
  const el=document.getElementById(id); if(el){el.scrollIntoView({block:'start'});}
}
function route(){
  const h=location.hash.slice(1);
  if(!h){show('page-home');return;}
  const pid=h.split('--')[0];
  show(pid.startsWith('page-')?pid:'page-home');
  const t=document.getElementById(h); if(t){t.scrollIntoView({block:'start'});}
}
window.addEventListener('hashchange',route);
const q=document.getElementById('q'), box=document.getElementById('results');
q.addEventListener('input',()=>{
  const kw=q.value.trim().toLowerCase();
  if(!kw){box.style.display='none';box.innerHTML='';return;}
  const hits=INDEX.filter(e=>(e.title+' '+e.text).toLowerCase().includes(kw)).slice(0,30);
  box.innerHTML=hits.length?hits.map(e=>`<a href="#${e.anchor}"><div>${e.title}</div><div class="sec">${e.page}</div></a>`).join(''):'<a>无匹配</a>';
  box.style.display='block';
});
document.addEventListener('click',e=>{if(!e.target.closest('.search'))box.style.display='none';});
document.querySelectorAll('pre').forEach(pre=>{
  const b=document.createElement('button');b.className='copy';b.textContent='复制';
  b.onclick=()=>{navigator.clipboard.writeText(pre.querySelector('code').innerText).then(()=>{b.textContent='已复制';setTimeout(()=>b.textContent='复制',1200);});};
  pre.appendChild(b);
});
route();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="生成使用说明站（自包含单文件）")
    parser.add_argument("--check", action="store_true", help="校验 docs/site/index.html 是否为最新")
    args = parser.parse_args()
    content = build_site()
    if args.check:
        current = OUT_PATH.read_text(encoding="utf-8") if OUT_PATH.exists() else ""
        if current != content:
            print("docs/site/index.html 已过期：请运行 scripts/build_docs_site.py", file=sys.stderr)
            return 1
        print(f"OK：docs/site/index.html 最新（{len(content)} 字节）")
        return 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(content, encoding="utf-8")
    print(f"已生成 {OUT_PATH.relative_to(REPO)}（{len(content)} 字节，{len(PAGES)} 页）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

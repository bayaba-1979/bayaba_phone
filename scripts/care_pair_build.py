#!/usr/bin/env python3
"""
care_pair_build.py — 돌봄 데몬 원고 → 페어(티스토리 + GitHub Pages) 동시 빌드.

"항상 페어로" 원칙의 실행기. 원고 md 하나에서:
  1. GitHub Pages html  → helana_log/docs/care-daemon/{type}/{NN}-{slug}.html
  2. 티스토리 발행 본문  → tistory-naver/posts/{NN}-{slug}.json  (post.py 입력)

care 블록(```care type= id= + YAML)은 두 타깃에서 다르게 렌더:
  - pages  : 인터랙티브·인포그래픽 (self-contained CSS/JS, design tokens)
  - tistory: 정적 fallback (테마 무관, 단순 HTML)

규격: helana_log/docs/care-daemon/_templates/SPEC.md

실행:
  python3 scripts/care_pair_build.py <원고.md>          # 페어 둘 다
  python3 scripts/care_pair_build.py <원고.md> --pages-only
  python3 scripts/care_pair_build.py --all               # care-daemon/ 전체
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]  # /root/work (helena_phone)
sys.path.insert(0, str(BASE / "scripts"))
from build_satellite_docs_Grok import shell, MD, BRANDS  # noqa: E402

HELANA_LOG = BASE / "helana_log"
CARE_ROOT = HELANA_LOG / "docs" / "care-daemon"
POSTS_DIR = BASE / "tistory-naver" / "posts"

BRAND = BRANDS["helana_log"]
# 돌봄 데몬 채널 전용 kicker (기존 "행정 대화록 · Docs" 대신)
BRAND = {**BRAND, "kicker": "돌봄 데몬 · Care"}

# ── care 블록 추출 ──────────────────────────────────────────────────────────
BLOCK_RE = re.compile(
    r'```care\s+type="(?P<type>[^"]+)"\s+id="(?P<id>[^"]+)"\s*\n'
    r"(?P<payload>.*?)```",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, text[m.end():]


# ── 컴포넌트 렌더러 (target: pages | tistory) ───────────────────────────────
def esc(s: str) -> str:
    return html.escape(str(s))


def render_callout(payload: dict, bid: str, target: str) -> str:
    level = payload.get("level", "info")
    text = payload.get("text", "")
    if target == "tistory":
        color = {"check": "#2e9e5b", "warn": "#d4a84b", "danger": "#e85d4c",
                 "info": "#3db8a8"}.get(level, "#3db8a8")
        return (f'<div style="border-left:4px solid {color};padding:10px 16px;'
                f'margin:1.2em 0;border-radius:0 4px 4px 0;">{esc(text)}</div>')
    return (f'<div class="care care-callout care-{level}" data-id="{esc(bid)}">'
            f'<span class="care-callout-badge">{esc(level.upper())}</span>'
            f'<span class="care-callout-text">{esc(text)}</span></div>')


def render_threshold_table(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    rows = payload.get("rows", [])
    if target == "tistory":
        t = f'<p style="font-weight:600;margin:1.2em 0 .4em">{esc(title)}</p>'
        t += '<table style="border-collapse:collapse;width:100%;font-size:.92em">'
        t += '<thead><tr><th style="border:1px solid #888;padding:6px 10px">항목</th>' \
             '<th style="border:1px solid #888;padding:6px 10px">임계값</th>' \
             '<th style="border:1px solid #888;padding:6px 10px">조치</th></tr></thead><tbody>'
        for r in rows:
            t += f'<tr><td style="border:1px solid #888;padding:6px 10px">{esc(r.get("label",""))}</td>' \
                 f'<td style="border:1px solid #888;padding:6px 10px"><code>{esc(r.get("threshold",""))}</code></td>' \
                 f'<td style="border:1px solid #888;padding:6px 10px">{esc(r.get("action",""))}</td></tr>'
        return t + '</tbody></table>'
    cells = []
    for r in rows:
        lv = r.get("level", "info")
        cells.append(
            f'<tr class="lv-{esc(lv)}">'
            f'<td>{esc(r.get("label",""))}</td>'
            f'<td><code>{esc(r.get("threshold",""))}</code></td>'
            f'<td>{esc(r.get("action",""))}</td></tr>'
        )
    return (f'<figure class="care care-threshold" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>'
            f'<table><thead><tr><th>항목</th><th>임계값</th><th>조치</th></tr></thead>'
            f'<tbody>{"".join(cells)}</tbody></table></figure>')


def render_flow(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    by_id = {n.get("id"): n for n in nodes}
    # 순서: 첫 edge의 from부터 선형 체인, 사이클(뒤로 가는 edge)은 루프 노트로
    order: list[str] = []
    seen = set()
    if edges:
        for e in edges:
            for x in (e.get("from"), e.get("to")):
                if x and x not in seen:
                    seen.add(x)
                    order.append(x)
    else:
        order = [n.get("id") for n in nodes]
    if target == "tistory":
        parts = []
        for i, nid in enumerate(order):
            parts.append(esc(by_id.get(nid, {}).get("label", nid)))
            if i < len(order) - 1:
                parts.append("→")
        cycle = [e for e in edges if e.get("to") == order[0] if order]
        suffix = " ↺" if cycle else ""
        return (f'<p style="margin:1.2em 0"><strong>{esc(title)}</strong><br>'
                f'<code>{" ".join(parts)}{suffix}</code></p>')
    node_html = []
    for i, nid in enumerate(order):
        n = by_id.get(nid, {})
        kind = n.get("kind", "")
        node_html.append(
            f'<div class="care-node {esc(kind)}"><span class="care-node-label">'
            f'{esc(n.get("label", nid))}</span></div>'
        )
        if i < len(order) - 1:
            # 이 구간의 edge label
            lbl = next((e.get("label", "") for e in edges
                        if e.get("from") == nid and e.get("to") == order[i + 1]), "")
            node_html.append(
                f'<div class="care-edge"><span class="care-arrow">→</span>'
                f'<span class="care-edge-label">{esc(lbl)}</span></div>'
            )
    loop_html = ""
    if order:
        cycle = [e for e in edges if e.get("to") == order[0]]
        if cycle:
            loop_html = f'<div class="care-loop">↺ {esc(cycle[0].get("label", "다음 주기"))}</div>'
    return (f'<figure class="care care-flow" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>'
            f'<div class="care-flow-row">{"".join(node_html)}{loop_html}</div></figure>')


def render_bar_chart(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    bars = payload.get("bars", [])
    mx = max((b.get("value", 0) for b in bars), default=1) or 1
    if target == "tistory":
        rows = "".join(f'<li>{esc(b.get("label",""))}: {esc(b.get("value",0))}</li>' for b in bars)
        return f'<p style="font-weight:600">{esc(title)}</p><ul>{rows}</ul>'
    rows = []
    for b in bars:
        v = b.get("value", 0)
        rows.append(
            f'<div class="care-bar"><span class="care-bar-label">{esc(b.get("label",""))}</span>'
            f'<span class="care-bar-track"><span class="care-bar-fill" style="width:{v/mx*100:.1f}%"></span></span>'
            f'<span class="care-bar-val">{esc(v)}</span></div>'
        )
    return (f'<figure class="care care-bars" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>{"".join(rows)}</figure>')


def render_timeline(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    events = payload.get("events", [])
    if target == "tistory":
        rows = "".join(f'<li><strong>{esc(e.get("time",""))}</strong> — {esc(e.get("label",""))}'
                       + (f' <em>({esc(e.get("note",""))})</em>' if e.get("note") else "") + '</li>'
                       for e in events)
        return f'<p style="font-weight:600">{esc(title)}</p><ul>{rows}</ul>'
    rows = []
    for e in events:
        note = f'<span class="care-tl-note">{esc(e.get("note",""))}</span>' if e.get("note") else ""
        rows.append(f'<div class="care-tl-item"><span class="care-tl-time">{esc(e.get("time",""))}</span>'
                    f'<span class="care-tl-label">{esc(e.get("label",""))}{note}</span></div>')
    return (f'<figure class="care care-timeline" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>{"".join(rows)}</figure>')


def render_checklist(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    items = payload.get("items", [])
    if target == "tistory":
        rows = "".join(f'<li><label><input type="checkbox"> {esc(i)}</label></li>' for i in items)
        return f'<p style="font-weight:600">{esc(title)}</p><ul style="list-style:none;padding-left:0">{rows}</ul>'
    rows = "".join(
        f'<li><label><input type="checkbox" class="care-chk" data-id="{esc(bid)}"> {esc(i)}</label></li>'
        for i in items)
    return (f'<figure class="care care-checklist" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption><ul>{rows}</ul></figure>')


def render_demo(payload: dict, bid: str, target: str) -> str:
    desc = payload.get("desc", "")
    code = payload.get("code", "")
    if target == "tistory":
        return (f'<p style="font-weight:600">🔧 인터랙티브 데모</p>'
                f'<p>{esc(desc)}</p>'
                f'<p style="font-size:.85em">※ 이 데모는 GitHub Pages에서만 동작합니다. 코드:</p>'
                f'<pre style="overflow-x:auto;padding:12px;border:1px solid #888">{esc(code)}</pre>')
    return (f'<figure class="care care-demo" data-id="{esc(bid)}">'
            f'<figcaption>🔧 {esc(desc)}</figcaption>'
            f'<div class="care-demo-stage" id="demo-{esc(bid)}"></div></figure>')


RENDERERS = {
    "callout": render_callout,
    "threshold-table": render_threshold_table,
    "flow": render_flow,
    "bar-chart": render_bar_chart,
    "timeline": render_timeline,
    "checklist": render_checklist,
    "demo": render_demo,
}

# Pages 전용 care 컴포넌트 CSS (shell의 design tokens 사용)
CARE_CSS = """
.care{margin:1.4em 0}
.care figcaption{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-mute);margin-bottom:.6em}
/* callout */
.care-callout{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border:1px solid var(--rule2);border-left:3px solid var(--accent);background:var(--paper-2)}
.care-callout-badge{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;padding:3px 7px;border-radius:2px;background:var(--accent);color:#0a0908;font-weight:600;flex:none;margin-top:2px}
.care-callout.care-warn{border-left-color:var(--gold)}
.care-callout.care-warn .care-callout-badge{background:var(--gold)}
.care-callout.care-danger{border-left-color:#e85d4c}
.care-callout.care-danger .care-callout-badge{background:#e85d4c}
.care-callout.care-check{border-left-color:#2e9e5b}
.care-callout.care-check .care-callout-badge{background:#2e9e5b}
.care-callout-text{color:var(--ink-dim);font-weight:300}
/* threshold table */
.care-threshold table{width:100%;border-collapse:collapse;font-size:.88rem}
.care-threshold th,.care-threshold td{border:1px solid var(--rule);padding:8px 10px;text-align:left;vertical-align:top}
.care-threshold th{background:var(--paper-3);color:var(--ink-mute);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase}
.care-threshold code{font-family:var(--mono);font-size:.85em;color:var(--accent)}
.care-threshold tr.lv-urgent td:first-child{border-left:3px solid #e85d4c}
.care-threshold tr.lv-warning td:first-child{border-left:3px solid var(--gold)}
.care-threshold tr.lv-info td:first-child{border-left:3px solid var(--accent)}
/* flow */
.care-flow-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.care-node{padding:10px 14px;border:1px solid var(--rule2);border-radius:4px;background:var(--paper-3);font-size:.85rem}
.care-node.start{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.care-node-label{font-family:var(--sans);font-weight:500}
.care-edge{display:flex;flex-direction:column;align-items:center;gap:2px;color:var(--ink-mute)}
.care-arrow{color:var(--accent);font-size:1.1rem}
.care-edge-label{font-size:.68rem;color:var(--ink-mute);white-space:nowrap}
.care-loop{margin-left:6px;padding:6px 10px;border:1px dashed var(--rule2);border-radius:999px;font-size:.75rem;color:var(--accent)}
/* bars */
.care-bar{display:flex;align-items:center;gap:10px;margin:.5em 0}
.care-bar-label{width:9em;flex:none;font-size:.82rem;color:var(--ink-dim)}
.care-bar-track{flex:1;height:14px;background:var(--paper-3);border:1px solid var(--rule);border-radius:2px;overflow:hidden}
.care-bar-fill{display:block;height:100%;background:var(--accent)}
.care-bar-val{width:3em;text-align:right;font-family:var(--mono);font-size:.78rem;color:var(--accent)}
/* timeline */
.care-timeline{border-left:1px solid var(--rule2);margin-left:6px;padding-left:16px}
.care-tl-item{position:relative;margin:.7em 0}
.care-tl-item::before{content:"";position:absolute;left:-21px;top:.4em;width:9px;height:9px;border-radius:50%;background:var(--accent)}
.care-tl-time{font-family:var(--mono);font-size:.72rem;color:var(--accent);margin-right:8px}
.care-tl-label{color:var(--ink-dim)}
.care-tl-note{color:var(--ink-mute);font-size:.8rem;margin-left:6px}
/* checklist */
.care-checklist ul{list-style:none;padding-left:0}
.care-checklist li{margin:.4em 0}
.care-checklist input{margin-right:8px;accent-color:var(--accent)}
.care-checklist input:checked + *{text-decoration:line-through;opacity:.55}
"""

CARE_JS = """
(() => {
  // checklist persistence (Pages)
  document.querySelectorAll('.care-checklist').forEach(fig => {
    const id = fig.dataset.id; const key = 'care-chk-' + id;
    const saved = JSON.parse(localStorage.getItem(key) || '[]');
    fig.querySelectorAll('input.care-chk').forEach((c, i) => { c.checked = saved[i] || false; });
    fig.addEventListener('change', () => {
      localStorage.setItem(key, JSON.stringify([...fig.querySelectorAll('input.care-chk')].map(c => c.checked)));
    });
  });
})();
"""


# ── 티스토리용 자체완결 다크 셸 ────────────────────────────────────────────────
# Pages 와 같은 .care 컴포넌트를 쓰되, 스킨의 :root 토큰에 의존하지 않도록
# .care-post 스코프에 디자인 토큰(다크 골드/틸)을 직접 선언한다.
# @import 는 실패해도 시스템 폰트 폴백으로 우아하게 깨진다.
TISTORY_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,400&family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400&display=swap');
.care-post{
  --ink:#f4efe6; --ink-dim:#c9bdac; --ink-mute:#8d8376;
  --paper:#0a0908; --paper-2:#14120f; --paper-3:#1d1a16;
  --rule:rgba(244,239,230,.10); --rule2:rgba(244,239,230,.20);
  --accent:#3db8a8; --gold:#d4a84b; --gold2:#f0c75e; --coral:#e85d4c;
  --serif:'Cormorant Garamond',Georgia,'Noto Serif KR',serif;
  --sans:'Noto Sans KR',-apple-system,'Apple SD Gothic Neo',Malgun Gothic,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;
  display:block; max-width:720px; margin:0 auto; padding:30px 22px 44px;
  background:var(--paper); color:var(--ink);
  font-family:var(--sans); font-size:15px; line-height:1.85; font-weight:300;
  border-radius:16px; box-shadow:0 12px 44px rgba(0,0,0,.4);
  word-break:keep-all; overflow-wrap:break-word;
}
.care-post *{box-sizing:border-box}
.care-kicker{font-size:.72rem; letter-spacing:.16em; text-transform:uppercase; color:var(--accent); font-weight:600; margin-bottom:12px}
.care-deck{color:var(--ink-dim); font-weight:300; font-size:1.02rem; border-left:2px solid var(--accent); padding-left:14px; margin:0 0 24px}
.care-post h2{font-family:var(--serif); font-size:1.45rem; font-weight:600; color:var(--ink); letter-spacing:-.01em; margin:2.2em 0 .7em; padding-top:.55em; border-top:1px solid var(--rule)}
.care-post h3{font-size:1.05rem; font-weight:500; color:var(--ink); margin:1.4em 0 .5em}
.care-post p{margin:0 0 1em; color:var(--ink-dim)}
.care-post strong{color:var(--ink); font-weight:600}
.care-post em{font-style:normal; color:var(--ink-mute)}
.care-post a{color:var(--gold2); text-decoration:none}
.care-post ul,.care-post ol{margin:0 0 1.2em 1.4em; padding:0}
.care-post li{margin:.35em 0; color:var(--ink-dim)}
.care-post code{font-family:var(--mono); font-size:.86em; color:var(--gold2); background:var(--paper-3); padding:2px 6px; border-radius:4px}
.care-post pre{background:var(--paper-2); border:1px solid var(--rule); padding:14px 16px; overflow-x:auto; margin:1.2em 0; border-radius:8px; font-size:.84rem}
.care-post pre code{background:none; padding:0; color:var(--ink-dim)}
.care-post blockquote{border-left:2px solid var(--accent); padding:10px 16px; color:var(--ink-dim); margin:1.4em 0; background:var(--paper-2)}
.care-post table{width:100%; border-collapse:collapse; font-size:.9rem; margin:1.2em 0}
.care-post th,.care-post td{border:1px solid var(--rule); padding:9px 12px; text-align:left; vertical-align:top}
.care-post th{background:var(--paper-3); color:var(--ink-mute); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; font-weight:500}
""" + CARE_CSS + """
</style>
"""


def render_blocks(body: str, target: str) -> tuple[str, list[str]]:
    """care 블록을 컴포넌트 HTML로 치환. (변환된 본문, 사용된 블록 id 목록) 반환."""
    blocks: list[dict] = []
    counter = 0

    def repl(m: re.Match) -> str:
        nonlocal counter
        try:
            payload = yaml.safe_load(m.group("payload")) or {}
        except yaml.YAMLError:
            payload = {}
        bid = m.group("id")
        blocks.append({"type": m.group("type"), "id": bid, "payload": payload})
        token = f"<!--CAREBLOCK{counter}-->"
        counter += 1
        return token

    body_no_blocks = BLOCK_RE.sub(repl, body)
    MD.reset()
    html_out = MD.convert(body_no_blocks)
    for i, b in enumerate(blocks):
        r = RENDERERS.get(b["type"])
        component = r(b["payload"], b["id"], target) if r else ""
        html_out = html_out.replace(f"<!--CAREBLOCK{i}-->", component)
    return html_out, [b["id"] for b in blocks]


def tistory_post_json(fm: dict, body_html: str, slug: str) -> dict:
    """post.py 입력 형식의 티스토리 발행 JSON."""
    return {
        "account": "mynote",
        "blog": "mynote11605",
        "title": fm.get("title", slug),
        "content": body_html,
        "tags": ["돌봄데몬", fm.get("type", "")],
        "category": str(fm.get("category", "")),
        "category_id": int(fm.get("category_id", 0)),
        "visibility": "private",  # 리뷰 전 기본 비공개
    }


def build_one(md_path: Path, *, pages: bool = True, tistory: bool = True) -> None:
    text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # body에서 h1(제목 중복) 제거
    body = re.sub(r"^#\s+.*$", "", body, count=1, flags=re.M).strip()

    # 상대 경로 & 출력 경로
    rel = md_path.relative_to(HELANA_LOG) if HELANA_LOG in md_path.parents else md_path
    slug = md_path.stem
    etype = md_path.parent.name  # manifesto|track|dialogue|solution

    if pages:
        pages_body, _ = render_blocks(body, "pages")
        depth = len(rel.parts) - 1
        rel_home = "../" * depth if depth > 0 else "./"
        title = fm.get("title", slug)
        deck = fm.get("answer", "")
        src = str(rel).replace("\\", "/")
        out = md_path.with_suffix(".html")
        page = shell(BRAND, title, deck, pages_body, src, rel_home=rel_home)
        # care CSS/JS 주입 (</style> 앞 / </body> 앞)
        page = page.replace("</style>", CARE_CSS + "</style>", 1)
        page = page.replace("</body>", f"<script>{CARE_JS}</script></body>", 1)
        out.write_text(page, encoding="utf-8")
        print(f"  [pages]   {out.relative_to(HELANA_LOG)}")

    if tistory:
        # Pages 와 동일한 풀 .care 컴포넌트(배지/색상행/플로우/타임라인/체크)를 렌더하고,
        # 자체완결 다크 셸(.care-post + <style>)로 감싼다. kicker + deck(answer) 로 헤드 구성.
        tbody, _ = render_blocks(body, "pages")
        deck = esc(fm.get("answer", ""))
        lead = '<div class="care-kicker">돌봄 데몬 · Care</div>'
        if deck:
            lead += f'<p class="care-deck">{deck}</p>'
        article = f'<div class="care-post">\n{TISTORY_STYLE}\n{lead}\n{tbody}\n</div>'
        post = tistory_post_json(fm, article, slug)
        POSTS_DIR.mkdir(parents=True, exist_ok=True)
        post_path = POSTS_DIR / f"{slug}.json"
        post_path.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [tistory] {post_path.relative_to(BASE)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="돌봄 데몬 원고 → 페어 빌드")
    ap.add_argument("path", nargs="?", help="원고 md 경로")
    ap.add_argument("--all", action="store_true", help="care-daemon/ 전체 원고 빌드")
    ap.add_argument("--pages-only", action="store_true")
    ap.add_argument("--tistory-only", action="store_true")
    args = ap.parse_args()

    if args.all:
        mds = sorted(p for p in CARE_ROOT.rglob("*.md") if "_templates" not in str(p))
        if not mds:
            print("원고 없음")
            return 0
        for p in mds:
            print(f"빌드 {p.relative_to(HELANA_LOG)}")
            build_one(p, pages=not args.tistory_only, tistory=not args.pages_only)
        return 0

    if not args.path:
        ap.error("원고 경로 또는 --all 필요")
    p = Path(args.path).resolve()
    if not p.exists():
        print(f"없음: {p}")
        return 1
    build_one(p, pages=not args.tistory_only, tistory=not args.pages_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
care_pair_build.py — 돌봄 데몬 원고 → 페어(티스토리 + GitHub Pages) 동시 빌드.

"항상 페어로" 원칙의 실행기. 원고 md 하나에서:
  1. GitHub Pages html  → helana_log/docs/care-daemon/{type}/{NN}-{slug}.html
  2. 티스토리 발행 본문  → tistory-naver/posts/{NN}-{slug}.json  (post.py/republish 입력)

두 타깃 모두 Boss 요구(Boss 2026-08-14 "반드시 아코디언·인포그래픽·JS 전부")를 충족:
  - 아코디언    : 티스토리 = <details><summary>(네이티브, JS 없이 동작)
                  Pages   = runtime JS 로 <h2> 를 .sec 접이식 섹션으로 감싼다
  - 인포그래픽  : 상단에 인라인 SVG 다이어그램(섹션 플로우) 자동 생성
  - 복붙 블록   : <pre><code> + 복사 버튼(<button class="care-copy">) + JS
  - 테이블      : 경계선을 뚜렷하게(인라인/!important) — "테이블 보이지도 않아" 대응

care 블록(```care type= id= + YAML)은 두 타깃에서 렌더:
  - pages  : 인터랙티브 클래스형(.care-*) — shell 디자인 토큰 사용
  - tistory: 자체완결 다크 인라인 스타일 — 스킨 무관, 경계선 선명

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

BASE = Path(__file__).resolve().parents[1]  # /root/work (bayaba_phone)
sys.path.insert(0, str(BASE / "scripts"))
from build_satellite_docs_Grok import shell, MD, BRANDS  # noqa: E402

HELANA_LOG = BASE / "helana_log"
CARE_ROOT = HELANA_LOG / "docs" / "care-daemon"
POSTS_DIR = BASE / "tistory-naver" / "posts"

BRAND = BRANDS["helana_log"]
# 돌봄 데몬 채널 전용 kicker
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


def esc(s: str) -> str:
    return html.escape(str(s))


# ── 티스토리 인라인 다크 팔레트 ─────────────────────────────────────────────
T = {
    "ink": "#f4efe6", "dim": "#c9bdac", "mute": "#8d8376",
    "paper": "#0a0908", "paper2": "#14120f", "paper3": "#1d1a16",
    "line": "#3a342c", "line2": "#4a423a", "thbg": "#221d17",
    "accent": "#3db8a8", "gold": "#d4a84b", "gold2": "#f0c75e",
    "coral": "#e85d4c", "green": "#2e9e5b",
}
LEVEL_COLOR = {"check": "#2e9e5b", "warn": "#d4a84b", "danger": "#e85d4c",
               "info": "#3db8a8", "urgent": "#e85d4c", "warning": "#d4a84b"}
_MONO = "ui-monospace,'JetBrains Mono',Menlo,Consolas,monospace"


# ── 컴포넌트 렌더러 (target: pages | tistory) ───────────────────────────────
def render_callout(payload: dict, bid: str, target: str) -> str:
    level = payload.get("level", "info")
    text = payload.get("text", "")
    if target == "tistory":
        color = LEVEL_COLOR.get(level, T["accent"])
        return (f'<div style="display:flex;gap:10px;align-items:flex-start;'
                f'padding:13px 16px;margin:1.4em 0;border:1px solid {T["line2"]};'
                f'border-left:3px solid {color};background:{T["paper2"]};'
                f'border-radius:0 8px 8px 0">'
                f'<span style="flex:none;font-size:.6rem;letter-spacing:.12em;'
                f'padding:3px 8px;border-radius:3px;background:{color};color:#0a0908;'
                f'font-weight:700;margin-top:2px">{esc(level.upper())}</span>'
                f'<span style="color:{T["dim"]};font-weight:300;line-height:1.75">{esc(text)}</span></div>')
    return (f'<div class="care care-callout care-{level}" data-id="{esc(bid)}">'
            f'<span class="care-callout-badge">{esc(level.upper())}</span>'
            f'<span class="care-callout-text">{esc(text)}</span></div>')


def _t_caption(title: str) -> str:
    return (f'<p style="font-weight:700;margin:1.5em 0 .5em;color:{T["gold"]};'
            f'font-size:.74rem;letter-spacing:.1em;text-transform:uppercase">{esc(title)}</p>')


def render_threshold_table(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    rows = payload.get("rows", [])
    if target == "tistory":
        th = (f'border:1px solid {T["line2"]};background:{T["thbg"]};color:{T["gold"]};'
              f'padding:10px 12px;text-align:left;font-size:.72rem;letter-spacing:.06em;'
              f'text-transform:uppercase;font-weight:600')
        body = ""
        for r in rows:
            lv = r.get("level", "info")
            lc = LEVEL_COLOR.get(lv, T["accent"])
            body += (f'<tr>'
                     f'<td style="border:1px solid {T["line2"]};border-left:3px solid {lc};'
                     f'padding:10px 12px;color:{T["ink"]};font-weight:500">{esc(r.get("label", ""))}</td>'
                     f'<td style="border:1px solid {T["line2"]};padding:10px 12px">'
                     f'<code style="font-family:{_MONO};font-size:.82em;color:{T["gold2"]};'
                     f'background:{T["paper3"]};padding:2px 7px;border-radius:4px">{esc(r.get("threshold", ""))}</code></td>'
                     f'<td style="border:1px solid {T["line2"]};padding:10px 12px;color:{T["dim"]}">{esc(r.get("action", ""))}</td>'
                     f'</tr>')
        return (_t_caption(title)
                + f'<table style="width:100%;border-collapse:collapse;font-size:.9rem;margin:.4em 0 1.4em">'
                + f'<thead><tr><th style="{th}">항목</th><th style="{th}">임계값</th><th style="{th}">조치</th></tr></thead>'
                + f'<tbody>{body}</tbody></table>')
    cells = []
    for r in rows:
        lv = r.get("level", "info")
        cells.append(
            f'<tr class="lv-{esc(lv)}">'
            f'<td>{esc(r.get("label", ""))}</td>'
            f'<td><code>{esc(r.get("threshold", ""))}</code></td>'
            f'<td>{esc(r.get("action", ""))}</td></tr>'
        )
    return (f'<figure class="care care-threshold" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>'
            f'<table><thead><tr><th>항목</th><th>임계값</th><th>조치</th></tr></thead>'
            f'<tbody>{"".join(cells)}</tbody></table></figure>')


def _flow_order(nodes: list, edges: list) -> list[str]:
    by_id = {n.get("id"): n for n in nodes}
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
    return order


def render_flow(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    by_id = {n.get("id"): n for n in nodes}
    order = _flow_order(nodes, edges)
    if target == "tistory":
        parts = []
        for i, nid in enumerate(order):
            n = by_id.get(nid, {})
            kind = n.get("kind", "")
            border = T["accent"] if kind == "start" else T["line2"]
            parts.append(f'<span style="padding:9px 14px;border:1px solid {border};'
                         f'border-radius:5px;background:{T["paper3"]};color:{T["ink"]};'
                         f'font-size:.86rem;font-weight:500;white-space:nowrap">{esc(n.get("label", nid))}</span>')
            if i < len(order) - 1:
                lbl = next((e.get("label", "") for e in edges
                            if e.get("from") == nid and e.get("to") == order[i + 1]), "")
                parts.append(f'<span style="color:{T["accent"]};font-weight:700;font-size:1rem">→</span>'
                             + (f'<span style="font-size:.7rem;color:{T["mute"]}">{esc(lbl)}</span>' if lbl else ""))
        loop = [e for e in edges if e.get("to") == order[0]] if order else []
        loop_html = (f'<span style="padding:5px 12px;border:1px dashed {T["line2"]};'
                     f'border-radius:999px;font-size:.74rem;color:{T["accent"]}">'
                     f'↺ {esc(loop[0].get("label", "다음 주기"))}</span>' if loop else "")
        return (_t_caption(title)
                + f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:.4em 0 1.4em">'
                + "".join(parts) + loop_html + "</div>")
    node_html = []
    for i, nid in enumerate(order):
        n = by_id.get(nid, {})
        kind = n.get("kind", "")
        node_html.append(
            f'<div class="care-node {esc(kind)}"><span class="care-node-label">'
            f'{esc(n.get("label", nid))}</span></div>'
        )
        if i < len(order) - 1:
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
        rows = ""
        for b in bars:
            v = b.get("value", 0)
            rows += (f'<div style="display:flex;align-items:center;gap:10px;margin:.5em 0">'
                     f'<span style="width:9em;flex:none;font-size:.82rem;color:{T["dim"]}">{esc(b.get("label", ""))}</span>'
                     f'<span style="flex:1;height:14px;background:{T["paper3"]};border:1px solid {T["line2"]};border-radius:2px;overflow:hidden">'
                     f'<span style="display:block;height:100%;background:{T["accent"]};width:{v/mx*100:.1f}%"></span></span>'
                     f'<span style="width:3em;text-align:right;font-family:{_MONO};font-size:.78rem;color:{T["accent"]}">{esc(v)}</span></div>')
        return _t_caption(title) + f'<div style="margin:.4em 0 1.4em">{rows}</div>'
    rows = []
    for b in bars:
        v = b.get("value", 0)
        rows.append(
            f'<div class="care-bar"><span class="care-bar-label">{esc(b.get("label", ""))}</span>'
            f'<span class="care-bar-track"><span class="care-bar-fill" style="width:{v/mx*100:.1f}%"></span></span>'
            f'<span class="care-bar-val">{esc(v)}</span></div>'
        )
    return (f'<figure class="care care-bars" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>{"".join(rows)}</figure>')


def render_timeline(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    events = payload.get("events", [])
    if target == "tistory":
        rows = ""
        for e in events:
            note = (f'<span style="color:{T["mute"]};font-size:.8rem">({esc(e.get("note", ""))})</span>'
                    if e.get("note") else "")
            rows += (f'<div style="position:relative;margin:.75em 0;padding-left:16px">'
                     f'<span style="position:absolute;left:-5px;top:.45em;width:9px;height:9px;'
                     f'border-radius:50%;background:{T["accent"]}"></span>'
                     f'<span style="font-family:{_MONO};font-size:.74rem;color:{T["accent"]};'
                     f'font-weight:600;margin-right:8px">{esc(e.get("time", ""))}</span>'
                     f'<span style="color:{T["dim"]}">{esc(e.get("label", ""))}</span> {note}</div>')
        return (_t_caption(title)
                + f'<div style="border-left:1px solid {T["line2"]};margin-left:5px;'
                f'padding-left:18px;margin-top:.5em;margin-bottom:1.4em">{rows}</div>')
    rows = []
    for e in events:
        note = f'<span class="care-tl-note">{esc(e.get("note", ""))}</span>' if e.get("note") else ""
        rows.append(f'<div class="care-tl-item"><span class="care-tl-time">{esc(e.get("time", ""))}</span>'
                    f'<span class="care-tl-label">{esc(e.get("label", ""))}{note}</span></div>')
    return (f'<figure class="care care-timeline" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption>{"".join(rows)}</figure>')


def render_checklist(payload: dict, bid: str, target: str) -> str:
    title = payload.get("title", "")
    items = payload.get("items", [])
    if target == "tistory":
        rows = "".join(
            f'<li style="margin:.45em 0;color:{T["dim"]}"><label>'
            f'<input type="checkbox" style="accent-color:{T["accent"]};margin-right:9px"> {esc(i)}</label></li>'
            for i in items)
        return (_t_caption(title)
                + f'<ul style="list-style:none;padding:0 0 0 4px;margin:.4em 0 1.4em">{rows}</ul>')
    rows = "".join(
        f'<li><label><input type="checkbox" class="care-chk" data-id="{esc(bid)}"> {esc(i)}</label></li>'
        for i in items)
    return (f'<figure class="care care-checklist" data-id="{esc(bid)}">'
            f'<figcaption>{esc(title)}</figcaption><ul>{rows}</ul></figure>')


def render_demo(payload: dict, bid: str, target: str) -> str:
    desc = payload.get("desc", "")
    code = payload.get("code", "")
    if target == "tistory":
        return (f'<div style="border:1px dashed {T["line2"]};padding:14px 16px;margin:1.4em 0;border-radius:8px">'
                f'<p style="color:{T["gold"]};font-weight:700;margin:0 0 6px">🔧 인터랙티브 데모</p>'
                f'<p style="color:{T["dim"]};margin:0 0 10px">{esc(desc)}</p>'
                f'<pre style="overflow-x:auto;padding:12px;border:1px solid {T["line2"]};'
                f'background:{T["paper2"]};border-radius:6px;margin:0;font-size:.82rem">'
                f'<code style="font-family:{_MONO};color:{T["dim"]}">{esc(code)}</code></pre></div>')
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


# ── 복사 버튼 ────────────────────────────────────────────────────────────────
def _code_copy(html_str: str) -> str:
    """<pre><code> 블록에 복사 버튼을 붙인다 (JS 로 textContent 를 읽어 복사)."""
    def repl(m: re.Match) -> str:
        attrs, code = m.group(1), m.group(2)
        return (f'<div class="care-code"><button class="care-copy" type="button" '
                f'title="코드 복사">복사</button><pre><code{attrs}>{code}</code></pre></div>')
    return re.sub(r"<pre><code([^>]*)>(.*?)</code></pre>", repl, html_str, flags=re.DOTALL)


# ── H2 분할 (아코디언 섹션) ──────────────────────────────────────────────────
def _split_h2(body: str) -> tuple[str, list[tuple[str, str]]]:
    """본문을 (intro, [(제목, 내용), ...]) 로 분할. intro = 첫 H2 이전 텍스트."""
    lines = body.splitlines()
    intro: list[str] = []
    sections: list[tuple[str, str]] = []
    cur_title: str | None = None
    cur: list[str] = []
    for ln in lines:
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            if cur_title is None:
                intro = cur
            else:
                sections.append((cur_title, "\n".join(cur)))
            cur_title = m.group(1)
            cur = []
        else:
            cur.append(ln)
    if cur_title is not None:
        sections.append((cur_title, "\n".join(cur)))
    return "\n".join(intro), sections


# ── 인포그래픽 (HTML/CSS 인라인 — 티스토리 SVG 제거 대응) ─────────────────────
def build_infographic(title: str, subtitle: str, sections: list[str]) -> str:
    n = max(len(sections), 1)
    MONO = "ui-monospace,'JetBrains Mono',Menlo,Consolas,monospace"
    SERIF = "'Cormorant Garamond',Georgia,'Noto Serif KR',serif"

    bar = (f'<div style="height:4px;'
           f'background:linear-gradient(90deg,{T["gold"]},{T["accent"]})"></div>')
    top = (f'<div style="display:flex;justify-content:space-between;align-items:center;'
           f'gap:10px;padding:16px 22px 0">'
           f'<span style="font-size:11px;font-weight:700;letter-spacing:2px;'
           f'color:{T["accent"]};text-transform:uppercase">CARE DAEMON · 돌봄 데몬</span>'
           f'<span style="font-size:12px;font-weight:700;letter-spacing:1px;'
           f'color:{T["gold"]};white-space:nowrap">{n} SECTION</span></div>')
    title_div = (f'<div style="padding:8px 22px 0;font-family:{SERIF};font-size:23px;'
                 f'font-weight:700;color:{T["ink"]};line-height:1.3">'
                 f'{esc(_clip(title, 44))}</div>')
    sub_div = (f'<div style="padding:6px 22px 0;font-size:12.5px;color:{T["mute"]};'
               f'line-height:1.6">{esc(_clip(subtitle, 72))}</div>' if subtitle else '')

    rows = []
    for i, sec in enumerate(sections):
        rows.append(
            f'<div style="display:flex;align-items:center;gap:14px;padding:7px 0">'
            f'<span style="flex:none;width:28px;height:28px;border-radius:50%;'
            f'background:rgba(61,184,168,.18);border:1px solid rgba(61,184,168,.35);'
            f'color:{T["gold"]};font-family:{MONO};font-size:13px;font-weight:700;'
            f'display:flex;align-items:center;justify-content:center">{i + 1}</span>'
            f'<span style="flex:1;background:{T["paper3"]};border:1px solid {T["line"]};'
            f'border-radius:8px;padding:8px 12px;font-size:13.5px;color:{T["dim"]}">'
            f'{esc(_clip(sec, 42))}</span></div>')
        if i < n - 1:
            rows.append(
                f'<div style="width:2px;height:12px;margin-left:13px;'
                f'background:{T["mute"]};position:relative"></div>')

    flow = '<div style="padding:14px 22px 20px">' + "\n".join(rows) + '</div>'
    inner = (f'<div style="background:{T["paper2"]};border:1px solid {T["line2"]};'
             f'border-radius:12px;overflow:hidden">{bar}{top}{title_div}{sub_div}{flow}</div>')
    return f'<figure class="care-info" style="margin:0 0 22px">{inner}</figure>'


def _clip(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ── Pages 전용 care 컴포넌트 CSS (shell 의 디자인 토큰 사용) ─────────────────
CARE_CSS = """
.care{margin:1.4em 0}
.care figcaption{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-mute);margin-bottom:.6em}
.care-info{margin:0 0 22px}
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
/* 복사 블록 */
.care-code{position:relative;margin:1.2em 0}
.care-code pre{background:var(--paper-2);border:1px solid var(--rule2);padding:16px;padding-top:34px;border-radius:8px;overflow-x:auto;margin:0}
.care-code code{font-family:var(--mono);font-size:.82rem;color:var(--gold2);background:none;padding:0}
.care-copy{position:absolute;top:8px;right:8px;border:1px solid var(--rule2);background:var(--paper-3);color:var(--ink-dim);font-size:11px;font-family:var(--sans);padding:4px 11px;border-radius:6px;cursor:pointer}
.care-copy:hover{color:var(--ink);border-color:var(--accent)}
/* 테이블 가독성 강화 (Boss: "테이블 보이지도 않아" 대응) */
.prose table,.care-threshold table{border-collapse:collapse}
.prose th,.prose td,.care-threshold th,.care-threshold td{border:1px solid color-mix(in srgb,var(--ink) 32%,transparent)!important}
.prose th,.care-threshold th{background:var(--paper-3)!important;color:var(--gold)!important}
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
  // 코드 복사 (Pages)
  function fallbackCopy(txt, done){ var ta=document.createElement('textarea'); ta.value=txt; document.body.appendChild(ta); ta.select(); try{document.execCommand('copy')}catch(e){} document.body.removeChild(ta); done(); }
  document.querySelectorAll('.care-copy').forEach(b => {
    b.addEventListener('click', () => {
      var code = b.parentNode.querySelector('pre code');
      if (!code) return;
      var txt = code.innerText;
      var done = function(){ b.textContent='복사됨'; setTimeout(function(){ b.textContent='복사'; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(done).catch(function(){ fallbackCopy(txt, done); });
      } else { fallbackCopy(txt, done); }
    });
  });
})();
"""


# ── 티스토리용 자체완결 다크 셸 ──────────────────────────────────────────────
# .care-post 스코프에 디자인 토큰을 직접 선언(스킨 :root 불신). 경계선·본문
# 대비는 뚜렷하게, 아코디언(<details>)·복사버튼·툴바·테이블 모두 자체 스타일.
TISTORY_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,400&family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400&display=swap');
.care-post{
  --ink:#f4efe6; --ink-dim:#c9bdac; --ink-mute:#8d8376;
  --paper:#0a0908; --paper-2:#14120f; --paper-3:#1d1a16;
  --rule:#3a342c; --rule2:#4a423a;
  --accent:#3db8a8; --gold:#d4a84b; --gold2:#f0c75e; --coral:#e85d4c;
  --serif:'Cormorant Garamond',Georgia,'Noto Serif KR',serif;
  --sans:'Noto Sans KR',-apple-system,'Apple SD Gothic Neo',Malgun Gothic,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;
  display:block; max-width:740px; margin:0 auto; padding:34px 26px 48px;
  background:var(--paper); color:var(--ink);
  font-family:var(--sans); font-size:15.5px; line-height:1.9; font-weight:400;
  border-radius:16px; box-shadow:0 14px 48px rgba(0,0,0,.45);
  word-break:keep-all; overflow-wrap:break-word;
}
.care-post *{box-sizing:border-box}
.care-kicker{font-size:.74rem; letter-spacing:.18em; text-transform:uppercase; color:var(--accent); font-weight:700; display:inline-block; margin:0 10px 0 0; vertical-align:2px}
.care-deck{color:var(--ink-dim); font-weight:300; font-size:1.05rem; line-height:1.8; border-left:3px solid var(--accent); padding-left:14px; margin:0 0 22px}
.care-post h2{font-family:var(--serif); font-size:1.5rem; font-weight:600; color:var(--ink); letter-spacing:-.01em; margin:2em 0 .7em; padding-top:.5em; border-top:1px solid var(--rule)}
.care-post h3{font-size:1.08rem; font-weight:600; color:var(--ink); margin:1.5em 0 .5em}
.care-post p{margin:0 0 1em; color:var(--ink-dim); font-weight:400}
.care-post strong{color:var(--ink); font-weight:700}
.care-post em{font-style:normal; color:var(--ink-mute)}
.care-post a{color:var(--gold2); text-decoration:none}
.care-post ul,.care-post ol{margin:0 0 1.2em 1.5em; padding:0}
.care-post li{margin:.4em 0; color:var(--ink-dim)}
.care-post code{font-family:var(--mono); font-size:.86em; color:var(--gold2); background:var(--paper-3); padding:2px 6px; border-radius:4px}
.care-post pre{background:var(--paper-2); border:1px solid var(--rule2); padding:14px 16px; overflow-x:auto; margin:1.2em 0; border-radius:8px; font-size:.84rem}
.care-post pre code{background:none; padding:0; color:var(--ink-dim)}
.care-post blockquote{border-left:3px solid var(--accent); padding:10px 16px; color:var(--ink-dim); margin:1.4em 0; background:var(--paper-2); border-radius:0 8px 8px 0}
/* 테이블 — 경계선 선명(스킨 override 무력화) */
.care-post table{width:100%; border-collapse:collapse !important; font-size:.9rem; margin:1.2em 0}
.care-post th,.care-post td{border:1px solid var(--rule2) !important; padding:10px 12px; text-align:left; vertical-align:top}
.care-post th{background:var(--paper-3) !important; color:var(--gold) !important; font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; font-weight:600}
/* 인포그래픽 */
.care-info{margin:0 0 24px}
/* 툴바 */
.care-toolbar{display:flex; gap:8px; margin:0 0 16px; flex-wrap:wrap}
.care-btn{appearance:none; border:1px solid var(--rule2); background:var(--paper-2); color:var(--ink-dim); font-size:12.5px; font-weight:600; padding:8px 16px; border-radius:999px; cursor:pointer; font-family:var(--sans); letter-spacing:.02em}
.care-btn:hover{background:var(--accent); color:#0a0908; border-color:var(--accent)}
/* 아코디언 */
.care-acc{border:1px solid var(--rule2) !important; border-radius:10px; margin:12px 0; background:var(--paper-2) !important; overflow:hidden}
.care-acc>summary{cursor:pointer; padding:15px 18px; font-family:var(--serif); font-weight:600; font-size:1.18rem; color:var(--ink); list-style:none !important; display:flex !important; align-items:center; gap:10px; background:var(--paper-2)}
.care-acc>summary::-webkit-details-marker{display:none}
.care-acc>summary::before{content:"▸"; color:var(--accent); font-size:14px; font-weight:700; transition:transform .18s; flex:none}
.care-acc[open]>summary::before{transform:rotate(90deg)}
.care-acc>summary:hover{color:var(--accent)}
.care-acc-body{padding:2px 20px 18px; border-top:1px solid var(--rule)}
/* 복사 블록 */
.care-code{position:relative; margin:1.2em 0}
.care-code pre{background:var(--paper-2); border:1px solid var(--rule2); padding:16px; padding-top:36px; border-radius:8px; overflow-x:auto; margin:0; font-size:.83rem}
.care-code code{font-family:var(--mono); font-size:.83rem; color:var(--gold2); background:none; padding:0}
.care-copy{position:absolute; top:8px; right:8px; border:1px solid var(--rule2); background:var(--paper-3); color:var(--ink-dim); font-size:11px; font-family:var(--sans); padding:4px 11px; border-radius:6px; cursor:pointer}
.care-copy:hover{color:var(--ink); border-color:var(--accent)}
</style>
"""

TISTORY_SCRIPT = """
<script>
(function(){
  function qs(sel){return Array.prototype.slice.call(document.querySelectorAll(sel))}
  qs('[data-care="expand"]').forEach(function(b){
    b.addEventListener('click',function(){qs('details.care-acc').forEach(function(d){d.open=true})})
  });
  qs('[data-care="collapse"]').forEach(function(b){
    b.addEventListener('click',function(){qs('details.care-acc').forEach(function(d){d.open=false})})
  });
  function fallback(txt, done){var ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(ta);done()}
  qs('.care-copy').forEach(function(b){
    b.addEventListener('click',function(){
      var code=b.parentNode.querySelector('pre code'); if(!code)return;
      var txt=code.innerText;
      var done=function(){b.textContent='복사됨';setTimeout(function(){b.textContent='복사'},1500)};
      if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(done).catch(function(){fallback(txt,done)})}
      else{fallback(txt,done)}
    })
  });
})();
</script>
"""


def render_tistory_article(fm: dict, intro_text: str, sections: list[tuple[str, str]],
                           titles: list[str]) -> str:
    """티스토리 본문: kicker+deck → 인포그래픽 → 툴바 → intro → 아코디언 → JS."""
    intro_html, _ = render_blocks(intro_text, "tistory") if intro_text.strip() else ("", [])
    intro_html = _code_copy(intro_html)

    acc = []
    for i, (t, content) in enumerate(sections):
        sec_html, _ = render_blocks(content, "tistory")
        sec_html = _code_copy(sec_html)
        open_attr = " open" if i == 0 else ""
        acc.append(f'<details class="care-acc"{open_attr}><summary>{esc(t)}</summary>'
                   f'<div class="care-acc-body">{sec_html}</div></details>')

    title = fm.get("title", "")
    deck = fm.get("answer", "")
    infographic = build_infographic(title, deck, titles)

    # 요약(summary)은 티스토리가 본문 텍스트 앞 400자를 자동 생성(설정 필드 없음).
    # 블록 요소끼리 공백이 없으면 "Care Daemon정신건강"처럼 붙어 나오므로,
    # kicker+answer를 한 <p> 안에서 공백으로 연결해 요약 앞부분을 깨끗하게 만든다.
    # answer가 문장종결 부호 없이 끝나면 다음 블록(intro)과 "이어진다이 편은"으로 붙으므로,
    # deck 표시에만 마침표를 보강해 끊어준다(원고 answer 필드는 건드리지 않음).
    deck_end = deck.strip()
    if deck_end and deck_end[-1] not in ".!?。！？":
        deck_end = deck_end + "."
    lead = '<p class="care-deck"><span class="care-kicker">돌봄 데몬 · Care Daemon</span>'
    if deck_end:
        lead += f' {esc(deck_end)}'
    lead += '</p>'
    toolbar = ('<div class="care-toolbar">'
               '<button class="care-btn" type="button" data-care="expand">전체 펼치기</button>'
               '<button class="care-btn" type="button" data-care="collapse">전체 접기</button>'
               '</div>')

    # 인포그래픽·툴바는 요약 오염원(제목·섹션목록·버튼 라벨 재탕) → intro 뒤로 밀어
    # 요약 앞 160자(카드 4줄)에서 제외. 읽는 흐름도 lead→intro→구조도→툴바→본문이 자연스럽다.
    parts = ['<div class="care-post">', TISTORY_STYLE, lead]
    if intro_html.strip():
        parts.append(f'<div class="care-intro">{intro_html}</div>')
    parts.append(infographic)
    parts.append(toolbar)
    parts.append("".join(acc))
    parts.append(TISTORY_SCRIPT)
    parts.append("</div>")
    return "\n".join(parts)


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
        "visibility": "public",
    }


def build_one(md_path: Path, *, pages: bool = True, tistory: bool = True) -> None:
    text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # body에서 h1(제목 중복) 제거
    body = re.sub(r"^#\s+.*$", "", body, count=1, flags=re.M).strip()

    intro_text, sections = _split_h2(body)
    titles = [t for t, _ in sections]

    rel = md_path.relative_to(HELANA_LOG) if HELANA_LOG in md_path.parents else md_path
    slug = md_path.stem
    etype = md_path.parent.name  # manifesto|track|dialogue|solution

    if pages:
        pages_body, _ = render_blocks(body, "pages")
        pages_body = _code_copy(pages_body)
        infographic = build_infographic(fm.get("title", slug), fm.get("answer", ""), titles)
        depth = len(rel.parts) - 1
        rel_home = "../" * depth if depth > 0 else "./"
        title = fm.get("title", slug)
        deck = fm.get("answer", "")
        src = str(rel).replace("\\", "/")
        out = md_path.with_suffix(".html")
        page = shell(BRAND, title, deck, pages_body, src, rel_home=rel_home)
        page = page.replace("</style>", CARE_CSS + "</style>", 1)
        page = page.replace('<article class="prose" id="prose">',
                            f'{infographic}<article class="prose" id="prose">', 1)
        page = page.replace("</body>", f"<script>{CARE_JS}</script></body>", 1)
        out.write_text(page, encoding="utf-8")
        print(f"  [pages]   {out.relative_to(HELANA_LOG)}")

    if tistory:
        article = render_tistory_article(fm, intro_text, sections, titles)
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

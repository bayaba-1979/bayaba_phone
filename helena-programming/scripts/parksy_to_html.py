#!/usr/bin/env python3
"""
parksy_to_html.py — ParksyCapture 대화 로그(.md) → Tistory HTML 대화록 변환기

입력:  ParksyCapture가 저장한 .md 대화 로그
출력:  JS 없는 CSS-only 인터랙티브 HTML (Tistory HTML 모드 최적화)

사용법:
  python3 scripts/parksy_to_html.py <입력.md> [--out 출력.html]
  python3 scripts/parksy_to_html.py ParksyLog_20260725.md
  python3 scripts/parksy_to_html.py ParksyLog_20260725.md --out /tmp/dialogue.html

특징:
  - 화자 자동 감지 (Boss/Grok/Claude/Aider/GAP/결정)
  - <details> 아코디언 대화 턴
  - SVG 사고 흐름 지도 자동 생성
  - CSS 바 차트 (화자별 턴 분포)
  - Fact/Feel/Gap/Fix/Next 방법론 카드
  - CSS-only 필터 탭 (전체/Boss/Grok/Gap)
  - 완전 JS-free → Tistory HTML 모드에서 그대로 발행 가능
"""

import sys
import re
import os
import json
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

SPEAKER_PATTERNS = {
    "boss": [
        r"(?:Boss|보스|BOSS|사용자|User)[:：]",
        r"^[>]?\s*(?:내가?|나는|우리|내 생각|내 의견)",
        r"^\s*질문[:：]",
        r"너\s.*\b(?:확인해|찾아|만들어|해줘|알려줘|보여줘)",
        r"^\s*\"[^\"]{10,}\"\s*$",  # quote-only turns
    ],
    "grok": [
        r"(?:Grok|그록|GROK)[:：]",
        r"^(?:PHASE|Phase|phase)\s+\d",
        r"^(?:리서치|확인했다|분석|검토)[:：]?",
        r"^\s*(?:cc|ds|Claude)가\s",
    ],
    "claude": [
        r"(?:Claude|클로드|CLAUDE|CC)[:：]",
        r"^(?:확인|검증|분석)[:：].*(?:입니다|니다|함)",
        r"^\s*(?:```|파일|코드|스크립트)",
    ],
    "aider": [
        r"(?:Aider|에이더|AIDER|DS)[:：]",
        r"^\s*(?:git|patch|diff|commit)",
    ],
}

GAP_PATTERNS = [
    r"(?:빈틈|빈칸|빠진|누락|갭|GAP|Gap|gap)[:：]?",
    r"🕳️",
    r"(?:문제|한계|병목|안 됨|불가|못 함|실패)[:：]",
    r"(?:여기서|이 지점에서)\s*(?:빈|비어|빠진)",
]

DECISION_PATTERNS = [
    r"(?:결정|확정|선택|채택|이걸로|이것으로)[:：]",
    r"(?:최종|확실히|분명히)\s*(?:결정|선택|확정)",
    r"★|✅.*(?:결정|확정|선택)",
    r"^\s*(?:그럼|자|좋아|오케이|OK|Okay)[,.]?\s*(?:이제|이걸로|이렇게|확정)",
]

METHOD_SECTION_HEADERS = {
    "fact":  [r"#+\s*(?:상황|Fact|사실|무엇이)", r"(?:상황|Fact)[:：]"],
    "feel":  [r"#+\s*(?:느낀|Feel|감정|느낌)", r"(?:느낀|Feel)[:：]"],
    "gap":   [r"#+\s*(?:개선점|Gap|빈틈|차이)", r"(?:개선점|Gap|빈틈)[:：]"],
    "fix":   [r"#+\s*(?:솔루션|Fix|해결|고침)", r"(?:솔루션|Fix|해결)[:：]"],
    "next":  [r"#+\s*(?:다음|Next|향후|앞으로)", r"(?:다음|Next)[:：]"],
}

# Speaker display info
SPEAKER_INFO = {
    "boss":     {"label": "Boss",    "emoji": "👤", "css_class": "turn-boss"},
    "grok":     {"label": "Grok",    "emoji": "🎨", "css_class": "turn-grok"},
    "claude":   {"label": "Claude",  "emoji": "📝", "css_class": "turn-claude"},
    "aider":    {"label": "Aider",   "emoji": "🔧", "css_class": "turn-aider"},
    "gap":      {"label": "GAP",     "emoji": "🕳️", "css_class": "turn-gap"},
    "decision": {"label": "결정",    "emoji": "★",   "css_class": "turn-decision"},
    "unknown":  {"label": "Speaker", "emoji": "💬", "css_class": "turn-boss"},
}


# ═══════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════

def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter from ParksyCapture logs."""
    meta = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if fm_match:
        body = text[fm_match.end():]
        for line in fm_match.group(1).split('\n'):
            line = line.strip()
            if ':' in line:
                key, _, val = line.partition(':')
                meta[key.strip()] = val.strip()
        return meta, body
    return meta, text


def detect_speaker(text: str) -> str:
    """Detect speaker from turn text."""
    for speaker, patterns in SPEAKER_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.MULTILINE | re.IGNORECASE):
                return speaker
    return "unknown"


def detect_special(text: str, speaker: str) -> str | None:
    """Detect if a turn is a GAP or DECISION."""
    # decision check first (more specific)
    for pat in DECISION_PATTERNS:
        if re.search(pat, text, re.MULTILINE):
            return "decision"
    # gap check
    for pat in GAP_PATTERNS:
        if re.search(pat, text, re.MULTILINE):
            return "gap"
    return None


def split_turns(body: str) -> list[dict]:
    """Split markdown body into conversation turns."""
    turns = []
    # split on double newline or markdown headings as turn boundaries
    paragraphs = re.split(r'\n{2,}', body.strip())

    buffer = []
    current_speaker = None
    turn_num = 0

    def flush_buffer():
        nonlocal turn_num
        if not buffer:
            return
        text = '\n\n'.join(buffer).strip()
        if len(text) < 15:  # skip too-short fragments
            buffer.clear()
            return

        speaker = detect_speaker(text)
        special = detect_special(text, speaker)
        if special:
            speaker = special

        turn_num += 1
        turns.append({
            "num": turn_num,
            "speaker": speaker,
            "text": clean_turn_text(text),
            "preview": text[:80].replace('\n', ' ').strip(),
        })
        buffer.clear()

    for para in paragraphs:
        para = para.strip()
        if not para:
            flush_buffer()
            continue

        # markdown heading = new turn
        if re.match(r'^#{1,3}\s', para):
            flush_buffer()
            buffer.append(para)
            flush_buffer()
            continue

        # PHASE marker = new turn
        if re.match(r'^(?:PHASE|Phase|phase)\s+\d', para):
            flush_buffer()

        buffer.append(para)

    flush_buffer()
    return turns


def clean_turn_text(text: str) -> str:
    """Clean markdown artifacts from turn text while preserving structure."""
    # Remove image references (Claude CDN URLs that died)
    text = re.sub(r'!\[.*?\]\(https://claude\.cdn\S*\)', '[이미지]', text)
    # Remove "더 보기" and similar UI fragments
    text = re.sub(r'\n더 보기\s*$', '', text)
    # Remove "Claude는 AI이며 실수할 수 있습니다" footer
    text = re.sub(r'\n+Claude는 AI이며 실수할 수 있습니다\..*$', '', text, flags=re.DOTALL)
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_method_sections(body: str) -> dict:
    """Extract Fact/Feel/Gap/Fix/Next sections from the body."""
    sections = {}
    lines = body.split('\n')

    current_section = None
    current_lines = []

    for line in lines:
        matched = None
        for key, patterns in METHOD_SECTION_HEADERS.items():
            for pat in patterns:
                if re.search(pat, line, re.IGNORECASE):
                    if current_section and current_lines:
                        sections[current_section] = '\n'.join(current_lines).strip()
                    current_section = key
                    current_lines = []
                    matched = True
                    break
            if matched:
                break
        if matched:
            continue

        if current_section:
            current_lines.append(line)

    if current_section and current_lines:
        sections[current_section] = '\n'.join(current_lines).strip()

    return sections


# ═══════════════════════════════════════════════════════════════
# SVG GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_thought_map_svg(turns: list[dict]) -> str:
    """Generate SVG thought-flow diagram from turns."""
    if len(turns) < 3:
        return ""

    # pick significant nodes (max ~8)
    nodes = []
    for t in turns:
        is_special = t["speaker"] in ("gap", "decision")
        is_question = t["speaker"] == "boss"
        if is_special or is_question or len(nodes) < 8:
            nodes.append(t)
        if len(nodes) >= 10:
            break

    if len(nodes) < 2:
        return ""

    colors = {
        "boss":     "#B87333",
        "grok":     "#4A90D9",
        "claude":   "#7B5EA7",
        "aider":    "#3DA37A",
        "gap":      "#E05555",
        "decision": "#D4A84B",
    }

    svg_width = 780
    svg_height = 130
    spacing = svg_width / (len(nodes) + 1)

    elements = []
    prev_cx = 0

    for i, node in enumerate(nodes):
        cx = int(spacing * (i + 1))
        cy = 55
        r = 16 if node["speaker"] in ("gap", "decision") else 13
        color = colors.get(node["speaker"], "#888")

        # edge
        if i > 0:
            edge_color = "#E05555" if node["speaker"] == "gap" else (
                "#D4A84B" if node["speaker"] == "decision" else "#ccc")
            edge_dash = "stroke-dasharray=\"4 3\"" if node["speaker"] not in ("gap", "decision") else ""
            stroke_w = 2 if node["speaker"] == "decision" else 1.3
            elements.append(
                f'<line x1="{prev_cx}" y1="55" x2="{cx}" y2="55" '
                f'stroke="{edge_color}" stroke-width="{stroke_w}" {edge_dash}/>')

        # node
        if node["speaker"] == "decision":
            elements.append(
                f'<rect x="{cx - r}" y="{cy - r + 2}" width="{r * 2}" height="{r * 2 - 4}" '
                f'rx="{r}" fill="{color}" stroke="#a8872e" stroke-width="1.5"/>')
            lbl = node["speaker"][:2].upper()
            elements.append(
                f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" fill="#2c2c2c" '
                f'font-size="8" font-weight="700">{lbl}</text>')
        else:
            elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
            lbl = f"Q{i}" if node["speaker"] == "boss" else (
                "A" if node["speaker"] in ("grok", "claude") else (
                "G" if node["speaker"] == "gap" else "•"))
            fill = "#2c2c2c" if node["speaker"] == "decision" else "white"
            elements.append(
                f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" fill="{fill}" '
                f'font-size="8" font-weight="700">{lbl}</text>')

        # mini label
        preview = node["preview"][:14]
        elements.append(
            f'<text x="{cx}" y="82" text-anchor="middle" font-size="7" fill="#888">{preview}</text>')

        prev_cx = cx

    return f'''<svg viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
  {"".join(elements)}
</svg>'''


def generate_decision_tree_svg(turns: list[dict], method: dict) -> str:
    """Generate SVG decision tree if gaps/decisions found."""
    decisions = [t for t in turns if t["speaker"] == "decision"]
    gaps = [t for t in turns if t["speaker"] == "gap"]

    if not decisions and not gaps:
        return ""

    # simplified decision flow
    elements = []
    y_pos = 20
    elements.append(
        f'<text x="20" y="{y_pos}" font-size="11" font-weight="700" fill="#2c2c2c">'
        f'결정 분기점 {len(decisions)}건 · Gap 발견 {len(gaps)}건</text>')

    for i, d in enumerate(decisions):
        y_pos += 22
        elements.append(
            f'<circle cx="30" cy="{y_pos}" r="5" fill="#D4A84B"/>'
            f'<text x="42" y="{y_pos + 4}" font-size="10" fill="#2c2c2c">{d["preview"][:60]}</text>')

    for i, g in enumerate(gaps):
        y_pos += 22
        elements.append(
            f'<circle cx="30" cy="{y_pos}" r="5" fill="#E05555"/>'
            f'<text x="42" y="{y_pos + 4}" font-size="10" fill="#a33">{g["preview"][:60]}</text>')

    svg_height = y_pos + 20
    return f'<svg viewBox="0 0 700 {svg_height}" xmlns="http://www.w3.org/2000/svg">\n{"".join(elements)}\n</svg>'


# ═══════════════════════════════════════════════════════════════
# HTML GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_stat_row(turns: list[dict]) -> str:
    """Generate stat cards row."""
    boss_count = sum(1 for t in turns if t["speaker"] == "boss")
    grok_count = sum(1 for t in turns if t["speaker"] == "grok")
    claude_count = sum(1 for t in turns if t["speaker"] == "claude")
    gap_count = sum(1 for t in turns if t["speaker"] == "gap")
    decision_count = sum(1 for t in turns if t["speaker"] == "decision")

    return f'''<div class="stat-row">
    <div class="stat-card"><div class="stat-num">{len(turns)}</div><div class="stat-label">대화 턴</div></div>
    <div class="stat-card"><div class="stat-num">{decision_count}</div><div class="stat-label">결정 분기점</div></div>
    <div class="stat-card"><div class="stat-num">{gap_count}</div><div class="stat-label">Gap 발견</div></div>
    <div class="stat-card"><div class="stat-num">{boss_count + grok_count + claude_count}</div><div class="stat-label">응답</div></div>
</div>'''


def generate_turn_html(turn: dict, turn_num: int) -> str:
    """Generate HTML for a single conversation turn."""
    info = SPEAKER_INFO.get(turn["speaker"], SPEAKER_INFO["unknown"])
    css_class = info["css_class"]
    label = info["label"]
    num_badge = "★" if turn["speaker"] == "decision" else f"{turn_num:02d}"

    # format body: simple paragraphs
    body_lines = turn["text"].split('\n')
    body_html_parts = []
    in_code = False

    for line in body_lines:
        line = line.strip()
        if not line:
            body_html_parts.append('<br>')
            continue

        # code block
        if line.startswith('```'):
            if in_code:
                body_html_parts.append('</pre>')
                in_code = False
            else:
                body_html_parts.append('<pre>')
                in_code = True
            continue

        if in_code:
            # escape HTML in code
            safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            body_html_parts.append(safe + '\n')
            continue

        # heading
        if re.match(r'^#{1,3}\s', line):
            level = len(re.match(r'^#+', line).group())
            content = line.lstrip('#').strip()
            tag = f'h{level + 2}' if level <= 2 else 'h5'
            body_html_parts.append(f'<{tag}>{content}</{tag}>')
            continue

        # list item
        if re.match(r'^[-*]\s', line):
            content = line.lstrip('-* ').strip()
            body_html_parts.append(f'<li>{content}</li>')
            continue

        # numbered list
        if re.match(r'^\d+[.)]\s', line):
            content = re.sub(r'^\d+[.)]\s*', '', line).strip()
            body_html_parts.append(f'<li>{content}</li>')
            continue

        # table row
        if '|' in line and line.count('|') >= 3:
            body_html_parts.append(f'<span class="table-row">{line.strip()}</span><br>')
            continue

        # gap marker
        if turn["speaker"] == "gap" and re.search(r'(?:빈틈|GAP|차이|발견|문제)', line):
            body_html_parts.append(f'<div class="gap-marker">{line}</div>')
            continue

        # normal paragraph
        body_html_parts.append(f'<p>{line}</p>')

    body_html = '\n'.join(body_html_parts)

    time_str = ""
    # try to extract time from text
    time_match = re.search(r'(\d{1,2}:\d{2})', turn["text"][:200])
    if time_match:
        time_str = f'<time>{time_match.group(1)}</time>'

    return f'''<details class="turn {css_class}" id="t{turn_num:02d}">
      <summary>
        <span class="turn-num">{num_badge}</span>
        <span class="turn-speaker">{label}</span>
        <span class="turn-preview">{turn["preview"]}</span>
        {time_str}
      </summary>
      <div class="turn-body">
        {body_html}
      </div>
    </details>'''


def generate_method_cards(method: dict) -> str:
    """Generate Fact/Feel/Gap/Fix/Next cards."""
    cards = []

    card_defs = [
        ("fact", "📋 상황", "card-fact"),
        ("feel", "💭 느낀 바", "card-feel"),
        ("gap",  "🕳️ 빈틈", "card-gap"),
        ("fix",  "🔧 해결", "card-fix"),
        ("next", "👉 다음", "card-next"),
    ]

    for key, title, css_class in card_defs:
        content = method.get(key, "")
        if not content:
            continue

        # simple text to HTML
        html_content = '<br>'.join(content.split('\n')[:8])
        # wrap list items
        if any(line.strip().startswith(('- ', '* ', '1.', '2.', '3.')) for line in content.split('\n')):
            items = []
            for line in content.split('\n')[:8]:
                line = line.strip()
                if re.match(r'^[-*\d+.)]\s', line):
                    items.append(f'<li>{line.lstrip("-* 1234567890.)").strip()}</li>')
                elif line:
                    items.append(f'<p>{line}</p>')
            html_content = '\n'.join(items)
            if any(line.startswith('<li>') for line in items):
                html_content = '<ul>' + html_content + '</ul>'

        is_full = key in ("next", "fix") and len(content) > 200
        full_class = " method-card-full" if is_full else ""

        cards.append(f'''<div class="method-card {css_class}{full_class}">
      <h3>{title}</h3>
      {html_content}
    </div>''')

    if not cards:
        return ""
    return '<div class="method-summary">\n' + '\n'.join(cards) + '\n</div>'


def generate_timeline(turns: list[dict]) -> str:
    """Generate CSS timeline from key moments."""
    items = []
    for t in turns:
        if t["speaker"] not in ("gap", "decision", "boss"):
            continue
        is_decision = t["speaker"] == "decision"
        css = " tl-decision" if is_decision else ""

        # try to extract time
        time_match = re.search(r'(\d{1,2}:\d{2})', t["text"][:200])
        time_html = f'<time>{time_match.group(1)}</time>' if time_match else ""

        items.append(f'''<div class="tl-item{css}">
      {time_html}
      <span class="tl-title">{SPEAKER_INFO[t["speaker"]]["label"]}</span>
      <p>{t["preview"][:80]}</p>
    </div>''')

    if not items:
        return ""
    return '<div class="timeline">\n<h2>⏱️ 타임라인</h2>\n' + '\n'.join(items[:10]) + '\n</div>'


def generate_filter_bar() -> str:
    """Generate CSS-only filter tab bar."""
    return '''<div class="filter-bar">
    <input type="radio" id="filter-all"     name="turn-filter" checked>
    <input type="radio" id="filter-boss"    name="turn-filter">
    <input type="radio" id="filter-grok"    name="turn-filter">
    <input type="radio" id="filter-claude"  name="turn-filter">
    <input type="radio" id="filter-gap-only" name="turn-filter">
    <label for="filter-all">전체</label>
    <label for="filter-boss">Boss 질문</label>
    <label for="filter-grok">Grok 응답</label>
    <label for="filter-claude">Claude</label>
    <label for="filter-gap-only">Gap만</label>
</div>'''


def build_html(
    title: str,
    date_str: str,
    meta: dict,
    turns: list[dict],
    method: dict,
    template_path: str | None = None
) -> str:
    """Build the complete HTML page."""
    stat_row = generate_stat_row(turns)
    thought_map = generate_thought_map_svg(turns)
    decision_tree = generate_decision_tree_svg(turns, method)
    filter_bar = generate_filter_bar()
    method_cards = generate_method_cards(method)
    timeline = generate_timeline(turns)

    # turn HTML
    turn_html_parts = []
    for t in turns:
        turn_html_parts.append(generate_turn_html(t, t["num"]))
    turn_list = '\n\n'.join(turn_html_parts)

    # speaker meta badges
    speakers_seen = set(t["speaker"] for t in turns)
    speaker_badges = []
    for s in sorted(speakers_seen):
        info = SPEAKER_INFO.get(s)
        if info:
            speaker_badges.append(f'<span><b class="speaker-dot" style="background:var(--c-{s})"></b> {info["label"]}</span>')

    # progress
    gap_count = sum(1 for t in turns if t["speaker"] == "gap")
    decision_count = sum(1 for t in turns if t["speaker"] == "decision")
    completeness = min(100, 70 + decision_count * 8 - gap_count * 3)

    thought_map_section = ""
    if thought_map:
        thought_map_section = f'''<section class="thought-map">
    <h2>🧭 사고 흐름 지도</h2>
    {thought_map}
    <p class="map-caption">{len(turns)}턴 · Gap {gap_count}회 · 결정 {decision_count}건</p>
</section>'''

    decision_tree_section = ""
    if decision_tree:
        decision_tree_section = f'''<section class="decision-tree">
    <h2>🌳 결정 분기점</h2>
    {decision_tree}
</section>'''

    timeline_section = timeline if timeline else ""

    method_section = method_cards if method_cards else ""

    graph_section = ""
    if turns:
        boss_n = sum(1 for t in turns if t["speaker"] == "boss")
        grok_n = sum(1 for t in turns if t["speaker"] == "grok")
        claude_n = sum(1 for t in turns if t["speaker"] == "claude")
        aid_n = sum(1 for t in turns if t["speaker"] == "aider")
        gap_n = sum(1 for t in turns if t["speaker"] == "gap")
        dec_n = sum(1 for t in turns if t["speaker"] == "decision")
        graph_section = f'''<section class="graph-view">
    <h2>📊 대화 턴 분포</h2>
    <div class="bar-chart">
      <div class="bar bar-q"><span class="bar-val">{boss_n}</span><span class="bar-label">Boss</span></div>
      <div class="bar bar-a"><span class="bar-val">{grok_n}</span><span class="bar-label">Grok</span></div>
      <div class="bar bar-c"><span class="bar-val">{claude_n}</span><span class="bar-label">Claude</span></div>
      <div class="bar bar-g"><span class="bar-val">{gap_n}</span><span class="bar-label">Gap</span></div>
    </div>
</section>'''

    # CSS (embedded full stylesheet)
    css = '''<style>
  :root {
    --bg: #F9F7F2; --card: #ffffff; --ink: #2c2c2c; --muted: #888;
    --border: #e0d8cc; --radius: 8px; --shadow: 0 2px 8px rgba(0,0,0,.06);
    --c-boss: #B87333; --c-grok: #4A90D9; --c-claude: #7B5EA7;
    --c-aider: #3DA37A; --c-gap: #E05555; --c-decision: #D4A84B;
  }
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1a1a1a;--card:#252525;--ink:#ddd;--muted:#999;--border:#3a3a3a}}
  :root[data-theme="dark"]{--bg:#1a1a1a;--card:#252525;--ink:#ddd;--muted:#999;--border:#3a3a3a}
  *{box-sizing:border-box;margin:0;padding:0}
  .dl-container{max-width:720px;margin:0 auto;font-family:'Noto Sans KR',sans-serif;color:var(--ink);background:var(--bg);padding:20px 14px 48px;line-height:1.7}
  .dl-header{text-align:center;padding:28px 14px 20px;border-bottom:2px dashed var(--border);margin-bottom:24px}
  .dl-header h1{font-size:1.5rem;margin:0 0 6px;color:var(--ink);letter-spacing:-.5px}
  .dl-meta{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;font-size:.82rem;color:var(--muted)}
  .dl-meta span{background:var(--card);padding:4px 11px;border-radius:18px;border:1px solid var(--border)}
  .speaker-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:3px;vertical-align:middle}
  section{margin:24px 0;padding:18px 14px;background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow)}
  section h2{font-size:.92rem;color:var(--ink);margin-bottom:12px;padding-left:10px;border-left:3px solid var(--c-claude)}
  .thought-map svg,.decision-tree svg{width:100%;height:auto}
  .map-caption{text-align:center;font-size:.72rem;color:var(--muted);margin-top:6px;font-style:italic}

  /* stats */
  .stat-row{display:flex;gap:12px;flex-wrap:wrap}
  .stat-card{flex:1;min-width:80px;text-align:center;background:var(--card);border-radius:var(--radius);padding:14px 10px;box-shadow:var(--shadow)}
  .stat-card .stat-num{font-size:1.6rem;font-weight:800;color:var(--ink);line-height:1.2}
  .stat-card .stat-label{font-size:.68rem;color:var(--muted);margin-top:3px}

  /* filter bar */
  .filter-bar{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}
  .filter-bar input[type="radio"]{display:none}
  .filter-bar label{padding:5px 12px;border-radius:16px;font-size:.74rem;cursor:pointer;border:1px solid var(--border);background:var(--card);color:var(--muted);transition:all .2s;user-select:none}
  .filter-bar label:hover{border-color:var(--c-decision);color:var(--ink)}
  .filter-bar input[type="radio"]:checked+label{background:#0F1C18;color:#fff;border-color:#0F1C18}
  #filter-all:checked~.turn-list .turn{display:block}
  #filter-boss:checked~.turn-list .turn:not(.turn-boss){display:none}
  #filter-grok:checked~.turn-list .turn:not(.turn-grok){display:none}
  #filter-claude:checked~.turn-list .turn:not(.turn-claude){display:none}
  #filter-gap-only:checked~.turn-list .turn:not(.turn-gap):not(.turn-decision){display:none}

  /* turns */
  .turn{margin-bottom:7px;border-radius:var(--radius);background:var(--card);box-shadow:var(--shadow);overflow:hidden;transition:box-shadow .3s}
  .turn:hover{box-shadow:0 4px 14px rgba(0,0,0,.1)}
  .turn-boss{border-left:4px solid var(--c-boss)}
  .turn-grok{border-left:4px solid var(--c-grok)}
  .turn-claude{border-left:4px solid var(--c-claude)}
  .turn-aider{border-left:4px solid var(--c-aider)}
  .turn-gap{border-left:4px solid var(--c-gap);background:#fff5f5}
  .turn-decision{border-left:4px solid var(--c-decision);background:#fffdf5}
  .turn summary{display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;list-style:none;user-select:none;font-size:.85rem;transition:background .2s}
  .turn summary::-webkit-details-marker{display:none}
  .turn summary:hover{background:rgba(0,0,0,.02)}
  .turn[open] summary{background:rgba(0,0,0,.03);border-bottom:1px solid var(--border)}
  .turn summary::after{content:"▸";flex-shrink:0;font-size:.65rem;color:var(--muted);transition:transform .3s}
  .turn[open] summary::after{transform:rotate(90deg)}
  .turn-num{flex-shrink:0;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;color:#fff}
  .turn-boss .turn-num{background:var(--c-boss)}
  .turn-grok .turn-num{background:var(--c-grok)}
  .turn-claude .turn-num{background:var(--c-claude)}
  .turn-aider .turn-num{background:var(--c-aider)}
  .turn-gap .turn-num{background:var(--c-gap)}
  .turn-decision .turn-num{background:var(--c-decision)}
  .turn-speaker{flex-shrink:0;font-weight:700;font-size:.72rem;min-width:44px;text-align:center;padding:2px 5px;border-radius:4px}
  .turn-boss .turn-speaker{color:var(--c-boss);background:#fdf3e7}
  .turn-grok .turn-speaker{color:var(--c-grok);background:#e8f1fb}
  .turn-claude .turn-speaker{color:var(--c-claude);background:#f0ebf7}
  .turn-aider .turn-speaker{color:var(--c-aider);background:#e6f5ee}
  .turn-gap .turn-speaker{color:var(--c-gap);background:#fce8e8}
  .turn-decision .turn-speaker{color:#a8872e;background:#fef9e7}
  .turn-preview{flex:1;color:var(--muted);font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .turn time{flex-shrink:0;font-size:.68rem;color:var(--muted)}
  .turn-body{padding:14px 18px 18px;font-size:.84rem;line-height:1.8;animation:slide-down .3s ease-out}
  .turn-body p,.turn-body li{margin-bottom:6px}
  .turn-body pre{background:#f7f5f0;border-radius:6px;padding:10px 14px;overflow-x:auto;font-size:.74rem}
  .turn-body ul{padding-left:16px}
  .gap-marker{margin-top:10px;padding:8px 12px;background:#fff0f0;border-left:3px solid var(--c-gap);border-radius:0 4px 4px 0;font-size:.76rem;color:#a33}
  .gap-marker::before{content:"🕳️ Gap: ";font-weight:700}
  @keyframes slide-down{from{opacity:0}to{opacity:1}}

  /* method cards */
  .method-summary{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:24px 0}
  @media(max-width:480px){.method-summary{grid-template-columns:1fr}}
  .method-card{background:var(--card);border-radius:var(--radius);padding:16px 14px;box-shadow:var(--shadow);transition:transform .2s;border-top:3px solid #ccc}
  .method-card:hover{transform:translateY(-2px)}
  .method-card h3{font-size:.82rem;margin-bottom:6px}
  .method-card p,.method-card li{font-size:.78rem;color:var(--muted)}
  .card-fact{border-top-color:#5B8DB8}
  .card-feel{border-top-color:#C47E9E}
  .card-gap{border-top-color:var(--c-gap)}
  .card-fix{border-top-color:var(--c-aider)}
  .card-next{border-top-color:var(--c-decision)}
  .method-card-full{grid-column:1/-1}

  /* timeline */
  .timeline{margin:24px 0;padding-left:24px;border-left:2px solid var(--border)}
  .timeline h2{font-size:.92rem;margin:0 0 12px -24px;padding-left:24px}
  .tl-item{position:relative;margin-bottom:18px;padding-left:18px;font-size:.8rem}
  .tl-item::before{content:"";position:absolute;left:-30px;top:5px;width:8px;height:8px;border-radius:50%;background:var(--border);border:2px solid var(--card)}
  .tl-item.tl-decision::before{background:var(--c-decision);width:12px;height:12px;left:-32px;top:3px}
  .tl-item time{font-size:.66rem;color:var(--muted);display:block}
  .tl-title{font-weight:700;color:var(--ink)}

  /* footer */
  .dl-footer{margin-top:32px;padding:16px;text-align:center;border-top:2px dashed var(--border);font-size:.72rem;color:var(--muted)}
</style>'''

    speakers_badge_html = ' '.join(speaker_badges)

    return f'''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
{css}
<div class="dl-container">
<header class="dl-header">
  <h1>{title}</h1>
  <div class="dl-meta">
    {speakers_badge_html}
    <span>🔄 {len(turns)}턴</span>
    <span>📅 {date_str}</span>
  </div>
</header>

{stat_row}

{thought_map_section}

{graph_section}

{decision_tree_section}

{filter_bar}

<div class="turn-list">
  <h2>💬 대화 기록</h2>
{turn_list}
</div>

{method_section}

{timeline_section}

<footer class="dl-footer">
  <p>📁 ParksyCapture 변환 · 📅 {date_str} · 🤖 JS-free CSS-only · Tistory 준비 완료</p>
</footer>
</div>'''


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 parksy_to_html.py <입력.md> [--out 출력.html]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = None

    # parse --out flag
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            output_path = args[i + 1]
            break

    # read input
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"❌ 파일 없음: {input_path}")
        sys.exit(1)

    # parse
    meta, body = parse_frontmatter(raw)
    turns = split_turns(body)
    method = extract_method_sections(body)

    if not turns:
        print("⚠️  대화 턴을 찾을 수 없습니다. 일반 텍스트 파일인가요?")
        sys.exit(1)

    # extract metadata
    date_str = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
    title = f"대화록 · {date_str}"
    if meta.get("source"):
        title += f" · {meta['source']}"

    # try to extract a title from first heading
    heading_match = re.search(r'^#\s+(.+)', body, re.MULTILINE)
    if heading_match:
        title = heading_match.group(1).strip()

    # build HTML
    html = build_html(title, date_str, meta, turns, method)

    # output
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML 생성 완료: {output_path}")
    else:
        # default output: same name, .html extension
        out = Path(input_path).with_suffix('.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML 생성 완료: {out}")

    # summary
    speakers = {}
    for t in turns:
        speakers[t["speaker"]] = speakers.get(t["speaker"], 0) + 1
    print(f"📊 {len(turns)}턴 분석 완료: ", end="")
    print(", ".join(f"{SPEAKER_INFO.get(k, {}).get('label', k)} {v}" for k, v in speakers.items()))


if __name__ == "__main__":
    main()

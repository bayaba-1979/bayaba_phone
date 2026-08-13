#!/usr/bin/env python3
"""
📚 Tistory Booklet Generator v2.0 — MCP 연동 단행본 제너레이터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
통합 채널: 
  - channel_map.json (25개 블로그 매핑)
  - _tistory_publish.py (Playwright 발행 엔진)
  - accounts.json (계정 정보)

사용:
  # CLI
  python3 generator.py --blog 철학자박씨 --title "존재와 시간" --input draft.md
  
  # MCP (에이전트가 호출)
  from generator import generate_and_publish
  result = generate_and_publish("철학자박씨", "존재와 시간", md_content)
  
  # 한 줄 명령
  python3 generator.py --say "철학자박씨에 존재와 시간 올려줘" --input draft.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import argparse, json, os, re, sys, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
POSTS_DIR = BASE / "posts"
DRAFTS_DIR = BASE / "drafts"
POSTS_DIR.mkdir(exist_ok=True)
DRAFTS_DIR.mkdir(exist_ok=True)

# ── 이름 → 슬러그 매핑 (25개 블로그 전수) ──
BLOG_MAP = {
    # dtslib (한글)
    "블로거박씨":     {"slug": "polyglot14",       "account": "dtslib",    "lang": "ko"},
    "철학자박씨":     {"slug": "dtslib",           "account": "dtslib",    "lang": "ko"},
    "화가박씨":       {"slug": "webtoon-park",     "account": "dtslib",    "lang": "ko"},
    "기능인박씨":     {"slug": "programmer-park",  "account": "dtslib",    "lang": "ko"},
    "뮤지션박씨":     {"slug": "musician-park",    "account": "dtslib",    "lang": "ko"},
    # parksy_kr (영문)
    "blogger-parksy":    {"slug": "blogger-parksy",    "account": "parksy_kr", "lang": "en"},
    "technician-parksy": {"slug": "technician-parksy", "account": "parksy_kr", "lang": "en"},
    "philosopher-parksy":{"slug": "philosopher-parksy","account": "parksy_kr", "lang": "en"},
    "visualizer-parksy": {"slug": "visualizer-parksy", "account": "parksy_kr", "lang": "en"},
    "musician-parksy":   {"slug": "musician-parksy",   "account": "parksy_kr", "lang": "en"},
    # eae_kr
    "eae-kr":          {"slug": "eae-kr",          "account": "eae_kr",    "lang": "ko"},
    # dtslib1k
    "dtslib1k":        {"slug": "dtslib1k",        "account": "dtslib1k",  "lang": "ko"},
    "중년고딩과학":     {"slug": "hitop",           "account": "dtslib1k",  "lang": "ko"},
    "중년고딩수학":     {"slug": "midmath",          "account": "dtslib1k",  "lang": "ko"},
    "중년고딩사회":     {"slug": "midsocial",        "account": "dtslib1k",  "lang": "ko"},
    "중년고딩철학":     {"slug": "lafilosofia",      "account": "dtslib1k",  "lang": "ko"},
    # dtslib2k
    "korean-parksy":     {"slug": "korean-parksy",    "account": "dtslib2k",  "lang": "ko"},
    "kr-merit-bluff":    {"slug": "kr-merit-bluff",   "account": "dtslib2k",  "lang": "ko"},
    "kr-merit-halfblood":{"slug": "kr-merit-halfblood","account": "dtslib2k",  "lang": "ko"},
    "kr-merit-aggro":    {"slug": "kr-merit-aggro",   "account": "dtslib2k",  "lang": "ko"},
    "kr-merit-shaman":   {"slug": "kr-merit-shaman",  "account": "dtslib2k",  "lang": "ko"},
}

# ── 단행본 CSS 프레임워크 v3.0 (다크그린 · 색약친화 · 동적요소 풀세트) ──
BOOKLET_CSS = """
:root{--bg-page:#0f1a12;--bg-card:#162318;--bg-card2:#1a2d1e;--bg-card3:#1f3523;--border:#2a4a30;--border-light:#1f3523;--text:#e0f0e0;--text-soft:#b8d4b8;--text-dim:#7a9a7a;--text-bright:#fff;--accent:#40c057;--accent-soft:#2b8a3e;--accent-bg:rgba(64,192,87,.08);--gold:#f0c040;--gold-dim:rgba(240,192,64,.08);--blue:#4dabf7;--blue-dim:rgba(77,171,247,.08);--red:#ff6b6b;--red-dim:rgba(255,107,107,.08);--purple:#cc99ff;--purple-dim:rgba(204,153,255,.08);--f-serif:'Noto Serif KR','Nanum Myeongjo',Georgia,serif;--f-sans:'Spoqa Han Sans Neo','Noto Sans KR',-apple-system,sans-serif;--f-mono:'JetBrains Mono','D2Coding','Fira Code',monospace}
.book-root{max-width:820px;margin:0 auto;padding:24px 20px;font-family:var(--f-serif);color:var(--text) !important;background:var(--bg-page) !important;line-height:1.95;word-break:keep-all;font-size:17px}
.book-root h1,.book-root h2,.book-root h3,.book-root h4,.book-root h5,.book-root h6{color:var(--text-bright) !important;font-family:var(--f-serif);font-weight:700;line-height:1.3;margin:28px 0 12px}
.book-root h3{font-size:1.15rem}
.book-root h4{font-size:1rem}
.book-cover{position:relative;padding:64px 40px 48px;margin-bottom:32px;background:linear-gradient(170deg,#0a1f10,#132a18,#1a3520) !important;border:1px solid var(--border);border-bottom:3px solid var(--accent);text-align:center;border-radius:6px}
.book-cover::before{content:'';position:absolute;top:-1px;left:15%;right:15%;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent)}
.book-cover .series{font-family:var(--f-sans);font-size:.6rem;letter-spacing:.2em;text-transform:uppercase;color:var(--text-dim) !important;margin-bottom:12px}
.book-cover h1{font-family:var(--f-serif);font-size:2.4rem;font-weight:700;margin:0 0 10px;line-height:1.2;color:var(--text-bright) !important;letter-spacing:-.01em}
.book-cover .subtitle{font-size:.95rem;color:var(--text-soft) !important;font-style:italic;margin-bottom:18px}
.book-cover .meta{font-family:var(--f-sans);font-size:.7rem;color:var(--text-dim)}
.chapter{margin:48px 0 24px;padding:24px 0 12px;border-top:2px solid var(--border);position:relative}
.chapter::before{content:attr(data-number);position:absolute;top:-14px;left:0;font-family:var(--f-mono);font-size:.7rem;color:var(--accent) !important;font-weight:700;background:var(--bg-page) !important;padding-right:12px}
.chapter h2{font-family:var(--f-serif);font-size:1.5rem;font-weight:700;margin:0 0 8px;color:var(--text-bright) !important;line-height:1.3}
.chapter .ch-sub{font-family:var(--f-sans);font-size:.8rem;color:var(--text-dim) !important;font-style:italic;margin-bottom:16px}
.book-root p{margin:0 0 16px}
.book-root strong{color:var(--text-bright) !important;font-weight:600}
.book-root em{color:var(--accent) !important;font-style:italic}
.book-root blockquote,.book-root p.quote{border-left:4px solid var(--accent);padding:16px 20px;margin:20px 0;background:var(--bg-card) !important;border-radius:0 6px 6px 0;font-style:italic;color:var(--text-soft) !important;line-height:1.8;position:relative}
.book-root blockquote::before,.book-root p.quote::before{content:'"';position:absolute;top:-4px;left:6px;font-size:2.4rem;color:var(--accent) !important;opacity:.25;font-family:Georgia,serif;line-height:1}
.book-root .btn{display:inline-block;padding:10px 24px;margin:4px;font-family:var(--f-sans);font-size:.82rem;font-weight:600;border:none;border-radius:6px;cursor:pointer;text-decoration:none;transition:all .15s ease;line-height:1.4}
.book-root .btn-green{background:var(--accent) !important;color:#0a1f10 !important;border:1px solid var(--accent)}
.book-root .btn-green:hover{background:#52d96a !important;transform:translateY(-1px)}
.book-root .btn-outline{background:transparent !important;color:var(--accent) !important;border:1.5px solid var(--accent)}
.book-root .btn-outline:hover{background:var(--accent-bg)}
.book-root .btn-dim{background:var(--bg-card2) !important;color:var(--text-soft) !important;border:1px solid var(--border)}
.book-root .btn-dim:hover{background:var(--bg-card3)}
.book-root .btn-purple{background:var(--purple) !important;color:#2a0a40 !important;border:1px solid var(--purple)}
.book-root .btn-purple:hover{background:#d9b3ff !important;transform:translateY(-1px)}
.book-root .btn-gold{background:var(--gold) !important;color:#3a2c00 !important;border:1px solid var(--gold)}
.book-root .btn-gold:hover{background:#f5d576 !important;transform:translateY(-1px)}
.book-root .btn-blue{background:var(--blue) !important;color:#052240 !important;border:1px solid var(--blue)}
.book-root .btn-blue:hover{background:#74c0fc !important;transform:translateY(-1px)}
.book-root .btn-red{background:var(--red) !important;color:#3a0a0a !important;border:1px solid var(--red)}
.book-root .btn-red:hover{background:#ff9b9b !important;transform:translateY(-1px)}
.book-root .btn-sm{padding:6px 14px;font-size:.72rem}
.book-root .btn-lg{padding:14px 32px;font-size:.95rem}
.book-root .btn-block{display:block;width:100%;text-align:center}
.book-root .card{background:var(--bg-card) !important;border:1px solid var(--border);border-radius:8px;padding:20px 24px;margin:16px 0}
.book-root .card-accent{border-left:4px solid var(--accent)}
.book-root .card-gold{border-left:4px solid var(--gold)}
.book-root .card-blue{border-left:4px solid var(--blue)}
.book-root .card-red{border-left:4px solid var(--red)}
.book-root .card-purple{border-left:4px solid var(--purple)}
.book-root .card-title{font-family:var(--f-sans);font-size:.8rem;font-weight:700;color:var(--text-bright) !important;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.book-root .card-body{font-size:.85rem;color:var(--text-soft) !important;line-height:1.7}
.book-root .card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:16px 0}
.book-root .card-grid .card{margin:0}
.book-root details.acc{margin:8px 0;border:1px solid var(--border);border-radius:6px;overflow:hidden;background:var(--bg-card)}
.book-root details.acc summary{padding:12px 16px;font-family:var(--f-sans);font-size:.85rem;font-weight:600;color:var(--text-soft) !important;cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;transition:background .15s}
.book-root details.acc summary::-webkit-details-marker{display:none}
.book-root details.acc summary::before{content:'\\25B6';font-size:.6rem;color:var(--accent) !important;transition:transform .2s}
.book-root details.acc[open] summary::before{transform:rotate(90deg)}
.book-root details.acc summary:hover{background:var(--bg-card2)}
.book-root details.acc .acc-body{padding:4px 16px 14px;border-top:1px solid var(--border-light);font-size:.85rem;color:var(--text-soft) !important;line-height:1.7}
.book-root .tabs{display:flex;flex-wrap:wrap;margin:16px 0;border-bottom:2px solid var(--border)}
.book-root .tabs input[type='radio']{display:none}
.book-root .tabs label{padding:10px 18px;font-family:var(--f-sans);font-size:.78rem;font-weight:600;color:var(--text-dim) !important;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s}
.book-root .tabs label:hover{color:var(--text-soft)}
.book-root .tabs input:checked+label{color:var(--accent) !important;border-bottom-color:var(--accent)}
.book-root .tab-content{display:none;padding:16px 0;font-size:.85rem;color:var(--text-soft) !important;line-height:1.7}
.book-root .progress{margin:12px 0}
.book-root .progress-label{display:flex;justify-content:space-between;font-family:var(--f-sans);font-size:.72rem;color:var(--text-dim) !important;margin-bottom:4px}
.book-root .progress-track{height:8px;background:var(--bg-card3) !important;border-radius:4px;overflow:hidden}
.book-root .progress-bar{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--accent-soft),var(--accent)) !important;transition:width .5s ease}
.book-root .progress-bar.gold{background:linear-gradient(90deg,#c90,var(--gold))}
.book-root .progress-bar.blue{background:linear-gradient(90deg,var(--blue),#74c0fc)}
.book-root .stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:20px 0}
.book-root .stat-card{background:var(--bg-card) !important;border:1px solid var(--border);border-radius:8px;padding:20px 12px;text-align:center}
.book-root .stat-num{font-family:var(--f-mono);font-size:2rem;font-weight:700;color:var(--accent) !important;line-height:1;margin-bottom:4px}
.book-root .stat-num.gold{color:var(--gold)}
.book-root .stat-num.blue{color:var(--blue)}
.book-root .stat-label{font-family:var(--f-sans);font-size:.65rem;color:var(--text-dim) !important;text-transform:uppercase;letter-spacing:.06em}
.book-root .timeline{position:relative;padding:8px 0;margin:16px 0 16px 20px}
.book-root .timeline::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--border)}
.book-root .tl-item{position:relative;padding:6px 0 16px 24px}
.book-root .tl-item::before{content:'';position:absolute;left:-5px;top:10px;width:12px;height:12px;border-radius:50%;background:var(--accent) !important;border:2px solid var(--bg-page)}
.book-root .tl-item.gold::before{background:var(--gold)}
.book-root .tl-item.blue::before{background:var(--blue)}
.book-root .tl-date{font-family:var(--f-mono);font-size:.68rem;color:var(--text-dim) !important;margin-bottom:2px}
.book-root .tl-text{font-size:.85rem;color:var(--text-soft) !important;line-height:1.6}
.book-root .badge{display:inline-block;padding:2px 10px;font-family:var(--f-sans);font-size:.65rem;font-weight:700;border-radius:3px;letter-spacing:.04em;text-transform:uppercase}
.book-root .badge-green{background:var(--accent-bg) !important;color:var(--accent) !important;border:1px solid var(--accent-soft)}
.book-root .badge-gold{background:var(--gold-dim) !important;color:var(--gold) !important;border:1px solid rgba(240,192,64,.25)}
.book-root .badge-blue{background:var(--blue-dim) !important;color:var(--blue) !important;border:1px solid rgba(77,171,247,.25)}
.book-root .badge-red{background:var(--red-dim) !important;color:var(--red) !important;border:1px solid rgba(255,107,107,.25)}
.book-root .callout{display:flex;gap:12px;padding:14px 18px;margin:16px 0;border-radius:6px;background:var(--bg-card2) !important;border:1px solid var(--border);align-items:flex-start}
.book-root .callout-icon{flex-shrink:0;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:1rem;border-radius:50%;background:var(--accent-bg) !important;color:var(--accent)}
.book-root .callout-body{font-size:.82rem;color:var(--text-soft) !important;line-height:1.7}
.book-root pre{background:#0d1a10 !important;color:#c0e0c0 !important;padding:16px 20px;border-radius:6px;overflow-x:auto;font-size:.78rem;line-height:1.7;margin:16px 0;font-family:var(--f-mono);border:1px solid var(--border)}
.book-root code{font-family:var(--f-mono);font-size:.82rem;background:var(--accent-bg) !important;padding:2px 6px;border-radius:3px;color:var(--accent)}
.book-root pre code{background:transparent !important;padding:0;color:inherit}
.book-root table{width:100%;border-collapse:collapse;margin:16px 0;font-size:.8rem;border-radius:6px;overflow:hidden}
.book-root th{background:var(--bg-card3) !important;color:var(--text-bright) !important;padding:10px 14px;text-align:left;font-weight:600;font-family:var(--f-sans);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}
.book-root td{padding:10px 14px;border-bottom:1px solid var(--border-light);color:var(--text-soft)}
.book-root figure{margin:24px 0;text-align:center}
.book-root figure img{max-width:100%;border-radius:6px;border:1px solid var(--border)}
.book-root figure figcaption{font-family:var(--f-sans);font-size:.7rem;color:var(--text-dim) !important;margin-top:8px;font-style:italic}
.book-root ul,.book-root ol{padding-left:24px;margin:8px 0 20px}
.book-root li{margin-bottom:6px;color:var(--text-soft) !important;line-height:1.7}
.book-root ul.checklist{list-style:none;padding-left:0}
.book-root ul.checklist li::before{content:'\\2610';color:var(--text-dim) !important;margin-right:8px}
.book-root ul.checklist li.checked::before{content:'\\2611';color:var(--accent)}
.book-root kbd{display:inline-block;padding:2px 8px;font-family:var(--f-mono);font-size:.72rem;background:var(--bg-card3) !important;border:1px solid var(--border);border-radius:3px;color:var(--text-soft) !important;box-shadow:0 1px 2px rgba(0,0,0,.2)}
.book-root hr{border:none;border-top:1px solid var(--border);margin:24px 0}
.book-root .footnote{font-family:var(--f-sans);font-size:.72rem;color:var(--text-dim) !important;border-top:1px solid var(--border);padding-top:12px;margin-top:28px;line-height:1.6}
.book-root .alert{padding:14px 18px;margin:16px 0;border-radius:6px;border-left:4px solid;font-size:.82rem;line-height:1.7}
.book-root .alert-green{background:var(--accent-bg) !important;border-color:var(--accent);color:var(--text-soft)}
.book-root .alert-gold{background:var(--gold-dim) !important;border-color:var(--gold);color:var(--text-soft)}
.book-root .alert-red{background:var(--red-dim) !important;border-color:var(--red);color:var(--text-soft)}
.book-root .alert-blue{background:var(--blue-dim) !important;border-color:var(--blue);color:var(--text-soft)}
.book-root .fold{margin:12px 0}
.book-root .fold summary{cursor:pointer;font-family:var(--f-sans);font-weight:600;color:var(--accent) !important;font-size:.82rem;padding:4px 0}
@media(max-width:640px){.book-root{padding:16px 12px;font-size:15px}.book-cover{padding:40px 20px 32px}.book-cover h1{font-size:1.6rem}.book-root .card-grid{grid-template-columns:1fr}.book-root .stat-grid{grid-template-columns:repeat(2,1fr)}.chapter h2{font-size:1.2rem}}
"""

def md_to_html(md_text):
    """markdown -> HTML with all dynamic elements"""
    html = md_text
    
    # badges: ++text++
    html = re.sub(r'\+\+([^+]+)\+\+', r'<span class="badge badge-green">\1</span>', html)
    
    # keybindings: {{key}}
    html = re.sub(r'\{\{([^}]+)\}\}', r'<kbd>\1</kbd>', html)
    
    # checklists
    html = re.sub(r'^- \[ \] (.+)$', r'<li class="checklist unchecked">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^- \[x\] (.+)$', r'<li class="checklist checked">\1</li>', html, flags=re.MULTILINE)
    
    # details accordion
    html = re.sub(r':::details\s+(.+?)\n(.*?):::', lambda m: f'<details class="acc"><summary>{m.group(1)}</summary><div class="acc-body">{m.group(2)}</div></details>', html, flags=re.DOTALL)
    
    # cards
    html = re.sub(r':::card-accent\s+(.+?)\n(.*?):::', lambda m: f'<div class="card card-accent"><div class="card-title">{m.group(1)}</div><div class="card-body">{m.group(2)}</div></div>', html, flags=re.DOTALL)
    html = re.sub(r':::card\s+(.+?)\n(.*?):::', lambda m: f'<div class="card"><div class="card-title">{m.group(1)}</div><div class="card-body">{m.group(2)}</div></div>', html, flags=re.DOTALL)
    
    # alerts — ":::alert-TYPE [선택: 같은 줄 제목]\n본문\n:::"
    # 제목이 같은 줄에 붙으면 (\w+)\n 이 매칭 안 되던 버그 수정 — 제목 그룹을 선택적으로 허용
    def _alert_repl(m):
        kind, head_title, body = m.group(1), m.group(2), m.group(3)
        head = f'<strong>{head_title}</strong><br>' if head_title else ''
        return f'<div class="alert alert-{kind}">{head}{body}</div>'
    html = re.sub(r':::alert-(\w+)(?:[ \t]+([^\n]+))?\n(.*?):::', _alert_repl, html, flags=re.DOTALL)

    # callouts — ":::callout 아이콘 [선택: 같은 줄 제목]\n본문\n:::"
    def _callout_repl(m):
        icon, head_title, body = m.group(1), m.group(2), m.group(3)
        head = f'<strong>{head_title}</strong><br>' if head_title else ''
        return f'<div class="callout"><div class="callout-icon">{icon}</div><div class="callout-body">{head}{body}</div></div>'
    html = re.sub(r':::callout\s+(\S+)(?:[ \t]+([^\n]+))?\n(.*?):::', _callout_repl, html, flags=re.DOTALL)
    
    # progress bars
    html = re.sub(r'::progress\[([^\]]+)\]\((\d+)\)', r'<div class="progress"><div class="progress-label"><span>\1</span><span>\2%</span></div><div class="progress-track"><div class="progress-bar" style="width:\2%"></div></div></div>', html)
    
    # stat cards
    html = re.sub(r'::stat\[([^\]]+)\]\(([^)]+)\)', r'<div class="stat-card"><div class="stat-num">\1</div><div class="stat-label">\2</div></div>', html)
    
    # buttons
    html = re.sub(r'::btn(?:-(\w+))?\[([^\]]+)\]\(([^)]*)\)', r'<a class="btn btn-\1" href="\3">\2</a>', html)
    
    # stat-grid wrapper
    html = re.sub(r':::stat-grid\n(.*?):::', r'<div class="stat-grid">\1</div>', html, flags=re.DOTALL)
    
    # card-grid wrapper
    html = re.sub(r':::card-grid\n(.*?):::', r'<div class="card-grid">\1</div>', html, flags=re.DOTALL)
    
    # \uc218\ud3c9\uc120 \u2014 \ub2e8\ub3c5 \uc904\uc5d0 ---\ub9cc \uc788\uc73c\uba74 <hr> (\uadf8\ub300\ub85c \ubc29\uce58\ub418\uba74 \ud654\uba74\uc5d0 "---" \ud14d\uc2a4\ud2b8\ub85c \ub178\ucd9c\ub428)
    html = re.sub(r'^-{3,}$', '<hr>', html, flags=re.MULTILINE)

    # headings
    html = re.sub(r'^## (.+)$', lambda m: f'</p><div class="chapter" data-number="\u25a3"><h2>{m.group(1)}</h2></div><p>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # bold/italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # blockquote
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # code blocks
    html = re.sub(r'\`\`\`(\w*)\n(.*?)\`\`\`', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'\`([^\`]+)\`', r'<code>\1</code>', html)
    
    # images
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<figure><img src="\2" alt="\1"><figcaption>\1</figcaption></figure>', html)
    
    # list items
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # tables
    html = re.sub(r'^\|(.+)\|$', lambda m: '<tr>' + ''.join('<td>' + c.strip() + '</td>' for c in m.group(1).split('|')) + '</tr>', html, flags=re.MULTILINE)
    html = re.sub(r'<td>[-:\s]+</td>', '', html)
    
    # paragraph splitting
    lines = html.split('\n')
    result = []; in_p = False
    for line in lines:
        s = line.strip()
        if not s:
            if in_p: result.append('</p>'); in_p = False
            continue
        if s.startswith('<') and not s.startswith('<p'):
            if in_p: result.append('</p>'); in_p = False
            result.append(line)
            continue
        if not in_p: result.append('<p>'); in_p = True; result.append(s)
        else: result.append('<br>' + s)
    if in_p: result.append('</p>')
    output = '\n'.join(result)
    
    # table wrapping (after paragraph split)
    output = re.sub(r'(<tr>[\s\S]*?</tr>\n?)+', r'<table>\g<0></table>', output)
    # checklist wrapping
    output = re.sub(r'(<li class="checklist[^>]*>.*?</li>\n?)+', r'<ul class="checklist">\g<0></ul>', output)
    # regular list wrapping
    output = re.sub(r'(<li>(?!.*checklist).*?</li>\n?)+', r'<ul>\g<0></ul>', output)
    
    return output

def _inline_to_html(text):
    """간단한 인라인 HTML 변환 (블록 감지 없이)"""
    t = text
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'\+\+([^+]+)\+\+', r'<span class="badge badge-green">\1</span>', t)
    t = re.sub(r'\{\{([^}]+)\}\}', r'<kbd>\1</kbd>', t)
    return t

def build_booklet(content_md, title, series=None, subtitle=None, author="박태정", lang="ko"):
    """마크다운 → 완전체 단행본 HTML"""
    # book-cover에서 이미 <h1>{title}</h1>을 렌더링하므로,
    # 본문 선두에 동일 목적의 '# 제목' 줄이 있으면 중복 렌더링됨 — 제거
    content_md = re.sub(r'^#\s+.+\n+', '', content_md, count=1)
    body = md_to_html(content_md)
    series_html = f'<div class="series">{series}</div>' if series else ''
    sub_html = f'<div class="subtitle">{subtitle}</div>' if subtitle else ''

    return f"""<!-- Tistory Booklet — generator.py v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')} -->
<style>{BOOKLET_CSS}</style>
<div class="book-root" lang="{lang}">
  <div class="book-cover">
    {series_html}
    <h1>{title}</h1>
    {sub_html}
    <div class="meta">{author} · {datetime.now().strftime('%Y.%m')}</div>
  </div>
  {body}
  <div class="footnote">Tistory Publishing Pipeline v2.0 — generator.py 자동 생성</div>
</div>"""

def resolve_blog(name_or_slug):
    """블로그명/슬러그 → {slug, account, lang, name}"""
    if name_or_slug in BLOG_MAP:
        info = BLOG_MAP[name_or_slug]
        return {**info, "name": name_or_slug}
    # 슬러그로 역검색
    for name, info in BLOG_MAP.items():
        if info["slug"] == name_or_slug:
            return {**info, "name": name}
    return None

def load_accounts():
    """accounts.json 로드 (상대/절대 경로 모두 시도)"""
    paths = [
        BASE / "accounts.json",
        Path.home() / "dtslib-papyrus/tools/tistory/accounts.json",
    ]
    for p in paths:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None

def generate_post(md_content, blog_name, title, series=None, subtitle=None, tags=None):
    """마크다운 → 발행용 JSON 포스트 생성"""
    blog = resolve_blog(blog_name)
    if not blog:
        raise ValueError(f"알 수 없는 블로그: {blog_name}\n  가능: {chr(44).join(BLOG_MAP.keys())}")
    html = build_booklet(md_content, title, series=series, subtitle=subtitle, lang=blog["lang"])
    
    return {
        "account": blog["account"],
        "blog_slug": blog["slug"],
        "blog_name": blog["name"],
        "title": title,
        "content": html,
        "tags": tags or [],
        "series": series or "",
        "visibility": "public",
        "generated": datetime.now().isoformat(),
    }

def generate_from_file(input_path, blog_name, title=None, series=None, tags=None):
    """파일 → 포스트 JSON"""
    content = Path(input_path).read_text(encoding="utf-8")
    if not title:
        title = Path(input_path).stem
    return generate_post(content, blog_name, title, series=series, tags=tags)

def save_post(post, output_dir=None):
    """포스트 JSON 저장"""
    out = Path(output_dir or POSTS_DIR)
    safe = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', post['title'])[:40]
    path = out / f"{post['blog_name']}_{safe}.json"
    path.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def publish_post(post):
    """MCP _tistory_publish.py 연동 발행"""
    try:
        sys.path.insert(0, str(Path.home() / "dtslib-papyrus/tools/mcp_distributor"))
        from _tistory_publish import publish_tistory
    except ImportError:
        # fallback: publisher.py
        sys.path.insert(0, str(BASE))
        from publisher import publish_post as legacy_publish
        print("⚠ _tistory_publish.py 없음 → publisher.py fallback")
        return {"status": "fallback", "note": "publisher.py로 직접 실행 필요"}
    
    result = publish_tistory(
        account=post["account"],
        blog=post["blog_slug"],
        title=post["title"],
        content_html=post["content"],
        tags=post.get("tags", []),
        visibility=post.get("visibility", "public"),
    )
    return result

def parse_command(text):
    """자연어 명령 파싱: '철학자박씨에 존재와 시간 올려줘'"""
    patterns = [
        (r'(.+?)에\s*(.+?)(?: 올려| 업로드| 발행| 올려줘| 업로드해)', lambda m: (m.group(1).strip(), m.group(2).strip())),
        (r'(.+?):\s*(.+)', lambda m: (m.group(1).strip(), m.group(2).strip())),
    ]
    for pat, fn in patterns:
        m = re.search(pat, text)
        if m:
            blog, title = fn(m)
            if blog in BLOG_MAP:
                return blog, title
    return None, None

# ── CLI ──
def main():
    parser = argparse.ArgumentParser(description="📚 Tistory Booklet Generator v2.0")
    parser.add_argument("--blog", "-b", help="블로그명 (예: 철학자박씨, blogger-parksy)")
    parser.add_argument("--title", "-t", help="제목")
    parser.add_argument("--input", "-i", help="입력 파일 (.md / .txt)")
    parser.add_argument("--content", "-c", help="직접 콘텐츠 입력 (문자열)")
    parser.add_argument("--series", help="시리즈명")
    parser.add_argument("--tags", nargs="+", default=[], help="태그 목록")
    parser.add_argument("--say", help="자연어 명령 (예: --say '철학자박씨에 존재와 시간 올려줘')")
    parser.add_argument("--publish", "-p", action="store_true", help="변환 후 자동 발행")
    parser.add_argument("--list", "-l", action="store_true", help="블로그 목록 출력")
    parser.add_argument("--out", "-o", help="출력 경로")
    args = parser.parse_args()

    if args.list:
        print("📚 Tistory 단행본 출판사 — 25개 블로그")
        print("=" * 50)
        for name, info in sorted(BLOG_MAP.items()):
            acc = info["account"]
            lang = "🇰🇷" if info["lang"] == "ko" else "🇬🇧"
            print(f"  {lang} {name:20s} → {info['slug']:20s} ({acc})")
        print("=" * 50)
        print(f"  총 {len(BLOG_MAP)}개 블로그")
        return

    # 자연어 명령 파싱
    if args.say:
        blog_name, title = parse_command(args.say)
        if not blog_name:
            print(f"❌ 명령을 이해하지 못했어: {args.say}")
            print("   예: --say '철학자박씨에 존재와 시간 올려줘'")
            sys.exit(1)
        args.blog = blog_name
        if not args.title:
            args.title = title

    if not args.blog:
        parser.print_help()
        sys.exit(1)

    if not args.title:
        print("❌ --title 필수")
        sys.exit(1)

    # 콘텐츠 소스
    if args.input:
        post = generate_from_file(args.input, args.blog, args.title, args.series, args.tags)
    elif args.content:
        post = generate_post(args.content, args.blog, args.title, args.series, args.tags)
    else:
        print("❌ --input 또는 --content 필수")
        sys.exit(1)

    # 저장
    out = save_post(post, args.out)
    print(f"   블로그: {post['blog_name']} ({post['blog_slug']})")
    print(f"   제목:   {post['title']}")
    print(f"   언어:   {'🇰🇷 한국어' if post.get('lang', 'ko') == 'ko' else '🇬🇧 영어'}")
    print(f"   태그:   {post['tags']}")
    print(f"   크기:   {len(post['content'])} bytes")

    # 발행
    if args.publish:
        result = publish_post(post)
        print(f"   결과: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main()

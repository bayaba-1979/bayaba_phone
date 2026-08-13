#!/usr/bin/env python3
"""
md_to_page.py — 범용 Markdown → GitHub Pages HTML 변환기

입력:  .md 파일 (노트북·README·백서·가이드 등)
출력:  풀인터랙티브 HTML (JS 복사버튼·PWA·다크모드)

사용법:
  python3 scripts/md_to_page.py <입력.md> [--out 출력.html]
  python3 scripts/md_to_page.py --all                          # 전체 콘텐츠 맵 기반 일괄 변환
  python3 scripts/md_to_page.py --part P1                      # Part 1만 변환
  python3 scripts/md_to_page.py <입력.md> --title "제목" --chap "Ch1.1"

특징:
  - markdown → HTML (python-markdown)
  - 공통 디자인 시스템 적용 (CSS 토큰·다크모드·반응형)
  - 모든 <pre> 블록에 복사 버튼 (JS clipboard API)
  - <details> 아코디언·<table>·info-box 등 컴포넌트 보존
  - GitHub Pages + Tistory CSS-only 듀얼 출력 지원 (--tistory 플래그)
"""

import sys
import re
import os
import json
import html as html_mod
from datetime import datetime
from pathlib import Path

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


# ═══════════════════════════════════════════════════════════════
# SHARED CSS (Design System)
# ═══════════════════════════════════════════════════════════════

SHARED_CSS = """<style>
:root{--bg:#f8f7f4;--s:#fefefe;--s2:#f0ede6;--t:#13110e;--t2:#4a4438;--t3:#7a7260;--bdr:#d9d2c0;--bdr2:#e8e3d4;--a:#1a3a5c;--a2:#2d5a88;--al:#e8f0f8;--g:#2d5a3e;--gbg:#e6f0e6;--rd:#a8403a;--rbg:#f8e8e6;--p:#5a3e7a;--pbg:#efe6f6;--y:#8a6a18;--ybg:#faf3e0;--o:#c06020;--obg:#fef0e4;--cbg:#eeebe4;--sh:0 1px 3px rgba(19,17,14,0.04);--r:8px;--rs:5px;--ff:"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;--ffm:"JetBrains Mono","D2Coding","Consolas",monospace}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14120e;--s:#1c1a14;--s2:#26231a;--t:#e8e4d8;--t2:#a89e88;--t3:#6e6450;--bdr:#3a3426;--bdr2:#2e2a1e;--a:#5a8eb8;--a2:#6ea8d8;--al:#162028;--g:#58a870;--gbg:#162818;--rd:#d06860;--rbg:#281816;--p:#9a78c0;--pbg:#201830;--y:#c8a040;--ybg:#282010;--o:#e89850;--obg:#2a1c10;--cbg:#201e16}}
:root[data-theme="dark"]{--bg:#14120e;--s:#1c1a14;--s2:#26231a;--t:#e8e4d8;--t2:#a89e88;--t3:#6e6450;--bdr:#3a3426;--bdr2:#2e2a1e;--a:#5a8eb8;--a2:#6ea8d8;--al:#162028;--g:#58a870;--gbg:#162818;--rd:#d06860;--rbg:#281816;--p:#9a78c0;--pbg:#201830;--y:#c8a040;--ybg:#282010;--o:#e89850;--obg:#2a1c10;--cbg:#201e16}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--ff);font-size:15px;line-height:1.74;color:var(--t);background:var(--bg);max-width:860px;margin:0 auto;padding:0 20px 80px;overflow-x:hidden}
.hero{text-align:center;padding:28px 0 16px;border-bottom:2px solid var(--bdr);margin-bottom:20px}
.hero .eyebrow{font-size:11px;letter-spacing:.18em;color:var(--a);text-transform:uppercase;margin-bottom:5px;font-weight:700}
.hero h1{font-size:1.45rem;font-weight:800;letter-spacing:-.02em;margin-bottom:4px;line-height:1.25}
.hero .subtitle{font-size:.9rem;color:var(--t2);line-height:1.55}
section{margin-bottom:24px}
h2{font-size:1.06rem;font-weight:800;border-bottom:1px solid var(--bdr);padding-bottom:6px;margin-bottom:10px}
h3{font-size:.92rem;font-weight:700;margin-bottom:6px;color:var(--a)}
h4{font-size:.84rem;font-weight:700;margin-bottom:4px;color:var(--t)}
p{margin-bottom:7px;color:var(--t2)}
p strong{color:var(--t)}
ul,ol{margin-bottom:10px;padding-left:22px;color:var(--t2)}
li{margin-bottom:3px}
li strong{color:var(--t)}
blockquote{margin-bottom:10px;padding:8px 12px;background:var(--al);border-left:3px solid var(--a);border-radius:0 var(--rs) var(--rs) 0;color:var(--t2);font-size:.9rem}
blockquote strong{color:var(--t)}
.tbl-wrap{max-width:100%;overflow-x:auto;margin-bottom:10px;-webkit-overflow-scrolling:touch}
.tbl-wrap table{min-width:480px}
table{width:100%;border-collapse:collapse;margin-bottom:10px;font-size:.82rem;line-height:1.45}
table th,table td{padding:6px 9px;border:1px solid var(--bdr2);text-align:left;vertical-align:top}
table th{background:var(--s2);font-weight:700;font-size:.73rem;letter-spacing:.04em;color:var(--t);white-space:nowrap}
table td{color:var(--t2)}
.copy-wrap{position:relative;margin-bottom:10px}
.copy-wrap pre{margin-bottom:0}
pre{background:var(--cbg);padding:10px 44px 10px 13px;border-radius:var(--r);font-family:var(--ffm);font-size:.76rem;line-height:1.55;overflow-x:auto;margin-bottom:10px;border:1px solid var(--bdr2);white-space:pre-wrap;word-break:break-all}
.copy-btn{position:absolute;top:6px;right:6px;width:30px;height:30px;border-radius:5px;border:1px solid var(--bdr2);background:var(--s);color:var(--t3);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.78rem;transition:all .15s;z-index:1}
.copy-btn:hover{background:var(--a);color:#fff;border-color:var(--a)}
.copy-btn.copied{background:var(--g);color:#fff;border-color:var(--g)}
code{font-family:var(--ffm);font-size:.88em;background:var(--cbg);padding:1px 5px;border-radius:3px}
pre code{background:none;padding:0;font-size:inherit}
.info-box{background:var(--al);border-left:3px solid var(--a);padding:9px 13px;border-radius:0 var(--rs) var(--rs) 0;margin-bottom:10px;font-size:.83rem;color:var(--t)}
.info-box.green{background:var(--gbg);border-left-color:var(--g)}
.info-box.red{background:var(--rbg);border-left-color:var(--rd)}
.info-box.gold{background:var(--ybg);border-left-color:var(--y)}
.info-box.purple{background:var(--pbg);border-left-color:var(--p)}
.info-box strong{color:var(--a)}.info-box.green strong{color:var(--g)}.info-box.red strong{color:var(--rd)}.info-box.gold strong{color:var(--y)}.info-box.purple strong{color:var(--p)}
.chip{display:inline-block;padding:2px 7px;border-radius:9px;font-size:.7rem;font-weight:700;letter-spacing:.03em;white-space:nowrap}
.chip-pages{background:#d8e8f6;color:#1a3a5c}.chip-tistory{background:#f8e0d0;color:#6e3000}
@media(prefers-color-scheme:dark){.chip-pages{background:#1a2838;color:#8cc0f0}.chip-tistory{background:#2a1c10;color:#f0a868}}
.card{background:var(--s);border:1px solid var(--bdr);border-radius:var(--r);padding:12px 14px;margin-bottom:8px;box-shadow:var(--sh)}
.card-hd{font-weight:800;font-size:.88rem;margin-bottom:3px}
.card-dsc{color:var(--t2);font-size:.82rem}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:10px}
@media(max-width:600px){.grid2{grid-template-columns:1fr}}
details.acc{background:var(--s);border:1px solid var(--bdr);border-radius:var(--r);margin-bottom:6px;box-shadow:var(--sh);overflow:hidden}
details.acc>summary{padding:11px 14px;font-weight:700;font-size:.88rem;cursor:pointer;list-style:none;user-select:none;display:flex;align-items:center;gap:7px;color:var(--t)}
details.acc>summary::-webkit-details-marker{display:none}
details.acc>summary::before{content:"▶";font-size:.55rem;color:var(--a);transition:transform .2s;display:inline-block;min-width:10px}
details.acc[open]>summary::before{transform:rotate(90deg)}
details.acc>summary:hover{background:var(--s2)}
details.acc>.acc-body{padding:0 14px 14px;overflow-x:hidden}
.footer{text-align:center;padding:16px 0 4px;border-top:1px solid var(--bdr);color:var(--t3);font-size:.74rem;margin-top:24px}
@media(max-width:480px){body{font-size:14px;padding:0 12px 60px}.hero h1{font-size:1.2rem}}
</style>"""

SHARED_JS = """<script>
(function(){
var pres=document.querySelectorAll('pre');
pres.forEach(function(pre){
var wrap=document.createElement('div');
wrap.className='copy-wrap';
pre.parentNode.insertBefore(wrap,pre);
wrap.appendChild(pre);
var btn=document.createElement('button');
btn.className='copy-btn';
btn.title='복사';
btn.textContent='📋';
btn.onclick=function(){
var txt=pre.textContent;
navigator.clipboard.writeText(txt).then(function(){
btn.textContent='✅';btn.classList.add('copied');
setTimeout(function(){btn.textContent='📋';btn.classList.remove('copied');},1500);
}).catch(function(){
var ta=document.createElement('textarea');
ta.value=txt;ta.style.position='fixed';ta.style.opacity='0';
document.body.appendChild(ta);ta.select();
document.execCommand('copy');document.body.removeChild(ta);
btn.textContent='✅';btn.classList.add('copied');
setTimeout(function(){btn.textContent='📋';btn.classList.remove('copied');},1500);
});
};
});
})();
</script>"""


# ═══════════════════════════════════════════════════════════════
# CONTENT MAP — 8 Parts · 31 Chapters · source files
# ═══════════════════════════════════════════════════════════════

CONTENT_MAP = {
    "P1": {
        "title": "온보딩 — 폰 하나로 AI 워크스테이션",
        "slug": "p1-onboarding",
        "chapters": {
            "Ch1.1": {"title": "워크스테이션 백서", "slug": "ch1-1-workstation-whitepaper",
                       "sources": ["helena-programming/templates/ai-workstation-setup.html"]},
            "Ch1.2": {"title": "Termux·proot·Ubuntu", "slug": "ch1-2-termux-proot",
                       "sources": ["_notebook/15-proot-report.md", "_notebook/07-cli-reference.md"]},
            "Ch1.3": {"title": "Claude Code·DeepSeek 배선", "slug": "ch1-3-claude-deepseek",
                       "sources": ["_notebook/ai-agents-cc-ds-grok-comparison-2026-07-25.md", "CONSTITUTION.md"]},
            "Ch1.4": {"title": "GitHub·Pages·무료전시장", "slug": "ch1-4-github-pages",
                       "sources": ["_notebook/04-github-pages.md", "_notebook/41-github-free-maxout_Boss.md"]},
            "Ch1.5": {"title": "실전 설치 사례", "slug": "ch1-5-real-cases",
                       "sources": ["_notebook/41-beginner-install-manual_Grok.md", "_notebook/40-pc-wsl-setup_Boss.md"]},
        }
    },
    "P2": {
        "title": "인프라 — 연결과 자동화",
        "slug": "p2-infra",
        "chapters": {
            "Ch2.1": {"title": "텔레그램·보고회의실", "slug": "ch2-1-telegram",
                       "sources": ["_notebook/03-telegram.md"]},
            "Ch2.2": {"title": "Discord·커뮤니티", "slug": "ch2-2-discord",
                       "sources": ["_notebook/02-discord.md"]},
            "Ch2.3": {"title": "Phone MCP·하드웨어 제어", "slug": "ch2-3-phone-mcp",
                       "sources": ["_notebook/10-phone-mcp.md", "_notebook/01-arch.md"]},
            "Ch2.4": {"title": "건강체크·돌봄 데몬", "slug": "ch2-4-health-check",
                       "sources": ["_notebook/11-health.md", "_notebook/14-daemon-design.md"]},
        }
    },
    "P3": {
        "title": "PD Pipeline — URL 하나로 숏폼 영상",
        "slug": "p3-pd-pipeline",
        "chapters": {
            "Ch3.1": {"title": "파이프라인 개요", "slug": "ch3-1-overview",
                       "sources": ["helena-programming/docs/PIPELINE.md", "_notebook/78-pd-pipeline-whitepaper_Claude.md"]},
            "Ch3.2": {"title": "P0 URL→콘텐츠 이해", "slug": "ch3-2-parse",
                       "sources": ["_notebook/72-pd-pipeline-standard-v2-lock_Grok.md"]},
            "Ch3.3": {"title": "P1·P2 캡처·음성합성", "slug": "ch3-3-capture-tts",
                       "sources": ["_notebook/59-grok-video-process-whitepaper_Grok.md"]},
            "Ch3.4": {"title": "P3·P4 영상·자막", "slug": "ch3-4-render",
                       "sources": ["_notebook/65-video-playable-encode-fix_Grok.md"]},
            "Ch3.5": {"title": "Director·연출 시스템", "slug": "ch3-5-director",
                       "sources": ["_notebook/60-director-pro-v8-wish_Grok.md"]},
            "Ch3.6": {"title": "BGM·브릿지·인코딩", "slug": "ch3-6-bgm-bridge",
                       "sources": ["_notebook/61-landing-6clip-bgm-plan_Grok.md", "_notebook/70-font-bgm-fix_Grok.md"]},
        }
    },
    "P4": {
        "title": "AI 목소리 — 내 목소리 복제",
        "slug": "p4-voice",
        "chapters": {
            "Ch4.1": {"title": "3트랙 목소리 전략", "slug": "ch4-1-strategy",
                       "sources": ["_notebook/69-voice-engine-plugin-final_Grok.md"]},
            "Ch4.2": {"title": "ParksyTTS·온디바이스 추론", "slug": "ch4-2-parksytts",
                       "sources": ["_notebook/70-ai-voice-core-gift-local-train_Grok.md"]},
            "Ch4.3": {"title": "Edge TTS·Piper", "slug": "ch4-3-edge-piper",
                       "sources": ["_notebook/74-tts-rvc-lightweight-solution_Claude.md"]},
            "Ch4.4": {"title": "RVC·학습·성우 백서", "slug": "ch4-4-rvc",
                       "sources": ["_notebook/80-ai-voice-actor-whitepaper_Boss.md"]},
        }
    },
    "P5": {
        "title": "출판·배포 — 만든 걸 세상에",
        "slug": "p5-publishing",
        "chapters": {
            "Ch5.1": {"title": "Paste Pipeline", "slug": "ch5-1-paste",
                       "sources": ["helena-programming/templates/paste-pipeline.html"]},
            "Ch5.2": {"title": "Step-Down Cascade", "slug": "ch5-2-cascade",
                       "sources": ["helena-programming/templates/stepdown-cascade.html"]},
            "Ch5.3": {"title": "루프백·사이버네틱 검증", "slug": "ch5-3-loopback",
                       "sources": ["helena-programming/templates/loopback-discovery.html"]},
            "Ch5.4": {"title": "YouTube·네이버 연동", "slug": "ch5-4-yt-naver",
                       "sources": ["_notebook/06-youtube.md", "_notebook/23-naver-webzine-solution.md"]},
            "Ch5.5": {"title": "WSL 슬롯·확장 로드맵", "slug": "ch5-5-wsl",
                       "sources": ["helena-programming/templates/s21-wsl-upgrade-path.html"]},
        }
    },
    "P6": {
        "title": "설계·아키텍처 — 이 모든 게 왜 작동하는가",
        "slug": "p6-architecture",
        "chapters": {
            "Ch6.1": {"title": "2계층·5×5×5 생태계", "slug": "ch6-1-ecosystem",
                       "sources": ["configs/ecosystem-map.json", "helena-programming/templates/ecosystem-knowledge-workflow.html"]},
            "Ch6.2": {"title": "슬롯 아키텍처·환경 독립", "slug": "ch6-2-slots",
                       "sources": ["helena-programming/templates/wsl-expansion-slot.html"]},
            "Ch6.3": {"title": "ROI·공짜 클라우드 정당화", "slug": "ch6-3-roi",
                       "sources": ["helena-programming/templates/ecosystem-roi-justification.html"]},
            "Ch6.4": {"title": "역방향 출판 패턴", "slug": "ch6-4-reverse-publishing",
                       "sources": ["_notebook/publishing/tistory-textbook-methodology.html"]},
            "Ch6.5": {"title": "4로봇·에이전트 방법론", "slug": "ch6-5-agents",
                       "sources": ["_notebook/31-agent-roles_Grok.md", "CONSTITUTION.md"]},
        }
    },
    "P7": {
        "title": "돌봄 트랙 — 기술의 목적",
        "slug": "p7-care",
        "chapters": {
            "Ch7.1": {"title": "기초생계·치매·장애 솔루션", "slug": "ch7-1-solutions",
                       "sources": ["helana_log/docs/tracks/basic-livelihood.md",
                                   "helana_log/docs/tracks/dementia-care.md",
                                   "helana_log/docs/tracks/disability-welfare.md"]},
            "Ch7.2": {"title": "대화록·방법론·아이덴티티", "slug": "ch7-2-identity",
                       "sources": ["helana_log/docs/IDENTITY.md", "helana_log/docs/METHOD.md"]},
        }
    },
    "P8": {
        "title": "실전 — 후기와 교훈",
        "slug": "p8-real-world",
        "chapters": {
            "Ch8.1": {"title": "설치 삽질 포스트모템", "slug": "ch8-1-postmortem",
                       "sources": ["_notebook/40-pc-wsl-setup_Boss.md", "_notebook/13-midterm-eval.md"]},
            "Ch8.2": {"title": "저사양 폰 AI 생존 테스트", "slug": "ch8-2-survival",
                       "sources": ["_notebook/99-devlog.md"]},
            "Ch8.3": {"title": "Hub vs Tistory 아키텍처", "slug": "ch8-3-architecture",
                       "sources": ["helena-programming/templates/hub-vs-history-architecture.html"]},
            "Ch8.4": {"title": "출판 스케줄러", "slug": "ch8-4-scheduler",
                       "sources": ["helena-programming/templates/publishing-scheduler.html"]},
        }
    },
}


# ═══════════════════════════════════════════════════════════════
# MARKDOWN → HTML
# ═══════════════════════════════════════════════════════════════

def md_to_html(text):
    """Convert markdown text to HTML body content."""
    if HAS_MARKDOWN:
        return markdown.markdown(text, extensions=['extra', 'codehilite', 'tables', 'fenced_code'])
    else:
        # Bare fallback: simple paragraph and code block conversion
        return _bare_md_to_html(text)


def _bare_md_to_html(text):
    """Minimal markdown converter (no external lib)."""
    lines = text.split('\n')
    out = []
    in_code = False
    code_buf = []
    in_table = False
    table_buf = []

    for line in lines:
        # Code blocks
        if line.startswith('```'):
            if in_code:
                lang = in_code if isinstance(in_code, str) else ''
                code_html = html_mod.escape('\n'.join(code_buf))
                out.append(f'<pre><code>{code_html}</code></pre>')
                code_buf = []
                in_code = False
            else:
                in_code = line[3:].strip() or True
            continue
        if in_code:
            code_buf.append(line)
            continue

        # Headings
        if line.startswith('#### '):
            out.append(f'<h4>{_inline_md(line[5:])}</h4>')
        elif line.startswith('### '):
            out.append(f'<h3>{_inline_md(line[4:])}</h3>')
        elif line.startswith('## '):
            out.append(f'<h2>{_inline_md(line[3:])}</h2>')
        elif line.startswith('# '):
            out.append(f'<h1>{_inline_md(line[2:])}</h1>')
        # Tables
        elif '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_buf = []
            table_buf.append(line)
            continue
        elif in_table and not ('|' in line and line.strip().startswith('|')):
            out.append(_render_table(table_buf))
            in_table = False
            table_buf = []
        # Blockquotes
        elif line.startswith('> '):
            out.append(f'<blockquote>{_inline_md(line[2:])}</blockquote>')
        # Lists
        elif re.match(r'^\s*[\-\*]\s', line):
            out.append(f'<li>{_inline_md(re.sub(r"^\s*[\-\*]\s+", "", line))}</li>')
        elif re.match(r'^\s*\d+[\.\)]\s', line):
            out.append(f'<li>{_inline_md(re.sub(r"^\s*\d+[\.\)]\s+", "", line))}</li>')
        # Empty lines
        elif not line.strip():
            out.append('<br>')
        # Regular paragraphs
        else:
            out.append(f'<p>{_inline_md(line)}</p>')

    if in_code:
        code_html = html_mod.escape('\n'.join(code_buf))
        out.append(f'<pre><code>{code_html}</code></pre>')
    if in_table and table_buf:
        out.append(_render_table(table_buf))

    return '\n'.join(out)


def _inline_md(text):
    """Convert inline markdown (bold, italic, code, links)."""
    text = html_mod.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color:var(--a)">\1</a>', text)
    return text


def _render_table(lines):
    """Render a simple markdown table."""
    if len(lines) < 2:
        return ''
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().split('|') if c.strip()]
        if all(re.match(r'^[\-\: ]+$', c) for c in cells):
            continue  # separator row
        rows.append(cells)
    if not rows:
        return ''
    html_rows = []
    for i, row in enumerate(rows):
        tag = 'th' if i == 0 else 'td'
        cells_html = ''.join(f'<{tag}>{_inline_md(c)}</{tag}>' for c in row)
        html_rows.append(f'<tr>{cells_html}</tr>')
    return f'<div class="tbl-wrap"><table>{"".join(html_rows)}</table></div>'


# ═══════════════════════════════════════════════════════════════
# PAGE BUILDER
# ═══════════════════════════════════════════════════════════════

def build_page(content_html, title, eyebrow=None, subtitle=None, footer_text=None, include_js=True):
    """Wrap content in the shared page template."""
    eyebrow_html = f'<div class="eyebrow">{html_mod.escape(eyebrow)}</div>' if eyebrow else ''
    subtitle_html = f'<div class="subtitle">{subtitle}</div>' if subtitle else ''

    footer = footer_text or f'📚 Helena Programming · Pages Textbook<br>🌐 <a href="https://helena751107.github.io/helena-programming/pages/" style="color:var(--a)">교재 홈</a> · 생성: {datetime.now().strftime("%Y-%m-%d")} (_Claude)'

    js = SHARED_JS if include_js else ''

    return f"""{SHARED_CSS}
<div class="hero">
{eyebrow_html}<h1>{html_mod.escape(title)}</h1>
{subtitle_html}</div>
{content_html}
<div class="footer"><p>{footer}</p></div>
{js}"""


def convert_file(input_path, output_path, title=None, eyebrow=None, subtitle=None, footer_text=None, tistory=False):
    """Convert a single markdown or existing HTML file to a Pages-ready HTML file."""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"  ⚠️  Skipping (not found): {input_path}")
        return False

    # Read source
    text = input_path.read_text(encoding='utf-8', errors='replace')

    # If already HTML, extract body content
    if input_path.suffix == '.html':
        # Check if it's a full page or just body content
        if '<body' in text.lower() or '<!doctype' in text.lower():
            # Full HTML — extract content between body tags or use as-is
            body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
            if body_match:
                content_html = body_match.group(1)
            else:
                content_html = text
        else:
            # Already a template-fragment HTML (style + divs)
            # Wrap it — extract style and body separately
            style_match = re.search(r'<style>(.*?)</style>', text, re.DOTALL)
            if style_match:
                # Remove style tag, use shared CSS instead
                content_html = re.sub(r'<style>.*?</style>', '', text, flags=re.DOTALL).strip()
            else:
                content_html = text
    else:
        # Markdown → HTML
        content_html = md_to_html(text)

    # Auto-detect title from first h1 if not provided
    if not title:
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content_html)
        if h1_match:
            title = re.sub(r'<[^>]+>', '', h1_match.group(1))
        else:
            title = input_path.stem.replace('-', ' ').replace('_', ' ').title()

    if not eyebrow:
        eyebrow = "Helena Programming · Textbook"

    # Wrap in template
    full_html = build_page(content_html, title, eyebrow, subtitle, footer_text,
                          include_js=not tistory)

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_html, encoding='utf-8')

    print(f"  ✅ {input_path.name} → {output_path}")
    return True


def build_chapter_page(part_id, chapter_id, chapter_info, pages_dir):
    """Build a chapter landing page that aggregates sources."""
    slug = chapter_info['slug']
    title = f"{chapter_info['title']}"
    part_title = CONTENT_MAP[part_id]['title']
    part_slug = CONTENT_MAP[part_id]['slug']

    # Build chapter overview content
    sources_html = '\n'.join(
        f'<li><code>{s}</code></li>' for s in chapter_info.get('sources', [])
    )

    content = f"""<section>
<div class="info-box"><strong>📖 {part_title}</strong> — 이 챕터가 속한 Part</div>
<p>{chapter_info['title']}에 관한 완결된 교재 페이지. 아래 소스 문서를 기반으로 작성되었다.</p>

<h2>📂 소스 문서</h2>
<ul>{sources_html}</ul>

<div class="grid2">
<div class="card"><div class="card-hd">📚 교재 보기</div><div class="card-dsc">이 챕터의 완결된 교재 페이지. 설치법·가이드·매뉴얼.</div></div>
<div class="card"><div class="card-hd">📓 사고흐름 보기</div><div class="card-dsc">이 주제가 어떻게 결정되었는지 — <a href="https://galaxys21-pwuser.tistory.com" style="color:var(--a)">Tistory</a>에서 확인.</div></div>
</div>

<p style="margin-top:12px"><a href="../{part_slug}/" style="color:var(--a)">← {part_title}</a> · <a href="../" style="color:var(--a)">📚 교재 홈</a></p>
</section>"""

    full_html = build_page(content, title,
                          eyebrow=f"{part_id} · {chapter_id}",
                          subtitle=f"{part_title} — 교과서 Chapter",
                          footer_text=f'📚 <a href="../" style="color:var(--a)">Helena Programming 교재</a> · {part_id} {chapter_id} · {datetime.now().strftime("%Y-%m-%d")} (_Claude)')

    output_path = pages_dir / part_slug / f'{slug}.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_html, encoding='utf-8')
    print(f"  📄 Chapter page: {output_path}")


def build_part_index(part_id, part_info, pages_dir):
    """Build a Part landing page listing all chapters."""
    slug = part_info['slug']
    chapters_html = ''

    for ch_id, ch_info in part_info['chapters'].items():
        ch_slug = ch_info['slug']
        chapters_html += f"""<div class="card">
<div class="card-hd"><a href="{ch_slug}.html" style="color:var(--a);text-decoration:none">{ch_id}: {ch_info['title']}</a></div>
<div class="card-dsc">{len(ch_info.get('sources', []))}개 소스 문서</div>
</div>"""

    content = f"""<section>
<div class="info-box green"><strong>📚 {part_info['title']}</strong> — {len(part_info['chapters'])}개 Chapter로 구성</div>

<h2>📖 Chapters</h2>
{chapters_html}

<p style="margin-top:12px"><a href="../" style="color:var(--a)">← 교재 홈</a></p>
</section>"""

    full_html = build_page(content, part_info['title'],
                          eyebrow=f"Part {part_id[1:]}",
                          subtitle=f"{len(part_info['chapters'])} Chapters · Helena Programming Textbook",
                          footer_text=f'📚 <a href="../" style="color:var(--a)">Helena Programming 교재</a> · {part_id} · {datetime.now().strftime("%Y-%m-%d")} (_Claude)')

    output_path = pages_dir / slug / 'index.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_html, encoding='utf-8')
    print(f"📄 Part index: {output_path}")


def build_home(pages_dir):
    """Build the textbook home page with full Part·Chapter tree."""
    parts_html = ''
    total_chapters = 0
    total_sources = 0

    for part_id, part_info in CONTENT_MAP.items():
        chapters_html = ''
        for ch_id, ch_info in part_info['chapters'].items():
            chapters_html += f"""<details class="acc"><summary>{ch_id}: {ch_info['title']} <span style="font-size:.7rem;color:var(--t3);font-weight:400">({len(ch_info.get('sources',[]))} docs)</span></summary><div class="acc-body">
<p>소스: {', '.join(f'<code>{s}</code>' for s in ch_info.get('sources',[]))}</p>
<p><a href="{part_info['slug']}/{ch_info['slug']}.html" style="color:var(--a)">📖 교재 보기</a></p>
</div></details>"""
            total_chapters += 1
            total_sources += len(ch_info.get('sources', []))

        parts_html += f"""<details class="acc" open><summary><strong>{part_id}: {part_info['title']}</strong> <span style="font-size:.7rem;color:var(--t3);font-weight:400">({len(part_info['chapters'])} Chapters)</span></summary><div class="acc-body">
{chapters_html}
<p><a href="{part_info['slug']}/" style="color:var(--a)">📂 {part_info['title']} Part 페이지 →</a></p>
</div></details>"""

    content = f"""<section>
<div class="counter-bar">
<div class="counter"><div class="num" style="color:var(--a)">8</div><div class="label">Parts</div></div>
<div class="counter"><div class="num" style="color:var(--o)">{total_chapters}</div><div class="label">Chapters</div></div>
<div class="counter"><div class="num" style="color:var(--g)">{total_sources}</div><div class="label">소스 문서</div></div>
<div class="counter"><div class="num" style="color:var(--p)">3</div><div class="label">레포</div></div>
</div>

<div class="info-box green"><strong>🎯 이 교재의 목적:</strong> S21 5년 된 폰 하나 + DeepSeek API로 AI 워크스테이션·출판·방송 파이프라인을 구축하는 <strong>완결된 교과서</strong>. 모든 페이지는 풀인터랙티브 HTML (복사버튼·다크모드·아코디언·PWA).</div>

<div class="info-box"><strong>🔗 투트랙 출판:</strong>
📚 <strong>GitHub Pages (여기)</strong> = 완결 교과서 (JS·PWA·복사버튼) &nbsp;|&nbsp;
📓 <a href="https://galaxys21-pwuser.tistory.com" style="color:var(--a)"><strong>Tistory</strong></a> = 사고흐름·결정과정 (CSS-only 인터랙티브)
<br>📺 <a href="https://youtube.com/@S21Phone" style="color:var(--a)"><strong>YouTube</strong></a> = 숏폼 튜토리얼 &nbsp;|&nbsp;
🗺️ <a href="https://blog.naver.com/helena1975" style="color:var(--a)"><strong>Naver</strong></a> = 주간 링크 퀼트 웹진
</div>

<p>자세한 워크플로: <a href="p5-publishing/ch5-2-cascade.html" style="color:var(--a)">🪜 Step-Down Cascade 매뉴얼</a></p>
</section>

<section>
<h2>📚 전체 Part · Chapter</h2>
{parts_html}
</section>"""

    full_html = build_page(content, "S21 Phone AI 워크스테이션 — 완결 교과서",
                          eyebrow="Helena Programming · Textbook v1.0",
                          subtitle="8 Parts · 31 Chapters · 3개 레포 · S21 단독 운영 · 풀인터랙티브 HTML",
                          footer_text=f'📚 <a href="https://helena751107.github.io/helena-programming/pages/" style="color:var(--a)">교재 홈</a> · <a href="https://github.com/helena751107/helena-programming" style="color:var(--a)">GitHub</a> · {datetime.now().strftime("%Y-%m-%d")} (_Claude)')

    output_path = pages_dir / 'index.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_html, encoding='utf-8')
    print(f"📄 Home page: {output_path}")


# ═══════════════════════════════════════════════════════════════
# MAIN — BATCH BUILD
# ═══════════════════════════════════════════════════════════════

def build_all(pages_dir, tistory=False):
    """Build all 93+ pages from the content map."""
    pages_dir = Path(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Build home page
    build_home(pages_dir)

    # Build each part index and chapter
    for part_id, part_info in CONTENT_MAP.items():
        build_part_index(part_id, part_info, pages_dir)

        for ch_id, ch_info in part_info['chapters'].items():
            build_chapter_page(part_id, ch_id, ch_info, pages_dir)

            # Try to convert each source file
            for source_rel in ch_info.get('sources', []):
                # Determine full path
                if source_rel.startswith('helena-programming/'):
                    full_path = Path('/root/work') / source_rel
                elif source_rel.startswith('helana_log/'):
                    full_path = Path('/root/work') / source_rel
                else:
                    full_path = Path('/root/work') / source_rel

                # Output path
                out_name = Path(source_rel).stem + '.html'
                out_path = pages_dir / part_info['slug'] / out_name

                if full_path.exists():
                    title = ch_info['title']
                    convert_file(str(full_path), str(out_path),
                               title=title,
                               eyebrow=f"{part_id} · {ch_id}",
                               subtitle=part_info['title'],
                               tistory=tistory)
                else:
                    print(f"  ⚠️  Not found: {full_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='md_to_page.py — Markdown → Pages HTML converter')
    parser.add_argument('input', nargs='?', help='Input .md or .html file')
    parser.add_argument('--out', help='Output .html file path')
    parser.add_argument('--title', help='Page title (auto-detected if omitted)')
    parser.add_argument('--eyebrow', help='Eyebrow label')
    parser.add_argument('--subtitle', help='Page subtitle')
    parser.add_argument('--chap', help='Chapter label (e.g. Ch1.1)')
    parser.add_argument('--all', action='store_true', help='Build ALL pages from content map')
    parser.add_argument('--tistory', action='store_true', help='Output Tistory CSS-only version (no JS)')
    parser.add_argument('--pages-dir', default='pages', help='Output directory for pages (default: pages/)')
    args = parser.parse_args()

    if args.all:
        print("🏗️  Building ALL textbook pages...")
        pages_dir = Path('/root/work/helena-programming') / args.pages_dir
        build_all(pages_dir, tistory=args.tistory)
        print(f"\n✅ Done! Pages directory: {pages_dir}")
        print(f"   Home: {pages_dir}/index.html")
    elif args.input:
        out_path = args.out or (Path(args.input).stem + '.html')
        ok = convert_file(args.input, out_path,
                         title=args.title,
                         eyebrow=args.eyebrow,
                         subtitle=args.subtitle,
                         tistory=args.tistory)
        if ok:
            print(f"\n✅ Converted: {out_path}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

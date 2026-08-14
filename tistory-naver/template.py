#!/usr/bin/env python3
"""
티스토리 HTML 템플릿 — 아코디언 + 인라인 SVG 인포그래픽 + 코드블록 + 버튼/JS
(Boss 2026-08-14 "반드시 아코디언·인포그래픽·JS 전부" 요구 대응)

티스토리 HTML 에디터(tinymce)가 살려주는 것만 쓰는 게 원칙:
  ✅ <details>/<summary>  아코디언 (네이티브, JS 없이도 동작)
  ✅ <svg> 인라인         인포그래픽 (외부 리소스 불필요)
  ✅ <pre><code>          설치법 코드블록
  ✅ <button> + <style>   버튼 + 인라인 스타일
  ⚠ <script>              생존 여부는 테스트 포스트로 실측 (Task #6)
     — script 가 잘려도 <details> 네이티브로 아코디언은 살아있게 설계

구조:
  1) 인포그래픽 SVG (제목 + 섹션 플로우 다이어그램) — 모든 포스트 상단에 자동 생성
  2) 본문 markdown → <h2> 단위로 아코디언 섹션 분할
  3) 코드블록 → <pre><code> + 복사 버튼 (JS)
  4) 마스터 버튼: 전체 펼치기/접기 + 복사 (JS)

사용법:
  python3 template.py _notebook/00-INDEX.md --account galaxys21 --title "…" --tags "태그1,태그2"
  → posts/<slug>.json 생성 (post.py 가 발행)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import markdown

BASE = Path(__file__).parent
POSTS_DIR = BASE / "posts"
POSTS_DIR.mkdir(exist_ok=True)

# webzine 과 동일한 markdown 렌더러 (일관성)
MD = markdown.Markdown(
    extensions=["tables", "fenced_code", "sane_lists", "smarty", "nl2br", "attr_list"],
)

ACCENT = "#14b8a6"      # teal (webzine color_tag 와 동일 계열)
ACCENT_DARK = "#0f766e"
INK = "#1f2937"
MUTED = "#6b7280"
LINE = "#e5e7eb"
BG = "#ffffff"


def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


def _clip(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ── 인포그래픽 SVG (제목 + 섹션 플로우) ──────────────────────
def build_infographic(title: str, subtitle: str, sections: list[str]) -> str:
    W = 720
    HEAD = 118
    ROW = 52
    PAD = 24
    n = len(sections)
    H = HEAD + n * ROW + PAD + 14

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="인포그래픽: {escape_xml(title)}" '
           f'style="width:100%;height:auto;display:block;border-radius:12px;">']
    svg.append("<defs>")
    svg.append(f'<linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="{ACCENT_DARK}"/>'
               f'<stop offset="1" stop-color="{ACCENT}"/></linearGradient>')
    svg.append(f'<marker id="arr" markerWidth="8" markerHeight="8" refX="5" refY="3" '
               f'orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{MUTED}"/></marker>')
    svg.append("</defs>")

    # 헤더
    svg.append(f'<rect x="0" y="0" width="{W}" height="{HEAD}" fill="url(#hdr)" rx="12"/>')
    svg.append(f'<rect x="0" y="0" width="{W}" height="14" fill="{ACCENT}" rx="12"/>')
    svg.append(f'<text x="{PAD}" y="44" font-family="-apple-system,Apple SD Gothic Neo,'
               f'Malgun Gothic,sans-serif" font-size="24" font-weight="700" fill="#ffffff">'
               f'{escape_xml(_clip(title, 40))}</text>')
    if subtitle:
        svg.append(f'<text x="{PAD}" y="74" font-family="-apple-system,Apple SD Gothic Neo,'
                   f'Malgun Gothic,sans-serif" font-size="13" fill="#ccfbf1">'
                   f'{escape_xml(_clip(subtitle, 60))}</text>')
    svg.append(f'<text x="{W - PAD}" y="86" text-anchor="end" '
               f'font-family="-apple-system,Malgun Gothic,sans-serif" font-size="13" '
               f'font-weight="700" fill="#ffffff">{n} SECTION</text>')

    # 섹션 노드 플로우
    for i, sec in enumerate(sections):
        y = HEAD + i * ROW
        cx = PAD
        cy = y + ROW // 2
        svg.append(f'<circle cx="{cx + 16}" cy="{cy}" r="15" fill="{ACCENT}" opacity="0.16"/>')
        svg.append(f'<text x="{cx + 16}" y="{cy + 5}" text-anchor="middle" '
                   f'font-family="ui-monospace,Menlo,monospace" font-size="14" '
                   f'font-weight="700" fill="{ACCENT_DARK}">{i + 1}</text>')
        svg.append(f'<rect x="{cx + 40}" y="{cy - 17}" width="{W - PAD - 40 - PAD}" height="34" '
                   f'rx="8" fill="#f8fafc" stroke="{LINE}"/>')
        svg.append(f'<text x="{cx + 52}" y="{cy + 5}" '
                   f'font-family="-apple-system,Apple SD Gothic Neo,Malgun Gothic,sans-serif" '
                   f'font-size="14" fill="{INK}">{escape_xml(_clip(sec, 44))}</text>')
        if i < n - 1:
            svg.append(f'<line x1="{cx + 16}" y1="{cy + 15}" x2="{cx + 16}" '
                       f'y2="{cy + ROW - 3}" stroke="{MUTED}" stroke-width="1.5" '
                       f'marker-end="url(#arr)"/>')

    svg.append("</svg>")
    return "\n".join(svg)


# ── 본문: <h2> 단위 아코디언 + 코드블록 복사 버튼 ─────────────
def _code_copy(html: str) -> str:
    """<pre><code> 블록에 복사 버튼을 붙인다."""
    def repl(m: re.Match) -> str:
        attrs, code = m.group(1), m.group(2)
        # JS 로 복사할 원문(디코딩된 텍스트)을 data- 속성에 담지 않고
        # 코드블록 textContent 를 읽어 복사 → sanitize 에 강함.
        return (f'<div class="s21-code"><button class="s21-copy" type="button" '
                f'title="코드 복사">복사</button><pre><code{attrs}>{code}</code></pre></div>')
    return re.sub(r"<pre><code([^>]*)>(.*?)</code></pre>", repl, html, flags=re.DOTALL)


def _h2_accordion(html: str) -> str:
    """<h2>…</h2> 로 시작하는 블록을 <details><summary>…</summary>…</details> 로 감싼다.
    첫 섹션은 open (펼친 상태). <h3> 이하는 그대로 두고 section 내부로 흡수된다.
    간단하고 견고한 방식: 소스 markdown 을 h2 로 분할(render 에서 수행)하므로
    여기선 이미 분할된 조각만 받는다."""
    return html


def _render_md_to_accordion(md_text: str) -> tuple[str, list[str]]:
    """markdown → (intro_html, section_titles, accordion_html)."""
    lines = md_text.splitlines()
    # h2 기준 분할
    sections: list[tuple[str, list[str]]] = []  # (title, [lines])
    intro: list[str] = []
    cur_title = None
    cur_buf: list[str] = []
    for ln in lines:
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            if cur_title is not None:
                sections.append((cur_title, cur_buf))
            cur_title = m.group(1)
            cur_buf = []
        else:
            (cur_buf if cur_title is not None else intro).append(ln)
    if cur_title is not None:
        sections.append((cur_title, cur_buf))

    intro_html = MD.convert("\n".join(intro)) if intro else ""

    titles: list[str] = []
    acc: list[str] = []
    for i, (t, body) in enumerate(sections):
        titles.append(t)
        body_html = _code_copy(MD.convert("\n".join(body)))
        open_attr = " open" if i == 0 else ""
        acc.append(
            f'<details class="s21-acc"{open_attr}><summary class="s21-acc">{escape_xml(t)}</summary>'
            f'<div class="s21-acc-body">{body_html}</div></details>'
        )
    return intro_html, titles, "\n".join(acc)


# ── 전체 HTML 셸 (style + script 는 티스토리가 살려주는지 실측 대상) ──
STYLE = """
<style>
.s21-post{max-width:760px;margin:0 auto;font-family:-apple-system,'Apple SD Gothic Neo',Malgun Gothic,'Noto Sans KR',sans-serif;color:#1f2937;line-height:1.7;font-size:15px;word-break:keep-all}
.s21-post a{color:#0f766e;text-decoration:none;border-bottom:1px solid #99f6e4}
.s21-toolbar{display:flex;gap:8px;margin:14px 0 6px}
.s21-btn{appearance:none;border:1px solid #14b8a6;background:#fff;color:#0f766e;font-size:13px;font-weight:600;padding:7px 14px;border-radius:999px;cursor:pointer;transition:all .15s}
.s21-btn:hover{background:#14b8a6;color:#fff}
.s21-acc{border:1px solid #e5e7eb;border-radius:10px;margin:10px 0;background:#fff;overflow:hidden}
.s21-acc>summary{cursor:pointer;padding:13px 16px;font-weight:700;font-size:16px;background:#f8fafc;list-style:none;display:flex;align-items:center;gap:8px}
.s21-acc>summary::before{content:"▸";color:#14b8a6;font-size:14px;transition:transform .15s}
.s21-acc[open]>summary::before{transform:rotate(90deg)}
.s21-acc>summary:hover{background:#f0fdfa}
.s21-acc-body{padding:6px 16px 14px}
.s21-acc-body h3{margin:18px 0 6px;font-size:16px}
.s21-code{position:relative;margin:12px 0}
.s21-code pre{background:#0f172a;color:#e2e8f0;padding:16px;border-radius:8px;overflow-x:auto;margin:0;font-size:13px;line-height:1.55}
.s21-code code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:transparent;color:inherit}
.s21-copy{position:absolute;top:8px;right:8px;appearance:none;border:1px solid #334155;background:#1e293b;color:#cbd5e1;font-size:11px;padding:4px 10px;border-radius:6px;cursor:pointer}
.s21-copy:hover{background:#334155;color:#fff}
@media (prefers-color-scheme:dark){
.s21-post{color:#e5e7eb}
.s21-acc,.s21-btn,.s21-acc>summary{background:#111827;border-color:#374151;color:#e5e7eb}
.s21-acc>summary:hover{background:#1f2937}
.s21-btn:hover{background:#14b8a6;color:#fff}
}
</style>
"""

SCRIPT = """
<script>
(function(){
  function qs(sel){return Array.prototype.slice.call(document.querySelectorAll(sel))}
  // 전체 펼치기/접기
  qs('[data-s21="expand"]').forEach(function(b){
    b.addEventListener('click',function(){qs('details.s21-acc').forEach(function(d){d.open=true})})
  });
  qs('[data-s21="collapse"]').forEach(function(b){
    b.addEventListener('click',function(){qs('details.s21-acc').forEach(function(d){d.open=false})})
  });
  // 코드 복사
  qs('.s21-copy').forEach(function(b){
    b.addEventListener('click',function(){
      var code=b.parentNode.querySelector('code');
      if(!code)return;
      var txt=code.innerText;
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(txt).then(function(){b.textContent='복사됨';setTimeout(function(){b.textContent='복사'},1500)});
      }else{
        var ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();
        try{document.execCommand('copy');b.textContent='복사됨'}catch(e){}
        document.body.removeChild(ta);setTimeout(function(){b.textContent='복사'},1500);
      }
    })
  });
})();
</script>
"""


def render_tistory_html(title: str, deck: str, md_body: str) -> str:
    intro_html, titles, acc_html = _render_md_to_accordion(md_body)
    infographic = build_infographic(title, deck, titles)
    parts = [
        '<div class="s21-post">',
        STYLE,
        infographic,
        '<div class="s21-toolbar">'
        '<button class="s21-btn" type="button" data-s21="expand">전체 펼치기</button>'
        '<button class="s21-btn" type="button" data-s21="collapse">전체 접기</button>'
        '</div>',
    ]
    if intro_html:
        parts.append(f'<div class="s21-intro">{intro_html}</div>')
    parts.append(acc_html)
    parts.append(SCRIPT)
    parts.append("</div>")
    return "\n".join(parts)


# ── markdown 소스에서 제목·덱 추출 ───────────────────────────
def extract_title_deck(md_text: str) -> tuple[str, str]:
    title, deck = "", ""
    for ln in md_text.splitlines():
        if not title and ln.startswith("# "):
            title = ln[2:].strip()
        if not deck and ln.strip().startswith(">"):
            deck = ln.strip().lstrip("> ").strip()
        if title and deck:
            break
    return title, deck


def strip_frontmatter(md_text: str) -> str:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", md_text, re.DOTALL)
    return md_text[m.end():] if m else md_text


# ── posts/*.json 생성 ───────────────────────────────────────
def build_post_json(md_path: Path, account: str, blog: str, title: str | None,
                    tags: list[str], visibility: str = "public") -> Path:
    raw = md_path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)
    t, deck = extract_title_deck(body)
    if not t:
        t = md_path.stem
    html = render_tistory_html(title or t, deck, body)

    slug = md_path.stem.replace("_", "-")
    data = {
        "account": account,
        "blog": blog,
        "title": title or t,
        "content": html,
        "tags": tags or ["S21", "업무수첩"],
        "category": "",
        "visibility": visibility,
    }
    out = POSTS_DIR / f"{slug}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="티스토리 HTML 템플릿 → posts/*.json")
    ap.add_argument("md", help="markdown 파일 경로")
    ap.add_argument("--account", default="galaxys21")
    ap.add_argument("--blog", default="galaxys21-pwuser")
    ap.add_argument("--title", default=None, help="제목 덮어쓰기 (기본: H1)")
    ap.add_argument("--tags", default="", help="쉼표 구분 태그")
    ap.add_argument("--visibility", default="public", choices=["public", "protected", "private"])
    ap.add_argument("--dump", action="store_true", help="HTML 을 stdout 으로 출력만")
    args = ap.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        print(f"❌ 없음: {md_path}", file=sys.stderr)
        return 1

    raw = md_path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)
    t, deck = extract_title_deck(body)
    if not t:
        t = md_path.stem
    html = render_tistory_html(args.title or t, deck, body)

    if args.dump:
        print(html)
        return 0

    tags = [x.strip() for x in args.tags.split(",") if x.strip()]
    out = build_post_json(md_path, args.account, args.blog, args.title, tags, args.visibility)
    print(f"✅ {out}")
    print(f"   제목: {args.title or t}")
    print(f"   분량: {len(html)}자 (HTML)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

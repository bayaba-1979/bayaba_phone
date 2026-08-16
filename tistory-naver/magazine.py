#!/usr/bin/env python3
"""
magazine.py — 피아노 웹진 아티클 렌더러 (웹진 디렉터 · 다크 네이비/골드 + 세리프)

DG/객석/Gramophone 계열 클래식 매거진 구조를 티스토리 글 본문 HTML로 렌더링한다:
  - 커버 히어로: kicker(오버라인) + 세리프 대제목 + dek(부제) + 바이라인
  - 드롭캡, 풀쿼트, figure(이미지+캡션), 오디오 임베드
  - markdown 본문(##/table/code/blockquote)은 기존 template.py와 같은 markdown lib 사용

사용법:
  python3 magazine.py articles/piano-02-clair-de-lune.md
  → posts/<slug>.json 생성 (post.py 가 발행)

마크다운 특수 블록:
  :::audio URL|제목            → 오디오 플레이어 블록
  :::figure key|캡션           → magazine-images.json 의 이미지 figure (key=debussy 등)
  ![캡션](URL)                 → 일반 이미지 figure (markdown 표준)

프론트매터:
  ---
  kicker: 감상 · Impression
  title: 달빛 — Clair de Lune
  dek: 드뷔시가 …
  hero: debussy               # magazine-images.json 키 (커버 이미지)
  hero_caption: (선택, 기본은 이미지 caption)
  byline: 웹진 디렉터
  date: 2026년 8월
  category: 감상
  tags: 드뷔시, 달빛, 클래식
  ---
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
IMAGES = json.loads((BASE / "assets" / "magazine-images.json").read_text(encoding="utf-8"))

MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"])

# ── 매거진 팔레트 (다크 네이비/골드 — 웹진 스킨과 일치) ──
GOLD = "#d4a84b"
GOLD_SOFT = "rgba(212,168,75,0.14)"
IVORY = "#ece7db"
MUTED = "#b8b2a6"
LINE = "rgba(212,168,75,0.22)"

MAG_CSS = """
.mag{max-width:760px;margin:0 auto;color:#ece7db;font-family:'Noto Serif KR','Nanum Myeongjo',Georgia,serif;line-height:1.85;font-size:17px;word-break:keep-all;overflow-wrap:anywhere}
.mag *{box-sizing:border-box}
.mag a{color:#d4a84b;text-decoration:none;border-bottom:1px solid rgba(212,168,75,0.35)}
.mag a:hover{color:#ecd39a}
.mag .mag-kicker{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:#d4a84b;margin:0 0 14px}
.mag h1.mag-title{font-family:'Cormorant Garamond','Noto Serif KR',Georgia,serif;font-size:clamp(34px,6vw,52px);font-weight:600;line-height:1.12;letter-spacing:0.01em;color:#f6f2e8;margin:0 0 18px}
.mag .mag-dek{font-family:'Cormorant Garamond','Noto Serif KR',serif;font-size:20px;line-height:1.55;color:#b8b2a6;font-style:italic;margin:0 0 20px;font-weight:400}
.mag .mag-byline{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:13px;letter-spacing:0.08em;color:#8f887a;margin:0 0 28px;text-transform:uppercase}
.mag figure{margin:34px 0;text-align:center}
.mag figure img{display:block;max-width:100%;height:auto;margin:0 auto;border-radius:4px;filter:saturate(0.92)}
.mag figure.mag-hero img{border-radius:6px;box-shadow:0 30px 60px -30px rgba(0,0,0,0.8)}
.mag figcaption{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:12.5px;color:#8f887a;margin-top:10px;letter-spacing:0.03em}
.mag h2{font-family:'Cormorant Garamond','Noto Serif KR',Georgia,serif;font-size:30px;font-weight:600;color:#f6f2e8;margin:46px 0 16px;padding-bottom:12px;border-bottom:1px solid rgba(212,168,75,0.22);letter-spacing:0.01em}
.mag h3{font-family:'Cormorant Garamond','Noto Serif KR',serif;font-size:23px;font-weight:600;color:#e4dcc8;margin:32px 0 12px}
.mag p{margin:0 0 20px}
.mag p.mag-dropcap::first-letter{font-family:'Cormorant Garamond',Georgia,serif;float:left;font-size:64px;line-height:0.82;padding:6px 10px 0 0;color:#d4a84b;font-weight:600}
.mag blockquote{margin:32px 0;padding:6px 0 6px 26px;border-left:3px solid #d4a84b;font-family:'Cormorant Garamond','Noto Serif KR',serif;font-size:24px;line-height:1.5;color:#f0ead9;font-style:italic}
.mag blockquote p{margin:0}
.mag .mag-audio{margin:30px 0;padding:18px 20px;border:1px solid rgba(212,168,75,0.25);border-left:3px solid #d4a84b;border-radius:6px;background:rgba(212,168,75,0.06)}
.mag .mag-audio .mag-audio-title{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:13px;letter-spacing:0.08em;color:#d4a84b;margin-bottom:12px;text-transform:uppercase}
.mag .mag-audio audio{width:100%;height:38px;display:block}
.mag .mag-audio .mag-audio-fallback{font-size:14px;margin-top:10px;color:#b8b2a6}
.mag .mag-audio .mag-audio-fallback a{color:#d4a84b}
.mag ul,.mag ol{margin:0 0 20px;padding-left:1.5em}
.mag li{margin:6px 0}
.mag code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:rgba(212,168,75,0.10);color:#ecd39a;padding:2px 6px;border-radius:4px;font-size:0.9em}
.mag pre{background:#0b1220;border:1px solid rgba(212,168,75,0.18);padding:18px;border-radius:8px;overflow-x:auto;margin:22px 0}
.mag pre code{background:transparent;color:#d7e0ea;padding:0;font-size:13.5px;line-height:1.6}
.mag table{width:100%;border-collapse:collapse;margin:24px 0;font-size:15px}
.mag th,.mag td{padding:11px 13px;text-align:left;border-bottom:1px solid rgba(212,168,75,0.16)}
.mag th{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:13px;letter-spacing:0.06em;color:#d4a84b;text-transform:uppercase;border-bottom:2px solid rgba(212,168,75,0.4)}
.mag hr{border:none;border-top:1px solid rgba(212,168,75,0.2);margin:40px 0}
.mag .mag-end{text-align:center;color:#8f887a;font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;font-size:13px;letter-spacing:0.3em;margin:44px 0 0;text-transform:uppercase}
.mag .mag-end::before{content:"❖";display:block;font-size:18px;color:#d4a84b;margin-bottom:10px}
"""


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    fm: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = parts[2]
    return fm, body.strip()


def _preprocess(body: str) -> str:
    """:::audio / :::figure 특수 블록 → HTML 로 치환 후 markdown 처리."""
    def audio(m):
        spec = m.group(1).strip()
        if "|" in spec:
            url, title = spec.split("|", 1)
        else:
            url, title = spec, "감상하기"
        return (
            f'<div class="mag-audio"><div class="mag-audio-title">▶ {title.strip()}</div>'
            f'<audio controls preload="none" src="{url.strip()}"></audio>'
            f'<div class="mag-audio-fallback"><a href="{url.strip()}" target="_blank">브라우저에서 재생이 안 되면 여기서 듣기 (MP3)</a></div></div>'
        )

    def figure(m):
        spec = m.group(1).strip()
        key = spec
        caption = None
        if "|" in spec:
            key, caption = spec.split("|", 1)
        key = key.strip()
        if key not in IMAGES:
            return f"<!-- figure key 없음: {key} -->"
        img = IMAGES[key]
        cap = (caption or img["caption"]).strip()
        return f'<figure><img src="{img["src"]}" alt="{cap}" loading="lazy"><figcaption>{cap}</figcaption></figure>'

    body = re.sub(r"^:::audio\s+(.+)$", audio, body, flags=re.M)
    body = re.sub(r"^:::figure\s+(.+)$", figure, body, flags=re.M)
    return body


def render_article(md_text: str) -> dict:
    fm, body = _parse_frontmatter(md_text)
    body = _preprocess(body)
    body_html = MD.convert(body)

    # 첫 <p>에 드롭캡 클래스 (가장 첫 단락)
    body_html = re.sub(
        r"(<p>)", r'<p class="mag-dropcap">', body_html, count=1
    )

    hero = ""
    if fm.get("hero") and fm["hero"] in IMAGES:
        img = IMAGES[fm["hero"]]
        cap = (fm.get("hero_caption") or img["caption"]).strip()
        hero = f'<figure class="mag-hero"><img src="{img["src"]}" alt="{cap}" loading="lazy"><figcaption>{cap}</figcaption></figure>'

    kicker = f'<div class="mag-kicker">{fm["kicker"]}</div>' if fm.get("kicker") else ""
    title = fm.get("title", "")
    dek = f'<p class="mag-dek">{fm["dek"]}</p>' if fm.get("dek") else ""
    byline_parts = [p for p in [fm.get("byline"), fm.get("date")] if p]
    byline = f'<div class="mag-byline">{" · ".join(byline_parts)}</div>' if byline_parts else ""

    html = (
        '<div class="mag">\n'
        f'<style>{MAG_CSS}</style>\n\n'
        f'<header>{kicker}\n<h1 class="mag-title">{title}</h1>\n{dek}\n{byline}</header>\n\n'
        f'{hero}\n\n'
        f'{body_html}\n\n'
        '<div class="mag-end">helena-piano · 세계 히스토리 웹진</div>\n'
        '</div>'
    )

    return {
        "account": "piano",
        "blog": "helena-piano",
        "title": title,
        "content": html,
        "tags": [t.strip() for t in fm.get("tags", "").split(",") if t.strip()],
        "category": fm.get("category", ""),
        "visibility": "private",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md", help="마크다운 기사 파일 (articles/*.md)")
    args = ap.parse_args()
    md_path = Path(args.md)
    md_text = md_path.read_text(encoding="utf-8")
    post = render_article(md_text)
    out = POSTS_DIR / (md_path.stem + ".json")
    out.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {out.name} 생성 — 제목: {post['title']} · 카테고리: {post['category']} · {len(post['tags'])}태그")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

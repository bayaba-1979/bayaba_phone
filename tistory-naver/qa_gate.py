#!/usr/bin/env python3
"""
QA 게이트 — 티스토리 발행 글의 '빵꾸'(제목만 있고 본문 없음)를 감지한다.

발생 원인 (실측): tinymce.setContent()가 True를 반환해도 일부 글은
본문이 에디터 폼에 커밋되지 않은 채 발행 → 제목만 있는 글 2개(/18·/19) 확인.

체크: 각 포스트 URL을 fetch → 본문 마커(s21-post / <details> / <svg>)와
본문 텍스트 길이로 '내용 있음/없음'을 판정한다.

입력:
  python3 qa_gate.py                          # RSS 최근 글 자동 검사
  python3 qa_gate.py --ids 11,12,13           # 특정 글 ID (--blog 필수)
  python3 qa_gate.py --urls https://…/11,...  # 전체 URL 직접

출력: assets/qa-gate.json + stdout 요약 (PASS / FAIL·빵꾸)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "qa-gate.json"

# 우리 템플릿이 발행하면 반드시 남기는 마커. 하나라도 없으면 빵꾸로 의심.
# ⚠ "<svg" 는 티스토리 사이트 크롬(아이콘)에도 항상 1개 있어서 신뢰 불가 → 제외.
#    빵꾸 글 실측: s21-post=0 / s21-acc=0 / <details=0 (전부 0)
MARKERS = ["s21-post", "s21-acc", "<details"]
MIN_TEXT = 2500         # 본문 텍스트 최소 글자(태그 제거 후). 티스토리 크롬만 ~2100자.
TIMEOUT = 20


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_tags(html: str) -> str:
    h = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.DOTALL)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def analyze(html: str) -> dict:
    """본문 마커 개수 + 텍스트 길이로 빵꾸 여부 판정."""
    marker_hits = {m: html.count(m) for m in MARKERS}
    has_marker = any(v > 0 for v in marker_hits.values())
    text_len = len(strip_tags(html))
    # 마커도 없고 본문 텍스트도 임계 미만이면 빵꾸
    empty = (not has_marker) and text_len < MIN_TEXT
    return {
        "marker_hits": marker_hits,
        "text_len": text_len,
        "empty": empty,
    }


def discover_from_rss(blog: str, limit: int = 20) -> list[tuple[str, str]]:
    """RSS 에서 (제목, URL) 최근 글 수집. RSS 는 보통 최근 10개만 노출."""
    xml = fetch(f"https://{blog}.tistory.com/rss")
    items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
    out = []
    for it in items[:limit]:
        t = re.search(r"<title>(.*?)</title>", it, re.DOTALL)
        l = re.search(r"<link>(.*?)</link>", it, re.DOTALL)
        if t and l:
            out.append((t.group(1).strip(), l.group(1).strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="티스토리 발행 글 빵꾸 QA 게이트")
    ap.add_argument("--blog", default="galaxys21-pwuser")
    ap.add_argument("--ids", help="쉼표 구분 글 ID (예: 11,12,13)")
    ap.add_argument("--urls", help="쉼표 구분 전체 URL")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    if args.urls:
        posts = [(u.rsplit("/", 1)[-1], u) for u in args.urls.split(",") if u.strip()]
    elif args.ids:
        posts = [(i, f"https://{args.blog}.tistory.com/{i.strip()}")
                 for i in args.ids.split(",") if i.strip()]
    else:
        posts = discover_from_rss(args.blog, args.limit)

    results = []
    empty = []
    for ident, url in posts:
        try:
            html = fetch(url)
            a = analyze(html)
        except Exception as e:
            a = {"marker_hits": {}, "text_len": 0, "empty": None, "error": str(e)}
        row = {"id": ident, "url": url, **a}
        results.append(row)
        if a.get("empty"):
            empty.append(ident)

    manifest = {
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "blog": args.blog,
        "markers": MARKERS,
        "min_text": MIN_TEXT,
        "total": len(results),
        "empty_count": len(empty),
        "empty": empty,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in results:
        if r.get("empty"):
            print(f"  ❌ 빵꾸 /{r['id']}  text={r.get('text_len',0)}자  markers={r.get('marker_hits')}")
        elif r.get("empty") is None:
            print(f"  ⚠ 오류 /{r['id']}  {r.get('error')}")
        else:
            print(f"  ✅ OK   /{r['id']}  text={r.get('text_len',0)}자")
    print(f"\n총 {len(results)}개 중 빵꾸 {len(empty)}개 → assets/qa-gate.json")
    return 1 if empty else 0


if __name__ == "__main__":
    raise SystemExit(main())

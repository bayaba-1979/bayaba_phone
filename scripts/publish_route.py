#!/usr/bin/env python3
"""
편집장 라우터 — 분모(레포 문서)를 자동 추론으로 라우팅한다.

로직 (Boss 2026-08-14):
  분모 U = _notebook/*.md 전체 (업무수첩)
  ├─ ① 먼저: GitHub Pages = U 전체 (아카이브)  ← build_webzine.py 가 이미 생성
  └─ ② 여집합: Tistory = U − pages-only        ← 읽는 글·설치법·코드블록

판별 규칙 (우선순위):
  1) frontmatter `channel: pages-only|tistory` → 명시 태그 우선
  2) 제목·덱·본문 키워드 점수 → 시각/인터랙티브가 우세하면 pages-only
  3) 그 외 → tistory (여집합 기본)

출력:
  assets/publish-route.json  — 라우팅 매니페스트 (분모/카운트/문서별 사유)
  stdout 요약

사용법:
  python3 scripts/publish_route.py            # 전체 스캔 + 요약
  python3 scripts/publish_route.py --pages    # pages-only 목록만
  python3 scripts/publish_route.py --tistory  # tistory 목록만
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "publish-route.json"

# 확장 가능한 스캔 범위 (분모). 업무수첩이 1차 대상.
SCAN_GLOBS = ["_notebook/*.md"]  # 추후: "_textbook/*.md", "0*/*.md"

# ── 판별 키워드 ─────────────────────────────────────────────
# pages-only: 티스토리가 못 담는 시각·인터랙티브 (제목·파일명에 등장하는 '형태' 단어만 — 본문 제외)
PAGES_ONLY_KEYWORDS = [
    "인포그래픽", "대시보드", "웹앱", "랜딩", "포털", "워크패드", "커버리지",
    "생태계맵", "생태계 지도", "생태계", "infographic", "dashboard", "webapp",
    "landing", "portal", "workpad", "coverage", "ecosystem",
]
# tistory: 읽는 글·설치법·코드블록 (검색·복붙 대상) — 기본값
TISTORY_KEYWORDS = [
    "설치", "가이드", "업무일지", "주의", "규칙", "전략", "기록", "교재",
    "튜토리얼", "회고", "랩업", "기점", "방법론", "패턴", "설명서", "백서",
    "보고", "표준", "install", "guide", "tutorial", "howto", "how-to",
    "whitepaper", "report", "standard",
]


# frontmatter `type:` 이 '읽는 글'을 명시하면 키워드와 무관하게 tistory 로 고정
READABLE_TYPES = {
    "standard", "report", "summary-comparison", "reference", "org-decision",
    "org-index", "lecture-draft", "naver-lecture-intro",
}


def parse_frontmatter(text: str) -> dict:
    """--- YAML --- 블록을 dict로. 없으면 {}."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        # 최상위 키만 (들여쓰기 있는 하위 항목 제외)
        if ":" in line and not line.startswith((" ", "\t")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def extract_h1(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def extract_deck(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">") and len(s) > 2:
            return s.lstrip("> ").strip()
    return ""


def classify(title: str, deck: str, fname: str, fm: dict) -> tuple[str, str]:
    """(channel, reason) 반환. channel ∈ {pages-only, tistory}."""
    # 1) 명시 태그
    ch = (fm.get("channel") or "").strip().lower()
    if ch == "pages-only":
        return "pages-only", "명시 태그 channel: pages-only"
    if ch == "tistory":
        return "tistory", "명시 태그 channel: tistory"

    # 2) frontmatter type 이 '읽는 글' 형식이면 → tistory (키워드보다 우선)
    typ = (fm.get("type") or "").strip().lower()
    if typ in READABLE_TYPES:
        return "tistory", f"type:{typ} 은 읽는 글 형식"

    # 3) 키워드 점수 — 제목·덱·파일명만 (본문은 산만해서 오분류 유발 → 제외)
    hay = (fname + " " + title + " " + deck).lower()
    p = sum(1 for k in PAGES_ONLY_KEYWORDS if k.lower() in hay)
    t = sum(1 for k in TISTORY_KEYWORDS if k.lower() in hay)

    # 4) 기본 = tistory(여집합). pages-only 는 신호가 명확할 때만
    if p > t and p >= 1:
        return "pages-only", f"시각·인터랙티브 형태 신호 (pages {p} > tistory {t})"
    return "tistory", f"여집합 기본 (tistory {t} ≥ pages {p})"


def collect() -> list[Path]:
    docs: list[Path] = []
    for g in SCAN_GLOBS:
        docs.extend(sorted(ROOT.glob(g)))
    return docs


def build_manifest(docs: list[Path]) -> dict:
    entries = []
    pages_only: list = []
    tistory: list = []
    for p in docs:
        if p.name.startswith("."):  # 숨김/드래프트 제외
            continue
        text = p.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        title = extract_h1(text) or p.stem
        deck = extract_deck(text)
        channel, reason = classify(title, deck, p.stem, fm)
        entry = {
            "file": p.name,
            "title": title,
            "channel": channel,
            "reason": reason,
        }
        entries.append(entry)
        (pages_only if channel == "pages-only" else tistory).append(entry)

    return {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "source": SCAN_GLOBS,
        "logic": "분모 → GitHub Pages(전량) + Tistory(여집합 = 분모 − pages-only)",
        "분모_total": len(entries),
        "counts": {"pages_only": len(pages_only), "tistory": len(tistory)},
        "rules": {
            "priority": ["channel 태그", "키워드 점수", "여집합 기본"],
            "pages_only_keywords": PAGES_ONLY_KEYWORDS,
            "tistory_keywords": TISTORY_KEYWORDS,
        },
        "pages_only": pages_only,
        "tistory": tistory,
    }


def main() -> int:
    docs = collect()
    manifest = build_manifest(docs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    only = sys.argv[1] if len(sys.argv) > 1 else ""
    if only == "--pages":
        for e in manifest["pages_only"]:
            print(f"{e['file']}\t{e['title']}\t{e['reason']}")
        return 0
    if only == "--tistory":
        for e in manifest["tistory"]:
            print(f"{e['file']}\t{e['title']}\t{e['reason']}")
        return 0

    n = manifest["분모_total"]
    po = manifest["counts"]["pages_only"]
    ti = manifest["counts"]["tistory"]
    print(f"분모(_notebook)        = {n}개")
    print(f"├─ GitHub Pages(전량)  = {n}개   ← build_webzine.py 자동 (아카이브)")
    print(f"├─ pages-only(단독)    = {po}개")
    print(f"└─ Tistory(여집합)     = {ti}개")
    print()
    if po:
        print("▶ Pages 단독 (티스토리 제외):")
        for e in manifest["pages_only"]:
            print(f"   · {e['file']}  — {e['reason']}")
    print(f"\n매니페스트 → assets/publish-route.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
build_install_guides.py — 갤럭시S21 설치법 파일럿 묶음 생성
(Boss Task #7: "설치법 파일럿 묶음 + 스케줄링")

대상: GUIDE.md(마스터) + 01~05 챕터의 설치 가이드 16종
결과: posts/*.json (galaxys21-pwuser) + assets/publish-schedule.json (스케줄)

사용법:
  python3 build_install_guides.py            # JSON 생성 + 스케줄 매니페스트
  python3 build_install_guides.py --dry-run  # 생성 없이 목록·분량만
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
sys.path.insert(0, str(BASE))
from template import build_post_json, strip_frontmatter, extract_title_deck

ACCOUNT = "galaxys21"
BLOG = "galaxys21-pwuser"

# 챕터별 (파일, 태그). README 는 챕터 색인이라 제외 (GUIDE.md 가 네비게이션 담당)
GUIDES = [
    ("01-foundation", "기반설치", ["termux-setup.md", "proot-ubuntu.md", "claude-code.md", "git-github.md"]),
    ("02-network", "통신망", ["github-pages.md", "discord.md", "telegram.md"]),
    ("03-broadcast", "방송발행", ["naver-auto.md", "tistory-auto.md", "youtube.md"]),
    ("04-phone-control", "원격제어", ["health-check.md", "phone-mcp.md", "termux-api.md"]),
    ("05-optimization", "최적화", ["battery-saving.md", "performance.md", "storage.md"]),
]

# 챕터 태그 → 기존 티스토리 카테고리(PART N) 매핑. 새 카테고리 생성 없이 기존 교재 트리에 편입.
CATEGORY = {
    "개요": "PART 1: 온보딩",       # GUIDE.md 마스터
    "기반설치": "PART 1: 온보딩",    # 01-foundation
    "통신망": "PART 2: 인프라",      # 02-network
    "방송발행": "PART 5: 출판·배포",  # 03-broadcast
    "원격제어": "PART 2: 인프라",    # 04-phone-control
    "최적화": "PART 2: 인프라",      # 05-optimization
}


def doc_size(md_path: Path) -> int:
    return len(strip_frontmatter(md_path.read_text(encoding="utf-8")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = []          # (경로, 제목, 태그, 카테고리, 분량)
    manifest = {"account": ACCOUNT, "blog": BLOG, "posts": []}

    # 1) 마스터 GUIDE.md → 카테고리 '개요'
    for p in [ROOT / "GUIDE.md"]:
        if p.exists():
            t, _ = extract_title_deck(strip_frontmatter(p.read_text(encoding="utf-8")))
            plan.append((p, t or p.stem, ["S21", "설치법", "가이드"], CATEGORY["개요"]))

    # 2) 챕터 설치 가이드 → 카테고리 = 기존 PART 매핑
    for chap, ctag, files in GUIDES:
        for f in files:
            p = ROOT / chap / f
            if not p.exists():
                continue
            t, _ = extract_title_deck(strip_frontmatter(p.read_text(encoding="utf-8")))
            plan.append((p, t or p.stem, ["S21", "설치법", ctag], CATEGORY.get(ctag, "PART 2: 인프라")))

    total_chars = 0
    for p, title, tags, cat in plan:
        size = doc_size(p)
        total_chars += size
        manifest["posts"].append({
            "file": str(p.relative_to(ROOT)),
            "title": title,
            "tags": tags,
            "category": cat,
            "size": size,
        })
        if not args.dry_run:
            out = build_post_json(p, ACCOUNT, BLOG, title, tags,
                                  visibility="public", category=cat)
            print(f"  ✅ {out.name}  ← {title}  [{cat}]")

    n = len(plan)
    print(f"\n설치법 파일럿: {n}개  /  원문 합계 {total_chars:,}자")
    if not args.dry_run:
        sched = {
            "phase": "1-install-guides",
            "account": ACCOUNT,
            "blog": BLOG,
            "total": n,
            "schedule": manifest["posts"],
        }
        out = ROOT / "assets" / "publish-schedule.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"스케줄 → assets/publish-schedule.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
category_map.py — 설치가이드 원고 → 티스토리 카테고리 단일 진실(SSOT).

기존에는 "원고 폴더(01~05) 번호 → PART" 라는 임시 맵이 있어서
'2.1 GitHub Pages'가 02폴더라는 이유로 PART 2:인프라로 잘못 들어가는 등
구조가 둘로 갈라져 있었다. 이 파일이 그걸 하나로 통일한다:

  기준 = 티스토리 카테고리 트리(PART N + Ch N.M) 그 자체.
  원고 한 편 = 트리 Ch 한 칸 (내용 기준 1:1 배치).

소비처:
  - build_install_guides.py  (posts/*.json 생성 시 category 부여)
  - retro-apply 스크립트      (기발행 글 역보정)
  - post.py                  (에디터 카테고리 선택)

⚠️ Ch 항목은 에디터 메뉴에서 "- ChN.M 이름" 으로 표시됨(post.py가 처리).
"""
from __future__ import annotations

from pathlib import Path

# 원고 파일명(basename) → 트리 Ch 카테고리 (정확한 이름 일치)
ARTICLE_CATEGORY: dict[str, str] = {
    # PART 1: 온보딩
    "GUIDE.md":            "Ch1.1 워크스테이션 백서",
    "termux-setup.md":     "Ch1.2 Termux·proot·Ubuntu",
    "proot-ubuntu.md":     "Ch1.2 Termux·proot·Ubuntu",
    "claude-code.md":      "Ch1.3 Claude Code·DeepSeek 배선",
    "git-github.md":       "Ch1.4 GitHub·Pages·무료전시장",
    "github-pages.md":     "Ch1.4 GitHub·Pages·무료전시장",
    # PART 2: 인프라
    "telegram.md":         "Ch2.1 텔레그램·보고회의실",
    "discord.md":          "Ch2.2 Discord·커뮤니티",
    "phone-mcp.md":        "Ch2.3 Phone MCP·하드웨어 제어",
    "termux-api.md":       "Ch2.3 Phone MCP·하드웨어 제어",
    "health-check.md":     "Ch2.4 건강체크·돌봄 데몬",
    "battery-saving.md":   "Ch2.4 건강체크·돌봄 데몬",
    "performance.md":      "Ch2.4 건강체크·돌봄 데몬",
    "storage.md":          "Ch2.4 건강체크·돌봄 데몬",
    # PART 5: 출판·배포
    "tistory-auto.md":     "Ch5.1 Paste Pipeline",
    "naver-auto.md":       "Ch5.3 YouTube·네이버 연동",
    "youtube.md":          "Ch5.3 YouTube·네이버 연동",
}


def category_for(path: str | Path) -> str:
    """원고 경로 → Ch 카테고리. 미등록이면 빈 문자열(미분류)."""
    name = Path(path).name
    return ARTICLE_CATEGORY.get(name, "")

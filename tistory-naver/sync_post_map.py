#!/usr/bin/env python3
"""
sync_post_map.py — 티스토리 발행 글 ID ↔ GitHub 원고 매핑 SSOT 생성 (읽기 전용)

배경: post.py 는 발행 후 글 ID를 저장하지 않았기 때문에, 이미 발행된 글을
      "수정/재발행"하려면 블로그에서 글 ID를 역으로 찾아야 한다. 이 스크립트가
      그 역탐색을 한다 — `/manage/posts.json` API 로 모든 글(id·title·permalink·
      category)을 읽어와 원고 제목(publish-route + director-overrides)과 매칭.

산출물: assets/history-post-map.json
  { "posts": { "<원고파일>": {"id", "permalink", "title", "published",
                             "categoryId", "category"} }, ... }

소비처: republish.py (기존 글 수정), day-1 백필 대상 식별.

실행:
  python3 tistory-naver/sync_post_map.py [--account galaxys21] [--json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ROOT = BASE.parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
ROUTE = ROOT / "assets" / "publish-route.json"
OVERRIDES = ROOT / "assets" / "director-overrides.json"
OUT = ROOT / "assets" / "history-post-map.json"

PAGE_SIZE = 15


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def norm(s: str) -> str:
    return " ".join(s.split())


def build_title_index() -> dict[str, str]:
    """정규화 제목 → 원고 파일명. (라우트 원제목 + 디렉터 확정 제목 둘 다)"""
    idx: dict[str, str] = {}
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        for e in route.get("tistory", []):
            if e.get("title"):
                idx.setdefault(norm(e["title"]), e["file"])
    if OVERRIDES.exists():
        ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        for fname, p in ov.get("posts", {}).items():
            if p.get("title"):
                idx.setdefault(norm(p["title"]), fname)
    return idx


async def fetch_all_posts(page, slug: str) -> list[dict]:
    items: list[dict] = []
    total = None
    page_no = 1
    while total is None or len(items) < total:
        u = (f"https://{slug}.tistory.com/manage/posts.json"
             f"?category=-3&page={page_no}&searchKeyword=&searchType=title&visibility=all")
        r = await page.request.get(u)
        if r.status != 200:
            log(f"  ⚠ posts.json {r.status} (page {page_no}) — 중단")
            break
        j = await r.json()
        total = j.get("totalCount", len(items))
        batch = j.get("items", [])
        if not batch:
            break
        items.extend(batch)
        page_no += 1
    log(f"  posts.json 수집: {len(items)}/{total} 글")
    return items


async def run(acc_id: str) -> dict:
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == acc_id)
    acc["password"] = data["password"]
    slug = acc["blog"]

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            headless=True, viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        st_path = COOKIES_DIR / f"{acc_id}_state.json"
        if st_path.exists():
            st = json.loads(st_path.read_text())
            now = int(time.time())
            cks = []
            for c in st.get("cookies", []):
                if c.get("domain") in (".tistory.com", ".www.tistory.com",
                                       "www.tistory.com", ".daum.net"):
                    if c.get("expires", -1) == -1:
                        c["expires"] = now + 86400 * 7
                    cks.append(c)
            if cks:
                await ctx.add_cookies(cks)
                log(f"  state 쿠키 {len(cks)}개 복원")

        posts = await fetch_all_posts(page, slug)
        await ctx.close()

    idx = build_title_index()
    matched: dict[str, dict] = {}
    unmatched: list[dict] = []
    for p in posts:
        fname = idx.get(norm(p.get("title", "")))
        info = {
            "id": p.get("id"),
            "permalink": p.get("permalink"),
            "title": p.get("title"),
            "published": p.get("published"),
            "categoryId": p.get("categoryId"),
            "category": p.get("category"),
        }
        if fname:
            matched[fname] = info
        else:
            unmatched.append(info)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "matched": len(matched),
        "total_posts": len(posts),
        "posts": matched,
        "unmatched_posts": unmatched,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="galaxys21")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    log(f"=== 글 ID 매핑 생성 (계정={args.account}) ===")
    out = asyncio.run(run(args.account))

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"매칭: {out['matched']}/{out['total_posts']} 글 → {OUT}")
    if out["unmatched_posts"]:
        print("\n매칭 안 된 글 (설치가이드·고아):")
        for p in out["unmatched_posts"]:
            print(f"  #{p['id']} {p['title']}  ({p['permalink']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
delete_posts.py — mynote11605 전처리: 남은 글 전부 삭제.

빵꾸 7편 + IT 4편 = 11편 모두 삭제 대상 (채널 비우고 재구축).
#17 은 이미 삭제됨 → 나머지 10편(18,16,15,13,12,11,8,4,3,2) 삭제.

API:
  GET  /manage/posts.json?category=-3&page=N&searchKeyword=&searchType=title&visibility=all
  DELETE /manage/post/{id}.json

실행:
  python3 delete_posts.py --account mynote --list   # 글 목록만 (삭제 안 함)
  python3 delete_posts.py --account mynote          # 전부 삭제
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"

sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def fetch_posts(page, slug: str) -> list[dict]:
    """모든 글(visibility=all) 수집. 페이지네이션."""
    posts: list[dict] = []
    page_no = 1
    while True:
        r = await page.request.get(
            f"https://{slug}.tistory.com/manage/posts.json",
            params={
                "category": -3,
                "page": page_no,
                "searchKeyword": "",
                "searchType": "title",
                "visibility": "all",
            },
        )
        if not r.ok:
            raise RuntimeError(f"posts.json status={r.status}: {(await r.text())[:300]}")
        data = await r.json()
        rows = data.get("items", [])
        if not rows:
            break
        posts.extend(rows)
        total = data.get("totalCount", 1)
        if page_no * 20 >= total:
            break
        page_no += 1
    return posts


async def delete_post(page, slug: str, post_id: int, title: str) -> bool:
    r = await page.request.delete(f"https://{slug}.tistory.com/manage/post/{post_id}.json")
    ok = r.status == 200
    log(f"  {'✅' if ok else '❌'} #{post_id} {title!r} → status={r.status}")
    if not ok:
        log(f"     응답: {(await r.text())[:300]}")
    return ok


async def run(acc_id: str, dry_run: bool) -> None:
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

        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            await ctx.close()
            return
        await ctx.storage_state(path=str(st_path))

        posts = await fetch_posts(page, slug)
        log(f"현재 글 {len(posts)}편:")
        for p in posts:
            log(f"  #{p['id']} {p.get('title', '')!r} [카테고리={p.get('categoryId')}]")

        if dry_run:
            log("[dry-run] 삭제 안 함")
            await ctx.close()
            return

        if not posts:
            log("삭제할 글이 없음")
            await ctx.close()
            return

        done = 0
        for p in posts:
            if await delete_post(page, slug, p["id"], p.get("title", "")):
                done += 1
            await asyncio.sleep(0.4)

        remaining = await fetch_posts(page, slug)
        log(f"삭제 완료 {done}/{len(posts)}편, 잔여 {len(remaining)}편")
        await ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--list", action="store_true", help="글 목록만")
    args = ap.parse_args()
    asyncio.run(run(args.account, args.list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

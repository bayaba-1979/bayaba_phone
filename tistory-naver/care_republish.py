#!/usr/bin/env python3
"""care_republish.py — 돌봄 데몬 페어 발행 글을 posts/*.json 기준으로 재발행(수정).

post.py 의 `_fill_and_save(post_id 지정)`를 재사용해 기존 글 본문을 덮어쓴다(URL 불변).
아코디언·인포그래픽·복붙·테이블이 들어간 새 본문으로 교체. 공개 유지 + 댓글 비허용.

실행:
  python3 tistory-naver/care_republish.py --map 01-care-daemon:19,02-disability-welfare:20
"""
import asyncio, argparse, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
POSTS_DIR = BASE / "posts"
sys.path.insert(0, str(BASE))
from post import ensure_logged_in, _fill_and_save  # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_map(s):
    out = {}
    for pair in s.split(","):
        if ":" not in pair:
            continue
        slug, pid = pair.split(":", 1)
        out[slug.strip()] = int(pid.strip())
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--map", required=True,
                    help="slug:post_id 콤마 목록 (예: 01-care-daemon:19,02-disability-welfare:20)")
    ap.add_argument("--visibility", default="public",
                    choices=["public", "protected", "private"])
    args = ap.parse_args()

    mapping = parse_map(args.map)

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / args.account),
            headless=True, viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            await ctx.close()
            sys.exit(1)
        await ctx.storage_state(path=str(COOKIES_DIR / f"{args.account}_state.json"))

        for slug_name, pid in mapping.items():
            pf = POSTS_DIR / f"{slug_name}.json"
            if not pf.exists():
                log(f"⚠ {slug_name}.json 없음 — 스킵")
                continue
            post = json.loads(pf.read_text(encoding="utf-8"))
            title = post.get("title", slug_name)
            content = post.get("content", "")
            tags = post.get("tags", [])
            cat = post.get("category", "")
            log(f"\n▶ #{pid} {slug_name} → '{title}'")
            ok = await _fill_and_save(page, slug, pid, title, content, tags, cat,
                                      args.visibility)
            log(f"  {'✅' if ok else '❌'} #{pid} 재발행 {'완료' if ok else '실패'}")
            await page.wait_for_timeout(2000)

        await ctx.close()
    log("완료")


if __name__ == "__main__":
    asyncio.run(main())

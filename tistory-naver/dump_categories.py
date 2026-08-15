#!/usr/bin/env python3
"""dump_categories.py — 티스토리 라이브 카테고리 트리 전체 덤프 (읽기 전용)."""
import asyncio, argparse, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    args = ap.parse_args()

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
            print("❌ 로그인 실패")
            await ctx.close()
            return
        r = await page.request.get(f"https://{slug}.tistory.com/manage/category.json")
        j = await r.json()
        print(f"rootLabel: {j.get('rootLabel')!r}")
        print("=== 라이브 카테고리 트리 ===")
        for c in j.get("categories", []):
            print(f"  #{c['id']}  {c['name']!r}  entries={c.get('entries')}  depth={c.get('depth')}")
            for ch in c.get("children", []):
                print(f"      └ #{ch['id']}  {ch['name']!r}  entries={ch.get('entries')}  depth={ch.get('depth')}")
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

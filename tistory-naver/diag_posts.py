#!/usr/bin/env python3
"""diag_posts.py — galaxys21 관리자 글 목록(임시저장+발행) 덤프. 발행 실패가 draft인지 확인."""
import asyncio, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from post import ensure_logged_in, kakao_login  # noqa: E402

ACCOUNTS_FILE = BASE / "accounts.json"

async def main():
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = data["password"]
    acc = next(a for a in data["accounts"] if a["id"] == "galaxys21")
    email, pw2 = acc["email"], pw

    async with async_playwright() as pw_:
        ctx = await pw_.chromium.launch_persistent_context(
            str(BASE / "cookies" / "galaxys21"),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        ok = await ensure_logged_in(page, email, pw2)
        print("login ok:", ok)
        await page.goto("https://galaxys21-pwuser.tistory.com/manage/posts",
                        wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3000)
        print("URL:", page.url)
        rows = await page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('tr').forEach(el => {
                const t = el.innerText.trim();
                if (t) out.push(t.replace(/\\n+/g, ' | '));
            });
            return out.slice(0, 60);
        }""")
        for r in rows:
            print("ROW:", r[:160])
        html = await page.content()
        print("관리자페이지?", "manage" in page.url, "| 로그인리다이렉트?", "login" in page.url)
        print("rows_len:", len(rows))
        await ctx.close()

asyncio.run(main())

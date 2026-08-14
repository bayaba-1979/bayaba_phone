#!/usr/bin/env python3
"""
check_script_survival.py — 발행된 티스토리 포스트에서 어떤 HTML 이 살아남았는지 실측한다.
(Boss Task #6: "테스트 포스트 발행 → <script> 생존 실측")

검사 항목:
  <script>        — 복사/펼치기 JS (tinymce 가 자를 가능성 높음)
  <style>         — 인라인 스타일
  <svg>           — 인포그래픽
  <details>       — 아코디언 (네이티브)
  .s21-copy       — 코드 복사 버튼
  <pre><code>     — 설치법 코드블록

사용법:
  python3 check_script_survival.py mynote <post_url 또는 빈값=최신글>
"""
import asyncio, sys, json, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"

sys.path.insert(0, str(BASE))
from post import kakao_login  # 로그인 로직 재사용


async def main():
    acc_id = sys.argv[1] if len(sys.argv) > 1 else "mynote"
    data = json.loads(ACCOUNTS.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == acc_id)
    email, pw = acc["email"], data["password"]
    slug = acc.get("blog", acc_id)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # 로그인 (쿠키 있으면 생략)
        cookies = await ctx.cookies("https://www.tistory.com")
        if not any(c["name"] == "TSSESSION" for c in cookies):
            ok = await kakao_login(page, email, pw)
            if not ok:
                print("❌ 로그인 실패")
                await ctx.close()
                return

        # 최신 글 목록 → 첫 글 URL
        await page.goto(f"https://{slug}.tistory.com/manage/posts",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        link = await page.evaluate("""() => {
            const a = document.querySelector('a.link_article, a[href*="/m/"][href*="/"], td.title a, a.article_link');
            return a ? a.href : null;
        }""")
        if not link:
            # 폴백: 목록에서 첫 아티클 제목 링크
            link = await page.evaluate("""() => {
                for (const a of document.querySelectorAll('a')) {
                    if (a.href && /\\/\\d+$/.test(a.href) && a.href.includes('.tistory.com')) return a.href;
                }
                return null;
            }""")
        print(f"글 URL: {link}")
        if not link:
            await ctx.close()
            return

        await page.goto(link, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        title = await page.title()
        html = await page.evaluate("() => { const c=document.querySelector('.tt_article_useless_p_margin, .article_view, article, .contents_style'); return c ? c.innerHTML : document.body.innerHTML; }")

        checks = {
            "<script>": "<script" in html,
            "<style>": "<style" in html,
            "<svg>": "<svg" in html,
            "<details>": "<details" in html,
            ".s21-copy": "s21-copy" in html,
            "<pre><code>": "<pre" in html and "<code" in html,
            "data-s21=펼치기": "data-s21" in html,
        }
        print(f"제목: {title}")
        print(f"본문 길이: {len(html)}자")
        print("\n=== 생존 실측 ===")
        for k, v in checks.items():
            print(f"  {'✅' if v else '❌'} {k}")

        # script 가 있으면 그 내용 일부도
        m = re.search(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
        if m:
            print("\n  <script> 내용(일부):", m.group(1).strip()[:120].replace("\n", " "))
        await ctx.close()


asyncio.run(main())

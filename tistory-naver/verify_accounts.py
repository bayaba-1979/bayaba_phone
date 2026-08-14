"""티스토리 5계정 소유권 검증 — 누나 공통 카카오 계정에 연결된 블로그 확인

- mynote11605 = 이미 발행 성공 → 양성 대조군(소유 확정)
- 나머지 4개(galaxys21/faith/piano/metalcare)를 같은 신호로 비교
- 신호: {slug}.tistory.com/manage 접속 시
    소유 = 관리 대시보드 로드 (URL 유지, '관리'/'새 글' UI)
    미소유 = 로그인 리다이렉트 또는 '권한 없음'
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from post import kakao_login  # 로그인 로직 재사용

ACCOUNTS = json.loads((BASE / "accounts.json").read_text(encoding="utf-8"))

async def verify():
    email = ACCOUNTS["accounts"][0]["email"]
    pw = ACCOUNTS["password"]
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(BASE / "cookies" / "verify"),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        ok = await kakao_login(page, email, pw)
        if not ok:
            print("❌ 로그인 실패")
            await ctx.close()
            return
        print(f"✅ 로그인 성공: {email}\n")

        for acc in ACCOUNTS["accounts"]:
            slug = acc["blog"]
            url = f"https://{slug}.tistory.com/manage"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
            cur = page.url
            title = ""
            body = ""
            try:
                title = await page.title()
            except Exception:
                pass
            try:
                body = (await page.evaluate("document.body.innerText"))[:300]
            except Exception:
                pass
            # 소유 신호: URL이 /manage 유지 + 로그인 리다이렉트 없음 + '관리' 지표
            redirected = ("login" in cur) or ("kakao.com" in cur)
            denied = ("권한이 없" in body) or ("본인의 블로그" in body) or ("로그인이 필요" in body)
            owned = (not redirected) and ("/manage" in cur) and (not denied)
            mark = "✅ 소유" if owned else "❌ 미소유/불명"
            print(f"{mark}  {acc['id']:10s} → {slug}.tistory.com")
            print(f"      url={cur}")
            print(f"      title={title[:60]!r}")
            print(f"      body={body.replace(chr(10),' ')[:120]!r}")
            print()

        await ctx.close()

asyncio.run(verify())

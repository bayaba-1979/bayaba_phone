"""
티스토리 공식 스킨 교체 자동화 — set.json API
- POST /manage/design/skin/set.json  FormData { name: <skinName> }
- post.py 검증된 헤드리스 카카오 로그인 재사용
- 공식 스킨 (title → skinName):
    Odyssey→Odyssey, Poster→pg_Poster, Whatever→pg_Whatever, Letter→xf_Letter,
    Portfolio→xf_Portfolio, Book Club→BookClub, Magazine→xf_Magazine,
    #2→Ray2, #1→Ray, Square→Square
실행: python3 tistory-naver/switch_skin.py --skin pg_Whatever [--account galaxys21]
"""

import asyncio, argparse, json, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def kakao_login(page, email, pw):
    log(f"  재로그인: {email}")
    await page.goto("https://www.tistory.com/auth/login",
                    wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)
    try:
        btn = page.locator("a.btn_login.link_kakao_id, a:has-text('카카오계정으로 로그인')").first
        await btn.wait_for(state="visible", timeout=8000)
        await btn.click()
        await page.wait_for_timeout(4000)
    except Exception as e:
        log(f"  카카오 버튼 없음: {e}")
        return False
    try:
        await page.wait_for_selector("#loginId--1, input[name='loginId'], input[autocomplete='username']", timeout=15000)
        await page.fill("#loginId--1, input[name='loginId'], input[autocomplete='username']", email)
        await page.fill("#password--2, input[name='password'], input[type='password']", pw)
        await page.click("button[type='submit'], .btn_g.btn_confirm, button.submit")
        await page.wait_for_timeout(5000)
    except Exception as e:
        log(f"  폼 입력 실패: {e}")
    for _ in range(10):
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            return True
        await page.wait_for_timeout(1000)
    return False


async def ensure_logged_in(page, email, pw):
    cookies = await page.context.cookies("https://www.tistory.com")
    if any(c["name"] == "TSSESSION" for c in cookies):
        log("  ✅ 기존 세션 유효 (TSSESSION)")
        return True
    return await kakao_login(page, email, pw)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=str, default="galaxys21")
    parser.add_argument("--skin", type=str, required=True, help="skinName (예: pg_Whatever, Odyssey, xf_Letter)")
    args = parser.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]

    log(f"=== 티스토리 스킨 교체 (set.json) === (계정={args.account}, 블로그={slug}, 대상={args.skin})")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / args.account),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            sys.exit(1)

        set_url = f"https://{slug}.tistory.com/manage/design/skin/set.json"
        log(f"  POST {set_url} (name={args.skin})")
        save = await page.request.post(set_url, multipart={"name": args.skin})
        body = await save.text()
        log(f"  status={save.status} | 응답: {body[:300]}")

        if save.status < 300:
            # 재조회로 검증
            chk = await page.request.get(f"https://{slug}.tistory.com/manage/design/skin/skinlist.json")
            cj = await chk.json()
            cur = cj.get("currentSkin", {})
            name = cur.get("name", "")
            log(f"  ✅ 적용 검증: currentSkin.name={name}")
        else:
            log(f"  ❌ 적용 실패: {save.status} — {body[:300]}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

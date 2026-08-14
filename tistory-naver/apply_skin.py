"""
티스토리 '오비탈' 스킨 CSS 주입 자동화 (API 직접 주입 — DOM 스크래핑 없음)
- post.py 검증된 헤드리스 카카오 로그인 (cookies/{id} persistent context)
- GET  /manage/design/skin/html.json  → {html, css, files, skinname}  (css = style.css 내용)
- css 필드 맨 아래에 skin-premium.css append → POST html.json {html, css, isPreview:false}
- 마커로 멱등 처리 (이미 주입됐으면 스킵)
실행: python3 tistory-naver/apply_skin.py [--account galaxys21] [--dry-run]
"""

import asyncio, argparse, json, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"
SKIN_CSS      = BASE / "skin-premium.css"

MARKER_START = "/* HELENA-ORBITAL-SKIN-START */"
MARKER_END   = "/* HELENA-ORBITAL-SKIN-END */"


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
    if "kakao.com" in page.url:
        try:
            other = page.locator("a:has-text('다른 계정'), button:has-text('다른 계정'), a:has-text('계정 추가')").first
            if await other.is_visible(timeout=3000):
                await other.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass
    try:
        await page.wait_for_selector("#loginId--1, input[name='loginId'], input[autocomplete='username']", timeout=15000)
        await page.fill("#loginId--1, input[name='loginId'], input[autocomplete='username']", email)
        await page.wait_for_timeout(300)
        await page.fill("#password--2, input[name='password'], input[type='password']", pw)
        await page.wait_for_timeout(300)
        await page.click("button[type='submit'], .btn_g.btn_confirm, button.submit")
        await page.wait_for_timeout(5000)
    except Exception as e:
        log(f"  폼 입력 실패: {e}")
    for _ in range(10):
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            log("  ✅ 재로그인 성공")
            return True
        await page.wait_for_timeout(1000)
    log("  ❌ 재로그인 실패")
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
    parser.add_argument("--dry-run", action="store_true", help="GET만 하고 저장 안 함")
    args = parser.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]
    css_add = SKIN_CSS.read_text(encoding="utf-8")

    log(f"=== 티스토리 오비탈 스킨 주입 v2 (API 직접) === (계정={args.account}, 블로그={slug})")

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
        await ctx.storage_state(path=str(COOKIES_DIR / f"{args.account}_state.json"))

        html_url = f"https://{slug}.tistory.com/manage/design/skin/html.json"
        log(f"  GET {html_url}")

        resp = await page.request.get(html_url)
        if resp.status != 200:
            log(f"  ❌ GET 실패: {resp.status} — {await resp.text()[:200]}")
            sys.exit(1)
        j = await resp.json()
        html = j.get("html", "")
        css = j.get("css", "")
        skinname = j.get("skinname", "")
        files = j.get("files")
        log(f"  skinname={skinname} | html={len(html)}자 | css={len(css)}자 | files={files}")

        if MARKER_START in css:
            log("  ⏭ 이미 주입됨 — 스킵")
            sys.exit(0)

        inject = f"\n{MARKER_START}\n{css_add}\n{MARKER_END}\n"
        new_css = css + inject
        log(f"  CSS 주입: {len(css)} → {len(new_css)}자 (+{len(inject)})")

        if args.dry_run:
            log("  [dry-run] 저장 생략")
            sys.exit(0)

        log(f"  POST {html_url} (isPreview=false)")
        payload = {"html": html, "css": new_css, "isPreview": False}
        save = await page.request.post(html_url, data=payload)
        log(f"  POST status={save.status} | content-type={save.headers.get('content-type','')}")
        body = await save.text()
        log(f"  응답: {body[:300]}")

        if save.status < 300:
            # 재조회로 검증
            chk = await page.request.get(html_url)
            chk_css = (await chk.json()).get("css", "")
            if MARKER_START in chk_css:
                log(f"  ✅✅ 스킨 주입 완료·검증: {slug}")
            else:
                log("  ⚠ 저장 응답은 성공이나 재조회에 마커 없음 — 수동 확인 필요")
        else:
            log(f"  ❌ 저장 실패: {save.status} — {body[:300]}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

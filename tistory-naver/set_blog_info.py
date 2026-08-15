"""
티스토리 블로그 정보(이름·설명) 매핑 — /manage/setting/blog
- React SPA라 XHR로 저장. 네트워크 캡처로 엔드포인트 기록 + 실제 저장 + 재조회 검증.
- 필드 식별은 placeholder 로 (name 속성 없음).
실행: python3 tistory-naver/set_blog_info.py --account mynote \
        --name "돌봄 데몬 — 기술로 돌보는 법" \
        --desc "돌봄(케어)을 수행하는 IT. ..." \
        [--dry-run]
"""
import asyncio, argparse, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def kakao_login(page, email, pw):
    log(f"  재로그인: {email}")
    await page.goto("https://www.tistory.com/auth/login", wait_until="domcontentloaded", timeout=30000)
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
    parser.add_argument("--account", type=str, default="mynote")
    parser.add_argument("--name", type=str, required=True, help="새 블로그 이름")
    parser.add_argument("--desc", type=str, required=True, help="새 블로그 설명")
    parser.add_argument("--dry-run", action="store_true", help="채우기+버튼 탐색만, 저장 안 함")
    args = parser.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]

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

        # 네트워크 캡처 (POST/PUT XHR)
        captured = []
        async def on_request(req):
            if req.method in ("POST", "PUT") and "tistory.com" in req.url:
                try:
                    pd = req.post_data
                except Exception:
                    pd = None
                captured.append({"method": req.method, "url": req.url, "post": (pd or "")[:600]})
        page.on("request", on_request)

        url = f"https://{slug}.tistory.com/manage/setting/blog"
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(4000)

        # 필드 식별 (placeholder)
        name_sel = "input[placeholder*='블로그 이름']"
        desc_sel = "textarea[placeholder*='블로그 설명']"

        try:
            await page.wait_for_selector(name_sel, timeout=10000)
        except Exception:
            log("❌ 블로그 이름 input 미발견")
            sys.exit(1)

        cur_name = await page.input_value(name_sel)
        cur_desc = await page.input_value(desc_sel)
        log(f"  현재 이름: {cur_name!r}")
        log(f"  현재 설명: {cur_desc!r}")

        await page.fill(name_sel, args.name)
        await page.fill(desc_sel, args.desc)
        log(f"  → 이름: {args.name!r}")
        log(f"  → 설명: {args.desc!r}")

        # 저장 버튼 탐색
        btns = await page.eval_on_selector_all(
            "button, a[role='button'], .btn_save, [class*='save']",
            "els => els.map(e => (e.textContent||'').trim().slice(0,20))",
        )
        log(f"  클릭가능 요소 목록: {btns[:40]}")

        if args.dry_run:
            log("  [dry-run] 저장 생략")
            await ctx.close()
            return

        # 저장 버튼 클릭 (텍스트 '저장'/'변경'/'적용')
        clicked = False
        for sel in ["button:has-text('저장')", "button:has-text('변경사항')", "button:has-text('적용')", ".btn_save", "[class*='save']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    clicked = True
                    log(f"  ✅ 저장 클릭: {sel}")
                    break
            except Exception:
                continue
        if not clicked:
            log("  ⚠ 저장 버튼을 못 찾음 — 캡처된 XHR: " + json.dumps(captured, ensure_ascii=False))
            await ctx.close()
            sys.exit(1)

        await page.wait_for_timeout(4000)
        log("  캡처된 XHR: " + json.dumps(captured, ensure_ascii=False))

        # 재조회 검증
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        v_name = await page.input_value(name_sel)
        v_desc = await page.input_value(desc_sel)
        ok = (v_name == args.name) and (v_desc == args.desc)
        log(f"  검증 이름: {v_name!r} → {'✅ 일치' if ok else '❌ 불일치'}")
        log(f"  검증 설명: {v_desc!r}")

        await ctx.close()
        if ok:
            log(f"  ✅✅ 블로그 정보 매핑 완료: {slug} → {args.name}")


if __name__ == "__main__":
    asyncio.run(main())

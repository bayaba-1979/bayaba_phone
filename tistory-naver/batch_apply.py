"""
티스토리 스킨 표준설정 일괄 적용 — galaxys21 외 나머지 4개 블로그
- 각 블로그: ① Whatever 스킨 전환(set.json) ② skin-premium.css + S21 레이아웃 주입(html.json)
- 로그인 1회(동일 Daum 계정 REDACTED, TSSESSION 공유) 후 4개 블로그 순회
실행: python3 tistory-naver/batch_apply.py [--only mynote,faith] [--dry-run]
"""

import asyncio, argparse, json, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"
SKIN_CSS      = BASE / "skin-premium.css"

# apply_layout.py 재사용
sys.path.insert(0, str(BASE))
from apply_layout import (CSS_START, CSS_END, HTML_START, HTML_END,
                          LAYOUT_HTML, replace_block)  # noqa: E402

TARGET_SKIN = "pg_Whatever"
SKIP = {"galaxys21"}  # 이미 적용된 메인 블로그


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def kakao_login(page, email, pw):
    """카카오 로그인 — 느린 네트워크 대응(폼 렌더 최대 ~60s) + evaluate 방식 채움.
    ⚠️ 반복 시도 시 카카오 봇감지 CAPTCHA가 뜸 — 쿨다운 필요."""
    try:
        await page.goto("https://www.tistory.com/auth/login", wait_until="commit", timeout=60000)
    except Exception:
        pass
    # 카카오 버튼 클릭 (재시도)
    clicked = False
    for i in range(5):
        try:
            btn = page.locator("a.btn_login.link_kakao_id, a:has-text('카카오계정으로 로그인')").first
            await btn.wait_for(state="visible", timeout=20000)
            await btn.click()
            clicked = True
            break
        except Exception:
            try:
                await page.reload(wait_until="commit", timeout=60000)
            except Exception:
                pass
            await page.wait_for_timeout(3000)
    if not clicked:
        log("  카카오 버튼 못 찾음")
        return False
    # 카카오 로그인 폼 렌더 대기 (계정정보 폼은 JS 로딩이라 느림 ~15s)
    ready = False
    for t in range(28):
        await page.wait_for_timeout(2500)
        n = await page.evaluate("() => document.querySelectorAll('#loginId--1, input[name=loginId]').length")
        if n:
            ready = True
            log(f"  카카오 로그인 폼 렌더 완료 (~{(t + 1) * 2.5:.0f}s)")
            break
    if not ready:
        log("  카카오 로그인 폼 미렌더")
        return False
    # evaluate 방식 채움 (fill 직렬화 버그 우회)
    filled = await page.evaluate("""([e, p]) => {
        function setVal(sel, v){
            const el = document.querySelector(sel);
            if (!el) return false;
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
        }
        return {id: setVal('#loginId--1, input[name=loginId]', e),
                pw: setVal('#password--2, input[name=password]', p)};
    }""", [email, pw])
    if not (filled and filled["id"] and filled["pw"]):
        log(f"  폼 채움 실패: {filled}")
        return False
    # 제출 (비밀번호 필드에서 Enter)
    await page.locator("#password--2, input[name=password]").first.press("Enter")
    # 리다이렉트 대기
    for _ in range(45):
        u = page.url
        if "tistory.com" in u and "login" not in u and "accounts.kakao" not in u:
            return True
        await page.wait_for_timeout(1000)
    # CAPTCHA 감지
    cap = await page.evaluate("() => document.body ? document.body.innerText.includes('답해 주세요') : false")
    if cap:
        log("  ⚠️ 카카오 봇감지 CAPTCHA — 쿨다운 필요")
    return False


async def switch_skin(page, slug):
    url = f"https://{slug}.tistory.com/manage/design/skin/set.json"
    try:
        r = await page.request.post(url, multipart={"name": TARGET_SKIN})
        body = await r.text()
        log(f"    스킨전환 POST {url} -> {r.status}")
        if r.status >= 300:
            log(f"      ❌ {body[:200]}")
            return False
        return True
    except Exception as e:
        log(f"    스킨전환 ERR {e}")
        return False


async def apply_layout(page, slug, css_add, dry_run):
    html_url = f"https://{slug}.tistory.com/manage/design/skin/html.json"
    r = await page.request.get(html_url)
    if r.status != 200:
        log(f"    ❌ html.json GET {r.status}")
        return False
    j = await r.json()
    html = j.get("html", "")
    css = j.get("css", "")
    log(f"    skinname={j.get('skinname')} | html={len(html)}자 css={len(css)}자")

    if HTML_START in html:
        new_html = replace_block(html, HTML_START, HTML_END, LAYOUT_HTML)
    else:
        anchor = "<section class=\"container\">"
        new_html = (html + "\n" + LAYOUT_HTML) if anchor not in html \
            else html.replace(anchor, anchor + "\n" + LAYOUT_HTML, 1)

    css_block = f"{CSS_START}\n{css_add}\n{CSS_END}"
    new_css = replace_block(css, CSS_START, CSS_END, css_block)

    if dry_run:
        log("    [dry-run] 저장 생략")
        return True

    payload = {"html": new_html, "css": new_css, "isPreview": False}
    save = await page.request.post(html_url, data=payload)
    body = await save.text()
    log(f"    POST html.json -> {save.status}")
    if save.status >= 300:
        log(f"      ❌ {body[:200]}")
        return False
    chk = await page.request.get(html_url)
    cj = await chk.json()
    ok = HTML_START in cj.get("html", "") and CSS_START in cj.get("css", "")
    log(f"    검증 html_marker={HTML_START in cj.get('html','')} css_marker={CSS_START in cj.get('css','')}")
    return ok


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default="", help="콤마구분 계정 id (예: mynote,faith)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = data["password"]
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    targets = [a for a in data["accounts"] if a["id"] not in SKIP and (not only or a["id"] in only)]

    css_add = SKIN_CSS.read_text(encoding="utf-8")
    log(f"=== 스킨 표준설정 일괄 적용 ({len(targets)}개 블로그) ===")
    for a in targets:
        log(f"  대상: {a['id']} -> {a['blog']}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / "galaxys21"), headless=True,
            viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        email = targets[0]["email"]
        if not any(c["name"] == "TSSESSION" for c in await page.context.cookies("https://www.tistory.com")):
            if not await kakao_login(page, email, pw):
                log("❌ 로그인 실패 — 종료")
                sys.exit(1)
        else:
            log("✅ 기존 세션 유효")

        results = []
        for a in targets:
            slug = a["blog"]
            log(f"\n▶ [{a['id']}] {slug}")
            ok_skin = await switch_skin(page, slug)
            ok_layout = await apply_layout(page, slug, css_add, args.dry_run)
            results.append((a["id"], slug, ok_skin, ok_layout))
            log(f"  → {a['id']}: 스킨={ok_skin} 레이아웃={ok_layout}")

        print("\n=== 결과 요약 ===")
        for rid, slug, ok_skin, ok_layout in results:
            status = "✅" if (ok_skin and ok_layout) else "⚠️"
            print(f"  {status} {rid:10s} {slug:22s} 스킨={ok_skin} 레이아웃={ok_layout}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
티스토리 레이아웃 주입 — 좌측 카테고리 + 줌인/줌아웃 (html.json API)
- HTML: section.container 안에 <aside id="category-nav">([##_category_##] 치환자) + 줌컨트롤 + JS
- CSS : skin-premium.css append (마커 멱등)
- 마커: <!-- HELENA-LAYOUT-START/END --> (HTML) / /* HELENA-ORBITAL-SKIN-START/END */ (CSS)
실행: python3 tistory-naver/apply_layout.py [--account galaxys21] [--dry-run]
"""

import asyncio, argparse, json, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"
SKIN_CSS      = BASE / "skin-premium.css"

CSS_START = "/* HELENA-ORBITAL-SKIN-START */"
CSS_END   = "/* HELENA-ORBITAL-SKIN-END */"
HTML_START = "<!-- HELENA-LAYOUT-START -->"
HTML_END   = "<!-- HELENA-LAYOUT-END -->"

_LAYOUT_BODY = """<aside id="category-nav">
  <h2 class="cat-title">카테고리</h2>
  <div class="cat-tree">[##_category_##]</div>
  <div id="zoom-ctrl" aria-label="글자 크기">
    <button type="button" id="zoom-out" aria-label="축소">−</button>
    <button type="button" id="zoom-reset" aria-label="초기화">A</button>
    <button type="button" id="zoom-in" aria-label="확대">+</button>
  </div>
</aside>
<div id="s21-bezel" aria-hidden="true"></div>
<div id="s21-camera" aria-hidden="true">
  <span class="lens l1"></span>
  <span class="lens l2"></span>
  <span class="lens l3"></span>
  <span class="flash"></span>
</div>
<div id="s21-punch" aria-hidden="true"></div>
<div id="s21-particles" aria-hidden="true">
  <i style="--x:8%;--y:18%;--s:3px;--d:3.2s;--dl:0s"></i>
  <i style="--x:16%;--y:64%;--s:2px;--d:4.1s;--dl:.6s"></i>
  <i style="--x:24%;--y:30%;--s:4px;--d:3.7s;--dl:1.2s"></i>
  <i style="--x:33%;--y:78%;--s:2px;--d:4.6s;--dl:.3s"></i>
  <i style="--x:41%;--y:12%;--s:3px;--d:3.4s;--dl:1.8s"></i>
  <i style="--x:49%;--y:55%;--s:2px;--d:4.9s;--dl:.9s"></i>
  <i style="--x:56%;--y:22%;--s:5px;--d:3.1s;--dl:2.1s"></i>
  <i style="--x:63%;--y:70%;--s:2px;--d:4.2s;--dl:.4s"></i>
  <i style="--x:71%;--y:38%;--s:3px;--d:3.9s;--dl:1.5s"></i>
  <i style="--x:79%;--y:16%;--s:2px;--d:4.7s;--dl:.7s"></i>
  <i style="--x:87%;--y:60%;--s:4px;--d:3.5s;--dl:2.4s"></i>
  <i style="--x:93%;--y:28%;--s:3px;--d:4.3s;--dl:1.1s"></i>
  <i style="--x:12%;--y:86%;--s:2px;--d:3.6s;--dl:1.9s"></i>
  <i style="--x:38%;--y:92%;--s:2px;--d:4.8s;--dl:.2s"></i>
  <i style="--x:66%;--y:88%;--s:3px;--d:3.3s;--dl:2.6s"></i>
  <i style="--x:90%;--y:82%;--s:2px;--d:4.4s;--dl:.8s"></i>
  <i style="--x:28%;--y:45%;--s:2px;--d:5.2s;--dl:1.4s"></i>
  <i style="--x:54%;--y:6%;--s:3px;--d:3.8s;--dl:.5s"></i>
  <b style="--x:78%;--y:20%;--d:7s;--dl:2s"></b>
  <b style="--x:60%;--y:8%;--d:9s;--dl:5s"></b>
  <b style="--x:88%;--y:34%;--d:11s;--dl:1s"></b>
</div>
<script>
(function(){var s=1,step=0.1,min=0.7,max=1.6;function ap(){var c=document.getElementById('content');if(c)c.style.fontSize=(100*s)+'%';}var zi=document.getElementById('zoom-in'),zo=document.getElementById('zoom-out'),zr=document.getElementById('zoom-reset');if(zi)zi.addEventListener('click',function(){s=Math.min(max,s+step);ap();});if(zo)zo.addEventListener('click',function(){s=Math.max(min,s-step);ap();});if(zr)zr.addEventListener('click',function(){s=1;ap();});})();
</script>"""

LAYOUT_HTML = HTML_START + "\n" + _LAYOUT_BODY + "\n" + HTML_END


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


def replace_block(text, start_marker, end_marker, new_block):
    """마커 블록 교체 (멱등). 없으면 append."""
    if start_marker in text and end_marker in text:
        s = text.index(start_marker)
        e = text.index(end_marker, s) + len(end_marker)
        return text[:s] + new_block + text[e:]
    return text + "\n" + new_block


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=str, default="galaxys21")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]
    css_add = SKIN_CSS.read_text(encoding="utf-8")

    log(f"=== 티스토리 레이아웃 주입 (좌측 카테고리+줌) === (계정={args.account}, 블로그={slug})")

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

        html_url = f"https://{slug}.tistory.com/manage/design/skin/html.json"
        log(f"  GET {html_url}")
        resp = await page.request.get(html_url)
        if resp.status != 200:
            log(f"  ❌ GET 실패: {resp.status}")
            sys.exit(1)
        j = await resp.json()
        html = j.get("html", "")
        css = j.get("css", "")
        log(f"  skinname={j.get('skinname')} | html={len(html)}자 | css={len(css)}자")

        # HTML 주입 (좌측 카테고리 + 줌) — section.container 바로 뒤
        if HTML_START in html:
            new_html = replace_block(html, HTML_START, HTML_END, LAYOUT_HTML)
            log("  HTML 레이아웃 블록 교체")
        else:
            anchor = "<section class=\"container\">"
            if anchor not in html:
                log("  ⚠ anchor(section.container) 없음 — body 끝에 주입")
                new_html = html + "\n" + LAYOUT_HTML
            else:
                new_html = html.replace(anchor, anchor + "\n" + LAYOUT_HTML, 1)
                log("  HTML 레이아웃 신규 주입 (section.container 뒤)")

        # CSS 주입
        css_block = f"{CSS_START}\n{css_add}\n{CSS_END}"
        new_css = replace_block(css, CSS_START, CSS_END, css_block)

        if args.dry_run:
            log("  [dry-run] 저장 생략")
            sys.exit(0)

        payload = {"html": new_html, "css": new_css, "isPreview": False}
        log(f"  POST {html_url} (html={len(new_html)}자, css={len(new_css)}자)")
        save = await page.request.post(html_url, data=payload)
        body = await save.text()
        log(f"  POST status={save.status} | 응답: {body[:200]}")

        if save.status < 300:
            chk = await page.request.get(html_url)
            cj = await chk.json()
            ok_html = HTML_START in cj.get("html", "")
            ok_css = CSS_START in cj.get("css", "")
            log(f"  ✅ 레이아웃 주입 검증: html_marker={ok_html}, css_marker={ok_css}")
        else:
            log(f"  ❌ 저장 실패: {save.status} — {body[:300]}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

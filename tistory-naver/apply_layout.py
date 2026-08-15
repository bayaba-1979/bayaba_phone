"""
티스토리 레이아웃 주입 — 좌측 카테고리 + 줌인/줌아웃 (html.json API)
- HTML: section.container 안에 <aside id="category-nav">([##_category_##] 치환자) + 줌컨트롤 + JS
- CSS : skin-premium.css append (마커 멱등)
- 마커: <!-- HELENA-LAYOUT-START/END --> (HTML) / /* HELENA-ORBITAL-SKIN-START/END */ (CSS)
실행: python3 tistory-naver/apply_layout.py [--account galaxys21] [--dry-run]
"""

import asyncio, argparse, json, time, sys, random
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
  <!--STARS-->
  <!--METEORS-->
</div>
<script>
(function(){var s=1,step=0.1,min=0.7,max=1.6;function ap(){var c=document.getElementById('content');if(c)c.style.fontSize=(100*s)+'%';}var zi=document.getElementById('zoom-in'),zo=document.getElementById('zoom-out'),zr=document.getElementById('zoom-reset');if(zi)zi.addEventListener('click',function(){s=Math.min(max,s+step);ap();});if(zo)zo.addEventListener('click',function(){s=Math.max(min,s-step);ap();});if(zr)zr.addEventListener('click',function(){s=1;ap();});})();
</script>"""

# ── 블로그별 테마 (색 + 스타필드) — Boss 2026-08-15 ─────────────────────────
# 각 블로그 정체성에 맞춘 액센트·성운·별·유성. CSS :root 기본값 = galaxys21.
# account id 키. seed 는 별/유성 좌표 결정적 생성용(재적용해도 동일 결과).
THEME_MAP = {
    "galaxys21": {  # 개발·도구(원본) — 틸-퍼플 은하수
        "accent": "#2dd4bf", "accent_rgb": "45, 212, 191",
        "accent2": "#f0b429", "accent2_rgb": "240, 180, 41",
        "nebula_a": "rgba(96, 70, 180, 0.16)",
        "nebula_b": "rgba(45, 212, 191, 0.12)",
        "nebula_c": "rgba(240, 180, 41, 0.07)",
        "star1": "#ffffff", "star2": "#7fe7ff", "star3": "#ffd98a",
        "meteor": "#ffffff",
        "stars": 18, "meteors": 3, "pace": 1.0, "seed": 21,
        "meteor_ang": "-30deg", "meteor_dx": "-190px", "meteor_dy": "110px",
    },
    "faith": {  # 신앙=영혼 — 금빛 확산, 느리고 은은
        "accent": "#e9d9a8", "accent_rgb": "233, 217, 168",
        "accent2": "#f3e6c8", "accent2_rgb": "243, 230, 200",
        "nebula_a": "rgba(243, 230, 200, 0.16)",
        "nebula_b": "rgba(232, 196, 120, 0.12)",
        "nebula_c": "rgba(255, 255, 255, 0.06)",
        "star1": "#fffdf4", "star2": "#ffe9b0", "star3": "#ffffff",
        "meteor": "#ffe9b0",
        "stars": 24, "meteors": 3, "pace": 1.4, "seed": 7,
        "meteor_ang": "-90deg", "meteor_dx": "0px", "meteor_dy": "140px",
    },
    "piano": {  # 연주=표현 — 블루-바이올렛, 리듬감
        "accent": "#6b8cff", "accent_rgb": "107, 140, 255",
        "accent2": "#c9d4e8", "accent2_rgb": "201, 212, 232",
        "nebula_a": "rgba(107, 140, 255, 0.16)",
        "nebula_b": "rgba(120, 90, 200, 0.14)",
        "nebula_c": "rgba(201, 212, 232, 0.06)",
        "star1": "#eaf0ff", "star2": "#8fb0ff", "star3": "#d6dff5",
        "meteor": "#c9d4e8",
        "stars": 18, "meteors": 3, "pace": 1.0, "seed": 88,
        "meteor_ang": "0deg", "meteor_dx": "-190px", "meteor_dy": "0px",
    },
    "metalcare": {  # 멘탈케어=마음 — 세이지-소프트블루, 숨결처럼 느림
        "accent": "#8fd6b3", "accent_rgb": "143, 214, 179",
        "accent2": "#eef3ea", "accent2_rgb": "238, 243, 234",
        "nebula_a": "rgba(143, 214, 179, 0.14)",
        "nebula_b": "rgba(120, 170, 190, 0.12)",
        "nebula_c": "rgba(238, 243, 234, 0.05)",
        "star1": "#f2f8f4", "star2": "#b9e6cf", "star3": "#e6efe9",
        "meteor": "#cdeedc",
        "stars": 12, "meteors": 2, "pace": 2.0, "seed": 3,
        "meteor_ang": "-30deg", "meteor_dx": "-120px", "meteor_dy": "70px",
    },
    "mynote": {  # 노트·기록 — 웜그레이-세피아(종이), 짧은 펜 스트로크
        "accent": "#e8a35a", "accent_rgb": "232, 163, 90",
        "accent2": "#c8c2b8", "accent2_rgb": "200, 194, 184",
        "nebula_a": "rgba(232, 163, 90, 0.14)",
        "nebula_b": "rgba(200, 194, 184, 0.12)",
        "nebula_c": "rgba(120, 110, 96, 0.08)",
        "star1": "#f5efe6", "star2": "#ffc98a", "star3": "#d8d0c4",
        "meteor": "#f0c898",
        "stars": 18, "meteors": 3, "pace": 1.15, "seed": 42,
        "meteor_ang": "-45deg", "meteor_dx": "-90px", "meteor_dy": "50px",
    },
}


def _starfield(theme):
    """블로그 테마에 맞춰 별(<i>)과 유성(<b>) HTML을 결정적으로 생성 (같은 seed → 같은 결과)."""
    rng = random.Random(theme.get("seed", 21))
    n_stars = theme.get("stars", 18)
    n_meteors = theme.get("meteors", 3)
    pace = theme.get("pace", 1.0)

    stars = []
    for _ in range(n_stars):
        x = round(rng.uniform(4, 96))
        y = round(rng.uniform(4, 96))
        s = rng.choice([2, 2, 3, 3, 4, 5])
        d = round(rng.uniform(3.0, 5.2) * pace, 2)
        dl = round(rng.uniform(0, 2.8), 1)
        stars.append(f'<i style="--x:{x}%;--y:{y}%;--s:{s}px;--d:{d}s;--dl:{dl}s"></i>')

    meteors = []
    for _ in range(n_meteors):
        x = round(rng.uniform(30, 90))
        y = round(rng.uniform(5, 40))
        d = round(rng.uniform(7, 12) * pace, 1)
        dl = round(rng.uniform(0, 6), 1)
        meteors.append(f'<b style="--x:{x}%;--y:{y}%;--d:{d}s;--dl:{dl}s"></b>')

    return "\n  ".join(stars), "\n  ".join(meteors)


def _theme_override(theme):
    """블로그별 :root 토큰 override <style> — CSS 의 기본값을 덮어씀."""
    lines = [
        f"--s21-accent:{theme['accent']};",
        f"--s21-accent-rgb:{theme['accent_rgb']};",
        f"--s21-accent2:{theme['accent2']};",
        f"--s21-accent2-rgb:{theme['accent2_rgb']};",
        f"--s21-nebula-a:{theme['nebula_a']};",
        f"--s21-nebula-b:{theme['nebula_b']};",
        f"--s21-nebula-c:{theme['nebula_c']};",
        f"--s21-star1:{theme['star1']};",
        f"--s21-star2:{theme['star2']};",
        f"--s21-star3:{theme['star3']};",
        f"--s21-meteor:{theme['meteor']};",
        f"--s21-meteor-ang:{theme.get('meteor_ang', '-30deg')};",
        f"--s21-meteor-dx:{theme.get('meteor_dx', '-190px')};",
        f"--s21-meteor-dy:{theme.get('meteor_dy', '110px')};",
    ]
    return '<style id="s21-theme">\n:root {\n  ' + "\n  ".join(lines) + "\n}\n</style>"


def render_layout(theme):
    """블로그 테마 → 마커 감싼 최종 레이아웃 HTML (카테고리+줌+스타필드+테마 override)."""
    stars, meteors = _starfield(theme)
    body = _LAYOUT_BODY.replace("<!--STARS-->", stars).replace("<!--METEORS-->", meteors)
    body += "\n" + _theme_override(theme)
    return HTML_START + "\n" + body + "\n" + HTML_END


# 기본(galaxys21) — 하위호환 import 용
LAYOUT_HTML = render_layout(THEME_MAP["galaxys21"])


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

        # state 파일 쿠키 복원 — TSSESSION(세션쿠키)은 프로파일에 영속 안 됨 (batch_apply와 동일)
        st_path = COOKIES_DIR / f"{args.account}_state.json"
        if st_path.exists():
            st = json.loads(st_path.read_text())
            now = int(time.time())
            cks = []
            for c in st.get("cookies", []):
                if c.get("domain") in (".tistory.com", ".www.tistory.com", "www.tistory.com", ".daum.net"):
                    if c.get("expires", -1) == -1:
                        c["expires"] = now + 86400 * 7
                    cks.append(c)
            if cks:
                await ctx.add_cookies(cks)
                log(f"  state 쿠키 {len(cks)}개 복원")

        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            sys.exit(1)
        await ctx.storage_state(path=str(st_path))

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

        # HTML 주입 (좌측 카테고리 + 줌 + 스타필드) — section.container 바로 뒤
        theme = THEME_MAP.get(args.account, THEME_MAP["galaxys21"])
        layout_html = render_layout(theme)
        if HTML_START in html:
            new_html = replace_block(html, HTML_START, HTML_END, layout_html)
            log("  HTML 레이아웃 블록 교체")
        else:
            anchor = "<section class=\"container\">"
            if anchor not in html:
                log("  ⚠ anchor(section.container) 없음 — body 끝에 주입")
                new_html = html + "\n" + layout_html
            else:
                new_html = html.replace(anchor, anchor + "\n" + layout_html, 1)
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

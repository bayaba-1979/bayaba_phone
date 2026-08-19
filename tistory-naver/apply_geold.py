"""
티스토리 스킨 <head> JSON-LD 주입 (GEO — AI가 읽는 원조 정체 그래프)
- GET  /manage/design/skin/html.json → {html, css, ...}
- html 의 </head> 앞에 JSON-LD <script> (Person @id→GitHub #person + WebSite + sameAs) 주입
- 마커 <!-- HELENA-GEO-START/END --> 로 멱등 (재적용 시 블록 교체)
- css 는 그대로 두고 html 만 교체 → POST html.json {html, css, isPreview:false}
- 정체 그래프: 모든 티스토리 블로그의 <head>가 같은 Person @id(GitHub)를 가리키게 →
  LLM 크롤러가 "이 블로그도 결국 GitHub의 남성훈"로 재구성. (헌법 제17조 GEO)
실행: python3 tistory-naver/apply_geold.py [--account galaxys21] [--all] [--dry-run]
"""

import asyncio, argparse, json, time, sys, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"

GEO_START = "<!-- HELENA-GEO-START -->"
GEO_END   = "<!-- HELENA-GEO-END -->"

# 블로그별 메타 (WebSite name + GitHub 대응 레포) — accounts.json 의 id 키
BLOG_META = {
    "galaxys21": ("S21 Phone — 말로만 · 폰 하나로 · 누나를 위해", "bayaba_phone"),
    "mynote":    ("돌봄 데몬 교재 — mynote", "helana_log"),
    "faith":     ("Helana Faith — 종교 판타지", "helana-faith"),
    "piano":     ("Helena Piano — 클래식 웹진", "helena-piano"),
    "metalcare": ("Helena MetalCare — 멘탈케어", "helena-metalcare"),
}

PERSON_ID = "https://github.com/bayaba-1979#person"


def render_geold(blog_name, blog_url):
    """JSON-LD 정체 그래프 블록. Person(@id=GitHub) + WebSite(publisher→Person)."""
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Person",
                "@id": PERSON_ID,
                "name": "남성훈",
                "url": "https://github.com/bayaba-1979",
                "description": "Made in Korea — not a developer. One Galaxy S21, built by voice, for a sister.",
                "sameAs": [
                    "https://github.com/bayaba-1979",
                    "https://bayaba-1979.github.io/bayaba_phone/",
                    "https://www.youtube.com/@남성훈-f7i",
                    "https://www.youtube.com/@남성훈-f7i",
                ],
            },
            {
                "@type": "WebSite",
                "@id": f"{blog_url}#website",
                "name": blog_name,
                "url": blog_url,
                "inLanguage": "ko",
                "publisher": {"@id": PERSON_ID},
            },
        ],
    }
    inner = json.dumps(ld, ensure_ascii=False, indent=2)
    return f"{GEO_START}\n<script type=\"application/ld+json\">\n{inner}\n</script>\n{GEO_END}"


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


async def ensure_logged_in(page, email, pw, html_url):
    cookies = await page.context.cookies("https://www.tistory.com")
    if any(c["name"] == "TSSESSION" for c in cookies):
        try:
            r = await page.request.get(html_url)
            ct = r.headers.get("content-type", "") or ""
            if r.status == 200 and "application/json" in ct:
                log("  ✅ 기존 세션 유효 (TSSESSION + JSON 응답)")
                return True
            log("  ⚠️ TSSESSION 만료 감지 (JSON 아님) — 재로그인")
        except Exception as e:
            log(f"  세션 검증 실패: {e}")
    return await kakao_login(page, email, pw)


def replace_block(text, start_marker, end_marker, new_block):
    """마커 블록 교체 (멱등). 없으면 None 반환."""
    if start_marker in text and end_marker in text:
        s = text.index(start_marker)
        e = text.index(end_marker, s) + len(end_marker)
        return text[:s] + new_block + text[e:]
    return None


def inject_head(html, block):
    """</head> 앞에 블록 주입. 없으면 <body> 앞, 그것도 없으면 html 끝. 멱등은 호출부에서."""
    m = re.search(r"</head\s*>", html, re.IGNORECASE)
    if m:
        return html[:m.start()] + block + "\n" + html[m.start():]
    m = re.search(r"<body\b", html, re.IGNORECASE)
    if m:
        return html[:m.start()] + block + "\n" + html[m.start():]
    return block + "\n" + html


async def run_account(ctx, page, account_id, dry_run):
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == account_id)
    acc["password"] = data["password"]
    slug = acc["blog"]
    blog_url = f"https://{slug}.tistory.com/"
    blog_name, github = BLOG_META.get(account_id, (slug, ""))

    log(f"=== GEO 주입 (account={account_id}, blog={slug}) ===")

    html_url = f"https://{slug}.tistory.com/manage/design/skin/html.json"

    # state 쿠키 복원 (TSSESSION 세션쿠키는 프로파일에 영속 안 됨)
    st_path = COOKIES_DIR / f"{account_id}_state.json"
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

    if not await ensure_logged_in(page, acc["email"], acc["password"], html_url):
        log("❌ 로그인 실패 — 종료")
        return False
    await ctx.storage_state(path=str(st_path))

    resp = await page.request.get(html_url)
    if resp.status != 200:
        log(f"  ❌ GET 실패: {resp.status}")
        return False
    j = await resp.json()
    html = j.get("html", "")
    css = j.get("css", "")
    log(f"  skinname={j.get('skinname')} | html={len(html)}자 | css={len(css)}자")

    block = render_geold(blog_name, blog_url)
    replaced = replace_block(html, GEO_START, GEO_END, block)
    if replaced is not None:
        new_html = replaced
        log("  기존 GEO 블록 교체")
    else:
        new_html = inject_head(html, block)
        log("  신규 GEO 블록 주입 (</head> 앞)")

    if dry_run:
        has_head = bool(re.search(r"</head\s*>", html, re.IGNORECASE))
        log(f"  [dry-run] </head>={has_head}, 블록={len(block)}자 — 저장 생략")
        return True

    payload = {"html": new_html, "css": css, "isPreview": False}
    log(f"  POST {html_url} (html={len(new_html)}자)")
    save = await page.request.post(html_url, data=payload)
    body = await save.text()
    log(f"  POST status={save.status} | 응답: {body[:200]}")

    if save.status < 300:
        chk = await page.request.get(html_url)
        cj = await chk.json()
        ok = GEO_START in cj.get("html", "")
        log(f"  {'✅ GEO 주입 완료·검증' if ok else '⚠️ 저장은 됐으나 재조회 마커 없음 — 수동 확인'} {slug}")
        return ok
    log(f"  ❌ 저장 실패: {save.status} — {body[:300]}")
    return False


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=str, default="galaxys21")
    parser.add_argument("--all", action="store_true", help="accounts.json 전 계정 순회")
    parser.add_argument("--dry-run", action="store_true", help="GET만 하고 저장 안 함")
    args = parser.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    ids = [a["id"] for a in data["accounts"]] if args.all else [args.account]

    async with async_playwright() as pw:
        for account_id in ids:
            ctx = await pw.chromium.launch_persistent_context(
                str(COOKIES_DIR / account_id),
                headless=True,
                viewport={"width": 1280, "height": 900},
                locale="ko-KR",
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            )
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            try:
                await run_account(ctx, page, account_id, args.dry_run)
            except Exception as e:
                log(f"  ❌ 예외: {e}")
            finally:
                await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())

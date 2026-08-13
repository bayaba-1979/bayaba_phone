#!/usr/bin/env python3
"""
티스토리 자동 발행기 v2.0 — 단행본 출판사 에디션
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실행:
  python3 publisher.py                         ← posts/ 전부 발행
  python3 publisher.py --post posts/001.json   ← 단일 파일
  python3 publisher.py --blog 철학자박씨        ← 특정 블로그만

posts/ 디렉토리 구조:
  posts/
  └── 철학자박씨_존재와시간.json
      {
        "account": "my_account",
        "blog_slug": "dtslib",
        "blog_name": "철학자박씨",
        "title": "존재와 시간",
        "content": "<article>...HTML...</article>",
        "tags": ["철학", "하이데거"],
        "visibility": "public"
      }

에이전트(Claude/DeepSeek)가 converter.py로 생성한 JSON을
이 스크립트가 Playwright로 자동 발행한다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import asyncio, argparse, json, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
POSTS_DIR = BASE / "posts"
LOG_FILE = BASE / "output" / f"publish_{time.strftime('%Y%m%d_%H%M%S')}.log"

COOKIES_DIR.mkdir(exist_ok=True)
POSTS_DIR.mkdir(exist_ok=True)
LOG_FILE.parent.mkdir(exist_ok=True)

LOG_LINES = []
RESULTS = {"success": [], "fail": []}

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)

def save_log():
    LOG_FILE.write_text("\n".join(LOG_LINES), encoding="utf-8")
    log(f"로그 저장: {LOG_FILE}")

async def ensure_logged_in(page, email, pw):
    await page.goto("https://www.tistory.com/manage", wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(2000)
    url = page.url
    if "login" in url or "kakao.com" in url:
        return await kakao_login(page, email, pw)
    return True

async def kakao_login(page, email, pw):
    log(f"  재로그인: {email}")
    await page.goto("https://www.tistory.com/auth/login", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)
    try:
        btn = page.locator("a.btn_login.link_kakao_id").first
        await btn.wait_for(state="visible", timeout=8000)
        await btn.click()
        await page.wait_for_timeout(4000)
    except:
        return False

    if "kakao.com" in page.url:
        try:
            other = page.locator("a:has-text('다른 계정')").first
            if await other.is_visible(timeout=3000):
                await other.click(); await page.wait_for_timeout(2000)
        except:
            pass
    try:
        await page.wait_for_selector("#loginId--1, input[name='loginId']", timeout=15000)
        await page.fill("#loginId--1, input[name='loginId']", email)
        await page.wait_for_timeout(300)
        await page.fill("#password--2, input[name='password']", pw)
        await page.wait_for_timeout(300)
        await page.click("button[type='submit']")
        await page.wait_for_timeout(5000)
    except:
        pass
    for _ in range(15):
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            log("  ✅ 재로그인 성공"); return True
        await page.wait_for_timeout(1000)
    return False

async def publish_post(page, post: dict):
    blog_slug = post["blog_slug"]
    blog_name = post.get("blog_name", blog_slug)
    title = post.get("title", "")
    content = post.get("content", "")
    tags = post.get("tags", [])
    vis = post.get("visibility", "public")

    write_url = f"https://{blog_slug}.tistory.com/manage/newpost/?type=post"
    log(f"  [{blog_name}] 에디터 접속...")
    await page.goto(write_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(6000)

    # ── 제목 입력 ──
    try:
        await page.evaluate(f"""(t) => {{
            const e = document.querySelector('#post-title-inp') || document.querySelector('textarea.textarea_tit');
            if (!e) return false;
            e.value = t;
            e.dispatchEvent(new Event('input', {{bubbles:true}}));
            e.dispatchEvent(new Event('change', {{bubbles:true}}));
            return true;
        }}""", title)
        log(f"  [{blog_name}] 제목 입력 OK")
    except Exception as e:
        log(f"  [{blog_name}] 제목 실패: {e}")

    await page.wait_for_timeout(500)

    # ── 본문 입력 (TinyMCE → iframe → textarea 순차 시도) ──
    filled = False
    try:
        result = await page.evaluate(f"""(html) => {{
            try {{
                if (window.tinymce && tinymce.activeEditor) {{
                    tinymce.activeEditor.setContent(html);
                    return 'tinymce';
                }}
                const ifr = document.querySelector('iframe#editor-tistory_ifr');
                if (ifr && ifr.contentDocument) {{
                    const b = ifr.contentDocument.querySelector('body#tinymce, body');
                    if (b) {{ b.innerHTML = html; return 'iframe'; }}
                }}
                return false;
            }} catch(e) {{ return false; }}
        }}""", content)
        if result:
            filled = True
            log(f"  [{blog_name}] 본문 입력 OK ({result})")
    except:
        pass

    if not filled:
        try:
            ta = page.locator("textarea#content, textarea").first
            if await ta.is_visible(timeout=3000):
                await ta.fill(content)
                filled = True
                log(f"  [{blog_name}] textarea 본문 입력 OK")
        except:
            pass

    if not filled:
        log(f"  [{blog_name}] 본문 입력 실패 — 스킵")
        RESULTS["fail"].append(f"{blog_name}:{title[:20]}")
        return False

    await page.wait_for_timeout(500)

    # ── 태그 입력 ──
    if tags:
        try:
            el = page.locator("#tagText, input[name='tag'], input[placeholder*='태그']").first
            if await el.is_visible(timeout=5000):
                await el.click()
                for tag in tags:
                    await el.fill(tag)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(300)
                log(f"  [{blog_name}] 태그 입력 OK")
        except:
            pass

    # ── 발행 ──
    published = False
    for sel in ["button:has-text('발행')", "#publish-btn", "input[type='submit'][value*='발행']"]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(3000)
                try:
                    cf = page.locator("button:has-text('확인')").first
                    if await cf.is_visible(timeout=2000):
                        await cf.click(); await page.wait_for_timeout(2000)
                except:
                    pass
                published = True
                log(f"  [{blog_name}] ✅ 발행 완료: {title[:30]}")
                RESULTS["success"].append(f"{blog_name}:{title[:20]}")
                break
        except:
            pass

    if not published:
        log(f"  [{blog_name}] 발행 버튼 없음")
        RESULTS["fail"].append(f"{blog_name}:{title[:20]}")
    return published

async def process_account(playwright, acc_id, acc_info, posts):
    email = acc_info["email"]
    pw = acc_info["password"]
    log(f"\n{'='*50}\n계정: {email} ({len(posts)}개 포스트)")

    state_path = COOKIES_DIR / f"{acc_id}_state.json"
    ctx = await playwright.chromium.launch_persistent_context(
        str(COOKIES_DIR / acc_id),
        channel="chrome", headless=False,
        viewport={"width": 1280, "height": 900},
        locale="ko-KR",
    )
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    try:
        ok = await ensure_logged_in(page, email, pw)
        if not ok:
            log(f"  로그인 실패 — 스킵"); return
        await ctx.storage_state(path=str(state_path))

        for post in posts:
            try:
                await publish_post(page, post)
            except Exception as e:
                slug = post.get("blog_name", post.get("blog_slug", "?"))
                log(f"  [{slug}] 오류: {e}")
                RESULTS["fail"].append(f"{slug}:{post.get('title','?')[:20]}")
            await page.wait_for_timeout(2000)
    except Exception as e:
        log(f"  계정 오류: {e}")
    finally:
        await ctx.close()

async def main():
    parser = argparse.ArgumentParser(description="티스토리 자동 발행기 v2.0")
    parser.add_argument("--post", type=str, help="단일 포스트 JSON")
    parser.add_argument("--blog", type=str, help="특정 블로그만 (blog_name)")
    args = parser.parse_args()

    log("=== 티스토리 자동 발행기 v2.0 ===")
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = data["password"]
    acc_map = {a["id"]: {**a, "password": pw} for a in data["accounts"]}

    if args.post:
        post_files = [Path(args.post)]
    else:
        post_files = sorted(POSTS_DIR.glob("*.json"))

    if not post_files:
        log("❌ 포스트 파일 없음"); sys.exit(1)

    log(f"포스트 파일: {len(post_files)}개")

    acc_posts = {}
    for pf in post_files:
        post = json.loads(pf.read_text(encoding="utf-8"))
        acc_id = post.get("account")
        blog_name = post.get("blog_name", "")
        if args.blog and args.blog not in (blog_name, post.get("blog_slug", "")):
            continue
        if not acc_id:
            log(f"⚠ 'account' 없음: {pf.name} — 스킵"); continue
        if acc_id not in acc_map:
            log(f"⚠ 알 수 없는 계정: {acc_id} — 스킵"); continue
        acc_posts.setdefault(acc_id, []).append(post)

    async with async_playwright() as pw_:
        for acc_id, posts in acc_posts.items():
            await process_account(pw_, acc_id, acc_map[acc_id], posts)
            await asyncio.sleep(3)

    log(f"\n{'='*50}")
    log(f"성공: {len(RESULTS['success'])}개 → {RESULTS['success']}")
    log(f"실패: {len(RESULTS['fail'])}개 → {RESULTS['fail']}")
    save_log()

if __name__ == "__main__":
    asyncio.run(main())

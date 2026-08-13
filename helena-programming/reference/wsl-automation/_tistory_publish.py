"""Tistory 직접 발행 — post.py 우회 (셀렉터/launch context 문제 회피).

진단스크립트로 검증된 흐름:
  1. storage_state로 launch (persistent_context 아님)
  2. /manage/newpost/?type=post (실제 에디터 URL)
  3. 8초 wait (SPA init)
  4. textarea#post-title-inp 직접 evaluate (visible 검사 우회)
  5. iframe#editor-tistory_ifr 안 body#tinymce.innerHTML 세팅
  6. 발행 버튼 클릭 (visibility=public)
"""
import asyncio
import json
import os
import time
from pathlib import Path

ACCOUNTS_FILE = Path("/home/dtsli/dtslib-papyrus/tools/tistory/accounts.json")
COOKIES_DIR = Path("/home/dtsli/dtslib-papyrus/tools/tistory/cookies")


async def _kakao_login(page, email: str, pw: str) -> bool:
    """카카오 자동 로그인 — 진단스크립트 검증 흐름."""
    await page.goto("https://www.tistory.com/auth/login", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    try:
        await page.locator("a.btn_login.link_kakao_id").first.click(timeout=8000)
    except Exception as e:
        return False
    await page.wait_for_timeout(4000)
    if "kakao.com" in page.url:
        try:
            other = page.locator("a:has-text('다른 계정'), button:has-text('다른 계정')").first
            if await other.is_visible(timeout=2000):
                await other.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass
        try:
            await page.wait_for_selector("input[name='loginId']", timeout=10000)
            await page.fill("input[name='loginId']", email)
            await page.fill("input[name='password']", pw)
            await page.click("button.btn_g.highlight.submit, button[type='submit']")
            await page.wait_for_timeout(7000)
        except Exception:
            return False
    for _ in range(15):
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            return True
        await page.wait_for_timeout(1000)
    return False


async def _publish(blog: str, title: str, content_html: str,
                   tags: list, visibility: str,
                   account_id: str, email: str, pw: str) -> dict:
    from playwright.async_api import async_playwright

    cookie_state = COOKIES_DIR / f"{account_id}_state.json"
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx_kwargs = {"locale": "ko-KR",
                      "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        if cookie_state.exists():
            ctx = await b.new_context(storage_state=str(cookie_state), **ctx_kwargs)
        else:
            ctx = await b.new_context(**ctx_kwargs)
        page = await ctx.new_page()

        # 1) 로그인 보장 + 서브도메인 SSO 쿠키 박기
        sub_url = f"https://{blog}.tistory.com/manage/"
        await page.goto(sub_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "kakao.com" in page.url or "auth" in page.url:
            # 카카오 로그인 (www.tistory 경유)
            if not await _kakao_login(page, email, pw):
                await b.close()
                return {"status": "fail", "error": "카카오 로그인 실패"}
            # 핵심: 서브도메인 ping → SSO 쿠키 박음
            await page.goto(sub_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            await ctx.storage_state(path=str(cookie_state))

        # 2) 에디터 진입
        write_url = f"https://{blog}.tistory.com/manage/newpost/?type=post"
        await page.goto(write_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(8000)

        # 3) 제목 — Playwright fill (React state 정확 트리거)
        try:
            title_el = page.locator("textarea#post-title-inp").first
            await title_el.click(timeout=5000)
            await page.keyboard.type(title, delay=20)
            await page.wait_for_timeout(500)
            title_ok = True
        except Exception as e:
            await page.screenshot(path=f"/tmp/tistory_fail_title_{int(time.time())}.png")
            await b.close()
            return {"status": "fail", "error": f"제목 입력 실패: {e}"}

        # 4) 본문 TinyMCE 직접
        # setContent()만으로는 iframe 화면엔 반영되지만 Tistory가 발행 시 읽는
        # 내부 textarea/React 상태로는 동기화되지 않음 — save() + change 이벤트로 강제 동기화.
        body_ok = await page.evaluate("""(html) => {
            try {
                if (window.tinymce && tinymce.activeEditor) {
                    const ed = tinymce.activeEditor;
                    ed.setContent(html);
                    try { ed.fire('change'); } catch(e2) {}
                    try { ed.fire('input'); } catch(e2) {}
                    try { ed.save(); } catch(e2) {}
                    return 'tinymce';
                }
                const ifr = document.querySelector('iframe#editor-tistory_ifr');
                if (ifr && ifr.contentDocument) {
                    const b = ifr.contentDocument.querySelector('body#tinymce, body');
                    if (b) { b.innerHTML = html; return 'iframe-body'; }
                }
                return false;
            } catch(e) { return 'err:' + e.message; }
        }""", content_html)
        if not body_ok or str(body_ok).startswith("err"):
            await b.close()
            return {"status": "fail", "error": f"본문 세팅 실패: {body_ok}"}
        await page.wait_for_timeout(1500)
        # 검증: setContent+save 직후 getContent()로 실제 반영 확인
        verify_len = await page.evaluate("""() => {
            try { return tinymce.activeEditor.getContent().length; } catch(e) { return -1; }
        }""")
        if verify_len < 100:
            await b.close()
            return {"status": "fail", "error": f"본문 동기화 검증 실패: getContent 길이 {verify_len}"}

        # 5) 태그 (선택)
        if tags:
            try:
                tag_input = page.locator("input#tagText").first
                if await tag_input.is_visible(timeout=3000):
                    for tag in tags[:10]:
                        await tag_input.fill(tag)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(300)
            except Exception:
                pass

        # 6) 발행 — v3.2 풀 흐름
        #    publish-layer-btn (완료) → publish_editor 열림
        #    카테고리 자동 (첫 카테고리) → 라디오 → publish-btn
        # alert/confirm 자동 accept
        page.on("dialog", lambda d: asyncio.create_task(d.accept()))
        await page.wait_for_timeout(1000)
        publish_done = False

        # (pre) 카테고리 자동 선택 — 첫 카테고리 클릭 (선택 안 함 시 발행 fail)
        try:
            await page.click("button#category-btn")
            await page.wait_for_timeout(1500)
            # 카테고리 dropdown 첫 클릭 가능 항목
            first_cat = await page.evaluate("""() => {
                const items = document.querySelectorAll('.bundle_item, [class*=category] li, [class*=cate] a');
                for (const it of items) {
                    if (it.offsetParent !== null) {
                        const t = (it.textContent||'').trim();
                        if (t && t.length < 50 && !t.includes('관리') && !t.includes('추가')) {
                            it.click();
                            return t;
                        }
                    }
                }
                return null;
            }""")
            if first_cat:
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # (a) "완료" 클릭 → publish_editor layer 열림
        try:
            await page.click("button#publish-layer-btn")
            await page.wait_for_timeout(3000)
        except Exception as e:
            await b.close()
            return {"status": "fail", "error": f"완료 클릭 실패: {e}",
                    "title_set": True, "body_set": body_ok}

        # (b) 공개 span 클릭 (React 호환 — dispatchEvent는 React 상태 변경 안 됨)
        # value=20 공개 / value=15 공개(보호) / value=0 비공개
        if visibility == "public":
            try:
                await page.locator("span.checkbox-text:text('공개')").first.click(force=True, timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                try:
                    await page.evaluate("""() => {
                        const r = document.querySelector('input#open20');
                        if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); r.dispatchEvent(new Event('click', {bubbles:true})); return true; }
                        return false;
                    }""")
                    await page.wait_for_timeout(500)
                except Exception:
                    pass

        # (c) publish-btn 진짜 발행
        try:
            btn = page.locator("button#publish-btn").first
            if await btn.is_visible(timeout=3000):
                btn_text = (await btn.text_content() or "").strip()
                await btn.click()
                publish_done = True
                await page.wait_for_timeout(6000)
        except Exception as e:
            # 발행 실패 → 임시저장 fallback
            try:
                saved = await page.evaluate("""() => {
                    const a = document.querySelector('.content-aside a.action');
                    if (a) { a.click(); return true; }
                    return false;
                }""")
                if saved:
                    await page.wait_for_timeout(3000)
                    publish_done = "draft_saved"
            except Exception:
                pass

        # 7) URL 확인 — 발행 후 /manage/posts/ 로 redirect 되면 성공
        await page.wait_for_timeout(3000)
        final_url = page.url
        success = "/manage/posts" in final_url or "/manage/post/" in final_url
        # 또는 발행된 글 ID 추출
        post_url = None
        if success:
            # 최근 글 1개 URL 추출 시도
            try:
                latest = await page.evaluate("""() => {
                    const a = document.querySelector('a[href*="/manage/post/"]') ||
                              document.querySelector('a[href*="entry/"]');
                    return a ? a.href : null;
                }""")
                post_url = latest
            except Exception:
                pass

        await ctx.storage_state(path=str(cookie_state))
        await b.close()

        return {
            "status": "ok" if success or publish_done else "uncertain",
            "blog": blog, "title": title,
            "body_method": body_ok,
            "publish_clicked": publish_done,
            "final_url": final_url,
            "post_url": post_url,
            "blog_url": f"https://{blog}.tistory.com",
        }


def publish_tistory(account: str, blog: str, title: str, content_html: str,
                    tags=None, visibility: str = "public") -> dict:
    """동기 wrapper. MCP가 호출."""
    accounts = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = accounts.get("password", "")
    acc = next((a for a in accounts["accounts"] if a["id"] == account), None)
    if not acc:
        return {"status": "fail", "error": f"account 미식별: {account}"}
    if blog not in acc.get("blogs", []):
        return {"status": "fail", "error": f"blog {blog} 가 account {account} 소유 아님"}
    return asyncio.run(_publish(blog, title, content_html, tags or [],
                                 visibility, acc["id"], acc["email"], pw))


if __name__ == "__main__":
    import sys
    r = publish_tistory(
        account="parksy_kr", blog="technician-parksy",
        title="parksy-distributor v1.1 가동 검증",
        content_html="<h2>v1.1 가동 검증</h2><p>74채널 통합 MCP 작동 확인.</p>",
        tags=["parksy", "mcp", "distributor"], visibility="public",
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))

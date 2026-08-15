#!/usr/bin/env python3
"""repro_publish.py — 신규 글 발행 실패를 재현하고 실패 순간 화면/URL/토스트를 캡처."""
import asyncio, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402

async def main():
    data = json.loads((BASE / "accounts.json").read_text(encoding="utf-8"))
    pw = data["password"]
    acc = next(a for a in data["accounts"] if a["id"] == "galaxys21")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(BASE / "cookies" / "galaxys21"),
            headless=True, viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        page = ctx.pages[0]
        await ensure_logged_in(page, acc["email"], pw)

        title = f"TEST-발행진단-{time.strftime('%H%M%S')}"
        body = "<p>발행 진단용 본문입니다. 이 글은 진단 후 삭제됩니다.</p>"

        await page.goto("https://galaxys21-pwuser.tistory.com/manage/newpost/?type=post",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        print("STEP1 editor url:", page.url)

        # 제목
        try:
            tb = page.locator("#post-title-inp").first
            await tb.click()
            await page.keyboard.type(title, delay=0)
            print("STEP2 title typed")
        except Exception as e:
            print("STEP2 title FAIL", e)

        # 본문
        try:
            await page.evaluate("""(html) => {
                if (window.tinymce && tinymce.activeEditor) {
                    tinymce.activeEditor.setContent(html);
                    tinymce.activeEditor.save();
                    tinymce.activeEditor.fire('change');
                    return true;
                }
                return false;
            }""", body)
            print("STEP3 body set")
        except Exception as e:
            print("STEP3 body FAIL", e)

        await page.wait_for_timeout(1500)

        # 발행 레이어
        try:
            await page.locator("#publish-layer-btn").click()
            await page.wait_for_timeout(2000)
            print("STEP4 layer opened, url:", page.url)
        except Exception as e:
            print("STEP4 layer FAIL", e)

        # 공개 설정
        try:
            await page.locator("input[name='basicSet'][value='20']").check()
            print("STEP5 public set")
        except Exception as e:
            print("STEP5 public FAIL", e)
        await page.wait_for_timeout(800)

        # 발행 버튼
        print("STEP6 clicking #publish-btn ...")
        try:
            await page.locator("#publish-btn").click()
            print("STEP6 clicked")
        except Exception as e:
            print("STEP6 click FAIL", e)

        for i in range(6):
            await page.wait_for_timeout(2000)
            url = page.url
            print(f"  t+{(i+1)*2}s url:", url)
            # 토스트/다이얼로그 텍스트
            try:
                toast = await page.evaluate("""() => {
                    const sels = ['.toast', '.alert', '[class*=toast]', '[class*=Toast]',
                                  '.mce-notification', '[class*=dialog]', '[class*=Dialog]',
                                  '[class*=modal]', '[class*=Modal]', '.layer_body', '[class*=alert]'];
                    for (const s of sels) {
                        const el = document.querySelector(s);
                        if (el && el.innerText && el.innerText.trim()) return s + ' :: ' + el.innerText.trim().slice(0,200);
                    }
                    return null;
                }""")
                if toast:
                    print("  TOAST:", toast)
            except Exception:
                pass

        await page.screenshot(path=str(BASE / "output" / "repro_after_publish.png"), full_page=False)
        print("screenshot saved")
        await ctx.close()

asyncio.run(main())

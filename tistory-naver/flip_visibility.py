#!/usr/bin/env python3
"""flip_visibility.py — 기존 발행글 공개/비공개 전환 (본문 불변, 공개 설정만).

발행 레이어(#publish-layer-btn → basicSet 라디오 → #publish-btn)를 열어
visibility 만 바꾼다. 본문·제목·카테고리는 서버에 이미 있으므로 손대지 않는다.
게시 전에 에디터 본문이 비어있지 않은지(빵꾸 가드) 확인한다.

실행:
  python3 tistory-naver/flip_visibility.py --account mynote --ids 19,20 --visibility public
"""
import asyncio, argparse, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
sys.path.insert(0, str(BASE))
from post import ensure_logged_in, _disable_comments  # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def body_len(page) -> int:
    try:
        return await page.evaluate("""() => {
            const ed = window.tinymce && tinymce.activeEditor;
            if (!ed) return -1;
            const ta = ed.targetElm || ed.getElement();
            const v = (ta && ta.value) ? ta.value : ed.getContent({format:'text'}) || '';
            return v.trim().length;
        }""")
    except Exception:
        return -1


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--ids", required=True, help="콤마 구분 post id (예: 19,20)")
    ap.add_argument("--visibility", default="public",
                    choices=["public", "protected", "private"])
    args = ap.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == args.account)
    acc["password"] = data["password"]
    slug = acc["blog"]
    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    vis_map = {"public": "20", "protected": "15", "private": "0"}
    vis_val = vis_map[args.visibility]

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / args.account),
            headless=True, viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            await ctx.close()
            sys.exit(1)
        await ctx.storage_state(path=str(COOKIES_DIR / f"{args.account}_state.json"))

        for pid in ids:
            url = f"https://{slug}.tistory.com/manage/newpost/{pid}?type=post"
            log(f"#{pid} 에디터 접근")
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(8000)

            # 빵꾸 가드: 본문이 비어있으면 건드리지 않음
            blen = await body_len(page)
            log(f"  본문 길이: {blen}")
            if blen is None or blen < 500:
                log(f"  ⚠ #{pid} 본문 미로드 의심({blen}) — 스킵 (빵꾸 방지)")
                continue

            try:
                await page.locator("#publish-layer-btn").click()
                await page.wait_for_timeout(2000)
            except Exception as e:
                log(f"  ❌ #{pid} 레이어 열기 실패: {e}")
                continue

            try:
                await page.locator(f"input[name='basicSet'][value='{vis_val}']").check()
                log(f"  #{pid} 공개 설정: {args.visibility} (value={vis_val})")
            except Exception as e:
                log(f"  ❌ #{pid} 공개 설정 실패: {e}")
                continue

            await page.wait_for_timeout(800)
            ok_cmt = await _disable_comments(page)
            log(f"  #{pid} 댓글 비허용: {'OK' if ok_cmt else '⚠ 실패(진행)'}")
            await page.wait_for_timeout(500)

            try:
                await page.locator("#publish-btn").click()
                await page.wait_for_timeout(6000)
                ok = "newpost" not in page.url
                log(f"  {'✅' if ok else '❌'} #{pid} → {args.visibility}")
            except Exception as e:
                log(f"  ❌ #{pid} 발행 클릭 실패: {e}")

            await page.wait_for_timeout(2000)

        await ctx.close()
    log("완료")


if __name__ == "__main__":
    asyncio.run(main())

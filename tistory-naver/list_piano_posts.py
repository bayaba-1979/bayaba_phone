#!/usr/bin/env python3
"""list_piano_posts.py — helena-piano 관리자 글 목록 덤프 (ID·제목·공개상태).

flip_visibility.py 의 --ids 입력값을 뽑기 위한 조회 도구.
비공개 글도 관리자 목록에는 표시되므로, 최근 발행한 9편 + id=2 의 post_id 를 얻는다.
"""
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402

ACCOUNTS_FILE = BASE / "accounts.json"
ACC = "piano"


async def main():
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = data["password"]
    acc = next(a for a in data["accounts"] if a["id"] == ACC)
    email = acc["email"]
    blog = acc.get("blog") or f"{ACC}-pwuser"

    async with async_playwright() as pw_:
        ctx = await pw_.chromium.launch_persistent_context(
            str(BASE / "cookies" / ACC),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        ok = await ensure_logged_in(page, email, pw)
        print(f"login ok: {ok}")

        await page.goto(f"https://{blog}.tistory.com/manage/posts",
                        wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3500)

        rows = await page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('a[href*="/manage/post/"], a[href*="postId="]').forEach(a => {
                const m = (a.getAttribute('href')||'').match(/post\\/(\\d+)|postId=(\\d+)/);
                if (!m) return;
                const id = m[1] || m[2];
                const t = (a.innerText||'').trim();
                if (!out[id]) out[id] = [];
                out[id].push(t);
            });
            return Object.entries(out).map(([id, texts]) => ({
                id,
                texts,
                title: texts.filter(t => t && t !== '수정' && t !== '삭제' && t !== '통계')
                            .sort((a,b)=>b.length-a.length)[0] || texts[0] || ''
            }));
        }""")
        # 공개 상태도 함께: 각 행의 row 텍스트에서 공개/비공개/보호 배지 추출
        badges = await page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('tr').forEach(tr => {
                const idm = (tr.innerHTML||'').match(/post\\/(\\d+)|postId=(\\d+)/);
                if (!idm) return;
                const id = idm[1] || idm[2];
                const t = (tr.innerText||'');
                if (/비공개/.test(t)) out[id] = 'private';
                else if (/보호/.test(t)) out[id] = 'protected';
                else if (/공개/.test(t)) out[id] = 'public';
            });
            return out;
        }""")
        rows.sort(key=lambda r: int(r["id"]))
        print(f"\n=== {blog} 글 목록 ({len(rows)}개) ===")
        for r in rows:
            vis = badges.get(r["id"], "?")
            print(f"  #{r['id']:>6} [{vis:9}] {r['title'][:46]}")
        print("\n--- private ids (flip 대상) ---")
        print(",".join(r["id"] for r in rows if badges.get(r["id"]) == "private"))
        print("--- 전체 ids ---")
        print(",".join(r["id"] for r in rows))
        await ctx.close()


asyncio.run(main())

#!/usr/bin/env python3
"""
reverse_fetch.py — 티스토리 발행 글의 원고 HTML을 로컬로 역가져오기.

"전시장(Tistory)엔 있는데 GitHub 원본은 없는" 글을 백업/이관한다.
posts.json API 로 모든 글 ID를 얻고, 각 글 에디터(/manage/newpost/{id})에서
tinymce.getContent()(본문 원고 HTML, 스킨 벗긴 것)를 읽어 로컬 .html 로 저장.

산출물:
  {out}/{account}/0001__slug.html ...   본문 원고 HTML (원고 한 편 = 파일 하나)
  {out}/{account}/index.json            id·제목·슬러그·permalink·파일 매핑

실행:
  python3 reverse_fetch.py --account mynote                 # 전 건
  python3 reverse_fetch.py --account mynote --limit 3       # 3건만 (테스트)
  python3 reverse_fetch.py --account mynote --dry-run       # 목록만
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
OUT_ROOT = BASE / "reverse_fetch"

sys.path.insert(0, str(BASE))
from post import kakao_login, ensure_logged_in  # noqa: E402


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sanitize(s: str) -> str:
    s = re.sub(r"[^\w가-힣-]+", "-", s or "").strip("-")
    return s or "post"


async def fetch_all_posts(page, slug: str) -> list[dict]:
    items: list[dict] = []
    total = None
    page_no = 1
    while total is None or len(items) < total:
        u = (f"https://{slug}.tistory.com/manage/posts.json"
             f"?category=-3&page={page_no}&searchKeyword=&searchType=title&visibility=all")
        r = await page.request.get(u)
        if r.status != 200 or "json" not in r.headers.get("content-type", ""):
            log(f"  ⚠ posts.json 비JSON 응답(status={r.status}) — 세션 무효로 간주")
            break
        j = await r.json()
        total = j.get("totalCount", len(items))
        batch = j.get("items", [])
        if not batch:
            break
        items.extend(batch)
        page_no += 1
    return items


async def extract_content(page, timeout: int = 20000) -> str | None:
    """에디터에서 tinymce 본문 원고 HTML 을 읽는다 (준비될 때까지 폴링).

    반환:
      None      → timeout 내 에디터가 준비되지 않음 (폴링 종료)
      str("")   → 에디터 준비됨 but 본문이 비어 있음 (빵꾸)
      str(html) → 본문 원고 HTML
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            c = await asyncio.wait_for(
                page.evaluate("""() => {
                    if (window.tinymce && tinymce.activeEditor) {
                        return {ready: true, html: tinymce.activeEditor.getContent() || ''};
                    }
                    return {ready: false, html: null};
                }"""),
                timeout=8,
            )
        except asyncio.TimeoutError:
            # 페이지 로딩 중 JS context 교체 등으로 evaluate가 매달리면 재시도
            await asyncio.sleep(1)
            continue
        if c and c.get("ready"):
            return c.get("html") or ""
        await asyncio.sleep(1)
    return None


async def run(acc_id: str, limit: int | None, dry_run: bool) -> None:
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == acc_id)
    acc["password"] = data["password"]
    slug = acc["blog"]
    out_dir = OUT_ROOT / acc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            headless=True, viewport={"width": 1280, "height": 900}, locale="ko-KR",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        st_path = COOKIES_DIR / f"{acc_id}_state.json"
        if st_path.exists():
            st = json.loads(st_path.read_text())
            now = int(time.time())
            cks = []
            for c in st.get("cookies", []):
                if c.get("domain") in (".tistory.com", ".www.tistory.com",
                                       "www.tistory.com", ".daum.net"):
                    if c.get("expires", -1) == -1:
                        c["expires"] = now + 86400 * 7
                    cks.append(c)
            if cks:
                await ctx.add_cookies(cks)
                log(f"  state 쿠키 {len(cks)}개 복원")

        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            await ctx.close()
            return
        await ctx.storage_state(path=str(st_path))

        # 세션 유효성 실측 (TSSESSION 쿠키 존재 ≠ 서버 유효. 만료 시 HTML 리다이렉트)
        probe = await page.request.get(
            f"https://{slug}.tistory.com/manage/posts.json"
            f"?category=-3&page=1&searchKeyword=&searchType=title&visibility=all")
        if "json" not in probe.headers.get("content-type", ""):
            log("  ⚠ 세션 만료 감지 — kakao 재로그인 시도")
            if await kakao_login(page, acc["email"], acc["password"]):
                await ctx.storage_state(path=str(st_path))
                log("  ✅ 재로그인 성공")
            else:
                log("  ❌ 재로그인 실패 — 수동 로그인 필요 (ncaptcha 가능)")
                await ctx.close()
                return

        posts = await fetch_all_posts(page, slug)
        if limit:
            posts = posts[:limit]

        log(f"=== 역가져오기 {acc_id} ({len(posts)}건) → {out_dir} ===")

        saved = []
        for p in posts:
            pid = p.get("id")
            slogan = sanitize(p.get("slogan") or f"post-{pid}")
            title = p.get("title", "")
            permalink = p.get("permalink", "")
            fname = f"{int(pid):04d}__{slogan}.html"

            if dry_run:
                log(f"  [dry-run] #{pid} {title}")
                continue

            if (out_dir / fname).exists():
                # 이미 저장된 파일 → 인덱스에만 포함 (완전한 매니페스트 유지)
                existing = (out_dir / fname).read_text(encoding="utf-8")
                is_empty = existing.strip() == "<!-- 빈 글 (본문 없음) -->"
                saved.append({
                    "id": pid, "slogan": p.get("slogan"), "title": title,
                    "permalink": permalink, "file": fname,
                    "published": p.get("published"), "category": p.get("category"),
                    "empty": is_empty,
                })
                log(f"  ⏭ #{pid} 이미 저장됨 — 스킵")
                continue

            url = f"https://{slug}.tistory.com/manage/newpost/{pid}?type=post"

            async def _fetch_one() -> None:
                # 새 페이지 = 이전 에디터의 dirty(beforeunload) 상태와 무관 → 내비게이션 안전
                t0 = time.time()
                p2 = await ctx.new_page()
                try:
                    await p2.goto(url, wait_until="domcontentloaded", timeout=60000)
                    try:
                        await p2.wait_for_load_state("load", timeout=10000)
                    except Exception:
                        pass
                    html = await extract_content(p2, timeout=30000)
                    if html is None:
                        log(f"  ⚠ #{pid} 에디터 미준비 — 스킵")
                        return
                    info = {
                        "id": pid, "slogan": p.get("slogan"), "title": title,
                        "permalink": permalink, "file": fname,
                        "published": p.get("published"), "category": p.get("category"),
                    }
                    if not html.strip():
                        (out_dir / fname).write_text("<!-- 빈 글 (본문 없음) -->\n", encoding="utf-8")
                        info["empty"] = True
                        saved.append(info)
                        log(f"  ⚪ #{pid} {title[:32]} (빈 글·빵꾸, {time.time()-t0:.0f}s)")
                        return
                    (out_dir / fname).write_text(html, encoding="utf-8")
                    saved.append(info)
                    log(f"  ✅ #{pid} {title[:32]} ({len(html)}자, {time.time()-t0:.0f}s)")
                finally:
                    try:
                        await p2.close(run_before_unload=False)
                    except Exception:
                        pass

            try:
                await asyncio.wait_for(_fetch_one(), timeout=120)
            except asyncio.TimeoutError:
                log(f"  ⏱ #{pid} 120초 타임아웃 — 스킵")
            except Exception as e:
                log(f"  ❌ #{pid} 오류: {e}")

        await ctx.close()

    if not dry_run:
        index = {
            "account": acc_id, "blog": slug,
            "generated": time.strftime("%Y-%m-%d %H:%M"),
            "count": len(saved), "posts": saved,
        }
        (out_dir / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"\n완료: {len(saved)}/{len(posts)}건 저장 → {out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.account, args.limit, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

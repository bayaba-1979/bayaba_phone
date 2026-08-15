#!/usr/bin/env python3
"""
republish.py — 기존 발행 글을 GitHub 원고 기준으로 재발행(수정).

"GitHub 원고(_notebook/*.md)가 곧 티스토리" — 디렉터 게이트 확정치(제목·카테고리)를
반영하고, 본문은 현재 md 에서 다시 렌더해서 기존 글에 덮어쓴다(같은 글 ID 유지 →
URL 불변). post.py 의 `_fill_and_save` 를 재사용(신규 발행과 동일 에디터 흐름).

전제:
  - sync_post_map.py 로 `assets/history-post-map.json` 생성 (글 ID 역탐색).
  - director_gate.py 로 `assets/director-overrides.json` 갱신 (제목·카테고리 SSOT).

실행:
  python3 republish.py --list                # 재발행 대상(수정 필요) 목록만
  python3 republish.py --file 00-INDEX.md    # 한 건만
  python3 republish.py --all                 # 수정 필요한 전 건 (day-1 백필 포함)
  python3 republish.py --all --dry-run       # 무엇을 바꿀지만 출력 (발행 안 함)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ROOT = BASE.parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"
MAP = ROOT / "assets" / "history-post-map.json"
OVERRIDES = ROOT / "assets" / "director-overrides.json"

sys.path.insert(0, str(BASE))
from post import _fill_and_save, ensure_logged_in  # noqa: E402
import template  # noqa: E402


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_map() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8")).get("posts", {})


def load_overrides() -> dict:
    return json.loads(OVERRIDES.read_text(encoding="utf-8")).get("posts", {})


def build_targets(only_files: list[str] | None) -> list[dict]:
    """수정이 필요한 발행 글 목록 → [{file, id, live_title, live_cat, new_title,
    new_cat, tags, changed}]."""
    pmap = load_map()
    ov = load_overrides()
    targets = []
    files = only_files if only_files else sorted(pmap.keys())
    for fname in files:
        live = pmap.get(fname)
        if not live:
            continue
        gate = ov.get(fname, {})
        new_title = gate.get("title") or live.get("title") or ""
        new_cat = gate.get("category", "")
        tags = gate.get("tags") or ["S21", "업무수첩"]
        changed = []
        if live.get("title") != new_title:
            changed.append("제목")
        cid = live.get("categoryId")
        no_cat = cid in (0, "0", None, "") or live.get("category") in (None, "", "카테고리 없음")
        if no_cat and new_cat:
            changed.append("카테고리")
        # 본문은 항상 md 기준 재렌더 → "수정됨"이 아니라 "동기화"로 취급
        targets.append({
            "file": fname,
            "id": live["id"],
            "live_title": live.get("title"),
            "live_cat": (live.get("category") in (None, "", "카테고리 없음")
                         and "미분류" or live.get("category")),
            "new_title": new_title,
            "new_cat": new_cat,
            "tags": tags,
            "changed": changed,
        })
    return targets


def render_content(fname: str, new_title: str) -> str:
    md = ROOT / "_notebook" / fname
    if not md.exists():
        raise FileNotFoundError(md)
    raw = md.read_text(encoding="utf-8")
    body = template.strip_frontmatter(raw)
    _, deck = template.extract_title_deck(body)
    return template.render_tistory_html(new_title, deck, body)


async def run(targets: list[dict], acc_id: str, dry_run: bool) -> None:
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == acc_id)
    acc["password"] = data["password"]
    slug = acc["blog"]

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
            sys.exit(1)
        await ctx.storage_state(path=str(st_path))

        for t in targets:
            if dry_run:
                log(f"  [dry-run] #{t['id']} {t['file']}  변경: {','.join(t['changed']) or '본문 동기화'}")
                continue
            try:
                content = render_content(t["file"], t["new_title"])
            except FileNotFoundError as e:
                log(f"  ⚠ {t['file']} 원고 없음 — 스킵: {e}")
                continue
            log(f"\n  ▶ #{t['id']} {t['file']}  ({','.join(t['changed']) or '본문 동기화'})")
            ok = await _fill_and_save(page, slug, t["id"], t["new_title"],
                                      content, t["tags"], t["new_cat"], "public")
            log(f"  {'✅' if ok else '❌'} {t['file']} 재발행 {'완료' if ok else '실패'}")
            await page.wait_for_timeout(2000)

        await ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="galaxys21")
    ap.add_argument("--file", type=str, help="단일 원고 파일명 (예: 00-INDEX.md)")
    ap.add_argument("--all", action="store_true", help="매핑된 전 건")
    ap.add_argument("--list", action="store_true", help="대상 목록만 출력")
    ap.add_argument("--dry-run", action="store_true", help="발행 없이 계획만")
    args = ap.parse_args()

    only = [args.file] if args.file else None
    targets = build_targets(only if not args.all else None)

    if args.list:
        print(f"=== 재발행 대상 {len(targets)}건 ===")
        for t in targets:
            fix = f"제목: '{t['live_title']}' → '{t['new_title']}'" if "제목" in t["changed"] else ""
            cat = f"카테고리: {t['live_cat']} → {t['new_cat']}" if "카테고리" in t["changed"] else ""
            print(f"  #{t['id']:>2} {t['file']:22s}  {fix} {cat}".rstrip())
        return 0

    if not targets:
        log("재발행 대상 없음")
        return 0

    log(f"=== 재발행 {len(targets)}건{' (dry-run)' if args.dry_run else ''} ===")
    asyncio.run(run(targets, args.account, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

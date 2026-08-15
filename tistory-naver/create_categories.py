#!/usr/bin/env python3
"""
create_categories.py — 티스토리 카테고리를 API로 생성 (mynote 돌봄 5트랙).

티스토리 관리자 카테고리 편집기(/manage/category)의 실제 PUT 요청을 리버스엔지니어링했다:
  PUT /manage/category.json
  {"rootLabel": "분류 전체보기", "delete": [], "append": [...], "update": [...]}

새 최상위 카테고리 노드는 append·update 둘 다에 동일하게 들어간다(updatedData=true).
id 는 음수 임시값(-1, -2, ...)을 쓰고, 서버가 실제 id 를 발급한다. parent=0 은 루트노드.

산출: 이미 존재하는 이름은 건너뛰고(멱등), 빠진 이름만 생성 → 검증 출력.

실행:
  python3 create_categories.py --account mynote --list      # 계획만 (생성 안 함)
  python3 create_categories.py --account mynote             # 실제 생성
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"

sys = __import__("sys")
sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402

# mynote11605 = 돌봄(케어) 하이테크 IT 채널 — 5트랙 구조
CATEGORIES = [
    "트랙 DW — 장애·정신건강 복지",
    "트랙 DC — 치매·노인 돌봄",
    "트랙 BL — 기초생활 보장",
    "대화록 — 하루 스토리",
    "솔루션 — 돌봄 자동화",
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def get_tree(page, slug: str) -> dict:
    r = await page.request.get(f"https://{slug}.tistory.com/manage/category.json")
    if not r.ok:
        raise RuntimeError(f"category.json status={r.status}: {(await r.text())[:300]}")
    return await r.json()


def top_level_names(tree: dict) -> dict[str, int]:
    """최상위 카테고리 이름 → (id, priority) 매핑."""
    out: dict[str, int] = {}
    for c in tree.get("categories", []):
        out[c["name"]] = c["id"]
    return out


def build_node(name: str, temp_id: int, priority: int) -> dict:
    return {
        "id": temp_id,
        "name": name,
        "children": [],
        "depth": 1,
        "opened": True,
        "priority": priority,
        "visibility": 20,
        "parent": 0,
        "viewChannel": None,
        "entries": 0,
        "categoryInfo": {},
        "isNew": True,
        "updatedData": True,
    }


async def run(acc_id: str, names: list[str], dry_run: bool) -> None:
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

        if not await ensure_logged_in(page, acc["email"], acc["password"]):
            log("❌ 로그인 실패 — 종료")
            await ctx.close()
            return
        await ctx.storage_state(path=str(st_path))

        tree = await get_tree(page, slug)
        existing = top_level_names(tree)
        root_label = tree.get("rootLabel", "분류 전체보기")

        missing = [n for n in names if n not in existing]
        if not missing:
            log(f"이미 전부 존재 — 건너뜀 ({len(names)}개)")
            await ctx.close()
            return

        next_priority = len(tree.get("categories", []))
        append = []
        for i, name in enumerate(missing):
            append.append(build_node(name, -(i + 1), next_priority + i))

        payload = {
            "rootLabel": root_label,
            "delete": [],
            "append": append,
            "update": [dict(n) for n in append],  # 새 노드는 update에도 동일 반영
        }

        log(f"생성 대상 {len(missing)}개: {missing}")
        if dry_run:
            for n in append:
                log(f"  [dry-run] + {n['name']} (priority={n['priority']})")
            await ctx.close()
            return

        r = await page.request.put(
            f"https://{slug}.tistory.com/manage/category.json",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
        )
        log(f"PUT status={r.status}")
        if r.status != 200:
            log(f"  응답: {(await r.text())[:500]}")
            await ctx.close()
            return

        # 검증
        tree2 = await get_tree(page, slug)
        names2 = list(top_level_names(tree2).keys())
        log("현재 최상위 카테고리:")
        for c in tree2.get("categories", []):
            mark = "✅" if c["name"] in names else "  "
            log(f"  {mark} #{c['id']} {c['name']!r} (entries={c['entries']})")
        await ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--list", action="store_true", help="계획만 출력")
    ap.add_argument("--name", action="append", default=None, help="개별 카테고리 추가(반복 가능)")
    args = ap.parse_args()
    names = args.name if args.name else CATEGORIES
    asyncio.run(run(args.account, names, args.list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

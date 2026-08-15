#!/usr/bin/env python3
"""
setup_care_categories.py — mynote11605 돌봄 데몬 채널 카테고리 계층형 재구축.

Boss 확정 구조 (2026-08-15, 계층형):

  매니페스토 — 기술로 돌보는 법        (01)
  트랙 — 제도                          (02~04)
    ├ DW — 장애·정신건강 복지
    ├ DC — 치매·노인 돌봄
    └ BL — 기초생활 보장
  대화록 — 하루 스토리                 (05)
  솔루션 — 돌봄 데몬                   (06~10)
    ├ 아키텍처
    ├ 배터리·온도
    ├ 위치·GPS
    ├ 원격 돌봄망
    └ 보고 무전기

방법: 기존 평면 5개(트랙 DW/DC/BL + 대화록 + 솔루션)를 삭제하고,
      새 4개 최상위(매니페스토/트랙/대화록/솔루션)를 만든 뒤,
      트랙·솔루션 아래 자식을 2단계로 붙인다 (자식은 실 parent id 필요).

API: PUT /manage/category.json {rootLabel, delete, append, update}
  — create_categories.py 에서 리버스엔지니어링한 계약 재사용.

실행:
  python3 setup_care_categories.py --account mynote --list   # 계획만
  python3 setup_care_categories.py --account mynote          # 실제 재구축
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
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"

sys.path.insert(0, str(BASE))
from post import ensure_logged_in  # noqa: E402

# 평면 5개 (삭제 대상) — 대화록은 이름이 동일하지만 재구축 위해 함께 삭제 후 재생성
OLD_FLAT = [
    "트랙 DW — 장애·정신건강 복지",
    "트랙 DC — 치매·노인 돌봄",
    "트랙 BL — 기초생활 보장",
    "대화록 — 하루 스토리",
    "솔루션 — 돌봄 자동화",
]

# 계층형 구조: 최상위명 → [자식명, ...] (빈 리스트 = 자식 없음)
STRUCTURE: dict[str, list[str]] = {
    "매니페스토 — 기술로 돌보는 법": [],
    "트랙 — 제도": [
        "DW — 장애·정신건강 복지",
        "DC — 치매·노인 돌봄",
        "BL — 기초생활 보장",
    ],
    "대화록 — 하루 스토리": [],
    "솔루션 — 돌봄 데몬": [
        "아키텍처",
        "배터리·온도",
        "위치·GPS",
        "원격 돌봄망",
        "보고 무전기",
    ],
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def node(name: str, temp_id: int, priority: int, parent=0, depth=1) -> dict:
    return {
        "id": temp_id, "name": name, "children": [], "depth": depth,
        "opened": True, "priority": priority, "visibility": 20,
        "parent": parent, "viewChannel": None, "entries": 0,
        "categoryInfo": {}, "isNew": True, "updatedData": True,
    }


async def get_tree(page, slug: str) -> dict:
    r = await page.request.get(f"https://{slug}.tistory.com/manage/category.json")
    if not r.ok:
        raise RuntimeError(f"category.json status={r.status}: {(await r.text())[:300]}")
    return await r.json()


async def put_tree(page, slug: str, payload: dict) -> None:
    r = await page.request.put(
        f"https://{slug}.tistory.com/manage/category.json",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False),
    )
    if r.status != 200:
        raise RuntimeError(f"PUT status={r.status}: {(await r.text())[:500]}")
    log(f"  PUT status={r.status}")


def find_id_by_name(tree: dict, name: str) -> int | None:
    for c in tree.get("categories", []):
        if c["name"] == name:
            return c["id"]
        for ch in c.get("children", []):
            if ch["name"] == name:
                return ch["id"]
    return None


async def run(acc_id: str, dry_run: bool) -> None:
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
        root_label = tree.get("rootLabel", "분류 전체보기")
        top = tree.get("categories", [])

        # 삭제 대상 id (평면 5개)
        delete_ids = [c["id"] for c in top if c["name"] in OLD_FLAT]
        # 삭제 후 남는 이름 기준으로, 빠진 최상위만 재생성 (멱등)
        remaining = {c["name"] for c in top if c["name"] not in OLD_FLAT}

        new_top = [n for n in STRUCTURE if n not in remaining]

        log(f"삭제 {len(delete_ids)}개: {[c['name'] for c in top if c['name'] in OLD_FLAT]}")
        log(f"새 최상위 {len(new_top)}개: {new_top}")
        log(f"자식 총 {sum(len(v) for v in STRUCTURE.values())}개")

        if dry_run:
            await ctx.close()
            return

        # ── Phase 1: 삭제 + 최상위 4개 생성 ──────────────────────────────
        base_priority = len(top)  # 기존(IT, 사고흐름) 뒤에 붙임
        top_nodes = [node(n, -(i + 1), base_priority + i) for i, n in enumerate(new_top)]
        payload = {
            "rootLabel": root_label,
            "delete": delete_ids,
            "append": top_nodes,
            "update": [dict(n) for n in top_nodes],
        }
        log("Phase 1 — 최상위 생성")
        await put_tree(page, slug, payload)

        # ── Phase 2: 자식 생성 (실 parent id 필요) ───────────────────────
        tree2 = await get_tree(page, slug)
        child_nodes = []
        temp_id = -1
        for parent_name, children in STRUCTURE.items():
            if not children:
                continue
            parent_id = find_id_by_name(tree2, parent_name)
            if parent_id is None:
                log(f"  ⚠ 부모 '{parent_name}' id 미확인 — 자식 스킵")
                continue
            for prio, ch_name in enumerate(children):
                child_nodes.append(node(ch_name, temp_id, prio, parent=parent_id, depth=2))
                temp_id -= 1
        if child_nodes:
            payload2 = {
                "rootLabel": root_label,
                "delete": [],
                "append": child_nodes,
                "update": [dict(n) for n in child_nodes],
            }
            log(f"Phase 2 — 자식 {len(child_nodes)}개 생성")
            await put_tree(page, slug, payload2)

        # ── 검증 ─────────────────────────────────────────────────────────
        tree3 = await get_tree(page, slug)
        log("=== 최종 카테고리 트리 ===")
        for c in tree3.get("categories", []):
            log(f"  #{c['id']} {c['name']!r} (entries={c['entries']})")
            for ch in c.get("children", []):
                log(f"      └ #{ch['id']} {ch['name']!r} (entries={ch['entries']})")
        await ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mynote")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.account, args.list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
verify_categories.py — 티스토리 카테고리 트리 검증 게이트 (읽기 전용)

역할: `tistory-categories.txt`(SSOT, 8 PART · 32 Chapter)와
      블로그 `/manage/category` 라이브 트리를 대조해 **미생성 카테고리를 검출**한다.

배경: history 발행 시 `post.py`의 `_set_category`는 없는 카테고리를
      **조용히 미분류로 강등**(크래시 아님)한다. 그래서 발행 전에 트리가
      완비됐는지 검증하는 게 품질 게이트의 전제다. (2026-08-15 실측: 41/500,
      SSOT 전 항목 존재 → 0 누락. 이 스크립트는 그 사실을 매번 재확인하는 장치.)

실행:
  python3 tistory-naver/verify_categories.py [--account galaxys21]
  exit 0 = SSOT 전 항목 존재 / exit 1 = 누락 있음(이름 출력)
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
SSOT = ROOT / "tistory-categories.txt"
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"


def parse_ssot(txt: str) -> list[tuple[str, list[str]]]:
    """tistory-categories.txt → [(PART 이름, [Ch 이름, ...]), ...].

    PART 라인은 ' — ' 설명어를 떼고 블로그 표기('PART 1: 온보딩')만 쓴다.
    Ch 라인은 '├─ / └─ ' 트리 글리프를 떼고 'ChN.M 이름'만 쓴다."""
    parts: list[tuple[str, list[str]]] = []
    cur: list[str] | None = None
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("PART "):
            name = s.split(" — ")[0].strip()
            parts.append((name, []))
            cur = parts[-1][1]
        elif ("├─" in s or "└─" in s) and "Ch" in s:
            if cur is not None:
                cur.append(s.split("─ ")[-1].strip())
    return parts


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def ensure_logged_in(page, email: str, pw: str) -> bool:
    cookies = await page.context.cookies("https://www.tistory.com")
    if any(c["name"] == "TSSESSION" for c in cookies):
        return True
    # 세션 만료 시 — post.py/apply_layout.py 와 동일한 재로그인은 하지 않는다.
    # (1회성 설정은 캡차 리스크. 여기선 "재로그인 필요" 로 실패시킨다.)
    log("  ⚠ TSSESSION 없음 — 세션 만료. post.py 재로그인 또는 수동 로그인 필요")
    return False


async def verify(acc_id: str) -> tuple[bool, list[str]]:
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    acc = next(a for a in data["accounts"] if a["id"] == acc_id)
    acc["password"] = data["password"]
    slug = acc["blog"]
    ssot = parse_ssot(SSOT.read_text(encoding="utf-8"))

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            headless=True,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
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
            await ctx.close()
            return False, ["로그인 실패"]

        url = f"https://{slug}.tistory.com/manage/category"
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(5000)
        body = await page.evaluate("() => document.body.innerText")
        await ctx.close()

    missing: list[str] = []
    for part, chs in ssot:
        if part not in body:
            missing.append(part)
        for ch in chs:
            if ch not in body:
                missing.append(f"  - {ch} (in {part})")
    return (len(missing) == 0, missing)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="galaxys21")
    args = ap.parse_args()

    log(f"=== 카테고리 트리 검증 (SSOT={SSOT.name}, 계정={args.account}) ===")
    ok, missing = asyncio.run(verify(args.account))
    if ok:
        log("✅ SSOT 전 항목 존재 (0 누락) — _set_category 정밀 배치 가능")
        return 0
    log(f"❌ 누락 {len(missing)}건:")
    for m in missing:
        log(f"  {m}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

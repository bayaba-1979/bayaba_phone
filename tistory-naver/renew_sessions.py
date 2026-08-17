#!/usr/bin/env python3
"""
티스토리 5블로그 세션 일괄 갱신 — 카카오 1회 로그인 → 5개 세션 시드

왜 필요한가:
  - 5개 티스토리 = 누나 카카오 1계정(accounts.json) 공유. 로그인 1번이면 5블로그 전부 커버.
  - post.py 의 ensure_logged_in() 은 TSSESSION 쿠키 "존재"만 보고 서버측 유효성은 안 본다.
    → 만료된 쿠키가 남아 있으면 재로그인을 안 하므로, 강제로 비우고 새로 로그인해야 한다.
  - TSSESSION 은 세션쿠키(expires=-1)라 persistent profile 에 영속되지 않음(재실행 시 유실).
    → 만료를 +7일로 보정해 add_cookies 로 영속화한다(batch_apply.py 의 검증된 패턴).

사용법:
  python3 renew_sessions.py            # 5개 일괄 갱신 (headless)
  python3 renew_sessions.py --headed   # 화면 띄워 captcha 수동 입력 (xvfb-run -a + RustDesk)
  python3 renew_sessions.py --dry-run  # 갱신 없이 현재 상태만 probe

절차:
  1) 만료 세션 삭제 (cookies/{id}_state.json + cookies/{id}/)
  2) 카카오 1회 로그인 (captcha 시 60초 수동 대기)
  3) 5개 계정에 동일 세션 시드 (persistent profile + state.json 둘 다)
  4) manage URL 실측 probe → 전부 ✅ 여야 exit 0
"""

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from post import kakao_login  # noqa: E402  (로그인 로직 재사용 — verify_accounts.py 와 동일)

ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR = BASE / "cookies"

# republish.py / batch_apply.py 와 동일한 쿠키 도메인 필터 (검증된 최소 세트)
USABLE_DOMAINS = {".tistory.com", ".www.tistory.com", "www.tistory.com", ".daum.net"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def mask(email: str) -> str:
    """이메일 일부 마스킹 — 로그에는 전체 이메일을 찍지 않는다."""
    if "@" not in email:
        return "***"
    user, domain = email.split("@", 1)
    return f"{user[0]}***@{domain}"


def _usable(cookies: list) -> list:
    """시드할 쿠키만 남기고, 세션쿠키(expires=-1)는 +7일로 보정(영속화)."""
    now = int(time.time())
    out = []
    for c in cookies:
        if c.get("domain") not in USABLE_DOMAINS:
            continue
        if c.get("expires", -1) == -1:
            c["expires"] = now + 86400 * 7
        out.append(c)
    return out


def purge(ids: list) -> None:
    """만료 세션 강제 삭제 — state.json + persistent profile 둘 다."""
    for acc_id in ids:
        st = COOKIES_DIR / f"{acc_id}_state.json"
        if st.exists():
            st.unlink()
        prof = COOKIES_DIR / acc_id
        if prof.exists():
            import shutil
            shutil.rmtree(prof)
    log(f"  만료 세션 {len(ids)}개 삭제 완료")


def probe_all(accounts: list) -> int:
    """manage URL 실측 probe — 302→login 이면 만료로 판정. preflight.sh 와 동일 신호."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}
    fail_cnt = 0
    print()
    for a in accounts:
        acct, slug = a["id"], a["blog"]
        st = COOKIES_DIR / f"{acct}_state.json"
        try:
            d = json.loads(st.read_text(encoding="utf-8"))
            header = "; ".join(f"{c['name']}={c['value']}" for c in d.get("cookies", []))
        except Exception:
            print(f"  ❌ {acct:10s} — state 없음")
            fail_cnt += 1
            continue
        try:
            req = urllib.request.Request(
                f"https://{slug}.tistory.com/manage", headers={"Cookie": header, **UA}
            )
            urllib.request.build_opener(NoRedirect).open(req, timeout=10)
            print(f"  ✅ {acct:10s} → {slug}.tistory.com — 세션 유효")
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location", "")
            if "/auth/login" in loc:
                print(f"  ❌ {acct:10s} → {slug}.tistory.com — 만료(login 리다이렉트)")
                fail_cnt += 1
            else:
                print(f"  ⚠️ {acct:10s} → {slug}.tistory.com — HTTP {e.code}")
        except Exception as e:
            print(f"  ⚠️ {acct:10s} → {slug}.tistory.com — probe 오류 {e}")
    print()
    return fail_cnt


async def renew(headed: bool) -> int:
    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw = data["password"]
    accounts = data["accounts"]
    email = accounts[0]["email"]
    ids = [a["id"] for a in accounts]
    ctx_kwargs = dict(
        headless=not headed,
        viewport={"width": 1280, "height": 900},
        locale="ko-KR",
        args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    )

    # 1) 만료 세션 삭제
    purge(ids)

    async with async_playwright() as p:
        # 2) 카카오 1회 로그인 (마스터 = galaxys21 프로파일)
        ctx = await p.chromium.launch_persistent_context(
            str(COOKIES_DIR / "galaxys21"), **ctx_kwargs
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        log(f"  카카오 로그인 시도: {mask(email)}")
        ok = await kakao_login(page, email, pw)
        if not ok:
            log("❌ 로그인 실패 — captcha/2FA 필요 시: xvfb-run -a python3 renew_sessions.py --headed")
            await ctx.close()
            return 1
        log("  ✅ 카카오 로그인 성공")

        # 블로그 서브도메인에서 세션 수용되는지 확인 (TSSESSION 도메인 정착)
        slug0 = accounts[0]["blog"]
        await page.goto(f"https://{slug0}.tistory.com/manage", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # 3) 쿠키 확보 + 세션쿠키 영속화 보정
        seeds = _usable(await ctx.cookies())
        if not any(c["name"] == "TSSESSION" for c in seeds):
            log("❌ TSSESSION 미확보 — 로그인은 됐으나 세션 쿠키 없음")
            await ctx.close()
            return 1
        await ctx.storage_state(path=str(COOKIES_DIR / "galaxys21_state.json"))
        await ctx.close()
        log(f"  마스터 세션 확보 (TSSESSION 포함 {len(seeds)}개 쿠키)")

        # 4) 5개 계정에 동일 세션 시드 (profile + state.json)
        for a in accounts:
            acc_id = a["id"]
            c = await p.chromium.launch_persistent_context(
                str(COOKIES_DIR / acc_id), **ctx_kwargs
            )
            if seeds:
                await c.add_cookies(seeds)
            await c.storage_state(path=str(COOKIES_DIR / f"{acc_id}_state.json"))
            await c.close()
            log(f"  ✅ {acc_id:10s} 시드 완료")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="티스토리 5블로그 세션 일괄 갱신")
    ap.add_argument("--headed", action="store_true", help="화면 띄움 (captcha 수동 입력용)")
    ap.add_argument("--dry-run", action="store_true", help="갱신 없이 현재 상태만 probe")
    ap.add_argument("--if-needed", action="store_true", help="만료일 때만 갱신 (전부 유효하면 스킵) — 발행 전 자가치유")
    args = ap.parse_args()

    data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    accounts = data["accounts"]
    log(f"=== 티스토리 세션 갱신 ({len(accounts)}개 블로그 / 카카오 1계정) ===")

    if args.if_needed:
        log("=== 자가치유: 현재 세션 상태 probe ===")
        if probe_all(accounts) == 0:
            log("ℹ 전 블로그 이미 유효 — 갱신 스킵")
            return 0
        log("⚠ 만료 감지 → 자동 갱신 시작")

    if args.dry_run:
        return 0 if probe_all(accounts) == 0 else 1

    rc = asyncio.run(renew(args.headed))
    if rc != 0:
        return rc

    # 5) 최종 검증
    log("=== 최종 검증 (manage URL 실측) ===")
    fail = probe_all(accounts)
    log("✅ 전 블로그 세션 유효" if fail == 0 else f"❌ {fail}개 블로그 여전히 만료")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

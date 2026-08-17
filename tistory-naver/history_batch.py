#!/usr/bin/env python3
"""
히스토리(업무수첩) → 티스토리 일일 배치 업로드 (계정토탈 15개/일 한도 준수)

Boss 2026-08-15: "히스토리 하루 12개씩, 자정 지나면 다음 배치".
2026-08-16 스케줄러 확실성 패치: 일일 한도는 "계정 단위 15개"이며 5개 블로그가
공유한다(실측 08-15: 13+2=15, 16번째 403). 그래서 배치 크기를 12개로 고정하지
않고, RSS로 5개 블로그의 오늘 발행수를 세서 "남은 한도"만큼만 배치한다.
  - 분모: assets/publish-route.json 의 tistory 목록 (110개, 순서 고정)
  - 민감 원천파일(실데이터 가능)은 스킵: 99-devlog · 17-chronicle · 세션 로그
  - 상태: assets/history-upload-state.json (done 목록) — 내일 이어받기
  - posts/*.json 생성 → post.py 가 실제 발행

실행:
  python3 history_batch.py --dry-run   # 오늘 남은 한도 안에서 다음 배치 목록
  python3 history_batch.py --build     # 배치 posts/*.json 생성 (기존 posts/ 비움)
  python3 history_batch.py --run       # build + post.py 발행 (권장)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(ROOT / "scripts"))
from template import build_post_json  # noqa: E402
from load_ecosystem import repos as _ecosystem_repos, repo_by_name, hub_repo  # noqa: E402

# 허브(galaxys21) = 히스토리(업무수첩) 발행 블로그. SSOT에서 role="hub"로 유도.
_hub = repo_by_name(hub_repo())
ACCOUNT = _hub.get("account", "galaxys21")
BLOG = _hub.get("blog", "galaxys21-pwuser")
ROUTE = ROOT / "assets" / "publish-route.json"
STATE = ROOT / "assets" / "history-upload-state.json"
OVERRIDES = ROOT / "assets" / "director-overrides.json"
POSTS_DIR = BASE / "posts"
BATCH_SIZE = 12
DEFAULT_TAGS = ["S21", "업무수첩", "히스토리"]

# ── 일일 한도 (계정 토탈) ──────────────────────────────────────────────────
# 티스토리 하루 신규 발행 한도는 "계정 단위 15개"이며 5개 블로그가 공유한다
# (실측 2026-08-15: galaxys21 13 + mynote 2 = 15, 16번째 403).
# 그래서 히스토리(galaxys21) 배치만 보면 안 되고, 5개 블로그의 오늘 발행수를
# 전부 세서 "남은 한도"만큼만 배치해야 한다. ← 스케줄러 확실성의 핵심.
def _load_daily_limit() -> int:
    """일일 한도 SSOT = configs/quota-manifest.json. 없으면 실측값 15 폴백."""
    try:
        with open(ROOT / "configs" / "quota-manifest.json", encoding="utf-8") as f:
            return int(json.load(f)["tistory"]["limit_per_day"])
    except Exception:
        return 15


DAILY_LIMIT = _load_daily_limit()
ALL_BLOGS = [r["blog"] for r in _ecosystem_repos() if r.get("blog")]

# 실데이터 가능한 원천파일(헌법: 돌봄 데이터 절대 공개 금지) — 스킵
SKIP_FILES = {
    "99-devlog.md",              # 원시 세션 devlog
    "17-merged-chronicle.md",    # 병합 연대기
}


def is_sensitive(fname: str) -> bool:
    if fname in SKIP_FILES:
        return True
    if re.search(r"session", fname, re.I):
        return True
    return False


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"done": [], "total": 0}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_overrides() -> dict:
    """디렉터 게이트 산출물(assets/director-overrides.json)의 posts 맵."""
    if OVERRIDES.exists():
        return json.loads(OVERRIDES.read_text(encoding="utf-8")).get("posts", {})
    return {}


def today_published_count() -> int:
    """오늘(KST) 5개 블로그에서 실제 발행된 신규 글 수를 RSS로 센다.

    티스토리 일일 한도(15개)는 "계정 토탈"이므로, galaxys21 히스토리 배치가
    mynote 돌봄 데몬·기타 블로그 글과 한도를 공유한다. 이 함수가 그 공유 분모를
    실제 서버(RSS pubDate)에서 읽어 남은 한도를 계산한다. 상태 파일이 아니라
    RSS를 쓰는 이유: 발행 실패·수동 발행·타 블로그 발행까지 전부 반영되기 때문.

    pubDate 포맷: "Sun, 16 Aug 2026 04:51:05 +0900" → 날짜 부분 "16 Aug 2026".
    """
    today = time.strftime("%d %b %Y")  # KST 기준 (호스트 TZ=Asia/Seoul)
    total = 0
    for b in ALL_BLOGS:
        try:
            raw = urllib.request.urlopen(f"https://{b}.tistory.com/rss", timeout=20).read()
            root = ET.fromstring(raw.decode("utf-8", "ignore"))
            for item in root.findall(".//item"):
                pub = item.findtext("pubDate") or ""
                if today in pub:
                    total += 1
        except Exception as e:
            print(f"  ⚠ 오늘 발행수 집계 실패({b}): {e}")
    return total


def remaining_budget() -> int:
    """오늘 남은 신규 발행 한도 (계정 토탈). 0 이하면 발행 중단."""
    return max(0, DAILY_LIMIT - today_published_count())


def is_blocked(fname: str, overrides: dict) -> bool:
    """디렉터 판정 HOLD/REVISE → 발행 보류."""
    return overrides.get(fname, {}).get("verdict") in ("HOLD", "REVISE")


def next_batch() -> list[dict]:
    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    tistory = route["tistory"]
    state = load_state()
    done = set(state.get("done", []))
    overrides = load_overrides()
    pending = [e for e in tistory
               if e["file"] not in done and not is_sensitive(e["file"])
               and not is_blocked(e["file"], overrides)]
    # 계정 토탈 일일 한도(15개) 반영 — 남은 한도만큼만 배치.
    budget = remaining_budget()
    cap = min(BATCH_SIZE, budget)
    print(f"  [한도] 오늘 계정토탈 발행 {today_published_count()}개 / 남은 한도 {budget}개 → 배치 {min(len(pending), cap)}개")
    if cap <= 0:
        print(f"  ⛔ 오늘 신규 발행 한도({DAILY_LIMIT}개) 소진 — 내일(KST 자정 이후) 다시 실행")
        return []
    return pending[:cap]


def build(batch: list[dict]) -> list[Path]:
    """기존 posts/*.json 비우고 새 12개 생성 (디렉터 게이트 반영)."""
    for old in POSTS_DIR.glob("*.json"):
        old.unlink()
    overrides = load_overrides()
    outs = []
    for e in batch:
        md = ROOT / "_notebook" / e["file"]
        if not md.exists():
            print(f"  ⚠ 없음: {e['file']}")
            continue
        ov = overrides.get(e["file"], {})
        verdict = ov.get("verdict", "")
        if verdict in ("HOLD", "REVISE"):
            print(f"  ⛔ {e['file']} — 디렉터 보류({verdict})")
            continue
        title = ov.get("title") or None
        tags = ov.get("tags") or DEFAULT_TAGS
        out = build_post_json(md, ACCOUNT, BLOG, title, tags,
                              visibility="public", category=ov.get("category", ""))
        outs.append(out)
    return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    batch = next_batch()
    state = load_state()
    print(f"=== 히스토리 일일 배치 ({len(batch)}개/일) ===")
    print(f"진행: {len(state.get('done', []))}개 완료 / 다음 {len(batch)}개")
    for i, e in enumerate(batch):
        print(f"  {i + 1:2d}. {e['file']}  — {e['title'][:44]}")

    if args.dry_run:
        return 0

    outs = build(batch)
    print(f"\n생성: {len(outs)}개 posts/*.json")

    if not args.run:
        print("(발행 생략 — post.py 를 직접 실행하거나 --run 사용)")
        return 0

    print("\n=== post.py 발행 시작 ===")
    r = subprocess.run([sys.executable, str(BASE / "post.py")],
                       cwd=str(BASE), text=True,
                       capture_output=True, timeout=1800)
    tail = (r.stdout or r.stderr or "")[-1500:]
    print(tail)

    # 발행 성공 판정 — "✅ 발행 완료: <제목>" 줄을 제목 prefix로 batch 파일에 매핑.
    # (post.py 성공 순서 ≠ batch 순서: 실패가 중간에 끼면 batch[:ok]는 오답.
    #  예: 04-github-pages가 오판됐고 00/05/06이 실패했을 때 batch[:8]은 4개나 틀림.)
    def _norm(t):
        return re.sub(r"\s+", " ", t).strip()

    success_titles = re.findall(r"✅ 발행 완료: (.+)", (r.stdout or "") + (r.stderr or ""))

    if r.returncode == 0 and success_titles:
        state.setdefault("done", [])
        done_set = set(state["done"])
        matched = []
        for e in batch:
            key = _norm(e["title"])[:30]
            if any(key == _norm(s)[:30] for s in success_titles):
                if e["file"] not in done_set:
                    done_set.add(e["file"])
                    matched.append(e["file"])
        state["done"] = sorted(done_set)
        state["total"] = len(state["done"])
        state["last_run"] = time.strftime("%Y-%m-%d %H:%M")
        save_state(state)
        print(f"\n✅ 상태 저장: {len(matched)}개 신규 완료 (누적 {state['total']}개) → {STATE.name}")
    else:
        print("\n⚠️ 발행 미완료 — 상태 저장 생략 (다음 실행에서 재시도)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

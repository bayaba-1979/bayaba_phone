#!/usr/bin/env python3
"""
히스토리(업무수첩) → 티스토리 일일 배치 업로드 (12개/일)

Boss 2026-08-15: "히스토리 하루 12개씩, 자정 지나면 다음 배치".
- 분모: assets/publish-route.json 의 tistory 목록 (110개, 순서 고정)
- 민감 원천파일(실데이터 가능)은 스킵: 99-devlog · 17-chronicle · 세션 로그
- 상태: assets/history-upload-state.json (done 목록) — 내일 이어받기
- posts/*.json 생성 → post.py 가 실제 발행

실행:
  python3 history_batch.py --dry-run   # 다음 12개 목록만
  python3 history_batch.py --build     # 12개 posts/*.json 생성 (기존 posts/ 비움)
  python3 history_batch.py --run       # build + post.py 발행 (권장)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
sys.path.insert(0, str(BASE))
from template import build_post_json  # noqa: E402

ACCOUNT = "galaxys21"
BLOG = "galaxys21-pwuser"
ROUTE = ROOT / "assets" / "publish-route.json"
STATE = ROOT / "assets" / "history-upload-state.json"
POSTS_DIR = BASE / "posts"
BATCH_SIZE = 12
DEFAULT_TAGS = ["S21", "업무수첩", "히스토리"]

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


def next_batch() -> list[dict]:
    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    tistory = route["tistory"]
    state = load_state()
    done = set(state.get("done", []))
    pending = [e for e in tistory
               if e["file"] not in done and not is_sensitive(e["file"])]
    return pending[:BATCH_SIZE]


def build(batch: list[dict]) -> list[Path]:
    """기존 posts/*.json 비우고 새 12개 생성."""
    for old in POSTS_DIR.glob("*.json"):
        old.unlink()
    outs = []
    for e in batch:
        md = ROOT / "_notebook" / e["file"]
        if not md.exists():
            print(f"  ⚠ 없음: {e['file']}")
            continue
        out = build_post_json(md, ACCOUNT, BLOG, None, DEFAULT_TAGS,
                              visibility="public", category="")
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

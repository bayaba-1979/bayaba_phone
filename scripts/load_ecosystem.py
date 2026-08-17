#!/usr/bin/env python3
"""
load_ecosystem.py — S21 생태계 SSOT 로더
=========================================
repo↔blog↔channel · owner · git 신원 · 동기화 설정을 configs/ecosystem.json 에서 읽는다.

우선순위:
  1. configs/ecosystem.json          (navigator가 생성 — gitignore, 사용자 실제값)
  2. configs/ecosystem.json.template (커밋된 샘플 = 헬레나 실측값)

이 파일은 "설정 파일을 읽는 공통 로더"다. 하드코딩된 slug/owner/channel 을
여기로 옮기고, 각 스크립트는 이 로더를 import 해 쓰면 된다.

사용법:
  import (scripts/ 또는 tistory-naver/ 어디서든):
      import sys; from pathlib import Path
      sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
      from load_ecosystem import load, repos, blog_by_repo, owner, git_identity

  CLI:
      python3 scripts/load_ecosystem.py --check       # 검증 + 요약
      python3 scripts/load_ecosystem.py --json owner  # 특정 키 출력 (쉘용)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REAL = BASE / "configs" / "ecosystem.json"
TEMPLATE = BASE / "configs" / "ecosystem.json.template"


def load() -> dict:
    """ecosystem.json(사용자) → 템플릿(샘플) 순으로 읽는다."""
    path = REAL if REAL.exists() else TEMPLATE
    if not path.exists():
        raise FileNotFoundError(f"ecosystem.json 없음: {REAL} / {TEMPLATE}")
    return json.loads(path.read_text(encoding="utf-8"))


def owner() -> str:
    return load().get("owner", "")


def identity() -> dict:
    """정체 그래프(GEO 원조 스탬프) 블록 — person_name/github_user/hub_repo/tagline/sameAs."""
    return load().get("identity", {})


def git_identity() -> dict:
    return load().get("git", {})


def sync_params() -> dict:
    return load().get("sync", {})


def repos() -> list:
    return load().get("repos", [])


def channels() -> list:
    return load().get("channels", [])


def naver() -> dict:
    return load().get("naver", {})


def youtube() -> dict:
    return load().get("youtube", {})


def repo_by_name(name: str) -> dict:
    for r in repos():
        if r.get("repo") == name:
            return r
    return {}


def repo_by_account(account: str) -> dict:
    for r in repos():
        if r.get("account") == account:
            return r
    return {}


def blog_by_repo(name: str) -> str:
    return repo_by_name(name).get("blog", "")


def blog_by_account(account: str) -> str:
    return repo_by_account(account).get("blog", "")


def channel_by_repo(name: str) -> str:
    return repo_by_name(name).get("channel", "")


def account_ids() -> list:
    return [r.get("account") for r in repos() if r.get("account")]


def blog_slugs() -> list:
    return [r.get("blog") for r in repos() if r.get("blog")]


def channel_id_by_handle(handle: str) -> str:
    for c in channels():
        if c.get("handle") == handle:
            return c.get("id", "")
    return ""


def hub_repo() -> str:
    for r in repos():
        if r.get("role") == "hub":
            return r.get("repo", "")
    return ""


# ── CLI ──────────────────────────────────────────────────────────────────────
def _check() -> int:
    d = load()
    print(f"owner : {d.get('owner')}")
    g = git_identity()
    print(f"git   : {g.get('name')} <{g.get('email')}> ua={g.get('user_agent')}")
    s = sync_params()
    print(f"sync  : cron={s.get('cron')} out_dir={s.get('out_dir')}")
    print(f"naver : {naver().get('blog')}")
    print(f"채널 {len(channels())}개:")
    for c in channels():
        print(f"  {c.get('handle'):16s} id={c.get('id') or '(비어있음)'}")
    print(f"레포 {len(repos())}개:")
    ok = True
    for r in repos():
        missing = [k for k in ("repo", "account", "blog", "channel") if not r.get(k)]
        if missing:
            ok = False
        flag = "✅" if not missing else f"❌ 누락 {missing}"
        print(f"  {flag} {r.get('repo'):16s} → {r.get('blog'):18s} → {r.get('channel')}")
    print("결과:", "✅ 정합" if ok else "❌ 누락 필드 있음")
    return 0 if ok else 1


def main() -> int:
    if "--check" in sys.argv:
        return _check()
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        key = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        val = load().get(key, "")
        print(val if isinstance(val, str) else json.dumps(val, ensure_ascii=False))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

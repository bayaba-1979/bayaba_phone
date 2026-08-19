#!/usr/bin/env python3
"""
search_console.py — 색인 제출 보조 (GSC · Bing WMT · 네이버 서치어드바이저)
========================================================================
헌법 제17조 측정 루프의 "색인" 단계. 사이트맵(sitemap.xml)은 이미 라이브(174 URL).
이 스크립트는 **소유권 인증 파일**을 올바른 레포 루트에 만들어 커밋·푸시해준다.
인증이 통과되면 각 엔진 UI에서 sitemap URL 하나만 붙여넣으면 된다.

사용법 (Boss가 각 엔진 UI에서 준 "토큰/파일명"을 그대로 넘기면 됨):
  python3 scripts/search_console.py verify --engine gsc   --token XXXX --repo bayaba_phone
  python3 scripts/search_console.py verify --engine bing  --token XXXX --repo bayaba_phone
  python3 scripts/search_console.py verify --engine naver --token XXXX --repo bayaba_phone

  python3 scripts/search_console.py list      # 5레포별 sitemap URL + 인증 상태 출력

인증 파일 규격(각 엔진 공식):
  GSC   → google{token}.html  (내용: google-site-verification: {token})
  Bing  → BingSiteAuth.xml    (내용: <users><user>{token}</user></users>)
  Naver → naver{token}.html   (내용: <meta name="naver-site-verification" content="{token}">)

주의: GitHub Pages 배포 반영까지 수십 초~2분 걸릴 수 있음. 인증 클릭은 파일이
라이브(HTTP 200)로 확인된 뒤에 하면 된다. --no-commit 플래그로 커밋 전 단계 확인 가능.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parents[1]  # /root/work (bayaba_phone)

# 5레포 (hub + 위성 4). 각각 GitHub Pages 프로젝트 사이트.
REPOS = {
    "bayaba_phone": "https://bayaba-1979.github.io/bayaba_phone/",
    "helena-piano": "https://bayaba-1979.github.io/helena-piano/",
    "helena-metalcare": "https://bayaba-1979.github.io/helena-metalcare/",
    "helana-faith": "https://bayaba-1979.github.io/helana-faith/",
    "helana_log": "https://bayaba-1979.github.io/helana_log/",
}


def _repo_path(repo: str) -> Path:
    if repo == "bayaba_phone":
        return HUB
    return HUB / repo


def _file_spec(engine: str, token: str):
    """(파일명, 내용) — 엔진별 공식 인증 파일 규격."""
    engine = engine.lower()
    if engine == "gsc":
        return f"google{token}.html", f"google-site-verification: {token}\n"
    if engine == "bing":
        return "BingSiteAuth.xml", f'<?xml version="1.0"?>\n<users>\n  <user>{token}</user>\n</users>\n'
    if engine == "naver":
        return f"naver{token}.html", f'<meta name="naver-site-verification" content="{token}" />\n'
    raise SystemExit(f"❌ 알 수 없는 엔진: {engine} (gsc|bing|naver)")


def verify(repo: str, engine: str, token: str, no_commit: bool = False) -> int:
    path = _repo_path(repo)
    if not path.exists():
        raise SystemExit(f"❌ 레포 없음: {repo} (경로 {path})")

    fname, content = _file_spec(engine, token)
    out = path / fname
    out.write_text(content, encoding="utf-8")
    url = REPOS[repo] + fname
    print(f"✅ 작성: {out.relative_to(HUB)}")
    print(f"   라이브 URL(인증 시): {url}")

    if no_commit:
        print("   (--no-commit: 커밋 안 함. 파일만 생성됨)")
        return 0

    r = subprocess.run(["git", "add", fname], cwd=path, capture_output=True, text=True)
    if r.returncode != 0:
        print("   ⚠️ git add 실패:", r.stderr.strip())
        return 1
    subprocess.run(
        ["git", "commit", "-q", "-m", f"chore: {engine} 소유권 인증 파일 추가"],
        cwd=path, capture_output=True, text=True,
    )
    r = subprocess.run(["git", "push", "origin", "main"], cwd=path, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"   ✅ 커밋·푸시 완료 ({repo})")
    else:
        print(f"   ⚠️ 푸시 실패: {r.stderr.strip()[-200:]}")
    return 0 if r.returncode == 0 else 1


def list_sites() -> int:
    print("레포별 sitemap URL + 라이브 상태:")
    print("=" * 64)
    for repo, base in REPOS.items():
        sm = base + "sitemap.xml"
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                            "--max-time", "15", sm], capture_output=True, text=True)
        code = r.stdout.strip()
        print(f"  {'✅' if code == '200' else '❌'} {repo:16s} {sm}  (HTTP {code})")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "list":
        return list_sites()
    if args[0] == "verify":
        kw = {}
        i = 1
        while i < len(args):
            if args[i] == "--no-commit":
                kw["no_commit"] = True
                i += 1
            elif args[i] in ("--engine", "--token", "--repo") and i + 1 < len(args):
                kw[args[i][2:]] = args[i + 1]
                i += 2
            else:
                raise SystemExit(f"❌ 알 수 없는 인자: {args[i]}")
        if not all(k in kw for k in ("engine", "token", "repo")):
            raise SystemExit("❌ --engine, --token, --repo 모두 필요")
        return verify(kw["repo"], kw["engine"], kw["token"], kw.get("no_commit", False))
    raise SystemExit("❌ 사용법: verify|list")


if __name__ == "__main__":
    raise SystemExit(main())

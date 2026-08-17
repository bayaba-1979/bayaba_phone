#!/usr/bin/env python3
"""
geo_measure.py — GEO 원조 스탬프 측정 루프 (헌법 제17조)
====================================================
"정체 → 빌드 → 발행 → 색인 → 검색 → AI 인용" 중 **발행(표면)** 을 자동 측정한다.
색인/검색/AI 인용은 GSC·Bing WMT·LLM 질의로 별도 확인(수동 — 아래 주석 참고).

측정 항목:
  1. 핵심 URL HTTP 200 (홈·robots·sitemap·llms.txt + 샘플 페이지)
  2. canonical + JSON-LD 정체 그래프(@id→GitHub #person) 실제 서빙·파싱 유효
  3. sitemap <url> 수

사용법:
  python3 scripts/geo_measure.py            # 전체 측정 + 통과/실패 요약
  python3 scripts/geo_measure.py --urls 5   # 샘플 페이지 수 조정(기본 3)

종료 코드: 0=전부 통과, 1=하나라도 실패(CI 게이트용)

색인/AI 인용 측정(수동, 계정 필요):
  - Google Search Console / Bing Webmaster Tools에 sitemap 제출 후 노출·클릭 확인
  - Bing WMT "AI Performance": AI 인용·grounding 쿼리 수
  - Perplexity/ChatGPT/Gemini에 "S21 원조" 질의 → 우리 URL이 cited되는지 스팟체크
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# ecosystem.json에서 base URL 로드(포크 호환), 없으면 헬레나 기본.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from load_ecosystem import owner as _owner, hub_repo as _hub
    _BASE = f"https://{_owner()}.github.io/{_hub()}/"
except Exception:
    _BASE = "https://helena751107.github.io/helena_phone/"

CORE_PATHS = ["", "robots.txt", "sitemap.xml", "llms.txt"]
SAMPLE_PAGES = ["constitution.html", "archive.html", "notebook/99-devlog.html"]


def _fetch(path: str) -> str:
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "15", _BASE + path],
                           capture_output=True, text=True)
        return r.stdout
    except Exception:
        return ""


def _check_page(path: str) -> dict:
    """HTTP 200 + canonical 정확성 + JSON-LD Person(@id→GitHub) 유효성."""
    html = _fetch(path)
    url = _BASE + path
    canon = re.search(r'rel="canonical" href="([^"]+)"', html)
    canon_ok = bool(canon and canon.group(1).rstrip("/") == url.rstrip("/"))
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ld_ok, person_id = False, ""
    for b in blocks:
        try:
            nodes = json.loads(b).get("@graph", [])
            for n in nodes:
                if n.get("@type") == "Person":
                    person_id = n.get("@id", "")
                    ld_ok = bool(person_id)
                    break
        except Exception:
            ld_ok = False
        if ld_ok:
            break
    return {"http": bool(html), "canonical": canon_ok, "ld": ld_ok, "person": person_id}


def main() -> int:
    n = 3
    if "--urls" in sys.argv:
        n = int(sys.argv[sys.argv.index("--urls") + 1])

    print(f"🌐 GEO 원조 스탬프 측정 — {_BASE}")
    print("=" * 62)
    fails = 0

    for p in CORE_PATHS + SAMPLE_PAGES[:n]:
        if p.endswith(("robots.txt", "sitemap.xml", "llms.txt")):
            ok = bool(_fetch(p))
            fails += 0 if ok else 1
            print(f"  {'✅' if ok else '❌'} {p:30s} HTTP 200")
            continue
        r = _check_page(p)
        ok = r["http"] and r["canonical"] and r["ld"]
        fails += 0 if ok else 1
        print(f"  {'✅' if ok else '❌'} {p:30s} "
              f"HTTP={'✅' if r['http'] else '❌'} "
              f"canonical={'✅' if r['canonical'] else '❌'} "
              f"JSON-LD={'✅' if r['ld'] else '❌'}")

    sitemap = _fetch("sitemap.xml")
    print(f"\n  sitemap <url> 수: {len(re.findall(r'<url>', sitemap))}")

    print("=" * 62)
    print("결과:", "✅ 발행 표면 전부 통과" if fails == 0 else f"❌ {fails}개 실패")
    print("(색인·AI 인용은 이 스크립트 밖 — GSC/Bing WMT/LLM 질의로 수동 측정)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

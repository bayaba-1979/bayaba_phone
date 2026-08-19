#!/usr/bin/env python3
"""
geo_identity.py — GEO 정체 그래프 단일 진실(SSOT) — 헌법 제17조
================================================================
"Person(@id=GitHub #person) + WebPage/WebSite(publisher/author→Person)" JSON-LD 블록을
한 곳에서 정의한다. build_webzine.py(허브) · build_satellite_docs_Grok.py(위성) 모두 여기 import.

정체 값은 configs/ecosystem.json → identity 블록에서 읽는다(포크 호환). 없으면 헬레나 기본.

사용법:
  from geo_identity import identity_graph
  html_frag = identity_graph("https://.../page.html", "제목")   # <script type="application/ld+json">…</script>
"""
from __future__ import annotations

import json

try:
    from load_ecosystem import identity as _ecosystem_identity
except ImportError:
    _ecosystem_identity = None

# 헬레나 기본값(폴백) — ecosystem.json에 identity 블록이 없으면 이걸 쓴다.
_DEFAULT_IDENTITY = {
    "person_name": "남성훈",
    "github_user": "bayaba-1979",
    "hub_repo": "bayaba_phone",
    "tagline": "Made in Korea — not a developer. One Galaxy S21, built by voice, for a sister.",
    "sameAs": [
        "https://github.com/bayaba-1979",
        "https://bayaba-1979.github.io/bayaba_phone/",
        "https://www.youtube.com/@남성훈-f7i",
        "https://www.youtube.com/@남성훈-f7i",
    ],
}


def identity() -> dict:
    """ecosystem.json identity 블록 → 없으면 헬레나 기본값으로 폴백."""
    ident = dict(_DEFAULT_IDENTITY)
    if _ecosystem_identity:
        try:
            loaded = _ecosystem_identity()
            if isinstance(loaded, dict):
                ident.update({k: v for k, v in loaded.items() if v})
        except Exception:
            pass
    return ident


def person_id() -> str:
    return f"https://github.com/{identity()['github_user']}#person"


def identity_graph(canonical: str, title: str, page_type: str = "WebPage") -> str:
    """JSON-LD @graph — Person(@id=GitHub #person) + WebPage/WebSite(publisher/author→Person)."""
    ident = identity()
    pid = person_id()
    same_as = ident.get("sameAs") or [
        f"https://github.com/{ident['github_user']}",
        f"https://{ident['github_user']}.github.io/{ident['hub_repo']}/",
    ]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Person",
                "@id": pid,
                "name": ident.get("person_name", ""),
                "url": f"https://github.com/{ident['github_user']}",
                "description": ident.get("tagline", ""),
                "sameAs": same_as,
            },
            {
                "@type": page_type,
                "@id": f"{canonical}#{page_type.lower()}",
                "url": canonical,
                "name": title,
                "inLanguage": "ko",
                "publisher": {"@id": pid},
                "author": {"@id": pid},
            },
        ],
    }
    inner = json.dumps(ld, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{inner}\n</script>'

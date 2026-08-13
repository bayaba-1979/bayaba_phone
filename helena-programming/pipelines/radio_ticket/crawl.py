#!/usr/bin/env python3
"""라디오 초대권 크롤러 — Yes24 티켓 + 인터파크 집계 기반"""
import requests
from bs4 import BeautifulSoup
import json, re, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
CONFIG = json.load(open(ROOT / "config.json"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def _safe_get(url: str, timeout=15) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ⚠️ {url[:70]}... → {e}")
        return None

def _clean_title(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

# ── Yes24 티켓 (주력) ─────────────────────────────
def crawl_yes24() -> list:
    """Yes24 클래식 카테고리 — 정적 HTML에서 공연 정보 추출"""
    results = []
    html = _safe_get("https://ticket.yes24.com/Genre/Classic")
    if not html:
        return results
    soup = BeautifulSoup(html, "html.parser")

    # A. swiper-slide: 제목 + 날짜 + 장소 + ID
    for slide in soup.select(".swiper-slide"):
        img = slide.find("img")
        a_tag = slide.find("a")
        title = img.get("alt", "") if img else ""
        href = a_tag.get("href", "") if a_tag else ""
        full_text = slide.get_text(strip=True)

        if not title or len(title) < 4:
            continue

        # Perf ID 추출
        perf_id = ""
        m = re.search(r'/Perf/(\d+)', href)
        if m:
            perf_id = m.group(1)

        # full_text에서 날짜/장소 분리 (예: "백건우70주년리사이틀2026.08.12. 평택아트센터")
        date_str = ""
        venue = ""
        date_m = re.search(r'(\d{4}\.\d{1,2}\.\d{1,2})', full_text)
        if date_m:
            date_str = date_m.group(1)
            # 날짜 이후 텍스트 = 장소
            venue = full_text[date_m.end():].strip().lstrip('.').strip()

        # venue 없으면 list-bigger-txt에서 찾기
        if not venue:
            parent = slide.find_parent()
            if parent:
                v_el = parent.select_one(".list-b-tit2, .list-bigger-txt .list-b-tit2")
                if v_el:
                    venue = v_el.get_text(strip=True)

        results.append({
            "title": _clean_title(title),
            "date": date_str,
            "venue": venue or "미정",
            "perf_id": perf_id,
            "source": "yes24.com",
            "url": f"https://ticket.yes24.com{href}" if href else ""
        })

    # B. list-bigger-txt: 제목 + 장소 (날짜 없음, swiper 보완)
    swiper_titles = {r["title"][:30] for r in results}
    for item in soup.select(".list-bigger-txt"):
        tit1 = item.select_one(".list-b-tit1")
        tit2 = item.select_one(".list-b-tit2")
        if tit1:
            title = _clean_title(tit1.get_text())
            venue = _clean_title(tit2.get_text()) if tit2 else "미정"
            # 중복 제거
            if title[:30] not in swiper_titles and len(title) > 4:
                swiper_titles.add(title[:30])
                results.append({
                    "title": title,
                    "date": "",
                    "venue": venue,
                    "perf_id": "",
                    "source": "yes24.com",
                    "url": ""
                })

    # C. 랭킹 섹션 (ms5-wrap)
    for img in soup.select(".ms5-wrap img[alt]"):
        alt = img.get("alt", "")
        if alt and len(alt) > 5 and alt not in ["더보기", "yes24 기본이미지"]:
            title = _clean_title(alt)
            if title[:30] not in swiper_titles:
                swiper_titles.add(title[:30])
                results.append({
                    "title": title,
                    "date": "",
                    "venue": "",
                    "perf_id": "",
                    "source": "yes24.com",
                    "url": ""
                })

    return results

# ── 인터파크 티켓 (보조) ──────────────────────────
def crawl_interpark() -> list:
    """인터파크 클래식 — API 시도"""
    results = []
    html = _safe_get("https://tickets.interpark.com/contents/search?keyword=클래식")
    if not html:
        return results
    soup = BeautifulSoup(html, "html.parser")
    noise = {"NOL 인터파크", "search-filter", "show-select-item", "review-star",
             "place", "stats-info", "검색", "로고", "이미지", "", "interpark"}
    for img in soup.select("img[alt]"):
        alt = img.get("alt", "").strip()
        if alt and len(alt) > 4 and alt not in noise:
            results.append({
                "title": _clean_title(alt),
                "date": "", "venue": "", "perf_id": "",
                "source": "interpark.com", "url": ""
            })
    return results

# ── 네이버 검색 (보완) ────────────────────────────
def search_naver(query: str = "서울 클래식 공연 2026년 8월") -> list:
    """네이버 검색으로 추가 공연 정보"""
    results = []
    url = f"https://search.naver.com/search.naver?query={quote(query)}"
    html = _safe_get(url)
    if not html:
        return results
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select(".total_wrap, .api_txt_lines, .total_area")[:15]:
        text = item.get_text(strip=True)[:200]
        if any(kw in text for kw in ["공연", "콘서트", "리사이틀", "오케스트라", "클래식"]):
            results.append({
                "title": text[:80],
                "date": "", "venue": "", "perf_id": "",
                "source": "naver.com", "url": ""
            })
    return results

# ── 통합 ──────────────────────────────────────────
def crawl_all() -> list:
    all_results = []

    # 주력: Yes24
    try:
        yes24 = crawl_yes24()
        print(f"  ✅ Yes24: {len(yes24)}건")
        all_results.extend(yes24)
    except Exception as e:
        print(f"  ❌ Yes24: {e}")

    # 보조: 인터파크
    try:
        interpark = crawl_interpark()
        if interpark:
            print(f"  ✅ 인터파크: {len(interpark)}건")
            all_results.extend(interpark)
    except Exception as e:
        print(f"  ❌ 인터파크: {e}")

    # 보완: 네이버 검색
    try:
        naver = search_naver()
        if naver:
            print(f"  🔍 네이버: {len(naver)}건")
            all_results.extend(naver)
    except Exception:
        pass

    # 중복 제거 + 정렬
    seen = set()
    unique = []
    for r in all_results:
        key = r["title"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique

if __name__ == "__main__":
    results = crawl_all()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n📊 총 {len(results)}건 수집")

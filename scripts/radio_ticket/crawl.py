#!/usr/bin/env python3
"""라디오 초대권 크롤러 — 공연장 + 검색 기반 하이브리드"""
import requests
from bs4 import BeautifulSoup
import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
CONFIG = json.load(open(ROOT / "config.json"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}
DESKTOP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def _safe_get(url: str, timeout=15, desktop=False) -> str | None:
    h = DESKTOP_HEADERS if desktop else HEADERS
    try:
        r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ⚠️ {url[:60]}... → {e}")
        return None

def _make_result(location: str, title: str, date: str = "미정", genre: str = "클래식") -> dict:
    # 필터: 네비게이션 텍스트, 메뉴 아이템 제거
    noise_words = ["예매안내", "공지사항", "백스테이지", "투어예약", "예약내역", "캘린더공연",
                   "전시관소개", "교육소개", "패키지패키지", "한글갤러리"]
    if any(nw in title for nw in noise_words) or len(title) < 6:
        return None
    # 제목 정제: 앞 80자만, 특수문자 정리
    clean = re.sub(r'\s+', ' ', title).strip()[:100]
    return {
        "performance_id": f"{location[:4]}_{datetime.now().strftime('%Y%m%d')}_{hash(clean) % 1000:03d}",
        "location": location,
        "title": clean,
        "date": date,
        "genre": genre,
        "source": "crawled"
    }

# ── 공연장 크롤러 ──────────────────────────────────

def crawl_sac() -> list:
    """예술의전당 — JS 동적 페이지. 모바일 달력 페이지 시도."""
    results = []
    # 모바일 버전 시도
    html = _safe_get("https://www.sac.or.kr/sac/main/schedule.do?lang=ko")
    if not html:
        return results
    soup = BeautifulSoup(html, "html.parser")
    # 시도: 달력에 data- 속성으로 공연 정보가 있는지
    for item in soup.select("[data-title], [data-concert], .schedule-item, .list-item")[:20]:
        text = item.get_text(strip=True)[:120]
        title = item.get("data-title", "") or text
        if title and len(title) > 3:
            r = _make_result("예술의전당", title)
            if r: results.append(r)
    return results

def crawl_lotte() -> list:
    """롯데콘서트홀 — API 직접 호출 시도."""
    results = []
    # API 엔드포인트 추측
    for endpoint in [
        "https://www.lotteconcerthall.com/kor/performance/calendar",
        "https://www.lotteconcerthall.com/kor/performance",
    ]:
        html = _safe_get(endpoint, desktop=True)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("a[href*='performance'], .perf-item, .concert-item, li:has(a)")[:20]:
            text = item.get_text(strip=True)[:120]
            if text and len(text) > 5:
                r = _make_result("롯데콘서트홀", text)
                if r: results.append(r)
        if results:
            break
    return results

def crawl_sejong() -> list:
    """세종문화회관 — 정적 페이지 시도."""
    results = []
    for url in [
        "https://www.sejongpac.or.kr/portal/performance/performanceList.do",
        "https://www.sejongpac.or.kr/portal/main/main.do",
    ]:
        html = _safe_get(url, desktop=True)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("a[href*='performance'], .perf-item, .list-item, li:has(a)")[:20]:
            text = item.get_text(strip=True)[:120]
            if text and len(text) > 5:
                r = _make_result("세종문화회관", text)
                if r: results.append(r)
        if results:
            break
    return results

def crawl_kumho() -> list:
    """금호아트홀 연세"""
    results = []
    html = _safe_get("https://www.kumhoarthall.com/kor/performance/schedule", desktop=True)
    if not html:
        return results
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("a[href*='performance'], .schedule-item, .perf-row, li:has(a)")[:20]:
        text = item.get_text(strip=True)[:120]
        if text and len(text) > 5:
            r = _make_result("금호아트홀", text)
            if r: results.append(r)
    return results

def crawl_kbshall() -> list:
    """KBS홀 — 올바른 URL로 재시도."""
    results = []
    for url in [
        "https://www.kbs.co.kr/studio/booking/schedule",
        "https://www.kbs.co.kr/studio/index.html",
    ]:
        html = _safe_get(url, desktop=True)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("a[href*='schedule'], a[href*='booking'], .schedule, li:has(a)")[:20]:
            text = item.get_text(strip=True)[:120]
            if text and len(text) > 3:
                r = _make_result("KBS홀", text)
                if r: results.append(r)
        if results:
            break
    return results

# ── 검색 기반 수집 ─────────────────────────────────

def search_concerts(query: str = "서울 클래식 공연 2026년 8월") -> list:
    """DuckDuckGo HTML 검색으로 공연 정보 수집 (API 키 불필요)"""
    results = []
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    html = _safe_get(url, desktop=True)
    if not html:
        return results

    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select(".result, .web-result, .result__body")[:15]:
        title_el = item.select_one(".result__title, .result__a, a.result-link")
        snippet_el = item.select_one(".result__snippet, .result__body")
        title = title_el.get_text(strip=True) if title_el else ""
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        combined = f"{title} {snippet}"[:200]
        if not combined or len(combined) < 10:
            continue

        # 키워드 필터: 클래식 공연 관련
        keywords = ["공연", "콘서트", "리사이틀", "오케스트라", "피아노", "클래식", "교향악", "예술의전당", "롯데콘서트홀", "세종문화회관", "금호아트홀", "KBS홀"]
        noise = ["목록", "정리", "블로그", "일정 (updated", "문화 행사 목록", "문화달력", "하반기"]
        if any(kw in combined for kw in keywords) and not any(nw in combined for nw in noise):
            # 공연장 추출
            venue = "서울"
            for v in ["예술의전당", "롯데콘서트홀", "세종문화회관", "금호아트홀", "KBS홀", "LG아트센터", "국립극장"]:
                if v in combined:
                    venue = v
                    break

            # 날짜 추출 시도 (연도 2025-2027 범위로 제한)
            date_match = re.search(r'(202[5-7])년?\s*(\d{1,2})월?\s*(\d{1,2})일?', combined)
            if date_match:
                y, m, d = date_match.group(1), date_match.group(2), date_match.group(3)
                if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                    date_str = f"{y}-{m}-{d}"
                else:
                    date_str = "미정"
            else:
                date_str = "미정"

            r = _make_result(venue, title or snippet[:80], date_str)
            if r: results.append(r)

    return results

# ── 통합 크롤링 ─────────────────────────────────────

def crawl_all() -> list:
    """직접 크롤 + 검색 기반 → 통합 결과"""
    all_results = []

    # 직접 크롤링 시도
    crawlers = [
        ("예술의전당", crawl_sac),
        ("롯데콘서트홀", crawl_lotte),
        ("세종문화회관", crawl_sejong),
        ("금호아트홀", crawl_kumho),
        ("KBS홀", crawl_kbshall),
    ]
    for name, func in crawlers:
        try:
            results = func()
            if results:
                print(f"  ✅ {name}: {len(results)}건")
            all_results.extend(results)
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    # 검색 기반 보완
    try:
        search_results = search_concerts()
        if search_results:
            print(f"  🔍 검색: {len(search_results)}건 추가")
            all_results.extend(search_results)
    except Exception:
        pass

    # 중복 제거
    seen = set()
    unique = []
    for r in all_results:
        key = r["title"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique

# ── CLI ────────────────────────────────────────────
if __name__ == "__main__":
    results = crawl_all()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n📊 총 {len(results)}건 수집")

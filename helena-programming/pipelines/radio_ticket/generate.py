#!/usr/bin/env python3
"""DeepSeek 사연 생성기 — 채널별 맞춤형 초대권 신청 사연 자동 생성"""
import json, os, sys, re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT = Path(__file__).parent
CONFIG = json.load(open(ROOT / "config.json"))

DS_KEY = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
DS_BASE = CONFIG["deepseek"]["base_url"]
DS_MODEL = CONFIG["deepseek"]["model"]

def call_deepseek(prompt: str, max_tokens: int = 2000) -> str:
    """DeepSeek API 호출 (OpenAI 호환 엔드포인트)"""
    if not DS_KEY:
        return _fallback_simple(prompt)

    data = json.dumps({
        "model": DS_MODEL,
        "messages": [
            {"role": "system", "content": "너는 대한민국 라디오 방송국에 사연을 보내는 전문 작가다. 진심이 묻어나는 편지글을 쓴다. 과장하지 않고, 진솔하게, 구체적인 디테일을 담는다. 절대 AI가 쓴 티를 내지 않는다. 평문만 출력한다. 마크다운, 제목, 서명, '##', '>' 등 형식 문법 절대 사용 금지."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.85
    }).encode()

    try:
        req = Request(f"{DS_BASE}/v1/chat/completions", data=data, headers={
            "Authorization": f"Bearer {DS_KEY}",
            "Content-Type": "application/json"
        })
        resp = json.loads(urlopen(req, timeout=90).read())
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️ DeepSeek API 실패: {e}")
        return _fallback_simple(prompt)

def _fallback_simple(prompt: str) -> str:
    """API 실패 시 템플릿 기반 사연"""
    return f"""안녕하세요.

수요일이 유일한 쉬는 날인 직장인입니다. 평소에 이 프로그램을 통해 큰 위로를 받고 있습니다.

치매가 있으신 어머니와 조현병을 앓고 있는 작은누나를 돌보며 살아가고 있는데, 음악이 제 삶의 유일한 쉼표입니다. 특히 작은누나는 피아노를 좋아해서, 누나에게 특별한 선물이 되었으면 하는 바람으로 사연 올립니다.

감사합니다."""

# ── 채널별 프롬프트 빌더 ────────────────────────────
def build_prompt(channel_type: str, performance: dict) -> str:
    """공연 정보 + 개인 프로필 → 채널 맞춤 프롬프트"""
    profile = CONFIG["profile"]
    ch = CONFIG["channels"][channel_type]

    base = f"""당신은 '{ch['name']}'에 보낼 사연을 쓰는 한국인 청취자다.

## 당신의 프로필
- {profile['role']}
- 쉬는 날: {profile['day_off']}
- 가족: {profile['family']['mother']}, {profile['family']['sister_small']}, {profile['family']['sister_big']}

## 프로그램 정보
- 프로그램: {ch['name']}
"""

    if channel_type == "classic":
        base += f"""- 톤: {ch['programs'][0]['tone'] if ch.get('programs') else '우아하고 진솔하게'}
- 공연 정보: {performance.get('title','')} / {performance.get('location','')} / {performance.get('date','')}

## 사연 작성 지침
1. 작은누나가 피아노를 좋아한다는 이야기를 자연스럽게 녹인다.
2. '내가' 아니라 '누나를 위해' 신청하는 마음을 담는다.
3. 수요일이 유일한 쉬는 날이라는 디테일을 넣는다.
4. 300~500자 이내. 짧고 진솔하게. AI 티 절대 내지 말 것.
5. 마지막에 "누나에게 이 공연을 선물하고 싶다"는 마음으로 마무리."""

    elif channel_type == "gayo":
        singers = ", ".join(ch.get("favorite_singers", []))
        base += f"""- 작은누나의 최애 가수: {singers}
- 톤: 가족애, 추억, 감동

## 사연 작성 지침
1. 학창 시절 작은누나가 이 가수를 얼마나 좋아했는지 추억을 담는다.
2. 조현병으로 힘들어하는 누나에게 예전 그 시절의 기쁨을 되찾아주고 싶다는 마음.
3. 수요일이 유일한 쉬는 날이라 방청 갈 수 있다는 실용적 디테일.
4. 300~500자. 눈물 나게 감동적으로. 하지만 과장하지 말 것.
5. 너는 자녀가 없는 미혼의 동생이다. 부모/자식 관계 언급 금지. 가족은 어머니(치매)와 누나들뿐이다."""

    elif channel_type == "pop":
        artists = ", ".join(ch.get("favorite_artists", []))
        base += f"""- 최애 팝 아티스트: {artists}
- 톤: {ch.get('tone', '치열한 삶 속 음악의 위로')}

## 사연 작성 지침
1. 육체노동과 AI 프로젝트를 병행하는 치열한 삶을 간략히 언급.
2. 퇴근길 배캠을 들으며 얻는 위로와 에너지.
3. 과거 크리스티나 아길레라 내한 라이브를 본 추억 (있다고 가정).
4. 300~500자. 진솔하게. 음악이 준 힘에 대한 이야기.
5. 너는 자녀가 없는 미혼의 동생이다. 가족은 어머니(치매)와 누나들뿐. '아빠', '딸', '아내' 등 존재하지 않는 가족 언급 금지."""

    else:
        base += f"""- 공연 정보: {performance.get('title','')} / {performance.get('location','')}

## 사연 작성 지침
1. 진솔한 가족 이야기를 담는다.
2. 300~500자 이내.
3. 수요일이 유일한 쉬는 날.
4. AI 티 내지 말 것."""

    return base

# ── 통합 생성 ──────────────────────────────────────
def generate_story(channel_type: str, performance: dict) -> dict:
    """채널 + 공연 정보 → 완성된 사연 (제출 링크 포함)"""
    prompt = build_prompt(channel_type, performance)
    story = call_deepseek(prompt)

    ch = CONFIG["channels"][channel_type]

    # 제출 링크 정보 — 채널 기본, 없으면 첫 프로그램의 URL
    apply_url = ch.get("apply_url", "")
    if not apply_url and ch.get("programs"):
        apply_url = ch["programs"][0].get("apply_url", "")
    apply_method = ch.get("apply_method", "web")
    apply_instruction = ch.get("apply_instruction", "")

    return {
        "channel": ch["name"],
        "channel_type": channel_type,
        "performance": performance.get("title", ""),
        "location": performance.get("location", ""),
        "date": performance.get("date", ""),
        "story": story,
        "generated_at": datetime.now().isoformat(),
        "apply": {
            "url": apply_url,
            "method": apply_method,
            "instruction": apply_instruction
        }
    }

def generate_all(performances: list) -> list:
    """모든 공연 × 모든 채널에 대해 사연 생성"""
    stories = []

    # 공연별 매칭
    for perf in performances:
        title = perf.get("title", "")
        location = perf.get("location", "")

        # 클래식 매칭: KBS 클래식 FM
        if any(kw in title.lower() + location.lower() for kw in
               ["피아노", "리사이틀", "오케스트라", "필하모닉", "교향악", "클래식", "예술의전당", "롯데콘서트홀", "세종문화회관", "금호", "kbs홀"]):
            stories.append(generate_story("classic", perf))
            break  # 주 1회 발송이므로 첫 매칭만

    # 가요 채널 (상시)
    stories.append(generate_story("gayo", {"title": "이번 주 방청 신청", "location": "지상파"}))
    # 팝 채널 (상시)
    stories.append(generate_story("pop", {"title": "이번 주 배캠 공개방송", "location": "MBC"}))

    return stories

# ── CLI ────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="테스트 모드: 샘플 공연으로 사연 생성")
    parser.add_argument("--channel", choices=["classic", "gayo", "pop"], help="특정 채널만")
    parser.add_argument("--title", default="백건우 피아노 리사이틀", help="공연 제목 (테스트용)")
    parser.add_argument("--location", default="예술의전당 콘서트홀", help="공연장 (테스트용)")
    parser.add_argument("--date", default="2026-08-12", help="날짜 (테스트용)")
    args = parser.parse_args()

    if args.test:
        perf = {"title": args.title, "location": args.location, "date": args.date}
        if args.channel:
            result = generate_story(args.channel, perf)
            print(f"\n🎯 {result['channel']}")
            print(f"📅 {result['date']} | {result['performance']} | {result['location']}")
            if result.get("apply", {}).get("url"):
                print(f"🔗 제출 링크: {result['apply']['url']}")
                print(f"📋 방법: {result['apply']['instruction']}")
            print(f"\n{result['story']}")
        else:
            for ch in ["classic", "gayo", "pop"]:
                result = generate_story(ch, perf)
                print(f"\n{'='*50}")
                print(f"🎯 {result['channel']}")
                if result.get("apply", {}).get("url"):
                    print(f"🔗 제출: {result['apply']['url']}")
                print(f"\n{result['story']}")
    else:
        # 크롤링된 데이터로 생성
        from crawl import crawl_all
        performances = crawl_all()
        if not performances:
            # 크롤링 실패 시 샘플로
            performances = [{"title": "백건우 피아노 리사이틀", "location": "예술의전당", "date": "수요일 미정"}]
        stories = generate_all(performances)
        print(json.dumps(stories, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""라디오 초대권 디스패처 — 크롤→생성→TG배달 (주 1회 일요일)
사용법:
  python3 dispatch.py              # 전체 파이프라인
  python3 dispatch.py --dry-run    # TG 전송 없이 생성만
  python3 dispatch.py --crawl-only # 크롤링만
"""
import json, os, sys, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(ROOT / "dispatch.log", "a") as f:
        f.write(line + "\n")

def find_tg_script() -> str | None:
    """tg.sh 위치 찾기 — helena_phone 레포의 tg.sh"""
    candidates = [
        "/root/work/tg.sh",
        "/root/work/helena_phone/tg.sh",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # PATH에서 찾기
    import shutil
    found = shutil.which("tg.sh")
    return found

def _save(stories: list, prefix: str = "dispatch"):
    """스토리 저장 + 선물함(giftbox) 관리"""
    out = ROOT / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    # 각 스토리에 제출 상태 필드 추가
    for s in stories:
        s["sent"] = False
        s["sent_at"] = None
    with open(out, "w") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    log(f"💾 저장: {out}")

    # 선물함 인덱스 업데이트
    giftbox = ROOT / "giftbox.json"
    gb = []
    if giftbox.exists():
        try:
            gb = json.loads(giftbox.read_text())
        except:
            pass
    for s in stories:
        gb.append({
            "id": f"{s.get('channel_type','')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "channel": s.get("channel", ""),
            "channel_type": s.get("channel_type", ""),
            "performance": s.get("performance", ""),
            "location": s.get("location", ""),
            "story": s.get("story", ""),  # 전체 사연 (복사용)
            "apply_url": (s.get("apply") or {}).get("url", ""),
            "apply_instruction": (s.get("apply") or {}).get("instruction", ""),
            "generated_at": s.get("generated_at", ""),
            "sent": False,
            "sent_at": None
        })
    with open(giftbox, "w") as f:
        json.dump(gb, f, ensure_ascii=False, indent=2)
    log(f"🎁 선물함: {len(gb)}건 누적")

    return out

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="TG 전송 없이 생성만")
    parser.add_argument("--crawl-only", action="store_true", help="크롤링만 실행")
    parser.add_argument("--test", action="store_true", help="테스트: 백건우 샘플 데이터로만")
    args = parser.parse_args()

    log("🚀 라디오 초대권 디스패처 시작")

    # 1. 크롤링
    log("📡 Yes24 공연 정보 크롤링...")
    from crawl import crawl_all
    performances = crawl_all()
    log(f"  → {len(performances)}건 수집")

    if args.test:
        performances = [{
            "title": "백건우 70주년 리사이틀",
            "location": "예술의전당 콘서트홀",
            "date": "2026.09.12",
        }]
        log("  🧪 테스트 모드: 샘플 데이터 사용")

    if args.crawl_only:
        _save(performances, "crawl")
        return

    if not performances:
        log("⚠️ 크롤링 0건 → fallback")
        performances = [{
            "title": "백건우 피아노 리사이틀",
            "location": "예술의전당 콘서트홀",
            "date": "수요일 (날짜 미확인)"
        }]

    # 2. 사연 생성
    log("✍️ DeepSeek 사연 생성...")
    from generate import generate_all
    stories = generate_all(performances)
    log(f"  → {len(stories)}개 채널 사연 완성")

    if args.dry_run:
        for s in stories:
            print(f"\n{'='*50}")
            print(f"🎙 {s['channel']} | {s['performance']} | {s['location']}")
            apply_info = s.get("apply", {})
            if apply_info.get("url"):
                print(f"🔗 제출: {apply_info['url']}")
                print(f"📋 방법: {apply_info.get('instruction','')}")
            print(f"\n{s['story']}")
        _save(stories, "dryrun")
        log("✅ dry-run 완료 (TG 미전송)")
        return

    # 3. TG 배달
    tg = find_tg_script()
    if not tg:
        log("❌ tg.sh 없음 — 파일 저장만")
        _save(stories)
        return

    for s in stories:
        apply_info = s.get("apply", {})
        apply_url = apply_info.get("url", "")
        apply_how = apply_info.get("instruction", "")

        msg = (
            f"🎙 <b>{s['channel']}</b> 초대권 사연\n\n"
            f"📅 {s['performance']} | {s['location']}\n"
            f"⏰ {s['generated_at'][:19]}\n\n"
            f"{s['story']}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📬 <b>제출하기:</b> {apply_how}\n"
            f"🔗 <a href=\"{apply_url}\">제출 페이지 열기</a>"
        )
        try:
            subprocess.run(["bash", tg, msg], timeout=30, capture_output=True)
            log(f"  ✅ {s['channel']} 전송 완료")
        except Exception as e:
            log(f"  ❌ {s['channel']} 전송 실패: {e}")

    _save(stories)
    log("✅ 디스패처 완료\n")

if __name__ == "__main__":
    main()

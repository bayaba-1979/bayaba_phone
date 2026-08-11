#!/usr/bin/env python3
"""라디오 초대권 자동화 — 크롤 → 생성 → 배달 (주 1회 일요일 밤)"""
import json, os, sys, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "dispatch.log"

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def main():
    log("🚀 라디오 초대권 파이프라인 시작")

    # 1. 크롤링
    log("📡 공연 정보 크롤링...")
    from crawl import crawl_all
    performances = crawl_all()
    log(f"  → {len(performances)}건 수집")

    if not performances:
        log("⚠️ 크롤링 0건 — 수동 fallback 데이터 사용")
        performances = [{
            "title": "백건우 피아노 리사이틀",
            "location": "예술의전당 콘서트홀",
            "date": "수요일 (날짜 미확인)"
        }]

    # 2. DeepSeek 사연 생성
    log("✍️ DeepSeek 사연 생성...")
    from generate import generate_all
    stories = generate_all(performances)
    log(f"  → {len(stories)}개 채널 사연 완성")

    # 3. Telegram 배달
    tg_script = ROOT.parent.parent / "tg.sh"  # scripts/../tg.sh = /root/work/tg.sh
    if not tg_script.exists():
        tg_script = "/root/work/tg.sh"  # fallback absolute
        if not os.path.exists(tg_script):
            log("❌ tg.sh not found — 스토리를 파일로만 저장")
            _save_stories(stories)
            return

    for s in stories:
        channel = s["channel"]
        story_text = s["story"]
        perf = f"{s['performance']} | {s['location']}"

        msg = (
            f"🎙 <b>{channel}</b> 초대권 사연\n\n"
            f"📅 공연: {perf}\n"
            f"⏰ 생성: {s['generated_at'][:19]}\n\n"
            f"{story_text}"
        )

        # --no-button: 이미 tg.sh에 버튼 달려있으니 중복 방지
        cmd = ["bash", str(tg_script), msg]
        try:
            subprocess.run(cmd, timeout=30, capture_output=True)
            log(f"  ✅ {channel} 전송 완료")
        except Exception as e:
            log(f"  ❌ {channel} 전송 실패: {e}")

    # 4. 로컬 저장
    _save_stories(stories)
    log("✅ 파이프라인 완료\n")

def _save_stories(stories: list):
    out = ROOT / f"dispatch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, "w") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    log(f"💾 저장: {out}")

if __name__ == "__main__":
    main()

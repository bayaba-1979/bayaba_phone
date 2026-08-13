# 🎙 라디오 초대권 자동화

> Yes24 클래식 공연 크롤링 → DeepSeek 사연 생성 → TG 배달. 주 1회 일요일 밤.

## 작동

```
크롤 (Yes24 22건)
    ↓
생성 (DeepSeek 3채널: 클래식/가요/팝)
    ↓
배달 (tg.sh → @S21Phone_Bot)
    ↓
저장 (dispatch_YYYYMMDD_HHMM.json)
```

## 설정

`config.json` 편집:
- `profile` — 사연에 반영될 개인 정보
- `channels` — 3채널(클래식/가요/팝) 프로그램·가수·톤
- `deepseek` — API base_url·model
- `schedule` — cron 표현식 (proot 미지원 → 수동/ScheduleWakeup)

## 사용법

```bash
# 전체 파이프라인
python3 dispatch.py

# TG 전송 없이 생성만
python3 dispatch.py --dry-run

# 크롤링만
python3 dispatch.py --crawl-only

# 테스트 (백건우 샘플)
python3 dispatch.py --test --dry-run
```

## MCP 도구

Claude Code에서 호출 가능 (`mcp/mcp_server.py`):
- `radio_ticket_crawl` — 공연 크롤링
- `radio_ticket_generate` — 사연 생성
- `radio_ticket_dispatch` — 전체 실행
- `radio_ticket_status` — 로그 조회

## WA 대시보드

`web/public/radio-ticket.html` → Vercel 배포됨.

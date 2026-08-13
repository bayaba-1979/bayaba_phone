# 🎙 Helena Ticket

> Yes24 클래식 공연 → DeepSeek 사연 → Telegram 배달. **PWA + TG + MCP 3way.**
> 각 사연마다 **실제 제출 페이지 링크** + **선물함(제출 관리)** 포함.

## 진입점

| 방법 | 실행 | 클릭 |
|------|------|------|
| **홈 화면** | `http://localhost:8766` → Add to Home | 1탭 |
| **텔레그램** | `/radio` → @S21Phone_Bot | 타이핑 |
| **텔레그램** | `/radio_box` → 선물함 조회 | 타이핑 |
| **Claude Code** | MCP `radio_ticket_dispatch` | 음성 |

## 서버 실행

```bash
cd apps/radio-ticket
python3 server.py              # http://localhost:8766
python3 server.py --daemon     # 백그라운드
```

## API

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /` | PWA 대시보드 (공연 + 선물함 + 실행) |
| `GET /api/crawl` | 공연 크롤링 실행 |
| `POST /api/dispatch` | 파이프라인 실행 `{"dry_run": true}` |
| `POST /api/generate` | 사연 생성 `{"title":"...","channel":"classic"}` |
| `GET /api/status` | 로그 조회 |
| `GET /api/venues` | 캐시된 공연 목록 |
| `GET /api/stories` | 🎁 선물함 — 생성된 사연 목록 (제출 상태 포함) |
| `POST /api/stories/{id}/sent` | ✅ 제출 완료 표시 |

## TG 명령어

| 명령어 | 설명 |
|--------|------|
| `/radio` | 전체 파이프라인 실행 + TG 배달 |
| `/radio_test` | dry-run (TG 전송 없이 사연만) |
| `/radio_status` | 최근 실행 로그 |
| `/radio_box` | 🎁 선물함 조회 (미제출 사연 + 제출 링크) |

## 의존성

- Python 3 (`http.server` 내장)
- `pipelines/radio_ticket/` (같은 레포)
- DeepSeek API 키 (환경변수)
- TG_TOKEN/TG_CHAT (.secrets.env)

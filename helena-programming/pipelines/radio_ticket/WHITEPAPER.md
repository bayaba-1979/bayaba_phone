# 🎙 Helena Ticket 기술 백서 v2

> Yes24 공연 크롤링 → DeepSeek AI 사연 생성 → 제출 링크 첨부 → 선물함 관리
> **PWA + Telegram + MCP 3way.** S21 폰 단독 구동. 월 0원.

---

## 1. 문제 정의

라디오 방송국 초대권/방청권 신청은 **반복 노동**이다:
- 매주 공연 정보 찾아보고
- 프로그램별로 다른 사연 작성하고
- 제출 페이지 일일이 찾아 들어가서
- 어디 제출했는지 기억해야 함

이걸 **주 1회 3채널 × 사연작성 + 제출**을 사람이 하면 20~30분. AI가 하면 3분.

**핵심 인사이트:** 사연 텍스트만 생성해주는 건 반쪽짜리다. **어디에 제출할지 링크까지 같이 줘야** 사람이 클릭 한 번으로 끝난다. 그래서 `apply_url` + `선물함`을 1차 구현에 포함시켰다.

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│                 Helena Ticket                     │
│                                                   │
│  Yes24 크롤링 ──→ DeepSeek 사연 ──→ TG 배달       │
│       │                │              │            │
│       ▼                ▼              ▼            │
│  crawl.py        generate.py    dispatch.py        │
│  (정적HTML)      (API 호출)     (오케스트레이터)   │
│                     │                              │
│          ┌──────────┼──────────┐                   │
│          ▼          ▼          ▼                   │
│       classic      gayo       pop                  │
│     (KBS 1FM)   (KBS TV)   (MBC FM4U)             │
│          │          │          │                   │
│          └──────────┼──────────┘                   │
│                     ▼                              │
│              giftbox.json                          │
│           (선물함 · 제출 상태)                     │
│                     │                              │
│     ┌───────────────┼───────────────┐              │
│     ▼               ▼               ▼              │
│   PWA(:8766)    TG Bot          MCP Server         │
│  (홈화면 아이콘)  (/radio)    (Claude Code)        │
└─────────────────────────────────────────────────┘
```

### 3진입점 전략

| 진입점 | 사용자 행동 | 클릭 수 |
|--------|------------|---------|
| **PWA** | 홈 화면 아이콘 탭 | 1탭 |
| **텔레그램** | `/radio` 입력 | 타이핑 |
| **Claude Code** | MCP `radio_ticket_dispatch` | 음성 |

---

## 3. 데이터 파이프라인 (4단계)

### P1 — 크롤링 (`crawl.py`)
- **소스:** `ticket.yes24.com/Genre/Classic` (정적 HTML)
- **파싱:** `swiper-slide` (제목+날짜+장소+PerfID), `list-bigger-txt`, `ms5-wrap` 랭킹
- **출력:** 19~22건/회, 그중 6건 정도 날짜 정보 완비
- **필터링:** nav 메뉴, 블로그 포스트 등 노이즈 제거

### P2 — 사연 생성 (`generate.py`)
- **엔진:** DeepSeek Chat API (`api.deepseek.com`, OpenAI 호환)
- **시스템 프롬프트:** "너는 대한민국 라디오 방송국에 사연을 보내는 전문 작가다. AI 티를 내지 않는다. 마크다운/형식문법 금지."
- **채널별 프롬프트:** 3개 채널 × 맞춤형 프로필 (박씨, 보호자, 치매어머니, 조현병 작은누나, 수요일 휴무)
- **API 실패 시:** 템플릿 폴백 (서비스 중단 없음)

### P3 — 디스패치 (`dispatch.py`)
- 오케스트레이터: 크롤링 → 생성 → TG 배달 → JSON 저장
- `--dry-run`: TG 전송 없이 사연만 확인
- `--test`: 샘플 데이터로 빠른 테스트
- 제출 링크를 TG 메시지에 HTML `<a href>`로 임베딩

### P4 — 선물함 (`giftbox.json`)
- `dispatch.py` 실행 시 자동 누적
- 각 항목: `id`, `channel`, `story`, `apply_url`, `apply_instruction`, `sent`, `sent_at`
- PWA와 TG 양쪽에서 조회·제출완료 체크 가능

---

## 4. 채널 × 제출 링크 매트릭스

### 🎻 KBS 클래식 FM (1FM)
| 프로그램 | 시간 | 제출 경로 |
|----------|------|-----------|
| KBS 음악실 | 09:00 | `program.kbs.co.kr/1fm/radio/musicroom/pc/board.html` |
| 출발 FM과 함께 | 07:00 | `program.kbs.co.kr/1fm/radio/morningfm/pc/board.html` |
| 가정음악 | 10:00 | `program.kbs.co.kr/1fm/radio/gajung/pc/board.html` |
| FM 살롱 | 11:00 | `program.kbs.co.kr/1fm/radio/salon/pc/board.html` |

> ⚠️ KBS 라디오 페이지는 해외 IP 403. 국내·KBS Kong 앱으로 접근 가능.

### 🎤 지상파 가요 (KBS TV 방청)
| 프로그램 | 제출 경로 | 확인 |
|----------|-----------|------|
| 열린음악회 | `program.kbs.co.kr/1tv/enter/openconcert/pc/board.html?smenu=9722f1` | ✅ 200 |
| 불후의 명곡 | `program.kbs.co.kr/2tv/enter/satfreedom/pc/board.html` | ✅ 200 |
| 가요무대 | `program.kbs.co.kr/1tv/enter/gayo/pc/board.html` | ✅ 200 |

### 🎸 배철수의 음악캠프 (MBC FM4U)
| 경로 | URL | 확인 |
|------|-----|------|
| MBC mini | `mini.imbc.com/...program=1000782100000100000` | ✅ 200 |

---

## 5. 레포지토리 구조

```
helena-programming/
├── apps/radio-ticket/          ← PWA 앱
│   ├── server.py               ← Python HTTP 서버 (8766)
│   │   ├── GET  /              → PWA 대시보드
│   │   ├── GET  /api/crawl     → 크롤링 실행
│   │   ├── POST /api/dispatch  → 파이프라인 실행
│   │   ├── POST /api/generate  → 사연 생성
│   │   ├── GET  /api/status    → 로그
│   │   ├── GET  /api/venues    → 공연 목록
│   │   ├── GET  /api/stories   → 🎁 선물함
│   │   └── POST /api/stories/{id}/sent → 제출완료
│   ├── pwa/
│   │   ├── index.html          ← 대시보드 UI (공연+선물함+실행)
│   │   ├── manifest.json       ← PWA manifest
│   │   └── sw.js               ← Service Worker
│   └── README.md
│
├── pipelines/radio_ticket/     ← 백엔드 파이프라인
│   ├── config.json             ← 채널·프로필·제출URL 설정
│   ├── crawl.py                ← Yes24 크롤러
│   ├── generate.py             ← DeepSeek 사연 생성기
│   ├── dispatch.py             ← 오케스트레이터
│   ├── giftbox.json            ← 🎁 선물함 데이터
│   └── dispatch_*.json         ← 실행 결과 아카이브
│
├── mcp/mcp_server.py           ← MCP 도구 등록 (4개 radio_ticket_*)
├── app-registry.json           ← helena-ticket 등록
└── index.html                  ← 랜딩 페이지 (🎙 Helena Ticket)
```

---

## 6. 의존성

| 요소 | 비고 |
|------|------|
| Python 3 | `http.server` 내장 (외부 웹프레임워크 불필요) |
| DeepSeek API | `api.deepseek.com`, OpenAI 호환 엔드포인트 |
| TG_TOKEN / TG_CHAT | `.secrets.env` |
| requests, beautifulsoup4 | 크롤링용 |
| edge-tts | TG 음성응답용 (선택) |

**제로 비용 설계:** 외부 서비스 일체 불필요. GitHub Pages 무료 호스팅 + DeepSeek API (기구독) + Telegram 무료 = **월간 운영비 0원**.

---

## 7. 사용자 플로우

### 플로우 A: PWA (가장 빠름)
```
홈 화면 아이콘 탭
  → 대시보드 열림
  → 「✍️ 사연만」 or 「🚀 전체실행」 탭
  → 3채널 사연 생성 완료
  → 🎁 선물함에서 사연 확인
  → 「📋 사연복사」 → 「🔗 제출페이지」 → 붙여넣기
  → 「✅ 제출했어요」 체크
```

### 플로우 B: 텔레그램
```
/radio        → 전체 파이프라인 실행 → TG로 사연+제출링크 수신
/radio_test   → dry-run (TG 전송 없이 사연만 확인)
/radio_box    → 선물함 조회 (미제출 사연 + 링크)
/radio_status → 최근 실행 로그
```

### 플로우 C: Claude Code
```
"헬레나 티켓 돌려줘" → MCP radio_ticket_dispatch → 결과 보고
```

---

## 8. 설계 결정

| 결정 | 이유 |
|------|------|
| `http.server` 내장 사용 | Flask/FastAPI 없이 의존성 제로. S21 폰에서 pip 설치 부담 없음 |
| PWA + manifest + SW | 홈 화면 아이콘 1탭 접근. 네이티브 APK보다 가볍고 업데이트 쉬움 |
| `giftbox.json` 단일 파일 | SQLite 없이 파일 기반. JSON이라 사람이 읽을 수 있음 |
| `subprocess.Popen` for daemon | `os.fork`보다 안정적. 포트 충돌 없음 |
| 포트 8766 | 8765는 MCP 서버가 사용 중. 충돌 회피 |
| 제출 링크를 config에 분리 | 프로그램 URL 바뀌어도 코드 수정 불필요 |
| `--dry-run` / `--test` 분리 | dry-run=TG 미전송, test=크롤링 대신 샘플 데이터 |

---

## 9. 향후 확장

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| P0 | KBS FM 프로그램 실제 제출 URL 확인 | 현재 추정 URL. 국내 IP에서 직접 접근해 verify 필요 |
| P1 | 크롤링 소스 확장 | 인터파크·멜론티켓 추가 → 더 많은 공연 커버 |
| P2 | 제출 자동화 | Selenium/Playwright로 실제 제출까지 자동화 (현재는 복사붙여넣기) |
| P3 | 당첨 추적 | 당첨/미당첨 결과 기록 → 어떤 패턴이 당첨률 높은지 분석 |
| P4 | 크론 자동화 | GitHub Actions cron으로 주 1회 자동 실행 → TG로 결과만 받기 |

---

## 10. 설치·실행

```bash
# 1. PWA 서버 시작 (1회)
cd ~/work/helena-programming/apps/radio-ticket
python3 server.py --daemon
# → http://localhost:8766

# 2. 홈 화면에 추가
# 폰 브라우저로 http://localhost:8766 접속 → "Add to Home Screen"

# 3. TG 봇 확인
# @S21Phone_Bot 에게 /radio_test 전송

# 4. 첫 실행
# PWA에서 「✍️ 사연만」 클릭 or TG에서 /radio_test
```

---

> **v2.0 | 2026-08-11**
> Helena Ticket · S21 Phone 단독 구동 · 월 0원
> GitHub: `helena751107/helena-programming/apps/radio-ticket`

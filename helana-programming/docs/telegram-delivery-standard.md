# Telegram 콘텐츠 전송 표준

> **버전:** v2.0 · 2026-08-09
> **적용:** helana_log → Telegram 전송 파이프라인
> **원칙:** 마크다운 우선. HTML은 선택.

---

## 표준 모드: 마크다운 직접 전송 (기본)

```
ParksyCapture .md 로그 → Telegram 텍스트 청크 → 복사 → Tistory 마크다운 모드 붙여넣기
```

### 기본 명령어
```bash
# 단일 파일
bash log_to_telegram.sh logs/2026/08/my-log.md

# git diff 변경분 전체
bash log_to_telegram.sh --diff
```

### Tistory 마크다운 모드 발행 흐름
1. Telegram `@helena_logbot`에서 PART 1~N 순서대로 전체 복사
2. Tistory 글쓰기 → **마크다운 모드** 선택
3. 붙여넣기 → 미리보기 확인 → 발행
4. 끝. 변환 단계 없음.

### 장점
- 중간 변환 없음 — 원본 그대로
- ParksyCapture 출력 형식과 일치
- Tistory 마크다운 모드가 알아서 렌더링
- 청크 수가 HTML보다 적음 (CSS 없음)

---

## 선택 모드: HTML 변환 전송 (`--html`)

```
ParksyCapture .md 로그 → parksy_to_html.py 변환 → Telegram 텍스트 청크 → 복사 → Tistory HTML 모드 붙여넣기
```

### 사용 시기
- 아코디언·SVG·CSS 애니메이션이 필요한 인터랙티브 페이지
- 인포그래픽 요소가 많은 대화록
- "보여주기 위한" 페이지 (방문자용)

### 명령어
```bash
# 단일 파일 HTML 모드
bash log_to_telegram.sh --html logs/2026/08/my-log.md

# 수동 workflow_dispatch → mode: html
```

---

## 자동화: GitHub Actions (helana_log)

### push 트리거 → 항상 마크다운 모드
```
helana_log에 .md push → 자동 마크다운 전송
```
기본값. 가장 빠르고 단순한 경로.

### workflow_dispatch → 모드 선택 가능
```
GitHub Actions → Log → Telegram (MD/HTML) → Run workflow
  mode: md (기본·마크다운) | html (Tistory HTML 모드용)
```

---

## Telegram 수신 형식

### 마크다운 모드 메시지
```
📄 대화록 · 2026-08-09
📝 마크다운 · 156줄 · Tistory 마크다운 모드 붙여넣기
⬇️ 아래 PART 1~N 순서대로 전체 복사 → 붙여넣기

[PART 1/N] ...마크다운 텍스트...
[PART 2/N] ...마크다운 텍스트...
```

### HTML 모드 메시지
```
📄 대화록 · 2026-08-09
🔄 24턴 · Tistory HTML 모드 붙여넣기
⬇️ 아래 PART 1~N 순서대로 전체 복사 → Tistory HTML 모드에 붙여넣기

[PART 1/N] ...HTML 코드...
[PART 2/N] ...HTML 코드...
```

---

## 파일 구조

```
helena-programming/
├── scripts/
│   ├── log_to_telegram.sh      ← 메인 전송 스크립트 (MD 기본, --html 선택)
│   └── parksy_to_html.py       ← MD→HTML 변환기 (--html 모드에서만 호출)
├── templates/
│   └── dialogue-log.html       ← HTML 템플릿
└── docs/
    └── telegram-delivery-standard.md  ← 이 문서

helana_log/
└── .github/workflows/
    └── log-to-tistory.yml      ← 자동 트리거 (push=MD, dispatch=선택)
```

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-08-09 | v1.0 | 초기: HTML-only 전송 |
| 2026-08-09 | v2.0 | **마크다운 기본으로 전환.** HTML은 `--html` 선택 모드로. Boss 결정: "마크다운으로 보내는 걸로 표준 프로세스로 정해" |

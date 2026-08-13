# Telegram 콘텐츠 전송 표준

> **버전:** v5.0 · 2026-08-09
> **적용:** helana_log → Telegram 전송 파이프라인
> **원칙:** 전부 1장 파일 첨부(sendDocument). MD는 .md, HTML은 .html 원본 그대로.

---

## 표준 모드: .md 파일 첨부 (기본)

```
.md 로그 → Telegram sendDocument .md 첨부 → 다운로드 → 전체 복사 → Tistory 마크다운 모드
```

```bash
bash log_to_telegram.sh logs/2026/08/my-log.md
bash log_to_telegram.sh --diff
```

---

## HTML 모드: .html 원본 첨부 (`--html`)

```
.md 로그 → parksy_to_html.py 변환 → Telegram sendDocument .html 첨부 → 다운로드 → 전체 복사 → Tistory HTML 모드
```

```bash
bash log_to_telegram.sh --html logs/2026/08/my-log.md
```

### 발행 흐름
1. Telegram `@helena_logbot`에서 `.html` 첨부파일 다운로드
2. 파일 열기 → **전체 복사**
3. Tistory 글쓰기 → **HTML 모드** → 붙여넣기 → 발행
4. 끝. **1장 파일, 코드블록 감쌀 필요 없음, HTML 코드 원형 그대로.**

---

## 자동화: GitHub Actions

| 트리거 | 모드 |
|--------|------|
| push (logs/**, docs/dialogue/**) | 항상 **.md 첨부** |
| workflow_dispatch | **md** (기본) / **html** (선택) |

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-08-09 | v1.0 | 초기: HTML-only 텍스트 청크 |
| 2026-08-09 | v2.0 | 마크다운 기본. HTML은 --html 선택. |
| 2026-08-09 | v3.0 | MD = sendDocument 첨부 (청크 폐기) |
| 2026-08-09 | v4.0 | HTML도 첨부로 (마크다운 코드블록에 감싸기) |
| 2026-08-09 | v5.0 | **HTML 코드 원형 그대로 .html 첨부.** Boss: "HTML 코드 그대로 복사 붙여넣을 수 있는 원형을 보내는 게 표준" |

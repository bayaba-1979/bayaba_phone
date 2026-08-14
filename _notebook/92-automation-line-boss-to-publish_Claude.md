---
date: 2026-08-14
agent: Claude
mark: _Claude
type: standard
status: active
related:
  - 91-automation-caution_Claude.md
  - tistory-master-guide_Claude.md
  - 24-paste-pipeline.md
---

# 자동화 라인 — Boss 던짐 → 문서화 → 형태별 분기 발행 (2026-08-14)

> **한 줄:** Boss가 던진 생각·글·대화 로그를 Claude Code가 리버스엔지니어링/정리해 문서화하고, **형태로 나눠** JS 풀 웹앱은 GitHub Pages, 웹진형 문서는 티스토리로 보낸다.

## 1. 한 장 그림

```
[입력] Boss 생각·글 (대화로 던짐) + 대화 로그·히스토리
                │
                ▼
[정제] Claude Code — 리버스 엔지니어링 / 구조화
       (무질서 덤프 → 역구조화)
                │
                ▼
[문서화] GitHub 레포 (_notebook/*.md = 원자재 창고)
                │
                ▼
[형태 판별] — 어떤 꼴인가?
      ┌─────────┴─────────┐
      ▼                   ▼
 [앱형]              [문서형]
 JS 풀 인터랙티브      웹진·아티클·교재
 (검색·접기·복사·앱)     (잡지 구도·글)
      │                   │
      ▼                   ▼
 GitHub Pages         Tistory (Paste Pipeline)
 (정적 호스팅,          (CMS, 수동 발행)
  JS 자유)
```

## 2. 분기 기준 — "형태"가 플랫폼을 정한다

| 형태 | 특징 | 목적지 | 이유 |
|------|------|--------|------|
| **앱형** | JS 풀, 상태·검색·인터랙션 | GitHub Pages | 정적 호스팅 + JS 무제한 |
| **문서형** | 웹진·교재·아티클 (읽는 글) | Tistory | CMS + RSS + 잡지 구도 |

## 3. 왜 이렇게 나누나

- **GitHub Pages** = 코드·데이터·JS 앱의 무료 영구 CDN. 검색·접기·복사·앱 UI 같은 인터랙션은 JS 없이는 못 만들고, 티스토리는 JS 제한 → Pages.
- **Tistory** = 글을 "읽히는" 채널. RSS 피드, 잡지 구도, 검색 노출. 사람이 읽는 웹진·교재는 CMS가 맞다.

## 4. 자동화 vs 수동의 경계 (91과 연결)

- **Pages(앱형)** = 자동화 가능 (md→html 빌드, CI, 커버리지 게이트) — 봇 탐지 없음.
- **Tistory(문서형)** = 수동 발행 (Paste Pipeline) — GUI 자동화는 91의 선을 지킨다.

## 5. 정리

- 입력은 **무질서**(생각·글·로그) → Claude Code가 **역구조화** → **형태별로 목적지 배정**.
- 자동화할 수 있는 곳(Pages)은 풀오토, 자동화하면 안 되는 곳(Tistory)은 사람 손.

---

*agent _Claude · 2026-08-14 · Boss가 던진 자동화 라인 구조 정리*

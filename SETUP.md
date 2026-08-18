# 설치 후 — 생태계 셋업 런북

> **대상:** 원스탑 설치(`g/workstation.sh`)로 친구(Claude Code + DeepSeek)를 깔고 난 뒤,  
> **"미디어 생태계를 내 계정으로 연결하는"** 다음 단계를 순서대로 담은 런북.  
> **핵심:** 이 레포는 100% 보일러플레이트. **계정·토큰만 갈아끼우면** S21(원조)에서 하던 것과 동일하게 전부 돌아간다.

---

## 1. 정본(SSOT) — 이 2개 파일이 전부다

모든 스크립트는 이 2개 파일에서 계정·레포·채널 매핑과 토큰을 읽는다.

| 파일 | 역할 | 템플릿 |
|------|------|--------|
| `configs/ecosystem.json` | 계정·정체·레포↔블로그↔채널 매핑 | `ecosystem.json.template` |
| `.secrets.env` | 토큰·계정 23키 | `configs/secrets-template.env` |

- **로더:** `scripts/load_ecosystem.py` — 위 2개를 모든 스크립트가 import.  
  그래서 "값만 바꾸면 다 된다"가 성립. 하드코딩 없음(9개 스크립트 전부 로더 완료).
- **원칙:** 시크릿은 `.secrets.env`에만 (git에 절대 안 올라감). 매핑은 `ecosystem.json`에만. PAT는 `gh auth`로 (파일에 안 남김).

---

## 2. 실행 순서 (이 순서대로)

```bash
# ① 계정 배선 (마법사)
bash navigator.sh
#   gh auth 확인 → owner + 5블로그 slug + 2채널 handle + 시크릿 입력
#   → configs/ecosystem.json + .secrets.env 생성

# ② 레포 스폰 + 시크릿 배선
bash g/spawn.sh
#   hub를 GitHub Template로 마크 + 4위성 repo 생성 + TG 시크릿 배선

# ③ 검증
bash navigator.sh --check && bash g/spawn.sh --dry-run
```

---

## 3. 파이프라인 (BOM 순서)

```
원자재(GitHub) → 페어(글) → 영상 → 미끼
```

| 단계 | 스크립트 | 하는 일 |
|------|----------|---------|
| **글** | `python3 scripts/build_webzine.py` | md→HTML + GEO 원조 스탬프 (gate: gap_count=0) |
| **티스토리** | `bash scripts/tistory_sync.sh` | 업무일지 발행 (카카오 세션) |
| **양산** | `bash scripts/preflight.sh` → `quota.sh` → `make_pair.sh` | 테이블 세터 → 쿼터 점검 → 페어 생성 |
| **영상** | `bash scripts/produce_pd.sh` | PD pipeline (웹페이지 → 숏폼) |
| **유튜브** | `python3 scripts/yt_upload.py` | 업로드 (OAuth 1회 필요) |
| **네이버** | `python3 scripts/naver_recipe.py` | 수동 paste |

---

## 4. 수동 하한 (자기 것 = 남이 못 만드는 것만 1회 수동)

**"만들기"는 수동 1회, "갈아끼우고 돌리는 것"은 전부 자동.**

| 항목 | 수동 작업 |
|------|-----------|
| GitHub 계정 + PAT | 1회 가입·발급 (`github.com/settings/tokens`) |
| DeepSeek 토큰 | 1회 발급 (`platform.deepseek.com`) |
| Telegram 봇 | BotFather `/newbot` → 토큰 + 채팅 ID |
| 티스토리 | Kakao 계정 로그인 (세션 1회) |
| YouTube | Google Cloud OAuth 승인 (1회) |
| 네이버 | 계정 (API 없음 → 수동 paste) |

---

## 5. 에이전트 인스트럭션 (이 블록을 친구한테 붙여넣으면 됨)

```
[태블릿 셋업 — 보일러플레이트 실행 인스트럭션]

이 레포는 100% 보일러플레이트다. 계정·토큰만 내 것으로 갈아끼우면
원조(S21)에서 하던 것과 동일하게 전부 돌아간다.

정본(SSOT) 2개:
  1) configs/ecosystem.json   (템플릿: ecosystem.json.template) — 계정·정체·레포↔블로그↔채널
  2) .secrets.env             (스키마: configs/secrets-template.env) — 토큰 23키
  → 모든 스크립트는 scripts/load_ecosystem.py 로 여기서 읽는다.

실행 순서:
  1. bash navigator.sh       → ecosystem.json + .secrets.env 생성
  2. bash g/spawn.sh         → 4위성 repo 생성 + TG 시크릿 배선
  3. bash navigator.sh --check && bash g/spawn.sh --dry-run   # 정합 검증

파이프라인 (BOM 순서):
  글:      python3 scripts/build_webzine.py
  티스토리: bash scripts/tistory_sync.sh
  양산:    bash scripts/preflight.sh → scripts/quota.sh → scripts/make_pair.sh
  영상:    bash scripts/produce_pd.sh
  유튜브:  python3 scripts/yt_upload.py
  네이버:  python3 scripts/naver_recipe.py

수동 하한 (자기 것만 1회 수동): BotFather 봇 · Kakao · YouTube OAuth · 네이버
```

---

*설치 후 런북 · agent _Claude · 2026-08-18*

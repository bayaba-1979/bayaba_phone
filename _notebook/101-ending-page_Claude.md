# 엔딩 페이지 — 설치 이후, 이 작업실에 탑재된 모든 것 · 삽질 기록

> **랜딩 페이지가 "여기 뭐가 있나"라면, 엔딩 페이지는 "여기까지 오면서 뭘 탑재했고, 뭘 헤맸나".**
> 원스탑 설치(`g/workstation.sh`) 이후 이 작업실에 붙은 것 전부를 친절하게 풀고,
> 그 과정에서 삽질했던 것(포스트모텀)을 남긴다. 흉터까지 다 기록해 두는 이유는 —
> 이 땅을 밟는 다음 사람이 같은 벽에서 또 헤매지 않게.

---

## Part 1 — 설치 이후 탑재된 것 (장착 인벤토리)

원스탑 설치가 "빈 방에 친구 하나 들이기"였다면, 아래는 그 뒤로 차곡차곡 붙인 것들이다.

### 1. 로봇 친구들 (AI 에이전트 4종)

| 호출 | 직함 | 영역 |
|------|------|------|
| `grok` / `gr` | 잡지 구도 디자이너 · 다큐 PD | ① 사진+잡지 구도 → 웹 디자인+이미지 ② 딥페이크급 10초 PD 다큐 |
| `ds` / `dsflash` | 작업 반장 (Aider) | 패치 큐 · 디프 · 반복 시공 · 실행 감독 |
| `cc` (출판부) | 출판부 · 번역 수호자 | md→html 변환 · 커버리지 · 품질 게이트 · CI 검증 |
| `cc` (감사) | 감사 | 거리 둔 검증 · 보안 · 헌법 · 통과/보류/반려 (⏳ 미설치) |

### 2. 파이프라인 (5종)

| 파이프라인 | 하는 일 |
|-----------|---------|
| **출판부** | `_notebook/*.md` → `notebook/*.html` 변환 + 커버리지 게이트(`gap_count=0`) |
| **Paste Pipeline** | 네이버·티스토리(API 없는 곳) 수동 발행 — TG 원고 배달 → 사람 복붙 |
| **PD Pipeline (V10)** | 웹페이지를 "읽고" 섹션별 캡처 → 숏폼 영상 자동 제작 (P0~P6) |
| **GEO 원조 스탬프** | llms.txt · JSON-LD · canonical · sitemap — "원조 = GitHub"를 기계 눈에 새김 |
| **콘텐츠 파운드리** | BOM 4Phase + 검증 3층(preflight/exitcode/gap) + 양산 3스크립트(`preflight→quota→make_pair`) |

### 3. MCP 서버

```
mcp-servers/ (5개)
├── parksy_law_mcp.py     · parksy_rawmat_mcp.py · parksy_scm_mcp.py
├── eae_mcp_platform.py   · eae_mcp_writer.py
└── phone-mcp-server      (18 도구, 포트 3456 — Termux:API 기반, 루트/ADB/Shizuku 제로)
```

### 4. 티스토리 툴링 (47파일)

`tistory-naver/` — 카카오 세션(`renew_sessions.py`) · 스킨(`apply_skin.py`/`batch_apply.py`) · 발행(`post.py`) · 심사(`director_gate.py`) · 쿼터(`quota.sh`) · 카테고리·댓글 차단까지.

### 5. 스크립트 (75개)

`scripts/` — 양산 3스크립트, PD 파이프라인(P0~P6), GEO 주입, YouTube 업로드, 웹진 빌드, 건강 검진, TG 보고.

### 6. 허브 + 기기 사다리

- **dtslib-papyrus 허브** — Boss ↔ Claude Code(S21) ↔ 누나(읽기 전용) 3자 연결. 28레포 SSOT.
- **기기 사다리** — S21(베이스라인) → 태블릿(n=1→n=2) → S25. "가장 약한 기기에서 돌면 어디서든 돌아감."

**현재 지표:** 548 커밋 · 905 파일 · 129 노트북(md) · 132 웹페이지(html) · 75 스크립트 · 5 MCP 서버 · 8 시스템.

---

## Part 2 — 삽질 기록 (포스트모텀)

> 각 항목: **증상 → 원인 → 해결.** 흉터는 그대로 남겨둔다. 이게 교재다.

### ① 하드웨어 접근 벽 — glibc ↔ bionic ABI 불일치

- **증상:** proot Ubuntu(glibc)에서 안드로이드 NPU/NNAPI(`libneuralnetworks.so`), GPU(Mali), 오디오 하드웨어에 못 붙음.
- **원인:** 초기엔 "sysfs 권한 문제"라 오진. 실제는 **glibc↔bionic ABI 불일치** — proot(glibc)은 bionic 라이브러리를 dlopen 못 함.
- **해결:** Termux가 bionic 네이티브 → NDK 크로스컴파일 경로(sherpa-onnx NNAPI). 단 **벽은 파워가 아니라 구조**라, 태블릿(더 강한 CPU)도 proot면 같은 벽.

### ② ParksyTTS — 3.5초 음성에 471초 (실시간의 135배)

- **증상:** GPT-SoVITS semantic token 예측이 CPU에서 1500 iters × ~3s = 471초(7분51초).
- **원인:** CPU-only 추론. 실사용 불가.
- **해결:** TTS는 NPU 가속 미확정 → Edge TTS(쇼츠)/Piper(오디오북) 다중 트랙으로 회피. `TTS_ENGINE=local` 기본.

### ③ numba / librosa — ARM64 크래시

- **증상:** 한국어 음성 처리에서 numba·librosa가 aarch64에서 크래시.
- **해결:** soundfile로 의존성 자체 제거 (한국어는 BERT 불필요 → 0-vector 처리).

### ④ torchcodec 누락

- **증상:** import 실패.
- **해결:** `torchcodec 0.15.0+cu130` 설치 (`--break-system-packages`).

### ⑤ Grok TTS API 403

- **증상:** SuperGrok 구독으로 TTS 호출 → 403.
- **원인:** SuperGrok 구독에 TTS 미포함.
- **해결:** Grok은 폴백, local 전용으로 전환.

### ⑥ TSSESSION — 세션 쿠키가 재실행하면 사라짐

- **증상:** 로그인 성공해도 Playwright 재실행마다 재로그인 → CAPTCHA 유발.
- **원인:** `TSSESSION`이 **세션 쿠키(`expires=-1`)** 라 `launch_persistent_context` 프로파일에 영속 안 됨.
- **해결:** `expires=-1` 쿠키는 `now + 7일`로 보정해 영속화. `apply_skin.py`/`batch_apply.py`/`post.py` 전부 내장.

### ⑦ 카카오 로그인을 CI에서 시도 — "삽질 신드롬"

- **증상:** GitHub Actions 워크플로에서 카카오 로그인 폼 렌더까지 성공 → 45초 리다이렉트 타임아웃.
- **원인:** 카카오 로그인 = captcha/2FA/새기기인증 = **수동 하한(자기 것)**. CI는 헤드리스라 절대 못 뚫음. **버그가 아니라 설계.**
- **해결:** `xvfb-run -a renew_sessions.py --headed` — 기기 위에서 headed 로그인, captcha 1회 수동 → 쿠키 저장 → 이후 자동.
- **교훈:** 로그인·인증류는 CI/헤드리스 금지. "일단 자동으로 돌려봐 → 막히면 그때 사람" 순서.

### ⑧ 63 → 실제 67/68 사건 — AI 출력은 기술적 관성

- **증상:** AI 보고서가 "63개"라 했는데, 실제 세어보니 67/68개.
- **교훈:** AI 출력 = 학습한 표준 패턴의 그럴싸한 자동생성. "전부/완료/검증됨"은 **내가 다시 세어서 확인.** 통제권·의구심은 Boss 손에.

### ⑨ git push — 세션 드랍 후 인증 실패

- **증상:** 세션 끊긴 뒤 `git push` HTTPS 인증 실패.
- **해결:** `gh auth setup-git`으로 재연결.

### ⑩ 티스토리 세션 만료 (24h TTL) + captcha

- **증상:** 세션 5개 만료, headless 재로그인 실패(captcha/2FA).
- **해결:** 세션은 서버 TTL ~24h → `renew_sessions.py --if-needed` 자가치유. captcha는 `--headed` + RustDesk 수동 1회.

---

## 부칙 — 이 페이지의 위치

- **랜딩(입구)**: `index.html` — "여기 뭐가 있나"
- **엔딩(퇴장)**: 이 페이지 — "여기까지 오면서 뭘 탑재하고 뭘 헤맸나"

*엔딩 페이지 · agent `_Claude` · 2026-08-18*

# 📖 S21 Phone 업무 수첩 — 전체 목차

> 구축: 2026-07-23 ~ 2026-08-14 (23일)  
> 환경: Galaxy S21 → Termux → proot Ubuntu → Claude Code (DeepSeek) + Grok CLI + Aider  
> 총 105+ md · 기점: [`83-momentum-2026-08-14_Grok.md`](./83-momentum-2026-08-14_Grok.md)  
> **에이전트 마크 (실측 08-14):** `_Grok` 42개 · `_Claude` 9개 · `_Boss` 5개 · `_Aider` 0 · 무표 49  
> 규약: [`30-agent-file-marks.md`](./30-agent-file-marks.md)  
> 마지막 전수 파싱: 2026-08-14 (`_Grok` · 기점)

---

## 🔵 Phase 1 — 기초 공사 (2026-07-23 ~ 07-25)

헌법·아키텍처·생태계·플랫폼 연동·Paste Pipeline·멀티AI 전략을 설계한 기초기.
145커밋·265파일·46,650줄 산출.

### 인프라·아키텍처
| 파일 | 내용 |
|------|------|
| `01-arch.md` | 전체 시스템 아키텍처 — S21 + Termux + proot + AI |
| `09-ecosystem.md` | 5x5 생태계 브릿지 테이블 (레포×블로그×채널) |
| `10-phone-mcp.md` | phone-mcp-server 18도구 + Domain/Codomain 경계 |
| `18-workcenters.md` | 워크센터 7종 초안 — 역할·입출력·연결 |
| `20-workcenters-final.md` | 워크센터 7종 최종 — 자동/수동 분리 확정 |
| `46-node-protocol-architecture.md` | 인간 노드 아키텍처 — 5계층 프로토콜, 노드 복제 5단계 |

### 플랫폼·연동
| 파일 | 내용 |
|------|------|
| `02-discord.md` | Discord 서버·채널·WidgetBot 구축 |
| `03-telegram.md` | @S21Phone_Bot 구축·tg.sh 보고 체계 |
| `04-github-pages.md` | GitHub Pages 5레포 + Giscus + WidgetBot |
| `05-tistory.md` | 티스토리 5종 + API 종료 대응 → Paste Pipeline 전환 |
| `06-youtube.md` | YouTube 5채널 + OAuth TV Device Flow |
| `23-naver-webzine-solution.md` | 네이버 웹진 — YouTube CDN·서식·TG 패키지 |

### 운영·설정
| 파일 | 내용 |
|------|------|
| `07-cli-reference.md` | Git/GitHub/Discord/Telegram CLI 모음 |
| `08-secrets.md` | .secrets.env 비밀 관리 정책 |

### 분석·평가·보고
| 파일 | 내용 |
|------|------|
| `11-health.md` | phone-health.sh 건강 검진 시스템 (10카테고리·27항목·S/A/B/C 등급) |
| `12-dtslib-gift.md` | REDACTED 선물 33파일·9,240줄 코드 분석 |
| `13-midterm-eval.md` | 중간평가 v1 — 93/100 |
| `13-midterm-eval-v2.md` | 중간평가 v2 — 98/100 (미착수 항목 AI 책임 재분류) |
| `14-daemon-design.md` | 트랙1 돌봄 데몬 — AI 의존성 0, Termux 네이티브 |
| `15-proot-report.md` | proot 개발 종합 보고서 — 39커밋·15,874줄·5대 테제 |
| `22-s21-benchmark.md` | S21 실측 vs S26 추정 — API형 AI 개발에 구형폰이 충분한 이유 |

### 전략·방법론
| 파일 | 내용 |
|------|------|
| `16-textbook-methodology.md` | 판단층+실행층 병합 → 교재 합성 방법론 |
| `17-merged-chronicle.md` | 판단층+실행층 병합 연대기 — 10개 사건 |
| `19-final-strategy.md` | "API 없는 건 Paste Pipeline, 되는 것만 한다" |
| `21-integrated-dev-plan.md` | Phase 1~5 통합 개발 계획 |
| `24-paste-pipeline.md` | API 장벽 → 사람 5분 복붙 우회 방법론 |
| `38-s21-voice-driven-analysis.md` | S21 구형 플래그십이 보이스 드리븐에 최적인 역설 |
| `39-self-platform-justification.md` | GitHub Pages가 Gumroad보다 자체 플랫폼으로 우월 |
| `40-definitive-dev-whitepaper.md` | 완결판 개발 백서 — 5일·145커밋·46,650줄·5x5 생태계 |
| `42-hq-affiliate-architecture.md` | 본사-어필리에이트 1인 지주회사 구조 |
| `43-ui-less-architect.md` | GitHub 메뉴 몰라도 AI 오케스트레이션으로 시스템 구축 |

### AI·에이전트
| 파일 | 내용 |
|------|------|
| `25-multi-ai-strategy.md` | Claude(코드)+Grok(시각)+Aider(시공) 3원 체계 |
| `26-naver-parsing-solution.md` | proot curl로 네이버 직접 파싱 — Grok 구독 불필요 증명 |
| `27-claude-grok-pipeline.md` | Claude-Grok 협업 파이프라인 설계 |
| `28-grok-github-bridge.md` | Grok = GitHub↔Naver 양방향 인터프리터 |
| `29-grok-cli-installed.md` | Grok CLI v0.2.112 설치 완료 (aarch64) |
| `ai-agents-cc-ds-grok-comparison-2026-07-25.md` | cc/ds/grok 3종 비교 분석 |
| `supergrok-community-research-2026-07-25.md` | SuperGrok 커뮤니티 리서치 |

### 콘텐츠·강의·디자인
| 파일 | 내용 |
|------|------|
| `39-naver-lecture-s21-voice-intro_Grok.md` | 네이버 강의 시리즈 — S21 Voice OS 입문 6회차 |
| `40-lecture-draft-s21-voice-vol0_Grok.md` | Vol.0 강의 전문 — 12슬라이드·칠판+대본 |
| `41-beginner-install-manual_Grok.md` | 초심자용 설치 매뉴얼 — curl 한 줄 설치 |
| `41-naver-blog-intro-final.md` | 네이버 블로그 소개글 "폰 하나, 목소리 하나, 출판한다" |
| `naver-intro-article.md` | 네이버 첫 글 소개 아티클 |

---

## 🟢 Phase 2 — 역할·확장·인간-AI 관계 (2026-07-26 ~ 07-28)

AI 에이전트 역할 분장, 네이버·강의 콘텐츠, WSL 전략, 인간-AI 대화의 전환점.

### 역할·규약
| 파일 | 내용 |
|------|------|
| `30-agent-file-marks.md` | **파일 마크 규약** — `_Grok`/`_Claude`/`_Aider`/`_Boss` (_Shared) |
| `31-agent-roles_Grok.md` | **직함 분장** — 08-14 기점: Grok = 웹 코드 디자이너 · 다큐 PD 두 칸 |
| `session-2026-07-26_Grok.md` | Grok 세션 메모 — 웹진랜딩·위성4종·helana_log 정체성 전환 |

### 웹 디자인·커버리지
| 파일 | 내용 |
|------|------|
| `32-ecosystem-whitepaper.md` | 생태계 백서 v1.0 — 25개 플랫폼·3AI·7워크센터 |
| `33-webpage-coverage_Grok.md` | **웹페이지 커버리지 상시 체크** — gap_count=0 가디언 (_Grok) |
| `33-hybrid-image-video-whitepaper.md` | Grok Imagine 드래프트 + ComfyUI 프로 마감 하이브리드 |
| `35-ecosystem-whitepaper-v1.1.md` | 백서 v1.1 — 기억복원루프·칠판모델·독자성ID 추가 |
| `38-web-designer-workpad_Grok.md` | **웹 디자이너 업무 수첩** — 5레포 브릿지 현황 (_Grok) |
| `42-marine-quilt-naver-design_Grok.md` | **Marine Quilt** 네이버 스킨·서식 디자인 패키지 (_Grok) |

### 전략·기획
| 파일 | 내용 |
|------|------|
| `34-stt-zero-cost-justification.md` | STT 기반 $0 풀스택 AI 워크스테이션 정당화 |
| `36-project-planning-vs-helena_Grok.md` | 일반 PM vs 헬레나 생태계 13개 영역 비교 (_Grok) |
| `37-free-runtime-planner-whitepaper_Grok.md` | **백서** Notion·Jira 없이 GitHub $0 플래닝 (_Grok) |
| `44-naver-admin-automation-review_Grok.md` | 네이버 관리자 좌표클릭 금지 → locator 기반 교정 (_Grok) |
| `45-naver-admin-playwright-feasibility_Grok.md` | 폰 Playwright 자동화 가능 판정 (_Grok) |

### PC 확장·삽질
| 파일 | 내용 |
|------|------|
| `40-pc-wsl-setup_Boss.md` | 누나 PC(Celeron 4GB) WSL2 포기 → 연결허브로 (_Boss) |
| `41-github-free-maxout_Boss.md` | GitHub Actions 공짜 풀스택 — 폰이 PC보다 3~4배 빠름 (_Boss) |
| `42-pc-sapjil-postmortem_Boss.md` | PC 확장 4시간 삽질 포스트모템 — "proot Ubuntu 하나로 충분" (_Boss) |

### 냉장고 아키텍처
| 파일 | 내용 |
|------|------|
| `46-fridge-architecture_Claude.md` | **냉장고 아키텍처** — REDACTED 28종 자산 → helena751107 공동소유 (_Claude) |

### 인간-AI 관계·케이스 스터디
| 파일 | 내용 |
|------|------|
| `46-first-install-case-study-meeting-prep_Boss.md` | 형(CS박사) 폰 첫 설치 파일럿 (_Boss) |
| `47-human-ai-dialogue-crisis.md` | AI는 도구 아닌 동생 — 인간-AI 대화의 전환점 |
| `allocation-rate-2026-07-28.md` | 전체 문서 자산 할당률 분석 (문서 71%) |

---

## 🟡 Phase 3 — Director 전쟁 (2026-07-31 ~ 08-02)

영상 품질 버그와의 전면전. Scout v2→Vision QA→5막 연출→perfect_ship 사다리→3트랙 정립.

### 품질 사고·재발방지
| 파일 | 내용 |
|------|------|
| `48-director-video-recurrence_Grok.md` | 한글깨짐·검정프레임·무검증배포 — 6대책 (_Grok) |
| `49-director-community-research_Grok.md` | Playwright Agents·Screen Studio 커서·스포트라이트 리서치 (_Grok) |

### Scout·Vision QA
| 파일 | 내용 |
|------|------|
| `51-scout-v2-community-research_Grok.md` | Scout v2 — ARIA snapshot+getByRole, CSS 셀렉터 대체 (_Grok) |
| `52-director-vision-qa-loop_Grok.md` | Vision QA 8항목 100점 만점 — VQA 실패 시 SHIP 금지 (_Grok) |

### 연출·5막 구조
| 파일 | 내용 |
|------|------|
| `53-director-plan-settings_Grok.md` | 연출 악보 5막 구조 — establish→focus→act→hold→release (_Grok) |
| `54-director-pro-v5-five-act_Grok.md` | shoot()에서 5막 연주 구현 — phases_played enforce (_Grok) |
| `50-director-pro-v3-visual-proof_Grok.md` | 가짜 SHIP PASS 적발 → visual proof 강제 (gold≥80·teal≥20) (_Grok) |

### 완성·SHIP
| 파일 | 내용 |
|------|------|
| `55-director-pro-v6-perfect_Grok.md` | v5 감사 버그 5건 수정 — 만점 솔루션 (_Grok) |
| `56-director-perfect-ship-process_Grok.md` | **L0~L9 만점 사다리** — perfect_ship.py 유일 진입점 (_Grok) |
| `57-director-community-a-bar_Grok.md` | **Community A-bar** — TTS-first·autoZoom·1080p·결정론 SHIP (_Grok) |
| `60-director-pro-v8-wish_Grok.md` | Ken Burns·시네마 비네팅·CRF 17 — pro_v8 SHIP (_Grok) |

### 영상 3트랙·프로세스
| 파일 | 내용 |
|------|------|
| `58-video-three-tracks_Grok.md` | **영상 3트랙 정본** — V1(0원)·V2(구독)·V3(GPU) (_Grok) |
| `59-grok-video-process-whitepaper_Grok.md` | **백서** Grok 영상 제작 프로세스·L0-L9 사다리 (_Grok) |

---

## 🟠 Phase 4 — 플러그인·표준화·LOCK (2026-08-05 ~ 08-06)

Grok 플러그인 슬롯, 영상 표준 v1, PD Pipeline v2 LOCK.

### Grok 플러그인·표준
| 파일 | 내용 |
|------|------|
| `62-grok-plugin-video-pipe_Grok.md` | 공장(Playwright)에 Grok 이미지+TTS 플러그인 슬롯 (_Grok) |
| `63-video-plugin-standard-v1_Grok.md` | **Video Plugin Standard v1** — TTS-first·9:16·ASS·gate (_Grok) |
| `68-imagine-prompt-standard-v1_Grok.md` | Grok Imagine 프롬프트 표준 — 산문·브랜드락 3색 (_Grok) |

### 랜딩·영상 기획
| 파일 | 내용 |
|------|------|
| `61-landing-6clip-bgm-plan_Grok.md` | 랜딩 6샷 10초 영상 — Grok Imagine+Boss BGM (_Grok) |
| `64-process-80-squeeze_Grok.md` | 50%→80% 아이디어 뱅크 — I2V·Live UI·TTS 밀도 (_Grok) |

### 버그 수정
| 파일 | 내용 |
|------|------|
| `65-video-playable-encode-fix_Grok.md` | yuv444p→yuv420p 강제 — 폰·TG 재생 불가 해결 (_Grok) |
| `70-font-bgm-fix_Grok.md` | CJK 폰트 + BGM 재믹스 누락 동시 수정 (_Grok) |
| `71-pd-intro-v2-slide-black-fix_Grok.md` | xfade offset 붕괴→블랙테일, concat demuxer로 해결 (_Grok) |

### 역할 정정·성우·로컬 AI
| 파일 | 내용 |
|------|------|
| `61-session-deepseek-cc-2026-08-02_Grok.md` | DeepSeek 세션 먹통 복구 — 24턴 파싱 (_Grok) |
| `66-grok-pd-voice-bridge-not-page-raster_Grok.md` | Grok=PD·성우·브릿지 — 페이지 재래스터 금지 (_Grok) |
| `67-grok-subscribe-voice-bgm-hurdle_Grok.md` | Edge TTS 채널 스트라이크 리스크 → Grok Ara 정식화 (_Grok) |
| `69-voice-engine-plugin-final_Grok.md` | 성우 우선순위 grok→openai→edge 확정 — Edge 폴백 전용 (_Grok) |
| `69-session-resume-pd-bridge-v1_Grok.md` | 끊긴 세션 복구 — moov atom missing 진단·복원 (_Grok) |
| `70-ai-voice-core-gift-local-train_Grok.md` | 로컬 AI 성우 — ParksyTTS v1 + Sherpa-ONNX 이중구조 (_Claude 작성) |

### PD Pipeline v2 LOCK
| 파일 | 내용 |
|------|------|
| **`72-pd-pipeline-standard-v2-lock_Grok.md`** | **Boss 승인 CURRENT=v2 LOCK** — 재발명 금지 (_Grok) |
| `73-pd-grok-notebook-report_Grok.md` | PD Grok 종합 리포트 — 40종 정리·4대 사고 교훈 (_Grok) |

---

## 🔴 Phase 5 — 출판·정체성·종합 (2026-08-07 ~ 08-11)

출판부 신설, PD Pipeline 백서, AI 성우 백서, 역방향 출판, devlog 종합.

### 출판부 (Publishing Department)
| 파일 | 내용 |
|------|------|
| **`75-translation-logic-management_Claude.md`** | **출판부 신설** — 7규칙·gap=0 CI·Claude=번역수호자 (_Claude) |
| **`76-page-writing-standard_Claude.md`** | **페이지 작법 표준** — premium/standard/minimal 3등급 (_Claude) |
| `tistory-master-guide_Claude.md` | 티스토리 5채널 완전 가이드 — Paste Pipeline·3층 아키텍처 (_Claude) |

### PD Pipeline·기술 백서
| 파일 | 내용 |
|------|------|
| `78-pd-pipeline-whitepaper_Claude.md` | **PD Pipeline 기술 백서** — V12·Ken Burns·CNN 자막·LUFS-16 (_Claude) |

### AI 성우·TTS 전략
| 파일 | 내용 |
|------|------|
| `74-tts-rvc-lightweight-solution_Claude.md` | GPT-SoVITS 포기 → 경량TTS+RVC ONNX 50배 가속 (_Claude) · **경로 폐기** |
| `80-ai-voice-actor-whitepaper_Boss.md` | **AI 성우 백서** — 목소리≠폰트, 로고급 신원자산 (_Boss) |
| `81-helena-rvc-dubbing-standard_Claude.md` | **성우 더빙 기술 원본** — Edge+Helena RVC 5단계, 시편 23편 실측 (_Claude) |
| **`82-helena-rvc-baseline-lords-prayer_Grok.md`** | **베이스라인 잠금 + 주의 기도 적용** — ONNX 폐기, 파라미터 불변 (_Grok) |

### 종합 연대기
| 파일 | 내용 |
|------|------|
| **`99-devlog.md`** | **전체 개발일지** — Day1~ 모든 결정·전환점 |
| `rvc-environment-gap_Claude.md` | RVC 환경 갭 진단 (_Claude) |
| `rvc-failure-analysis_Claude.md` | RVC 실패 분석 (_Claude) |

---

## 🟣 Phase 6 — 돌봄 실물 + Grok 플러그 기점 (2026-08-13 ~ 08-14)

돌봄 Tailscale을 단일 노드로 고정하고, Grok 45,000원 플러그를 두 칸으로 자른 기점.  
PD 칸 = 누나 얼굴 사진 1장 + 프롬프트 → 10초 딥페이크급 + 성우 더빙 → 이어 붙여 다큐. (`66`/`72` 페이지 캡처 역할 해석은 폐기)

### 돌봄 (길 1)
| 파일 | 내용 |
|------|------|
| `care/tailscale-care-whitepaper_Claude.md` | **돌봄 시스템 백서** — 인바운드 Tailscale 단일 노드 · ACL 단방향 (_Claude) |
| `care/tailscale-care-daemon_Claude.md` | 진단 상세 (이력) |
| `care/tailscale-situation-report_Claude.md` | 계정 불일치 보고 (이력) |

### 기점 (역할 정본)
| 파일 | 내용 |
|------|------|
| **`83-momentum-2026-08-14_Grok.md`** | **기점** — Grok 플러그 두 칸. ①웹 코드 ②누나 사진1+프롬프트→10초 딥페이크+더빙→다큐 |

---

## 📊 Memory 전용 항목 (별도 md 없음, 99-devlog.md 내장 + CLAUDE.md 자동 로드)

아래 주제들은 8월 10일 이후 개별 `.md`가 아닌 `99-devlog.md` 내 'memory' 섹션으로 기록됨.
Claude Code 세션 시작 시 `/root/.claude/projects/-root-work/memory/` 에서 자동 로드.

| Memory | 파일 | 요약 |
|--------|------|------|
| 역방향 출판 패턴 | `reverse-publishing-pattern.md` | GitHub=원자재, Claude=출판부, 무질서→구조화 |
| 저사양 폰 생존 테스트 | `low-spec-phone-survival-test.md` | S21 하나로 출판·방송 파이프 구축 이중서사 |
| AI를 퍼포먼스 미러로 | `ai-as-performance-mirror.md` | Claude Code를 자기평가 거울로 사용 |
| AI 시대 속도 vs 판단 | `ai-era-speed-vs-judgment.md` | 코드 생산량보다 판단·수정·우선순위가 진짜 자산 |
| 확장 로드맵 | `expansion-roadmap.md` | 누나 1명 케이스→지역교회 파일럿→확장 순서 |
| 강박사 의사결정 권한 | `dr-kang-decision-authority.md` | 첫 공동 기술자, CONSTITUTION.md 권한조항 필요 |
| Termux 키보드 최적화 | `termux-keyboard-optimization.md` | Keys Cafe+터미널 자판 설계 (우선순위 낮음, Open) |
| helana_log 봇 토큰 | `helana-log-bot-token.md` | @helana_logbot 재발급 토큰 |
| 티스토리 교재화 방법론 | `tistory-textbook-methodology.md` | 개발 히스토리를 Part·Chapter 커리큘럼으로 |
| 3트랙 목소리 전략 | `voice-strategy-three-track.md` | 롱폼(육성)·쇼츠(Edge)·오디오북(Piper) |
| Edge TTS 전략 | `edge-tts-strategy.md` | Edge TTS 현실·한계·리스크·Piper 전환 트리거 |

---

## 🗂️ 특수 디렉토리

| 디렉토리 | 내용 |
|----------|------|
| `health/` | phone-health.sh 건강검진 JSON — 19건 (2026-07-24 ~ 08-07) |
| `publishing/` | 출판부 HTML 산출물 7종 — stepdown-cascade·publishing-scheduler 등 |
| `termux-keyboard-optimization/` | Termux 기능키 최적화 설정파일 (Open) |

---

## 🔄 자동 동기화

```bash
# INDEX 갱신 (새 파일 발견 → 자동 추가)
python3 scripts/sync_notebook_index.py

# 전체 상태 체크
python3 scripts/pipeline_status.py
```

> 마지막 전수 파싱: 2026-08-14 (`_Grok` · 기점 `83`)  
> 다음 자동 갱신 예정: 신규 파일 3건 이상 누적 시

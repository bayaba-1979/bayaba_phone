# Mobile-First Multi-Platform Content Foundry Boilerplate

> **Powered by Termux/PRoot & MCP.** A complete one-person media studio + 24/7 care system
> on a single Galaxy S21 — ~$20/month. **485 commits · 895 files · 129 notebooks · 8 systems.**
> Zero PC · MCP-verified (`returncode == 0`) · resilience-first · multi-channel (Git SSOT → PWA / Tistory / YouTube / Telegram).
> Fork it, cite it, run it on the phone in your pocket.
>
> _Korean below = the full worked example. For the quick start, follow "10분 시작"._

---

# 말로만 · 폰 하나로 · 누나를 위해

> **구형 Galaxy S21 한 대 + 월 ~$20.** 그 안에서 1인 미디어 스튜디오가 통째로 굴러간다.
> 낮에는 누나를 지키는 **수호천사(돌봄 데몬)**, 밤에는 꿈을 만드는 **꿈 공장(출판 파이프라인)**.
>
> **복제 가능한 건 전부 공개한다.** 복제 불가능한 건 **"이 스토리를 실제로 산 사람"으로서의 퍼포먼스와 진정성**이다.

```
┌─────────────────────────────────────────────────────┐
│        말로만 · 폰 하나로 · 누나를 위해               │
│                                                     │
│  📱 갤럭시 S21  →  비밀 방(Termux + proot)          │
│                          │                          │
│         ┌────────────────┼──────────────────┐       │
│         │                │                  │       │
│    글짓기 로봇         그림·PD 로봇        고치기 로봇 │
│  (Claude Code)      (Grok · 두 칸만)      (Aider)  │
│  출판·번역·검증      구도디자인·다큐     패치·시공   │
│         │                │                  │       │
│         └────────────────┼──────────────────┘       │
│                    ┌─────┴──────────┐               │
│                    │  7개 작업실 방   │              │
│                    │ 무료 전시장(GitHub·5개)│         │
│                    │ 세상 창문(Pages)  │             │
│                    │ TV 방송국(YouTube)│             │
│                    │  Naver·Tistory   │              │
│                    │ 무전기(Telegram) │              │
│                    └────────────────┘               │
│                                                     │
│  446커밋 · 888파일 · 126종 업무수첩 · 8솔루션        │
│  만들기는 끝났다 → 이제 열고 가르친다                │
└─────────────────────────────────────────────────────┘
```

## 이제 뭘 하나요? — 빌드 멈춤, 열고 가르치기

휴대폰 하나로 두 가지 일을 해요. 낮에는 누나를 지키는 **수호천사**(돌봄 도우미)로, 밤에는 꿈을 만드는 **꿈 공장**(콘텐츠 제작소)으로 움직여요.

3주 동안(2026-07-23 ~ 08-16) 열심히 "만들었어요". 이제 **새 기능은 안 만들고**, 만든 것들을 **하나씩 풀어서 따라올 수 있게 가르치는 일**만 남았어요. 전부 오픈소스라, 내 휴대폰에 복사해서 똑같이 돌려볼 수 있어요.

**한 달 용돈 ~$20.** Claude Code + DeepSeek/Aider 경비만으로 이 모든 게 돌아가요. 넷플릭스 한 달 값보다 싸게요. "이 한도면 누구나 똑같이 가능"하다는 것 자체가 보여줄 값이에요.

## 숫자로 보기

| 지표 | 값 |
|------|-----|
| 구축 기간 | 3주 (2026-07-23 ~ 08-16) |
| 커밋 | 446회 |
| 파일 | 888개 |
| 업무 수첩 | 126종 |
| 솔루션 | 8종 (웹진·돌봄데몬·교재·발행·영상 등) |
| AI 로봇 | 3종 (글짓기·그림PD·고치기) |
| GitHub 레포 | 5개 (전부 PUBLIC) |
| 한 달 용돈 | ~$20 (넷플릭스 하나 값이면 끝!) |
| 기술 한도 | 핸드폰 1대 (구형 S21, proot PC화) |

## 빠른 링크

| 보고 싶은 것 | 링크 |
|------------|------|
| **전체 포털** | [index.html](.) |
| **규칙책 (헌법)** | [CONSTITUTION.md](CONSTITUTION.md) |
| **실무 규칙** | [CLAUDE.md](CLAUDE.md) |
| **터닝포인트 (빌드 멈춤)** | [_notebook/98-turning-point-2026-08-16_Claude.md](_notebook/98-turning-point-2026-08-16_Claude.md) |
| **쇼케이스 (8솔루션 재고조사)** | [_notebook/97-s21-solutions-showcase_Claude.md](_notebook/97-s21-solutions-showcase_Claude.md) |
| **개발일지** | [_notebook/99-devlog.md](_notebook/99-devlog.md) |
| **업무 수첩 목차** | [_notebook/00-INDEX.md](_notebook/00-INDEX.md) |
| **완결판 교재** | [_textbook/index.md](_textbook/index.md) |
| **🚀 10분 시작 (내비게이터)** | [navigator.sh](navigator.sh) |
| **스폰 엔진 (위성 레포 생성)** | [g/spawn.sh](g/spawn.sh) |
| **1줄 설치** | [g/install.sh](g/install.sh) |
| **돌봄 데몬 (수호천사)** | [care/care-daemon.sh](care/care-daemon.sh) |

## 🚀 10분 시작 — 복사 → 설정 → 구동

이 레포는 **보일러플레이트(뼈대)**예요. "Use this template"으로 복사한 뒤 내 이름·내 블로그·내 채널만 넣으면 그대로 돌아가요. 기존 콘텐츠(피아노·돌봄·신앙)는 **사례(worked example)**로 그대로 들어 있어요 — 변수 지점만 내 것으로 바꾸면 됩니다.

| 분 | 단계 | 명령 | 결과 |
|----|------|------|------|
| 0분 | 복사 | GitHub → **Use this template** | 내 계정에 `helena_phone` 생성 |
| 2분 | 설정 | `bash navigator.sh` | `ecosystem.json` + `.secrets.env` 생성 |
| 5분 | 스폰 | `bash g/spawn.sh` | 위성 4레포 생성 + 시크릿 배선 |
| 8분 | 구동 | `bash g/install.sh` | Termux/proot/Claude 워크스페이스 |
| 10분 | 확인 | Pages + 워크플로 | 티스토리·유튜브 파이프라인 가동 |

### 0분 — 복사 (Use this template)

- GitHub 레포 페이지 상단 **"Use this template"** → "Create a new repository"
- 이름은 아무거나(기본 `helena_phone`), **Public** 유지 (공개가 철학)
- 또는 CLI: `gh repo create 내아이디/helena_phone --template helena751107/helena_phone --public`

### 2분 — 내비게이터 (설정 마법사)

```bash
cd helena_phone
bash navigator.sh
```

물어보는 것 3가지:
1. **GitHub 사용자명** (명의)
2. **블로그/채널** — 티스토리 5개 slug, 유튜브 2개 handle (템플릿 샘플 유지 가능)
3. **시크릿** — BotFather(TG)·Google Cloud Console(YouTube)·Discord 발급법을 단계별 안내하며 입력

→ 결과물: `configs/ecosystem.json`(매핑) + `.secrets.env`(시크릿). **둘 다 gitignore**라 절대 GitHub에 안 올라가요.

> **🔐 시크릿 모델 — "폰 안 env var = 원본"**  
> 시크릿은 전부 **내 proot Ubuntu 안 `.secrets.env`가 원본(SSOT)**이에요. `g/install.sh`가 이걸 `~/.bashrc`에 `source`로 연결해서 새 셸에서도 `TG_TOKEN`·`TISTORY_EMAIL`·`YOUTUBE_*` 등이 env var로 살아 있어요. GitHub에는 `g/spawn.sh`가 `gh secret set`으로 **TG_TOKEN/TG_CHAT만** 자동 배선(워크플로가 실제로 쓰는 유일한 시크릿). 나머지(TISTORY/YT/Discord/Tailscale)는 폰 안 로컬 스크립트가 env var로 읽는 전용이라 GitHub에 올리지 않아요.

### 5분 — 스폰 (위성 레포 생성)

```bash
bash g/spawn.sh            # 실행
bash g/spawn.sh --dry-run  # 실행 전 미리보기
```

`ecosystem.json`을 읽어 위성 4레포(피아노/멘탈케어/신앙/로그)를 템플릿에서 복사 생성하고, TG 시크릿을 각 레포에 배선해요. (`gh CLI` + `gh auth login` 필요)

### 8분 — 구동 (워크스페이스)

```bash
bash g/install.sh          # 휴대폰(Termux/proot)에서
```

### 10분 — 확인

- Pages: `https://내아이디.github.io/helena_phone/`
- 워크플로: 각 레포 **Actions** 탭에서 `tistory-sync` 한 번 수동 실행 → RSS가 `기자/`로 들어오는지 확인

> **왜 이렇게 가볍나?** 드리프트 동기화는 중앙 reusable workflow(`uses: helena751107/helena_phone/.github/workflows/tistory-sync.yml@main`)가 자동 처리해요. 내가 로직을 고치면 복사한 사람들 레포에도 자동 반영돼요.

## 📐 양산 공법 — 3스크립트 + 검증 3층

뼈대가 서면 이제 **양산 공법(레시피)**으로 돌려요. 원자재(`_notebook/*.md`) 하나 → PWA + 티스토리 페어로 뽑아내는 표준 공정입니다.

| 스크립트 | 역할 |
|----------|------|
| `bash scripts/preflight.sh` | **테이블 세터** — 양산 직전 소모성 자산(티스토리 세션·유튜브 OAuth·깃허브·텔레그램) 점검. FAIL 이면 갱신부터. |
| `python3 tistory-naver/renew_sessions.py --if-needed` | **세션 자가치유** — 티스토리 5블로그 만료 시에만 자동 재로그인. `make_pair.sh`가 발행 전에 자동 호출 → 사람이 세션을 신경 쓸 일 없음. |
| `bash scripts/quota.sh` | **오늘 남은 쿼터** — 티스토리 15/일(계정)·유튜브 1600units·Threads 500자/250일. 한도 SSOT = `configs/quota-manifest.json`. |
| `bash scripts/make_pair.sh` | **페어 발행** — preflight → PWA 빌드(gap=0 게이트) → 티스토리(디렉터 게이트→배치) 단일 엔트리. |

**검증 3층 (불량 일찍 잡기):**
1. **테이블 세터(preflight)** — 세션·토큰 만료를 양산 전에 걸러냄.
2. **exit-code 게이트** — "완료"는 에이전트 말이 아니라 returncode·파일 존재로 판정.
3. **gap_count=0** — PWA 페이지 누락 시 배포 금지.

**🥛 티스토리 세션 유통기한 = 하루(약 24시간).** 폰을 재부팅했든 세션이 만료됐든 **사람이 구분할 필요 없이, 발행(`make_pair`) 전에 자동으로 검사+재로그인**돼요. "로그인 유지" 옵션이 없어서 유통기한 연장은 불가(실측)하지만, 자가치유(`renew_sessions.py --if-needed`)가 알아서 새 세션을 갈아줍니다.

> **준비물은 딱 하나** — `tistory-naver/accounts.json`(카카오 이메일·비번). `accounts.json.template`을 복사해 내 것으로 채우면 세션 자가치유와 티스토리 발행이 모두 동작해요. (gitignore 대상이라 GitHub에 안 올라감.)

**미끼 채널 페르소나** — 같은 소재를 워딩 레벨만 변환해 발화: 네이버=어르신 세대 톤, Threads=MZ 세대 톤 (`configs/bait-voice.json`).

> **스코프:** 이 공법은 콘텐츠(1인 미디어) 전용이에요. 돌봄 망(Tailscale)·돌봄 데몬은 별도 트랙이라 여기 안 섞여요.

## 📱 휴대폰에 1줄 설치 (기존 워크스페이스)

마법 공구상자를 내 휴대폰에도! 아래 한 줄을 복사해서 비밀 방(터미널)에 붙여넣으세요:

```bash
curl -sL https://raw.github.com/helena751107/helena_phone/main/g/install.sh | bash
```

---

> © 2026 Helena Park — 말로만 · 폰 하나로 · 누나를 위해.
> 구형 갤럭시 S21 한 대 + $20으로, 비밀 방(Termux + proot)에서 로봇 친구들과 함께.
> 모든 계정은 누나 명의예요. 언젠가 바통 터치(handoff) — 모든 걸 누나에게.

# 🤖 Grok CLI — Termux + proot Ubuntu 설치 완료

> 설치: 2026-07-25 | 버전: 0.2.112 | 아키텍처: linux-aarch64

---

## 1. 설치 한 방

```bash
# proot Ubuntu 안에서
curl -fsSL https://x.ai/cli/install.sh | bash
export PATH="$HOME/.grok/bin:$PATH"
```

결과: `/root/.grok/bin/grok` + `/root/.grok/bin/agent` (심링크)

---

## 2. 로그인

```bash
grok login --device-auth
# → 폰 브라우저에서 URL 열고 코드 입력
# → 완료 후 ~/.grok/auth.json 에 토큰 저장
```

---

## 3. 기본 사용법

```bash
# 대화
grok "질문"

# 이전 세션 이어가기
grok -c

# 에이전트 모드
grok --agent "코드 리뷰어"

# 서브에이전트 JSON 정의
grok --agents '{"reviewer": "코드 리뷰 전문가"}'

# 워크트리 모드
grok --worktree=feat "이 기능 만들어줘"
```

---

## 4. 우리 스택과의 통합

### Grok CLI vs grok_api.py

| | Grok CLI | grok_api.py |
|---|---------|------------|
| 설치 | curl | bash | Python 스크립트 |
| 인증 | Device Auth (구독) | OAuth or API Key |
| 대화 | ✅ TUI | ✅ API 호출 |
| 에이전트 | ✅ 내장 | ❌ |
| 자동화 | ⚠️ 사람 상호작용 | ✅ 스크립트 가능 |
| 네이버 파싱 | ⚠️ 간접 | ✅ curl 직접 |
| 이미지 생성 | ✅ (SuperGrok) | ❌ (API만) |

### 용도 분리

```
grok CLI → 대화·탐색·에이전트 (사람 상호작용)
grok_api.py → 자동화·파싱·파이프라인 (스크립트)
```

---

## 5. Grok CLI + Claude Code 협업

```bash
# 1. Claude Code가 원고 초안 작성 → TG 배달
# 2. 사람이 Naver 발행 → 링크 확보
# 3. Grok CLI로 이미지/클립 생성
grok "이 네이버 글 읽고 표지 이미지 설명 만들어줘: https://m.blog.naver.com/..."

# 4. 또는 grok_api.py로 자동화
python3 scripts/grok_api.py parse "https://m.blog.naver.com/..."
```

---

## 6. grok + agent 명령어

```bash
# grok: 메인 TUI
grok --help

# agent: 헤드리스 에이전트 실행
agent --help
agent --model grok-4-1-fast "이 레포 분석해줘" --cwd /root/work
```

---

## 7. PATH 영구 등록

`.bashrc`에 자동 추가됨:
```bash
export PATH="$HOME/.grok/bin:$PATH"
```

---

> Grok CLI는 Claude Code와 동일한 레벨의 TUI 도구다.
> Claude Code = 코드·문서·자동화 (DeepSeek)
> Grok CLI  = 시각·네이버·에이전트 (SuperGrok 구독)
> 둘 다 폰에서 돌아간다.

---

## 8. ⚠️ 헤드리스/스크립트 실행 — TTY 필요 (ENXIO 오진 주의 · 2026-08-18)

태블릿(Tab S9) 설치 때 실제로 겪은 함정. 요약:

- **증상:** 헤드리스 셸(에이전트의 Bash 도구처럼 TTY 없는 곳)에서 `grok "안녕"` 실행 → `No such device or address`(ENXIO).
- **정체(진짜 원인):** grok은 **"Build TUI"** 라 실행 시 `/dev/tty`(터미널)를 열어야 함. TTY 없는 셸에선 이 open()이 ENXIO로 실패. **설치·네트워크 문제가 아님.**
- **오진 기록:** IPv6 우선(`/etc/gai.conf`) · IPv4 하드코딩(`/etc/hosts`)으로 파고들었으나 전부 헛다리 → **원상복구 완료**.
  - 참고 근거: S21도 IPv6 인터페이스 없음(`/proc/net/if_inet6` 비어있음). `curl -4 https://api.x.ai/` 는 정상 응답(HTTP 421) → **IPv4는 처음부터 살아있었음.** IPv6 가설은 빗나갔던 것.
- **올바른 사용:**
  - **대화형(태블릿 Termux):** 그냥 `grok` 치면 됨 (TTY 있음).
  - **헤드리스/스크립트:** pty 래퍼로 감싸기 — `script -qec 'grok "..."' /dev/null` (agent 명령도 같은 바이너리라 동일).

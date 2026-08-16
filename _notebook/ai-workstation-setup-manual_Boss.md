---
date: 2026-08-12
agent: Boss (음성입력·에이전트 공동) — 폰 하나로 AI 워크스테이션 설치 매뉴얼
mark: _Boss
type: manual
status: active
note: /sdcard/Download 로컬 복사본에서 S21 레포로 이관 (2026-08-16)
---
# 백서: 폰 하나로 AI 워크스테이션 짓기 (완결판)
### Termux → proot Ubuntu → Claude Code + DeepSeek — 처음부터 끝까지, 에러 없는 순서

> 이 문서는 여러 대의 폰(S21, 호야당 아저씨, 친구)에 실제로 설치하면서
> 나온 사고들을 전부 반영해 고친 최종 버전이다. 앞으로는 이 순서 그대로
> 가면 오늘 겪은 에러들을 하나도 다시 안 만난다.

---

## 준비물 — 미리 발급받아둘 것

| 변수 | 어디서 | 필수 여부 |
|---|---|---|
| DeepSeek API 키 | platform.deepseek.com → API Keys | 필수 |
| GitHub 아이디 + 개인 액세스 토큰(ghp_...) | github.com → Settings → Developer settings (repo 권한) | 필수 |
| 텔레그램 봇 토큰 | 텔레그램 `@BotFather` → `/newbot` | 선택 |

**원칙 하나만 기억해라: 어떤 스크립트도 토큰을 채팅에 적으라고 요구하지
않는다.** 전부 `read`로 그 자리에서 직접 입력받는다.

---

## 1단계 — 우분투 설치 (겉, Termux `~ $`)

```bash
pkg update -y && pkg upgrade -y
pkg install -y proot-distro
proot-distro install ubuntu
proot-distro login ubuntu
```
✅ 프롬프트가 `root@localhost:~#`로 바뀌면 통과.

> ⚠️ `proot-distro install ubuntu`를 실수로 두 번 치면 "container
> already exists" 뜬다 — 에러 아니다, 그냥 `proot-distro login ubuntu`로
> 바로 넘어가면 된다.

## 2단계 — 기본 도구 + Claude Code (속, `root@`)

```bash
apt update && apt install -y curl git nano nodejs npm python3 python3-venv
npm install -g @anthropic-ai/claude-code
claude --version
```
✅ 버전 번호(`2.x.x`) 찍히면 통과.

## 3단계 — DeepSeek 엔진 배선 (대화형)

```bash
read -p "DeepSeek API 키 입력: " DEEPSEEK_API_KEY
cat >> ~/.bashrc << EOF
export DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=\$DEEPSEEK_API_KEY
export ANTHROPIC_MODEL=deepseek-v4-pro
EOF
grep -E 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.bashrc >> ~/.profile
source ~/.bashrc
echo $ANTHROPIC_BASE_URL
```
✅ `https://api.deepseek.com/anthropic` 출력되면 통과.

> 모델명은 `deepseek-v4-pro` 고정. `deepseek-chat`은 2026년 7월 24일부로
> 완전히 폐기된 이름이라 절대 쓰지 않는다.

## 4단계 — 과금 안전장치 (⚠️ 여기서 건너뛰지 말 것)

이 단계를 빼먹으면 나중에 잔액이 며칠 만에 증발할 수 있다 — Claude
Code가 매 요청마다 랜덤 식별값을 헤더에 박아 넣는데, 이게 DeepSeek의
캐시 프리픽스를 매번 깨뜨려서 정상가의 최대 50배로 과금되는 알려진
문제가 있다. 미리 막는다.

```bash
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ENABLE_TOOL_SEARCH": "true",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro"
  }
}
EOF

python3 -c "
import json, os
p = os.path.expanduser('~/.claude.json')
try:
    with open(p) as f: d = json.load(f)
except FileNotFoundError:
    d = {}
d['hasCompletedOnboarding'] = True
d['primaryApiKey'] = os.environ.get('DEEPSEEK_API_KEY','')
with open(p,'w') as f: json.dump(d, f, indent=2)
print('patched:', p)
"
```
✅ `patched: /root/.claude.json` 출력되면 통과.

## 5단계 — 발사 테스트

```bash
mkdir -p ~/work && cd ~/work
IS_SANDBOX=1 claude --dangerously-skip-permissions
```
동의화면 뜨면 화살표로 **`2. Yes, I accept`** 선택 → 엔터.

✅ 로그인 요구 없이 바로 메인 화면 뜨고, 배너에 `deepseek-v4-pro`
표시되면 통과. `hey`처럼 아무 말이나 쳐서 응답+`Cost` 표시까지 나오면
완전 확인.

## 6단계 — 두 글자 진입로 (⚠️ 반드시 겉으로 나온 뒤)

```bash
exit
```
Claude Code 안이면 `/exit`로 먼저 나오고, 그 다음 셸에서 `exit` 한 번
**더** — **프롬프트가 `~ $`인지 반드시 확인.** (`root@` 상태에서 다음
줄을 치면 알리아스가 컨테이너 안에 박혀서 "proot-distro should not be
executed under PRoot" 에러가 난다 — 오늘 두 번 겪었던 사고다.)

```bash
echo "alias cc='proot-distro login ubuntu -- bash -lc \"cd ~/work && IS_SANDBOX=1 claude --dangerously-skip-permissions\"'" >> ~/.bashrc
source ~/.bashrc
cc
```
✅ 겉(`~ $`)에서 `cc` 두 글자로 바로 Claude Code 뜨면 완료.

## 7단계 — GitHub 연동 (대화형)

```bash
proot-distro login ubuntu

read -p "GitHub 아이디: " GITHUB_USER
read -sp "GitHub 토큰(ghp_...): " GITHUB_TOKEN; echo
read -p "새 레포 이름: " REPO_NAME

git config --global user.name "$GITHUB_USER"
git config --global user.email "$GITHUB_USER@users.noreply.github.com"
git config --global credential.helper store

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos -d "{\"name\":\"$REPO_NAME\"}"

cd ~/work
git init 2>/dev/null
git remote remove origin 2>/dev/null
git remote add origin "https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"
git branch -M main
echo "<!DOCTYPE html><html><body><h1>Workstation Live</h1></body></html>" > index.html
git add -A && git commit -m "init: workstation"
git push -u origin main

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$GITHUB_USER/$REPO_NAME/pages" \
  -d '{"source":{"branch":"main","path":"/"}}'
```
✅ push 성공 + Pages 활성화 응답 오면 통과. 2분 뒤
`https://<아이디>.github.io/<레포>/` 접속 확인.

## 8단계 — 텔레그램 보고 회의실 (선택, 대화형)

텔레그램에서 만든 봇한테 먼저 메시지 1개 보내둘 것(필수 선행 조건).

```bash
read -sp "텔레그램 봇 토큰: " TG_TOKEN; echo
TG_CHAT=$(curl -s "https://api.telegram.org/bot$TG_TOKEN/getUpdates" \
  | grep -o '"chat":{"id":[0-9-]*' | head -1 | grep -o '[0-9-]*$')

echo "export TG_TOKEN=\"$TG_TOKEN\"" >> ~/.bashrc
echo "export TG_CHAT=\"$TG_CHAT\"" >> ~/.bashrc
source ~/.bashrc

cat > ~/work/tg.sh << 'EOF'
#!/bin/bash
curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
  -d chat_id=$TG_CHAT -d text="$1" >/dev/null
EOF
chmod +x ~/work/tg.sh
bash ~/work/tg.sh "🟢 워크스테이션 개통 완료"
```
✅ 텔레그램에 메시지 도착하면 통과.

## 9단계 — 나머지는 에이전트한테 자연어로 위임

폰 하드웨어 제어(MCP), YouTube 연동처럼 절차가 자주 바뀌는 것들은
하드코딩하지 않는다. `cc` 켜고 그냥 말로 시킨다:

```
phone-mcp-server 설치해줘. 순수 Termux:API 기반인지, 루트/Shizuku
필요 없는지 먼저 확인하고 진행해.
```

```
YouTube 채널 연동하고 싶어. 콘솔에서 뭘 눌러야 하는지 순서대로 알려주고,
클라이언트ID/시크릿 받으면 Device Code Flow로 인증까지 진행해줘.
```

## 10단계 — 헌법 씨앗 (마지막)

```
cc 안에서 이렇게 시켜라:
CONSTITUTION.md 만들어줘. 최소 3원칙만:
1) 루팅/Shizuku 금지
2) 토큰은 절대 대화 로그에 하드코딩하지 말 것 — read 프롬프트나
   환경변수 파일에서만 읽을 것
3) 새 세션은 이 문서부터 읽고 시작할 것
```

---

## 오늘 발견된 버그 요약 (참고용)

| 증상 | 원인 | 이 매뉴얼에서 반영된 위치 |
|---|---|---|
| pip/numpy 빌드 에러 | 겉(Termux)에서 pip 직접 설치 시도 | 1~2단계에서 처음부터 우분투 안에서만 설치 |
| `proot-distro should not be executed under PRoot` | 알리아스를 속(root@)에서 등록 | 6단계 경고문으로 명시 |
| `/login` 요구, "Opus 5" 배너 | 서드파티 백엔드 사용 시 온보딩 플래그 미설정 | 4단계 `.claude.json` 패치로 사전 차단 |
| 며칠 만에 잔액 증발 | attribution 헤더가 캐시 프리픽스를 매번 깨뜨림 | 4단계에서 처음부터 차단 |
| `deepseek-chat` 관련 400 에러 | 폐기된 모델명 재사용 | 전 구간 `deepseek-v4-pro`로 고정 |

**39커밋 · 102파일 · 15,874줄짜리 삽질이 이 10단계로 압축됐다. 다음 폰
부터는 이거 하나면 끝난다.**

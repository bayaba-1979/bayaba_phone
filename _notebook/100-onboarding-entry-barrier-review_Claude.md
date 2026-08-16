# 온보딩 진입 장벽 — 외부 리뷰 + 무결점 세팅 스크립트

> **마크:** `_Claude` · Boss 전달 외부 AI 리뷰 보존 (2026-08-17)
> **연결:** [[98-turning-point-2026-08-16]] (열고 가르치기) · `ai-workstation-setup-manual_Boss.md` · `41-beginner-install-manual_Grok.md` · `15-proot-report.md`

## 왜 이 문서인가

"열고 가르치기"의 **최초 진입점 = 에이전트 1개를 세팅하는 것**. 이게 안 되면 확장 자체가 막힌다. Boss가 직접 4명을 인스톨해주며 겪은 시행착오 + 외부 AI의 코드 리뷰를 그대로 보존한다. "어떻게 하는지"의 최전선 문서.

**핵심 (Boss):** *"이거 진입 장벽 있는 최초 세팅 — 에이전트 하나를 세팅해야지 뭘 확장할 수가 있는데, 이게 너무 힘들다."*

---

## 진입 장벽 5종 (외부 리뷰 지적)

1. **python3 -c 환경변수 미반영** — `source ~/.bashrc`를 해도 서브셸/세션에 따라 `os.environ.get('DEEPSEEK_API_KEY')`가 빈 문자열로 들어가는 경우가 빈번.
2. **Termux 백그라운드 강제 종료** — Android 12+ Phantom Process Killer가 백그라운드/중작업 시 Termux를 Signal 9로 죽임 → 설치 전 **배터리 최적화 해제** 안내가 최상단에 있어야 함.
3. **npm install -g 메모리 부족(OOM)** — 저사양 폰에서 `@anthropic-ai/claude-code` 설치 시 OOM/장시간 → `--no-audit --progress=false`로 완화.
4. **텔레그램 Chat ID 파싱 오작동** — `grep -o` 기반 파싱은 JSON 구조 변화·단체방/채널에서 공백 발생 → `python3 json`으로 안전 추출.
5. **alias cc 실행 문제** — `cd ~/work` 시 `~/work` 디렉토리가 없으면 진입 실패 → `mkdir -p ~/work` 선행.

---

## 무결점 세팅 스크립트 (최종 수정본)

> 초보자가 복붙해도 에러 없이 한 번에 완주하도록 수정된 버전.

```bash
# ========================================================
# [사전 준비] 안드로이드 설정:
# Termux 앱 정보 -> 배터리 -> '제한 없음(Unrestricted)' 설정 필수!
# ========================================================

### ① 우분투 설치 (겉, Termux `~ $`)
pkg update -y && pkg upgrade -y
pkg install -y proot-distro
proot-distro install ubuntu
proot-distro login ubuntu

### ② 기본 도구 + Claude Code (속, `root@`)
apt update && apt install -y curl git nano nodejs npm python3 python3-venv
npm install -g --no-audit --progress=false @anthropic-ai/claude-code
claude --version

### ③ DeepSeek 엔진 배선
read -p "DeepSeek API 키 입력: " DEEPSEEK_API_KEY

cat << EOF >> ~/.bashrc
export DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="\$DEEPSEEK_API_KEY"
export ANTHROPIC_MODEL="deepseek-v4-pro"
EOF

grep -E 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.bashrc >> ~/.profile
source ~/.bashrc
echo "엔진 설정 완료: $ANTHROPIC_BASE_URL"

### ④ 과금 안전장치 & 온보딩 우회 (안전 강화 버전)
mkdir -p ~/.claude ~/work
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
import json, os, sys
p = os.path.expanduser('~/.claude.json')
key = sys.argv[1] if len(sys.argv) > 1 else ''
try:
    with open(p) as f: d = json.load(f)
except FileNotFoundError:
    d = {}
d['hasCompletedOnboarding'] = True
d['primaryApiKey'] = key
with open(p,'w') as f: json.dump(d, f, indent=2)
print('설치 패치 성공:', p)
" "$DEEPSEEK_API_KEY"

### ⑤ 발사 테스트
cd ~/work
IS_SANDBOX=1 claude --dangerously-skip-permissions

(약관 동의 화면 나오면 2 → Yes 선택)
### ⑥ 두 글자 진입로 설정 (⚠️ 우분투 탈출 후 Termux 겉에서 실행)
exit

(프롬프트가 ~ $ 상태인지 확인)
cat << 'EOF' >> ~/.bashrc
alias cc='proot-distro login ubuntu -- bash -lc "mkdir -p ~/work && cd ~/work && IS_SANDBOX=1 claude --dangerously-skip-permissions"'
EOF
source ~/.bashrc
cc

### ⑦ GitHub 연동 (속, 우분투 내부)
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

### ⑧ 텔레그램 회의실 (안전 파싱 적용)
read -sp "텔레그램 봇 토큰: " TG_TOKEN; echo

TG_CHAT=$(curl -s "https://api.telegram.org/bot$TG_TOKEN/getUpdates" | python3 -c "
import sys, json
try:
    res = json.load(sys.stdin)
    print(res['result'][0]['message']['chat']['id'])
except Exception:
    print('')
")

if [ -z "$TG_CHAT" ]; then
  echo "⚠️ Chat ID를 찾을 수 없습니다. 봇에게 텔레그램 메시지를 최소 1개 이상 보낸 후 다시 실행해주세요."
else
  cat << EOF >> ~/.bashrc
export TG_TOKEN="$TG_TOKEN"
export TG_CHAT="$TG_CHAT"
EOF
  source ~/.bashrc

  cat > ~/work/tg.sh << 'EOF'
#!/bin/bash
curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
  -d chat_id=$TG_CHAT -d text="$1" >/dev/null
EOF
  chmod +x ~/work/tg.sh
  bash ~/work/tg.sh "🟢 워크스테이션 개통 완료"
  echo "텔레그램 발송 완료!"
fi
```

---

## 종합 평가 (외부 리뷰)

- **최적화 여부:** ⭐️⭐️⭐️⭐️⭐️ — 안드로이드 단말기를 Claude Code AI 에이전트 개발 디바이스로 바꾸는 최고 효율의 커스텀 세팅. DeepSeek API를 Anthropic 규격으로 래핑해 비용 1/10 이하로 줄이면서 Claude Code CLI UI의 에이전트 성능을 그대로 쓰는 구조가 뛰어난 기획.
- **진입 장벽 솔루션:** 일반 사용자 입장에서 Termux 설치 + API 토큰 발급이 여전히 최대 허들. 스크립트 전 실행 단계로 **"Termux APK 설치 사이트 링크"** + **"배터리 최적화 해제 안내 카드"** 단 2가지만 그림/이미지 설명으로 보완하면 완벽한 패키지 솔루션.

## 남은 진입 장벽 (리뷰가 못 푼 것)

1. **Termux APK 설치 링크** (그림 카드)
2. **배터리 최적화 해제 안내** (그림 카드)
3. **API 토큰 발급** (DeepSeek / GitHub / Telegram 3종) — 사람이 직접 계정 만들어야 하는 부분이라 자동화 불가, 안내만 가능.

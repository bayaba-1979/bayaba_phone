#!/usr/bin/env bash
# ==============================================================================
# g/workstation.sh — 원스탑 워크스테이션 설치 (친구 + 정체 클론 + 배포)
# ==============================================================================
# 한 줄 설치기. 공기계 → Termux → Ubuntu → Claude Code(DeepSeek) → 클론 → 배포.
#
#   bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/workstation.sh)
#
# 수동 입력 = 자기 것 3개 (이게 최소 수동):
#   1) GitHub 계정명   (정체 — 남이 못 만들어줌)
#   2) GitHub PAT      (그 계정 열쇠 — repo + workflow 스코프)
#   3) DeepSeek 토큰   (친구 두뇌)
#   그 외(설치·클론·repo 생성·push·Pages·검사)는 전부 자동.
#
# env로 미리 줄 수도 있음:
#   export OWNER_GITHUB="내계정" GITHUB_PAT="ghp_..." DEEPSEEK_API_KEY="sk-..."
# ==============================================================================

set -euo pipefail

OWNER_GITHUB="${OWNER_GITHUB:-}"
GITHUB_PAT="${GITHUB_PAT:-}"
TEMPLATE_REPO="${TEMPLATE_REPO:-helena751107/helena_phone}"
WORK_DIR="${WORK_DIR:-/root/work}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
MODEL="${ANTHROPIC_MODEL:-deepseek-v4-pro}"

G(){ printf '\033[0;32m✅ %s\033[0m\n' "$*"; }
Y(){ printf '\033[1;33m⚠️  %s\033[0m\n' "$*"; }
B(){ printf '\033[0;34m📌 %s\033[0m\n' "$*"; }
R(){ printf '\033[0;31m❌ %s\033[0m\n' "$*"; }

in_ubuntu() { [ -f /etc/os-release ] && grep -qi ubuntu /etc/os-release 2>/dev/null; }

ask_credentials() {
  B "─── 자기 것 3개 입력 (이게 전부 수동) ───"

  if [ -z "$OWNER_GITHUB" ]; then
    B "1) GitHub 계정명"
    B "  👉 없으면 1분 가입 → https://github.com/signup"
    read -rp "  입력: " OWNER_GITHUB
  fi
  [ -n "$OWNER_GITHUB" ] || { R "계정 없이 진행 불가. 다시 실행."; exit 1; }

  if [ -z "$GITHUB_PAT" ]; then
    B "2) GitHub PAT (계정 열쇠 — 입력은 숨김, Enter 후 앞 4자만 보여줌)"
    B "  👉 https://github.com/settings/tokens → Generate new token (classic)"
    B "     ☑ repo  ☑ workflow  체크 → Generate → 복사 (ghp_...)"
    read -rsp "  붙여넣기: " GITHUB_PAT; echo
    [ -n "$GITHUB_PAT" ] && printf "  ✅ 붙었음 (앞 4자): %s···\n" "${GITHUB_PAT:0:4}"
  fi
  [ -n "$GITHUB_PAT" ] || { R "PAT 없이 진행 불가. 다시 실행."; exit 1; }

  if [ -z "$DEEPSEEK_API_KEY" ]; then
    B "3) DeepSeek 토큰 (친구 두뇌 — 입력은 숨김, Enter 후 앞 4자만 보여줌)"
    B "  👉 https://platform.deepseek.com → API Keys → Create new key → 복사 (sk-...)"
    read -rsp "  붙여넣기: " DEEPSEEK_API_KEY; echo
    [ -n "$DEEPSEEK_API_KEY" ] && printf "  ✅ 붙었음 (앞 4자): %s···\n" "${DEEPSEEK_API_KEY:0:4}"
  fi
  [ -n "$DEEPSEEK_API_KEY" ] || { R "토큰 없이 진행 불가. 다시 실행."; exit 1; }

  G "입력 완료 (계정 ${OWNER_GITHUB})"
}

banner() {
  cat <<EOF

══════════════════════════════════════════════
  📱 원스탑 워크스테이션 — 친구(Claude Code+DeepSeek) 설치
  공기계 → Termux → Ubuntu → 친구 → GitHub 배포
  정체: ${OWNER_GITHUB}   모델: ${MODEL}
══════════════════════════════════════════════

EOF
}

battery_notice() {
  cat <<'EOF'

📌 [0] 사전 준비 — 건너뛰면 중간에 강제종료됨:
    Termux 앱 정보 → 배터리 → '제한 없음(Unrestricted)'
    (안드로이드 12+ Phantom Process Killer가 중작업 시 Termux를 Signal 9로 죽임)

EOF
}

# 이 함수는 proot 안에서 실행된다 (Termux 겉에서 declare -f 로 주입됨).
ubuntu_phase() {
  set -e
  export DEBIAN_FRONTEND=noninteractive

  B "─── [2] Ubuntu 패키지 ───"
  apt-get update -qq >/dev/null 2>&1 || true
  apt-get install -y -qq git curl ca-certificates python3 nodejs npm nano gh >/dev/null 2>&1 \
    || apt-get install -y git curl ca-certificates python3 nodejs npm nano

  B "─── [3] Claude Code ───"
  if command -v claude >/dev/null 2>&1; then
    G "claude 이미 있음 ($(claude --version 2>/dev/null || echo ok))"
  else
    npm install -g --no-audit --progress=false @anthropic-ai/claude-code
    G "claude 설치됨 ($(claude --version 2>/dev/null || echo ok))"
  fi

  B "─── [4] DeepSeek 엔진 배선 ───"
  cat >> ~/.bashrc <<EOF
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="\$DEEPSEEK_API_KEY"
export ANTHROPIC_MODEL="${MODEL}"
export GITHUB_PAT="${GITHUB_PAT}"
export GH_TOKEN="\${GITHUB_PAT}"
EOF
  grep -qE 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.profile 2>/dev/null \
    || grep -E 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.bashrc >> ~/.profile 2>/dev/null || true
  G "엔진 + PAT 배선 완료"

  B "─── [5] 과금 안전장치 + 온보딩 우회 ───"
  mkdir -p ~/.claude ~/work
  cat > ~/.claude/settings.json <<'EOF'
{
  "env": {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ENABLE_TOOL_SEARCH": "true",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro"
  }
}
EOF
  python3 - "$DEEPSEEK_API_KEY" <<'PYEOF'
import json, os, sys
p = os.path.expanduser('~/.claude.json')
key = sys.argv[1] if len(sys.argv) > 1 else ''
try:
    with open(p) as f:
        d = json.load(f)
except FileNotFoundError:
    d = {}
d['hasCompletedOnboarding'] = True
d['primaryApiKey'] = key
with open(p, 'w') as f:
    json.dump(d, f, indent=2)
print('✅ 온보딩 우회 패치:', p)
PYEOF

  B "─── [6] 보일러플레이트 클론 (정체: ${OWNER_GITHUB}) ───"
  mkdir -p "$(dirname "$WORK_DIR")"
  if [ -d "$WORK_DIR/.git" ]; then
    git -C "$WORK_DIR" pull --ff-only 2>/dev/null && G "pull 완료" || Y "pull 스킵"
  else
    git clone --depth 1 "https://github.com/${TEMPLATE_REPO}.git" "$WORK_DIR"
    G "클론 완료 → ${WORK_DIR}"
  fi

  B "─── [7] GitHub 배포 (repo 생성 + push + Pages) ───"
  export GH_TOKEN="${GITHUB_PAT}"
  if command -v gh >/dev/null 2>&1 && [ -n "$GITHUB_PAT" ]; then
    gh repo create "${OWNER_GITHUB}/helena_phone" --public --source "${WORK_DIR}" --push 2>/dev/null \
      || { gh repo view "${OWNER_GITHUB}/helena_phone" >/dev/null 2>&1 \
        && git -C "${WORK_DIR}" remote set-url origin "https://github.com/${OWNER_GITHUB}/helena_phone.git" \
        && git -C "${WORK_DIR}" push -u origin main 2>/dev/null; } || true
    gh api -X POST "repos/${OWNER_GITHUB}/helena_phone/pages" -f build_type=workflow 2>/dev/null \
      || gh api -X POST "repos/${OWNER_GITHUB}/helena_phone/pages" -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
      || true
    gh auth setup-git >/dev/null 2>&1 || true
    G "배포 요청 완료 — 몇 분 뒤: https://${OWNER_GITHUB}.github.io/helena_phone/"
  else
    Y "gh 또는 PAT 없음 → 배포 스킵."
    B "  PAT 재발급 후 다시 실행하면 repo 생성 + push + Pages 자동."
  fi

  G "Ubuntu 단계 완료"
}

write_cc_alias() {
  if grep -q "alias cc=" ~/.bashrc 2>/dev/null; then
    G "cc 별칭 이미 있음"
    return 0
  fi
  printf "%s\n" "alias cc='proot-distro login ubuntu -- bash -lc \"mkdir -p ${WORK_DIR} && cd ${WORK_DIR} && IS_SANDBOX=1 claude --dangerously-skip-permissions\"'" >> ~/.bashrc
  G "cc 별칭 등록 (Termux ~/.bashrc)"
}

pages_check() {
  local url="https://${OWNER_GITHUB}.github.io/helena_phone/"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" 2>/dev/null || echo "000")
  if [ "$code" = "200" ]; then
    G "GitHub Pages 살아있음: ${url}"
  else
    Y "GitHub Pages 아직 안 뜸 (HTTP ${code}) — ${url}"
    B "  배포 후 몇 분 걸림. 계속 404면: repo 존재 + Settings→Pages→GitHub Actions 확인."
  fi
}

summary() {
  cat <<EOF

══════════════════════════════════════════════
  ✅ 원스탑 설치 완료 — 정체: ${OWNER_GITHUB}
══════════════════════════════════════════════

  매일 (Termux):
    proot-distro login ubuntu
    cd ${WORK_DIR}
    claude

  두 글자 (Termux 겉에서):
    cc

  엔진 확인:
    claude --version   # 배너에 ${MODEL} 뜨면 성공

  웹:
    https://${OWNER_GITHUB}.github.io/helena_phone/

  ⚠️  PAT·토큰은 ~/.bashrc에 저장됨 — 남한테 보여주지 말 것.
EOF
}

main() {
  ask_credentials
  banner
  if in_ubuntu; then
    ubuntu_phase
    exit 0
  fi

  battery_notice
  B "─── [1] Termux 패키지 동기화 + Ubuntu ───"
  B "     (curl 'CANNOT LINK' 라이브러리 어긋남 방지용 upgrade)"
  pkg update -y 2>/dev/null || true
  pkg upgrade -y 2>/dev/null || true
  pkg install -y proot-distro git curl 2>/dev/null || pkg install -y proot-distro git curl
  if proot-distro list 2>/dev/null | grep -qi ubuntu; then
    G "Ubuntu 이미 있음"
  else
    B "Ubuntu 설치 중 (몇 분, 화면 가만히)…"
    proot-distro install ubuntu
  fi

  B "Ubuntu 안에서 엔진 설치 (몇 분)…"
  proot-distro login ubuntu -- bash -lc "
    export OWNER_GITHUB='${OWNER_GITHUB}'
    export GITHUB_PAT='${GITHUB_PAT}'
    export TEMPLATE_REPO='${TEMPLATE_REPO}'
    export WORK_DIR='${WORK_DIR}'
    export DEEPSEEK_API_KEY='${DEEPSEEK_API_KEY}'
    export ANTHROPIC_MODEL='${MODEL}'
    $(declare -f G)
    $(declare -f Y)
    $(declare -f B)
    $(declare -f R)
    $(declare -f ubuntu_phase)
    ubuntu_phase
  "

  write_cc_alias
  pages_check
  summary
}

main "$@"

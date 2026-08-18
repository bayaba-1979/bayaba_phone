#!/usr/bin/env bash
# ==============================================================================
# g/workstation.sh — 원스탑 워크스테이션 설치 (엔진 + 정체 클론)
# ==============================================================================
# Boss의 "새 폰 최종판 8블록"(실사용 4회 검증) + install.sh의 정체 클론을 합친
# 한 줄 설치기. 공기계 → Termux → Ubuntu → Claude Code(DeepSeek) → 클론.
#
# 한 줄 (Termux 겉 ~ $):
#   bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/workstation.sh)
#
# 정체(내 GitHub 계정)는 필수 — 안 넣으면 실행 중에 물어봄. 고정값 금지(교재).
#   export OWNER_GITHUB="내계정"    # 각자 자기 계정 (예: 태블릿 노드 = thomas.tj.park)
#   bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/workstation.sh)
#
# 준비물: 내 GitHub 계정(정체) · DeepSeek 키(없으면 read로 그 자리 입력)
# 사전 조치: Termux 앱 정보 → 배터리 → '제한 없음' (안드로이드 12+ 강제종료 방지)
# ==============================================================================

set -euo pipefail

OWNER_GITHUB="${OWNER_GITHUB:-}"                          # 정체(내 계정) — 고정값 금지. 각자 자기 계정을 넣는다.
TEMPLATE_REPO="${TEMPLATE_REPO:-helena751107/helena_phone}"  # 교재 원본(소스). 덮어쓰기 가능.
WORK_DIR="${WORK_DIR:-/root/work}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
MODEL="${ANTHROPIC_MODEL:-deepseek-v4-pro}"

G(){ printf '\033[0;32m✅ %s\033[0m\n' "$*"; }
Y(){ printf '\033[1;33m⚠️  %s\033[0m\n' "$*"; }
B(){ printf '\033[0;34m📌 %s\033[0m\n' "$*"; }
R(){ printf '\033[0;31m❌ %s\033[0m\n' "$*"; }

in_ubuntu() { [ -f /etc/os-release ] && grep -qi ubuntu /etc/os-release 2>/dev/null; }

# 정체(계정)는 필수 변수. 고정값 금지 — 교재는 각자 자기 계정으로 깐다.
ask_identity() {
  if [ -z "$OWNER_GITHUB" ]; then
    B "GitHub 계정 — 없으면 1분이면 만들어 (무료):"
    B "  👉 https://github.com/signup → 계정 생성 → 계정명 기억"
    read -rp "  내 GitHub 계정명 입력: " OWNER_GITHUB
  fi
  if [ -z "$OWNER_GITHUB" ]; then
    R "계정 없이 진행 불가. export OWNER_GITHUB=내계정 후 다시 실행."
    exit 1
  fi
  G "정체(계정): ${OWNER_GITHUB}"
}

banner() {
  cat <<EOF

══════════════════════════════════════════════
  📱 원스탑 워크스테이션 — 엔진 + 정체 클론
  공기계 → Termux → Ubuntu → Claude Code(DeepSeek)
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

  B "─── [3] Claude Code (--no-audit --progress=false) ───"
  if command -v claude >/dev/null 2>&1; then
    G "claude 이미 있음 ($(claude --version 2>/dev/null || echo ok))"
  else
    npm install -g --no-audit --progress=false @anthropic-ai/claude-code
    G "claude 설치됨 ($(claude --version 2>/dev/null || echo ok))"
  fi

  B "─── [4] DeepSeek 엔진 배선 ───"
  if [ -z "$DEEPSEEK_API_KEY" ]; then
    B "DeepSeek API 키 발급 (1분):"
    B "  👉 https://platform.deepseek.com → API Keys → Create new key → 복사"
    read -rp "  DeepSeek API 키 붙여넣기: " DEEPSEEK_API_KEY
  fi
  cat >> ~/.bashrc <<EOF
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="\$DEEPSEEK_API_KEY"
export ANTHROPIC_MODEL="${MODEL}"
EOF
  grep -qE 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.profile 2>/dev/null \
    || grep -E 'DEEPSEEK_API_KEY|ANTHROPIC_' ~/.bashrc >> ~/.profile 2>/dev/null || true
  G "엔진 배선 완료"

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
  # 키를 sys.argv로 직접 넘긴다 (환경변수 미반영 방지)
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
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo create "${OWNER_GITHUB}/helena_phone" --public --source "${WORK_DIR}" --push 2>/dev/null \
      || { gh repo view "${OWNER_GITHUB}/helena_phone" >/dev/null 2>&1 \
        && git -C "${WORK_DIR}" remote set-url origin "https://github.com/${OWNER_GITHUB}/helena_phone.git" \
        && git -C "${WORK_DIR}" push -u origin main 2>/dev/null; } || true
    gh api -X POST "repos/${OWNER_GITHUB}/helena_phone/pages" -f build_type=workflow 2>/dev/null \
      || gh api -X POST "repos/${OWNER_GITHUB}/helena_phone/pages" -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
      || true
    G "배포 요청 완료 — 몇 분 뒤: https://${OWNER_GITHUB}.github.io/helena_phone/"
  else
    Y "gh 로그인 안 됨 → GitHub 자동 배포 스킵."
    B "  한 번만: 'gh auth login' 후 다시 실행하면 repo 생성+push+Pages 자동."
    B "  수동: 1) github.com/new 로 helena_phone 생성  2) push  3) Settings→Pages→GitHub Actions"
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
EOF
}

main() {
  ask_identity
  banner
  if in_ubuntu; then
    ubuntu_phase
    exit 0
  fi

  battery_notice
  B "─── [1] Termux 패키지 + Ubuntu ───"
  pkg update -y 2>/dev/null || true
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
    export TEMPLATE_REPO='${TEMPLATE_REPO}'
    export WORK_DIR='${WORK_DIR}'
    export DEEPSEEK_API_KEY='${DEEPSEEK_API_KEY}'
    export ANTHROPIC_MODEL='${MODEL}'
    $(declare -f ubuntu_phase)
    ubuntu_phase
  "

  write_cc_alias
  pages_check
  summary
}

main "$@"

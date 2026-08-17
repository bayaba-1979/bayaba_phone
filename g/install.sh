#!/usr/bin/env bash
# ==============================================================================
# g/install.sh — S21 Phone one-line installer v3 (owner-named · parameterized · beginner-friendly)
# ==============================================================================
# Agent-mark doc: _notebook/41-beginner-install-manual_Grok.md
#
# One-liner (template clone · read-first):
#   bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/install.sh)
#
# Recommended (run with variables · works on the owner's phone / Boss's work phone):
#   export OWNER_GITHUB="helena751107"          # ownership (owner) account
#   export WORK_GITHUB="your-work-account"      # the work account that actually pushes (optional)
#   export GITHUB_TOKEN="ghp_...."              # WORK or OWNER token
#   export GITHUB_REPO="helena_phone"           # workspace repo name
#   export DEEPSEEK_API_KEY="sk-...."           # optional
#   export TG_TOKEN="..." TG_CHAT="..."         # optional
#   bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/install.sh)
#
# Philosophy: every public surface is owned by OWNER. Boss hands off via collab / visit-install.
# ==============================================================================

set -euo pipefail

# ── Ecosystem variables (override via env vars) ──────────────────────────────
OWNER_GITHUB="${OWNER_GITHUB:-}"                       # 정체(내 계정) — 고정값 금지(교재)
OWNER_NAME="${OWNER_NAME:-Owner}"                      # display name
WORK_GITHUB="${WORK_GITHUB:-${GITHUB_USER:-}}"         # work push account (empty = OWNER)
GITHUB_USER="${GITHUB_USER:-${WORK_GITHUB:-$OWNER_GITHUB}}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_REPO="${GITHUB_REPO:-helena_phone}"
TEMPLATE_REPO="${TEMPLATE_REPO:-helena751107/helena_phone}"
WORK_DIR="${WORK_DIR:-/root/work}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
TG_TOKEN="${TG_TOKEN:-}"
TG_CHAT="${TG_CHAT:-}"
INSTALL_GROK="${INSTALL_GROK:-0}"                      # if 1, only guide grok (manual login)
SKIP_CLAUDE="${SKIP_CLAUDE:-0}"
SKIP_MCP="${SKIP_MCP:-0}"
CLONE_SATELLITES="${CLONE_SATELLITES:-0}"               # if 1, guide the 4 satellite repos
SPAWN_ECOSYSTEM="${SPAWN_ECOSYSTEM:-0}"                 # if 1, create satellites + wire secrets via g/spawn.sh

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${BLUE}📌${NC} $*"; }

banner() {
  echo ""
  echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  📱 S21 Phone — one-line installer v3${NC}"
  echo -e "${BOLD}  old phone → Termux → Ubuntu → workspace${NC}"
  echo -e "${BOLD}  OWNER=${OWNER_GITHUB}  USER=${GITHUB_USER}${NC}"
  echo -e "${BOLD}  cost: \$0 runtime | prep: phone + WiFi + GitHub${NC}"
  echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
  echo ""
}

check_vars() {
  echo "─── Step 0: variables ───"
  info "OWNER_GITHUB (ownership)=${OWNER_GITHUB}"
  info "GITHUB_USER (work)=${GITHUB_USER}"
  info "GITHUB_REPO=${GITHUB_REPO}"
  info "TEMPLATE_REPO=${TEMPLATE_REPO}"
  info "WORK_DIR=${WORK_DIR}"

  if [ -z "$OWNER_GITHUB" ]; then
    echo -n "  내 GitHub 계정(정체/소유): "
    read -r OWNER_GITHUB
  fi
  [ -z "$OWNER_GITHUB" ] && { fail "OWNER_GITHUB 필요 (정체 계정)"; exit 1; }

  GITHUB_USER="${GITHUB_USER:-$OWNER_GITHUB}"
  if [ -z "$GITHUB_USER" ]; then
    echo -n "  Work GitHub username: "
    read -r GITHUB_USER
  fi
  ok "Work account: ${GITHUB_USER}"

  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    ok "gh authenticated — push uses gh auth credentials (no PAT in URL/files)"
  else
    warn "gh not authenticated — clone works, push later (recommended: gh auth login)"
  fi

  [ -n "$DEEPSEEK_API_KEY" ] && ok "DeepSeek key present" || warn "DEEPSEEK_API_KEY missing (needed to run cc)"
  [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ] && ok "Telegram configured" || warn "TG is optional"
}

check_env() {
  echo ""
  echo "─── Step 1: environment check ───"
  # Termux often reports Android; some builds differ
  if [ "$(uname -o 2>/dev/null)" != "Android" ] && [ -z "${TERMUX_VERSION:-}" ] && [ ! -d /data/data/com.termux ]; then
    fail "Run inside Android/Termux (F-Droid Termux recommended)"
    exit 1
  fi
  ok "Android/Termux environment"

  if [ -z "${TERMUX_VERSION:-}" ]; then
    warn "TERMUX_VERSION empty — make sure you're inside the Termux app"
  else
    ok "Termux ${TERMUX_VERSION}"
  fi

  local free_mb
  free_mb=$(df /data 2>/dev/null | awk 'NR==2{print int($4/1024)}' || echo 0)
  if [ "$free_mb" -gt 0 ] && [ "$free_mb" -lt 5120 ]; then
    warn "Storage ${free_mb}MB (5GB recommended)"
  else
    ok "Storage checked (${free_mb}MB)"
  fi

  if ping -c1 -W3 8.8.8.8 >/dev/null 2>&1 || ping -c1 -W3 github.com >/dev/null 2>&1; then
    ok "Internet connected"
  else
    fail "Internet required"; exit 1
  fi
}

install_pkgs() {
  echo ""
  echo "─── Step 2: Termux packages ───"
  if command -v pkg >/dev/null 2>&1; then
    pkg update -y >/dev/null 2>&1 && ok "pkg update" || warn "pkg update warning"
    for p in proot-distro git curl; do
      if command -v "$p" >/dev/null 2>&1; then ok "$p"
      else info "$p install..."; pkg install -y "$p" >/dev/null 2>&1 && ok "$p" || warn "$p failed"
      fi
    done
    pkg install -y termux-api >/dev/null 2>&1 && ok "termux-api" || warn "termux-api (install the app too, recommended)"
  else
    warn "no pkg — you may be inside proot or on a PC"
  fi
}

install_proot() {
  echo ""
  echo "─── Step 3: proot Ubuntu ───"
  if ! command -v proot-distro >/dev/null 2>&1; then
    warn "no proot-distro — in Termux run pkg install proot-distro"
    return 0
  fi
  if proot-distro list 2>/dev/null | grep -qi ubuntu; then
    ok "proot Ubuntu already present"
  else
    info "installing ubuntu (a few minutes)..."
    proot-distro install ubuntu && ok "Ubuntu installed" || { fail "Ubuntu install failed"; exit 1; }
  fi
}

# The real work happens inside proot. On the Termux host, guide a re-run after login.
in_proot() {
  # rough: not android path for home
  [ -f /etc/os-release ] && grep -qi ubuntu /etc/os-release 2>/dev/null
}

setup_repo() {
  echo ""
  echo "─── Step 4: clone workspace ───"
  mkdir -p "$(dirname "$WORK_DIR")"

  if [ -d "$WORK_DIR/.git" ]; then
    ok "Already present: $WORK_DIR"
    git -C "$WORK_DIR" pull --ff-only 2>/dev/null && ok "git pull" || warn "pull skipped"
  else
    local url="https://github.com/${TEMPLATE_REPO}.git"
    info "clone ${TEMPLATE_REPO} → ${WORK_DIR}"
    # Do not put the token in the URL (prevents plaintext leak in .git/config).
    # For a private repo, use gh repo clone after gh auth login.
    git clone "$url" "$WORK_DIR" && ok "clone complete" || { fail "clone failed"; exit 1; }
  fi

  # remote: when pointing at the work account's fork/same repo (no token in URL)
  if [ -n "$GITHUB_USER" ]; then
    git -C "$WORK_DIR" remote set-url origin \
      "https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git" 2>/dev/null \
      && ok "origin → ${GITHUB_USER}/${GITHUB_REPO} (push via gh auth)" \
      || warn "keeping remote (template origin)"
  fi

  # Write the env snippet (no token in the file)
  mkdir -p "$WORK_DIR/configs"
  cat > "$WORK_DIR/configs/helena-env.example.sh" << EOF
# Copy: cp configs/helena-env.example.sh configs/helena-env.sh && nano configs/helena-env.sh
# source configs/helena-env.sh
export OWNER_GITHUB="${OWNER_GITHUB}"
export OWNER_NAME="${OWNER_NAME}"
export WORK_GITHUB="${GITHUB_USER}"
export GITHUB_USER="${GITHUB_USER}"
export GITHUB_REPO="${GITHUB_REPO}"
export TEMPLATE_REPO="${TEMPLATE_REPO}"
export WORK_DIR="${WORK_DIR}"
# export GITHUB_TOKEN="ghp_..."          # prefer a session export over putting it in a file
# export DEEPSEEK_API_KEY="sk-..."
# export TG_TOKEN="..." TG_CHAT="..."
EOF
  ok "configs/helena-env.example.sh written"

  # Persist secrets (.secrets.env) into proot shell env vars
  # source the .secrets.env made by navigator.sh into ~/.bashrc, so
  # new shells can read TG_TOKEN/TISTORY/YT as env vars (for tg.sh etc.).
  # (proot env var = SSOT — secrets never go to GitHub, only to on-phone env)
  if [ -f "$WORK_DIR/.secrets.env" ]; then
    if [ -f "$HOME/.bashrc" ]; then
      grep -q "\.secrets\.env" "$HOME/.bashrc" 2>/dev/null \
        || echo "source ${WORK_DIR}/.secrets.env 2>/dev/null" >> "$HOME/.bashrc"
      ok ".secrets.env linked into .bashrc (env var persistence)"
    fi
  else
    warn ".secrets.env missing — recommended: run bash navigator.sh first"
  fi
}

setup_ubuntu_pkgs() {
  echo ""
  echo "─── Step 5: Ubuntu packages (inside proot) ───"
  if ! in_proot; then
    warn "You may be on the Termux host right now. Inside Ubuntu:"
    echo "  proot-distro login ubuntu"
    echo "  apt update && apt install -y git curl nodejs npm python3 python3-pip"
    return 0
  fi
  apt-get update -qq >/dev/null 2>&1 || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git curl ca-certificates python3 python3-pip >/dev/null 2>&1 \
    && ok "git curl python3" || warn "apt partially failed"
  if ! command -v node >/dev/null 2>&1; then
    info "trying nodejs..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs npm >/dev/null 2>&1 \
      && ok "nodejs" || warn "nodejs needs manual install"
  else
    ok "node $(node -v 2>/dev/null || echo ok)"
  fi
}

setup_claude() {
  echo ""
  echo "─── Step 6: Claude Code + DeepSeek ───"
  if [ "$SKIP_CLAUDE" = "1" ]; then warn "SKIP_CLAUDE=1"; return 0; fi

  mkdir -p "$WORK_DIR/configs"
  cat > "$WORK_DIR/configs/deepseek.env" << 'DSEOF'
# source this file inside proot Ubuntu
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_MODEL=deepseek-chat
DSEOF
  if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "export ANTHROPIC_API_KEY=${DEEPSEEK_API_KEY}" >> "$WORK_DIR/configs/deepseek.env"
    echo "export DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}" >> "$WORK_DIR/configs/deepseek.env"
    ok "DeepSeek key written to deepseek.env"
  else
    warn "no key — add it to configs/deepseek.env later"
  fi

  if command -v npm >/dev/null 2>&1; then
    if command -v claude >/dev/null 2>&1; then ok "claude already present"
    else
      info "npm i -g @anthropic-ai/claude-code ..."
      npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 && ok "Claude Code" || warn "Claude Code install failed — manual"
    fi
  else
    warn "no npm — install Ubuntu packages, then re-run"
  fi

  if [ -f "$HOME/.bashrc" ]; then
    grep -q "deepseek.env" "$HOME/.bashrc" 2>/dev/null \
      || echo "source ${WORK_DIR}/configs/deepseek.env 2>/dev/null" >> "$HOME/.bashrc"
    ok "deepseek.env linked into .bashrc"
  fi
}

setup_mcp() {
  echo ""
  echo "─── Step 7: phone-mcp (optional) ───"
  if [ "$SKIP_MCP" = "1" ]; then warn "SKIP_MCP=1"; return 0; fi
  local mcp_dir="/tmp/phone-mcp-server"
  if [ ! -f "$mcp_dir/server.py" ]; then
    git clone --depth 1 https://github.com/htekdev/phone-mcp-server "$mcp_dir" >/dev/null 2>&1 \
      && ok "phone-mcp-server cloned" || warn "mcp clone failed"
  else
    ok "phone-mcp already present"
  fi
  mkdir -p "$HOME/.claude"
  if [ -f "$WORK_DIR/configs/settings.json" ]; then
    cp "$WORK_DIR/configs/settings.json" "$HOME/.claude/settings.json" 2>/dev/null && ok "MCP settings copied"
  fi
}

setup_telegram() {
  echo ""
  echo "─── Step 8: Telegram ───"
  # source .secrets.env to read env vars (no pre-export dependency)
  [ -f "$WORK_DIR/.secrets.env" ] && source "$WORK_DIR/.secrets.env" 2>/dev/null || true
  if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
    ok "TG_TOKEN / TG_CHAT configured"
    if [ -x "$WORK_DIR/tg.sh" ] || [ -f "$WORK_DIR/tg.sh" ]; then
      chmod +x "$WORK_DIR/tg.sh" 2>/dev/null || true
      (cd "$WORK_DIR" && TG_TOKEN="$TG_TOKEN" TG_CHAT="$TG_CHAT" bash tg.sh "✅ S21 install v3 complete · OWNER=${OWNER_GITHUB} USER=${GITHUB_USER}") 2>/dev/null \
        && ok "test message sent" || warn "tg test skipped"
    fi
  else
    warn "no TG — use @BotFather, then export TG_TOKEN TG_CHAT"
  fi
}

run_health() {
  echo ""
  echo "─── Step 9: health check ───"
  if [ -f "$WORK_DIR/phone-health.sh" ]; then
    chmod +x "$WORK_DIR/phone-health.sh"
    bash "$WORK_DIR/phone-health.sh" 2>&1 | tail -8 || warn "health check warning"
    ok "phone-health ran"
  else
    warn "phone-health.sh missing"
  fi
}

show_satellites() {
  echo ""
  echo "─── Satellite repos (reference) ───"
  cat << EOF
  Public surfaces under the owner account:
    https://github.com/${OWNER_GITHUB}/helena_phone
    https://github.com/${OWNER_GITHUB}/helana_log
    https://github.com/${OWNER_GITHUB}/helana-faith
    https://github.com/${OWNER_GITHUB}/helena-piano
    https://github.com/${OWNER_GITHUB}/helena-metalcare

  Pages:
    https://${OWNER_GITHUB}.github.io/helena_phone/
    https://${OWNER_GITHUB}.github.io/helana_log/
    ...
EOF
  if [ "$CLONE_SATELLITES" = "1" ]; then
    info "CLONE_SATELLITES=1 — cloning into /root/sites"
    mkdir -p /root/sites
    for r in helana_log helana-faith helena-piano helena-metalcare; do
      [ -d "/root/sites/$r/.git" ] && continue
      git clone "https://github.com/${OWNER_GITHUB}/${r}.git" "/root/sites/$r" 2>/dev/null \
        && ok "$r" || warn "$r clone failed"
    done
  fi
}

spawn_ecosystem() {
  echo ""
  echo "─── Step 10: ecosystem spawn (optional) ───"
  if [ "$SPAWN_ECOSYSTEM" != "1" ]; then
    warn "runs only when SPAWN_ECOSYSTEM=1 (skipping)"
    echo "  To create the 4 satellites (piano/metalcare/faith/log) from the template:"
    echo "    SPAWN_ECOSYSTEM=1 bash g/install.sh   # or   bash g/spawn.sh"
    echo "  Configure first: bash navigator.sh  (creates configs/ecosystem.json + .secrets.env)"
    return 0
  fi
  if [ -f "$WORK_DIR/g/spawn.sh" ]; then
    bash "$WORK_DIR/g/spawn.sh"
  else
    warn "g/spawn.sh missing — template is an old version"
  fi
}

summary() {
  echo ""
  echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  ✅ install flow complete (v3)${NC}"
  echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
  cat << EOF

  OWNER:      ${OWNER_GITHUB} (${OWNER_NAME})
  USER:       ${GITHUB_USER}
  Workspace:  ${WORK_DIR}
  Template:   ${TEMPLATE_REPO}

  Next commands (Termux):
    proot-distro login ubuntu
    cd ${WORK_DIR}
    source configs/deepseek.env   # once the key is set
    source configs/helena-env.example.sh
    claude                        # or grok / bash scripts/ds.sh

  Health:      bash phone-health.sh
  Report:      bash tg.sh 'message'
  Care:        bash care/care-setup.sh
  Production:  bash scripts/preflight.sh   # table-setter (session/token check)
               bash scripts/quota.sh       # today's remaining quota
               bash scripts/make_pair.sh   # raw asset → PWA+Tistory pair
  Manual:      cat _notebook/41-beginner-install-manual_Grok.md
               or https://${OWNER_GITHUB}.github.io/helena_phone/install-guide.html

  Pages: https://${OWNER_GITHUB}.github.io/${GITHUB_REPO}/

EOF
}

main() {
  banner
  check_vars
  check_env
  install_pkgs
  install_proot

  if ! in_proot; then
    echo ""
    warn "You may have completed up to the Termux host stage."
    echo "  Run the following, then re-run this script inside Ubuntu:"
    echo ""
    echo "  proot-distro login ubuntu"
    echo "  apt update && apt install -y git curl nodejs npm python3"
    echo "  export OWNER_GITHUB=${OWNER_GITHUB} GITHUB_USER=${GITHUB_USER} GITHUB_REPO=${GITHUB_REPO}"
    echo "  export GITHUB_TOKEN=... DEEPSEEK_API_KEY=..."
    echo "  bash <(curl -sL https://raw.githubusercontent.com/${TEMPLATE_REPO}/main/g/install.sh)"
    echo ""
  fi

  setup_ubuntu_pkgs
  setup_repo
  setup_claude
  setup_mcp
  setup_telegram
  run_health
  show_satellites
  spawn_ecosystem
  summary
}

main "$@"

#!/usr/bin/env bash
# ==============================================================================
# g/spawn.sh — spawn engine (ecosystem.json → create GitHub repos + wire secrets)
# ==============================================================================
# Reads configs/ecosystem.json (made by navigator.sh):
#   ① Mark the hub (helena_phone) as a GitHub Template Repo
#   ② Create the 4 satellites (piano/metalcare/faith/log) from the template (--public)
#   ③ Wire .secrets.env's TG_TOKEN/TG_CHAT into each repo's GitHub Actions secrets
#
# Usage:
#   bash g/spawn.sh              # run (idempotent — skips if already present)
#   bash g/spawn.sh --dry-run    # preview only (doesn't run)
#
# Rule: no PAT — authenticate via gh auth. Secrets via gh secret set (values never touch a file).
# ==============================================================================

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$BASE/scripts"
REAL="$BASE/configs/ecosystem.json"
SECRETS="$BASE/.secrets.env"
TEMPLATE_OWNER="${TEMPLATE_OWNER:-helena751107}"   # boilerplate's original owner

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${BLUE}📌${NC} $*"; }

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

# ── Loader: owner / hub / satellite list ─────────────────────────────────────
owner()   { python3 "$SCRIPTS/load_ecosystem.py" --json owner; }
hub_repo() { python3 -c "import sys;sys.path.insert(0,'$SCRIPTS');from load_ecosystem import hub_repo;print(hub_repo())"; }

# Print the satellite repos (role != hub) as "repo<TAB>blog"
satellites() {
  python3 - "$SCRIPTS" << 'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[1])
from load_ecosystem import repos
for r in repos():
    if r.get("role") != "hub":
        print(f"{r['repo']}\t{r.get('blog','')}")
PYEOF
}

require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    fail "gh CLI missing — install https://cli.github.com/ then gh auth login"
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    fail "gh not authenticated — run 'gh auth login' first (no PAT in files)"
    exit 1
  fi
  ok "gh auth verified"
}

exists() { gh repo view "$1" >/dev/null 2>&1; }

mark_hub_template() {
  local hub="$1"
  if [ "$DRY" = "1" ]; then
    info "dry-run: gh repo edit ${OWNER}/${hub} --template"
    return 0
  fi
  if exists "${OWNER}/${hub}"; then
    gh repo edit "${OWNER}/${hub}" --template 2>/dev/null \
      && ok "marked as template: ${OWNER}/${hub}" \
      || warn "mark-as-template failed (may already be): ${OWNER}/${hub}"
  else
    warn "hub repo missing: ${OWNER}/${hub} (create it via use-this-template first)"
  fi
}

spawn_satellites() {
  while IFS=$'\t' read -r repo blog; do
    [ -z "$repo" ] && continue
    if [ "$DRY" = "1" ]; then
      info "dry-run: gh repo create ${OWNER}/${repo} --template ${TEMPLATE_OWNER}/${repo} --public   # → ${blog}"
      continue
    fi
    if exists "${OWNER}/${repo}"; then
      ok "already present: ${OWNER}/${repo} (skip)"
    else
      info "create: ${OWNER}/${repo} ← ${TEMPLATE_OWNER}/${repo}"
      gh repo create "${OWNER}/${repo}" --template "${TEMPLATE_OWNER}/${repo}" --public \
        && ok "created: ${OWNER}/${repo}" \
        || warn "create failed (check permission/template): ${OWNER}/${repo}"
    fi
  done < <(satellites)
}

set_secrets() {
  # source .secrets.env to read env vars (proot env var = SSOT).
  # The only secrets GitHub Actions actually reads are TG_TOKEN/TG_CHAT (helana_log log-to-tistory.yml).
  # TISTORY/YOUTUBE/DISCORD/TAILSCALE are read by local scripts on the phone's proot, so they're not wired to GitHub (avoid needless exposure).
  local tg_token="" tg_chat=""
  if [ -f "$SECRETS" ]; then
    source "$SECRETS" 2>/dev/null || true
    tg_token="${TG_TOKEN:-}"
    tg_chat="${TG_CHAT:-}"
  fi
  [ -z "$tg_token" ] && { warn "TG_TOKEN missing — skipping secret wiring (bash navigator.sh --secrets)"; return 0; }

  # wiring targets = hub + all satellites (generic bot)
  local repos_list="$1
$(satellites | cut -f1)"
  local repo
  while IFS= read -r repo; do
    [ -z "$repo" ] && continue
    if [ "$DRY" = "1" ]; then
      info "dry-run: gh secret set TG_TOKEN/TG_CHAT -R ${OWNER}/${repo}"
      continue
    fi
    exists "${OWNER}/${repo}" || { warn "repo missing (skip): ${OWNER}/${repo}"; continue; }
    printf '%s' "$tg_token" | gh secret set TG_TOKEN -R "${OWNER}/${repo}" \
      && printf '%s' "$tg_chat" | gh secret set TG_CHAT -R "${OWNER}/${repo}" \
      && ok "secret wired: ${OWNER}/${repo} (TG_TOKEN/TG_CHAT)" \
      || warn "secret wiring failed: ${OWNER}/${repo}"
  done <<< "$repos_list"

  # per-repo dedicated bot (schema advanced keys) — if present, overwrite that repo's
  wire_repo_bot helena-piano     HELENA_PIANO_TG_TOKEN   HELENA_PIANO_TG_CHAT
  wire_repo_bot helena-metalcare HELENA_PSYCARE_TG_TOKEN HELENA_PSYCARE_TG_CHAT
  wire_repo_bot helana-faith     HELENA_FAITH_TG_TOKEN   HELENA_FAITH_TG_CHAT
  wire_repo_bot helana_log       HELANA_LOG_TG_TOKEN     HELANA_LOG_TG_CHAT
}

# Wire a per-repo dedicated bot token (if present, overwrites that repo's TG_TOKEN/TG_CHAT)
wire_repo_bot() {
  local repo="$1" tok_var="$2" chat_var="$3"
  local tok="${!tok_var:-}" chat="${!chat_var:-}"
  [ -z "$tok" ] && return 0
  if [ "$DRY" = "1" ]; then
    info "dry-run: gh secret set TG_TOKEN/TG_CHAT -R ${OWNER}/${repo} (dedicated bot ${tok_var})"
    return 0
  fi
  exists "${OWNER}/${repo}" || { warn "repo missing (skip): ${OWNER}/${repo}"; return 0; }
  printf '%s' "$tok" | gh secret set TG_TOKEN -R "${OWNER}/${repo}" \
    && printf '%s' "$chat" | gh secret set TG_CHAT -R "${OWNER}/${repo}" \
    && ok "dedicated bot wired: ${OWNER}/${repo} (${tok_var})" \
    || warn "dedicated bot wiring failed: ${OWNER}/${repo}"
}

# ── main ────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BOLD}═══ Spawn engine (ecosystem.json → GitHub) ═══${NC}"
  echo ""

  if [ ! -f "$REAL" ]; then
    warn "configs/ecosystem.json missing — run bash navigator.sh first"
    warn "Proceeding from the template (${REAL}.template)."
  fi

  OWNER="$(owner)"
  HUB="$(hub_repo)"
  info "owner=${OWNER}  hub=${HUB}  template_owner=${TEMPLATE_OWNER}"

  if [ "$DRY" = "1" ]; then
    info "── dry-run (no action) ──"
    echo ""
  else
    require_gh
  fi

  mark_hub_template "$HUB"
  echo ""
  spawn_satellites
  echo ""
  set_secrets "$HUB"

  echo ""
  if [ "$DRY" = "1" ]; then
    info "To actually run the above: bash g/spawn.sh"
  else
    ok "Spawn complete. Check each repo's Pages/workflows on GitHub."
    info "Drift sync is handled automatically by the central reusable workflow (uses: helena751107/...)."
  fi
}

main "$@"

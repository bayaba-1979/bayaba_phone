#!/usr/bin/env bash
# ==============================================================================
# navigator.sh — S21 ecosystem setup wizard (navigator)
# ==============================================================================
# The entry point for "copy-paste → it just runs."
# What this script does:
#   ① Verify the GitHub account (`gh auth`)
#   ② Collect owner (ownership) · 5 blog slugs · 2 channel handles
#   ③ Guide you through BotFather / Google Cloud Console / Discord, then paste values
#   ④ Create configs/ecosystem.json + .secrets.env (both gitignored)
#   ⑤ Pre-spawn dry-run summary (the actual spawn is done by g/spawn.sh)
#
# Usage:
#   bash navigator.sh            # interactive wizard
#   bash navigator.sh --check    # non-interactive dry-run (validate ecosystem.json + spawn list)
#   bash navigator.sh --secrets  # re-enter secrets only (regenerate .secrets.env)
#
# Rule: secrets go only in .secrets.env, mapping only in ecosystem.json, PAT via gh auth.
# ==============================================================================

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$BASE/configs"
TEMPLATE="$CONFIG_DIR/ecosystem.json.template"
REAL="$CONFIG_DIR/ecosystem.json"
SECRETS="$BASE/.secrets.env"
SECRETS_TEMPLATE="$CONFIG_DIR/secrets-template.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${BLUE}📌${NC} $*"; }
step() { echo ""; echo -e "${CYAN}${BOLD}── $* ──${NC}"; }

banner() {
  echo ""
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  🧭 S21 Ecosystem Navigator${NC}"
  echo -e "${BOLD}  GitHub username + a few slugs + secrets → run it now${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo ""
}

# ── Interactive input helpers (with defaults) ────────────────────────────────
# prompt "question" "default" → prints the answer to stdout (empty input = default)
prompt() {
  local q="$1" def="$2" ans=""
  if [ -n "$def" ]; then
    printf "  ${BOLD}%s${NC} [%s]: " "$q" "$def"
  else
    printf "  ${BOLD}%s${NC}: " "$q"
  fi
  IFS= read -r ans || true
  if [ -z "$ans" ] && [ -n "$def" ]; then ans="$def"; fi
  printf '%s' "$ans"
}

# For secrets — hide the input from the screen
prompt_secret() {
  local q="$1" ans=""
  printf "  ${BOLD}%s${NC} (hidden input): " "$q"
  IFS= read -rs ans || true
  echo ""
  printf '%s' "$ans"
}

# ── Step 0: gh auth ──────────────────────────────────────────────────────────
ensure_gh_auth() {
  step "0. GitHub auth"
  if ! command -v gh >/dev/null 2>&1; then
    warn "gh CLI not found. Install: https://cli.github.com/  (or apt install gh)"
    warn "The only safe way that avoids putting a PAT in a file is gh auth."
    return 0
  fi
  if gh auth status >/dev/null 2>&1; then
    ok "gh authenticated: $(gh auth status 2>&1 | grep -oE 'Logged in to [^ ]+' | head -1 || echo 'ok')"
  else
    warn "gh not authenticated — let's log in."
    echo "  A browser will open — enter the code:"
    echo "  $ gh auth login"
    echo ""
    if [ -t 0 ]; then
      printf "  Run it now? [Y/n]: "
      read -r do_auth || true
      if [ "$do_auth" != "n" ] && [ "$do_auth" != "N" ]; then
        gh auth login
      fi
    fi
  fi
}

# ── Step 1: owner + mapping ──────────────────────────────────────────────────
collect_mapping() {
  step "1. Ownership (owner) + blog/channel mapping"

  local owner_default
  owner_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE')).get('owner','bayaba-1979'))" 2>/dev/null || echo bayaba-1979)"
  OWNER="$(prompt "GitHub username/org (ownership)" "$owner_default")"
  ok "owner = $OWNER"

  echo ""
  info "Change the blog/channel slugs now? (the template ships with Helena's sample values)"
  printf "  ${BOLD}Change them?${NC} [N/y]: "
  read -r do_map || true
  if [ "$do_map" = "y" ] || [ "$do_map" = "Y" ]; then
    ADVANCED=1
  else
    ADVANCED=0
    warn "Keeping the sample mapping — you can edit configs/ecosystem.json later"
  fi
}

# Interactively collect each repo's blog and each channel's handle (python reads them in this order)
collect_map_details() {
  [ "$ADVANCED" = "1" ] || return 0
  step "1a. 5 blog slugs"

  local repo_names blogs="" h="" c
  repo_names="$(python3 -c "import json;print('\n'.join(r['repo'] for r in json.load(open('$TEMPLATE'))['repos']))")"
  NAV_BLOGS=""
  while IFS= read -r c; do
    [ -z "$c" ] && continue
    local cur
    cur="$(python3 -c "import json;[print(r['blog']) for r in json.load(open('$TEMPLATE'))['repos'] if r['repo']=='$c']")"
    h="$(prompt "  ${c} → Tistory blog slug" "$cur")"
    NAV_BLOGS="${NAV_BLOGS}${h}"$'\n'
  done <<< "$repo_names"

  step "1b. 2 channel handles"
  local ch_names
  ch_names="$(python3 -c "import json;print('\n'.join(c['key']+': '+c['handle'] for c in json.load(open('$TEMPLATE'))['channels']))")"
  NAV_HANDLES=""
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    local key="${line%%:*}" cur_h="${line#*: }"
    h="$(prompt "  ${key} channel handle" "$cur_h")"
    NAV_HANDLES="${NAV_HANDLES}${h}"$'\n'
  done <<< "$ch_names"
}

# ── Step 2: git identity (optional) ──────────────────────────────────────────
collect_git() {
  step "2. Git bot identity (commit author — usually keep the defaults)"
  local gname_default gemail_default
  gname_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE'))['git']['name'])")"
  gemail_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE'))['git']['email'])")"
  GIT_NAME="$(prompt "  Commit author name" "$gname_default")"
  GIT_EMAIL="$(prompt "  Commit author email" "$gemail_default")"
}

# ── Step 3: secrets ──────────────────────────────────────────────────────────
collect_secrets() {
  step "3. Secrets (guided issuance, then paste — empty = skip, fill later)"

  echo ""
  info "── 3a. Telegram bot (reporting channel) ──"
  echo "  1) In Telegram, search @BotFather → /newbot"
  echo "  2) Set the bot name/id (ending in 'bot') → copy the 'Use this token' token"
  echo "  3) Send your bot any message → ask @userinfobot for your numeric chat ID"
  SECRET_TG_TOKEN="$(prompt_secret "  TG_TOKEN (BotFather token)")"
  SECRET_TG_CHAT="$(prompt_secret "  TG_CHAT (numeric chat ID)")"

  echo ""
  info "── 3b. Tistory (auto-publish login) ──"
  echo "  Kakao account email/password — used by post.py to issue a session cookie"
  SECRET_TISTORY_EMAIL="$(prompt "  TISTORY_EMAIL" "")"
  SECRET_TISTORY_PW="$(prompt_secret "  TISTORY_PW")"

  echo ""
  info "── 3c. YouTube (Google Cloud Console) ──"
  echo "  1) https://console.cloud.google.com → create a project"
  echo "  2) 'APIs & Services' → Library → enable 'YouTube Data API v3'"
  echo "  3) Configure 'OAuth consent screen' (External) → 'Credentials' → 'OAuth 2.0 Client ID'"
  echo "     Application type = Desktop app → copy client ID/secret"
  echo "  (access/refresh tokens are issued automatically by scripts/yt_oauth_setup.sh on first upload)"
  SECRET_YT_CLIENT_ID="$(prompt "  YOUTUBE_CLIENT_ID" "")"
  SECRET_YT_CLIENT_SECRET="$(prompt_secret "  YOUTUBE_CLIENT_SECRET")"

  echo ""
  info "── 3d. Discord (optional — reporting webhook/bot) ──"
  echo "  1) https://discord.com/developers/applications → New Application → Bot → Reset Token"
  echo "  2) Discord settings → Advanced → Developer Mode ON → right-click channel/server → Copy ID"
  SECRET_DISCORD_BOT_TOKEN="$(prompt_secret "  DISCORD_BOT_TOKEN")"
  SECRET_DISCORD_CHANNEL_ID="$(prompt "  DISCORD_CHANNEL_ID" "")"
  SECRET_DISCORD_SERVER_ID="$(prompt "  DISCORD_SERVER_ID" "")"

  echo ""
  info "── 3e. Tailscale (optional — remote access) ──"
  echo "  https://login.tailscale.com/admin → Settings → Keys → Generate auth key"
  SECRET_TAILSCALE_AUTH_KEY="$(prompt_secret "  TAILSCALE_AUTH_KEY")"
}

# ── Step 4: write files ──────────────────────────────────────────────────────
write_ecosystem() {
  step "4. Create configs/ecosystem.json"
  NAV_OWNER="$OWNER" \
  NAV_GIT_NAME="$GIT_NAME" \
  NAV_GIT_EMAIL="$GIT_EMAIL" \
  NAV_BLOGS="${NAV_BLOGS:-}" \
  NAV_HANDLES="${NAV_HANDLES:-}" \
  NAV_TEMPLATE="$TEMPLATE" \
  NAV_REAL="$REAL" \
  python3 << 'PYEOF'
import json, os
tmpl = json.load(open(os.environ["NAV_TEMPLATE"], encoding="utf-8"))
tmpl["owner"] = os.environ.get("NAV_OWNER", tmpl.get("owner", "")).strip()

if os.environ.get("NAV_GIT_NAME"):
    tmpl.setdefault("git", {})["name"] = os.environ["NAV_GIT_NAME"].strip()
if os.environ.get("NAV_GIT_EMAIL"):
    tmpl.setdefault("git", {})["email"] = os.environ["NAV_GIT_EMAIL"].strip()

blogs = [l for l in os.environ.get("NAV_BLOGS", "").splitlines() if l.strip()]
if blogs:
    for r, b in zip(tmpl.get("repos", []), blogs):
        r["blog"] = b.strip()

handles = [l for l in os.environ.get("NAV_HANDLES", "").splitlines() if l.strip()]
if handles:
    for c, h in zip(tmpl.get("channels", []), handles):
        # if the handle changes, the old channel id is invalid → clear it
        if c.get("handle", "").strip() != h.strip():
            c["id"] = ""
        c["handle"] = h.strip()

os.makedirs(os.path.dirname(os.environ["NAV_REAL"]), exist_ok=True)
with open(os.environ["NAV_REAL"], "w", encoding="utf-8") as f:
    json.dump(tmpl, f, ensure_ascii=False, indent=2)
print(f"  ✅ wrote {os.environ['NAV_REAL']}")
PYEOF
  ok "ecosystem.json created"
}

write_secrets() {
  step "5. Create .secrets.env"
  # Read the schema and fill only the entered values (other keys stay blank)
  SECRET_TG_TOKEN="${SECRET_TG_TOKEN:-}" \
  SECRET_TG_CHAT="${SECRET_TG_CHAT:-}" \
  SECRET_TISTORY_EMAIL="${SECRET_TISTORY_EMAIL:-}" \
  SECRET_TISTORY_PW="${SECRET_TISTORY_PW:-}" \
  SECRET_YT_CLIENT_ID="${SECRET_YT_CLIENT_ID:-}" \
  SECRET_YT_CLIENT_SECRET="${SECRET_YT_CLIENT_SECRET:-}" \
  SECRET_DISCORD_BOT_TOKEN="${SECRET_DISCORD_BOT_TOKEN:-}" \
  SECRET_DISCORD_CHANNEL_ID="${SECRET_DISCORD_CHANNEL_ID:-}" \
  SECRET_DISCORD_SERVER_ID="${SECRET_DISCORD_SERVER_ID:-}" \
  SECRET_TAILSCALE_AUTH_KEY="${SECRET_TAILSCALE_AUTH_KEY:-}" \
  SECRETS_TEMPLATE="$SECRETS_TEMPLATE" \
  SECRETS="$SECRETS" \
  python3 << 'PYEOF'
import os, re
src = open(os.environ["SECRETS_TEMPLATE"], encoding="utf-8").read()
overrides = {
    "TG_TOKEN": os.environ.get("SECRET_TG_TOKEN", ""),
    "TG_CHAT": os.environ.get("SECRET_TG_CHAT", ""),
    "TISTORY_EMAIL": os.environ.get("SECRET_TISTORY_EMAIL", ""),
    "TISTORY_PW": os.environ.get("SECRET_TISTORY_PW", ""),
    "YOUTUBE_CLIENT_ID": os.environ.get("SECRET_YT_CLIENT_ID", ""),
    "YOUTUBE_CLIENT_SECRET": os.environ.get("SECRET_YT_CLIENT_SECRET", ""),
    "DISCORD_BOT_TOKEN": os.environ.get("SECRET_DISCORD_BOT_TOKEN", ""),
    "DISCORD_CHANNEL_ID": os.environ.get("SECRET_DISCORD_CHANNEL_ID", ""),
    "DISCORD_SERVER_ID": os.environ.get("SECRET_DISCORD_SERVER_ID", ""),
    "TAILSCALE_AUTH_KEY": os.environ.get("SECRET_TAILSCALE_AUTH_KEY", ""),
}
for key, val in overrides.items():
    if val:
        src = re.sub(rf'^({key}=)(".*"|)$', rf'\g<1>"{val}"', src, flags=re.M)
with open(os.environ["SECRETS"], "w", encoding="utf-8") as f:
    f.write(src)
print(f"  ✅ wrote {os.environ['SECRETS']} (blank keys can be filled in later)")
PYEOF
  chmod 600 "$SECRETS" 2>/dev/null || true
  ok ".secrets.env created (chmod 600)"
}

# ── Step 5: dry-run summary ──────────────────────────────────────────────────
dry_run_summary() {
  step "6. Pre-spawn summary (dry-run)"
  echo -e "  ${BOLD}owner:${NC} $(python3 "$CONFIG_DIR/../scripts/load_ecosystem.py" --json owner 2>/dev/null || echo "$OWNER")"
  echo ""
  python3 - << PYEOF
import json, subprocess, sys, os
sys.path.insert(0, "$BASE/scripts")
from load_ecosystem import repos, channels
print("  Repos to be spawned:")
for r in repos():
    print(f"    gh repo create $OWNER/{r['repo']} --template bayaba-1979/{r['repo']} --public   # {r['blog']} → {r['channel']}")
print("")
print("  Secret wiring (gh secret set -R):")
print("    TG_TOKEN · TG_CHAT · TISTORY_EMAIL · TISTORY_PW · YOUTUBE_CLIENT_ID · YOUTUBE_CLIENT_SECRET")
print("")
print("  Next steps:")
print("    bash g/spawn.sh        # create 4 satellite repos + wire secrets (needs gh CLI)")
print("    bash g/install.sh      # build the workspace (Termux/proot/Claude)")
print("")
print("  Production recipe (after install):")
print("    bash scripts/preflight.sh   # table-setter — pre-check sessions & tokens")
print("    bash scripts/quota.sh       # today's remaining quota (Tistory 15/day, etc.)")
print("    bash scripts/make_pair.sh   # raw asset → PWA+Tistory pair publish")
PYEOF
  echo ""
  info "Spawning is done by g/spawn.sh, workspace by g/install.sh (navigator only 'configures')."
  warn "Verify .gitignore so secrets never reach git (git status)."
}

# ── --check (non-interactive dry-run) ────────────────────────────────────────
mode_check() {
  banner
  info "Non-interactive dry-run — validate ecosystem.json + spawn list"
  echo ""
  if [ -f "$REAL" ]; then
    ok "configs/ecosystem.json present (user settings)"
  else
    warn "configs/ecosystem.json missing → using the template (samples)"
  fi
  echo ""
  python3 "$BASE/scripts/load_ecosystem.py" --check
  echo ""
  if [ -f "$SECRETS" ]; then
    local filled
    filled="$(grep -cE '="[^"]+"' "$SECRETS" 2>/dev/null || echo 0)"
    ok ".secrets.env present (${filled} keys filled)"
  else
    warn ".secrets.env missing → run bash navigator.sh to create it"
  fi
  echo ""
  info "Spawn command preview (by owner):"
  local own
  own="$(python3 "$BASE/scripts/load_ecosystem.py" --json owner)"
  python3 - << PYEOF
import sys
sys.path.insert(0, "$BASE/scripts")
from load_ecosystem import repos
own = "$own"
for r in repos():
    print(f"  gh repo create {own}/{r['repo']} --template bayaba-1979/{r['repo']} --public")
PYEOF
}

# ── main ────────────────────────────────────────────────────────────────────
main() {
  case "${1:-}" in
    --check) mode_check; return 0 ;;
    --secrets) banner; ensure_gh_auth; collect_secrets; write_secrets; return 0 ;;
  esac

  banner
  ensure_gh_auth
  collect_mapping
  collect_map_details
  collect_git
  collect_secrets
  write_ecosystem
  write_secrets
  dry_run_summary
}

main "$@"

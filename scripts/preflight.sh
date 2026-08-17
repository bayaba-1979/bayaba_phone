#!/usr/bin/env bash
# ==============================================================================
# preflight.sh — table-setter (pre-check consumable assets right before production)
# ==============================================================================
# Purpose: before running production (content publishing), pre-check the assets
#          that expire easily (sessions · tokens · keys) and show "what to renew
#          now" as a table.
#          → a pre-gate so Boss renews them by hand before production runs.
#
# Usage:
#   bash scripts/preflight.sh          # print the table only
#   bash scripts/preflight.sh --tg     # also report the result to Telegram (uses tg.sh)
#
# Checks (content-production scope only — care (Tailscale · care daemon) excluded):
#   1. Tistory session (live manage URL probe — 302→login means the session expired)
#   2. YouTube OAuth (actually try refreshing with the refresh token)
#   3. GitHub auth (gh auth status)
#   4. Telegram bot (getMe probe)
#
# ⚠️ Tistory sessions are judged by a live manage-URL probe, not file freshness (24h).
#    The server-side session expires before the cookie expires (client-side, 6 days),
#    so an mtime heuristic misses it (live 2026-08-17: all 5 → 302→login).
#    Shelf life = ~24h after login (server policy). No "keep me signed in" option → cannot extend.
#    Independent of phone reboots (cookies are disk-persistent); the real limit is the 24h server TTL.
#    Renew in one line:  python3 tistory-naver/renew_sessions.py  (one Kakao login → seeds 5 blogs)
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="$BASE/.secrets.env"
TG="$BASE/tg.sh"

# ── Load secrets (SSOT) ──
# set -a = export every sourced variable to child processes (python/curl)
set -a
[ -f "$SECRETS" ] && source "$SECRETS" 2>/dev/null
set +a

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "  ${RED}❌${NC} $*"; }

FAIL_CNT=0; WARN_CNT=0
RENEW=()   # list of items needing renewal

echo "════════════════════════════════════════"
echo "  🔧 Preflight (pre-production check)"
echo "════════════════════════════════════════"

# ── 1. Tistory sessions (live manage URL probe) ──
echo ""
echo "[1] Tistory sessions (5 blogs, live probe)"
TISTORY_RESULT=$(python3 - "$BASE" <<'PY'
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1]

# account→blog slug (ecosystem.json SSOT, fall back to samples if missing)
try:
    sys.path.insert(0, BASE + "/scripts")
    from load_ecosystem import repos
    pairs = [(r.get("account", ""), r.get("blog", "")) for r in repos()]
except Exception:
    pairs = [
        ("galaxys21", "galaxys21-pwuser"),
        ("mynote", "mynote11605"),
        ("piano", "helena-piano"),
        ("metalcare", "helena-metalcare"),
        ("faith", "helana-christianity"),
    ]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}

for acct, slug in pairs:
    if not acct or not slug:
        continue
    st = f"{BASE}/tistory-naver/cookies/{acct}_state.json"
    try:
        d = json.load(open(st, encoding="utf-8"))
        header = "; ".join(f"{c['name']}={c['value']}" for c in d.get("cookies", []))
    except Exception:
        print(f"{acct}\tMISSING")
        continue
    try:
        req = urllib.request.Request(
            f"https://{slug}.tistory.com/manage", headers={"Cookie": header, **UA}
        )
        urllib.request.build_opener(NoRedirect).open(req, timeout=10)
        print(f"{acct}\tOK")
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        print(f"{acct}\tEXPIRED" if "/auth/login" in loc else f"{acct}\tHTTP{e.code}")
    except Exception:
        print(f"{acct}\tERR")
PY
)
while IFS=$'\t' read -r acct status; do
  [ -z "$acct" ] && continue
  case "$status" in
    OK)      ok "Tistory $acct — session valid" ;;
    EXPIRED) fail "Tistory $acct — session expired (auto-renewed when publishing via make_pair)"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("Tistory $acct re-login") ;;
    MISSING) fail "Tistory $acct — state missing (auto-renewed when publishing via make_pair)"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("Tistory $acct re-login") ;;
    *)       warn "Tistory $acct — cannot check ($status)" ;;
  esac
done <<< "$TISTORY_RESULT"

# ── 2. YouTube OAuth (live refresh) ──
echo ""
echo "[2] YouTube OAuth"
YT_RESULT=$(python3 - "$BASE" <<'PY'
import os, sys, json, urllib.request, urllib.parse
BASE = sys.argv[1]
cid = os.environ.get("YOUTUBE_CLIENT_ID","")
cs  = os.environ.get("YOUTUBE_CLIENT_SECRET","")
rt  = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
if not rt:
    try:
        d = json.load(open(os.path.join(BASE, "configs", "yt_tokens.json")))
        rt = d.get("refresh_token","")
    except Exception:
        pass
if not (cid and cs and rt):
    print("MISSING")
else:
    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": cs,
        "refresh_token": rt, "grant_type": "refresh_token",
    }).encode()
    try:
        urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=12)
        print("OK")
    except Exception:
        print("FAIL")
PY
)
case "$YT_RESULT" in
  OK) ok "YouTube OAuth — refresh succeeded";;
  MISSING) fail "YouTube — tokens not set → run yt_oauth_setup.sh"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("YouTube OAuth re-auth");;
  FAIL) fail "YouTube — refresh failed (expired/revoked) → re-auth needed"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("YouTube OAuth re-auth");;
  *) warn "YouTube — cannot check ($YT_RESULT)";;
esac

# ── 3. GitHub auth ──
echo ""
echo "[3] GitHub auth"
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    ok "GitHub — gh auth valid"
  else
    fail "GitHub — not authenticated → run gh auth login"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("GitHub re-auth")
  fi
else
  warn "GitHub — gh CLI missing (skip)"
fi

# ── 4. Telegram bot ──
echo ""
echo "[4] Telegram bot (main reporting)"
if [ -n "${TG_TOKEN:-}" ]; then
  TG_RESP=$(curl -s -m 10 "https://api.telegram.org/bot${TG_TOKEN}/getMe")
  if echo "$TG_RESP" | grep -q '"ok":true'; then
    ok "Telegram — bot responds"
  else
    fail "Telegram — getMe failed (token revoked?) → reissue via BotFather"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("Telegram bot token reissue")
  fi
else
  fail "Telegram — TG_TOKEN not set"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("Telegram TG_TOKEN")
fi

# ── Summary ──
echo ""
echo "════════════════════════════════════════"
if [ "$FAIL_CNT" -eq 0 ] && [ "$WARN_CNT" -eq 0 ]; then
  echo -e "  ${GREEN}✅ all checks pass — ready to produce${NC}"
elif [ "$FAIL_CNT" -eq 0 ]; then
  echo -e "  ${YELLOW}⚠️  ${WARN_CNT} warning(s) (can proceed, renewal recommended)${NC}"
else
  echo -e "  ${RED}❌ ${FAIL_CNT} failure(s) — renew before producing${NC}"
fi
if [ "${#RENEW[@]}" -gt 0 ]; then
  echo ""
  echo "  📋 needs renewal:"
  for r in "${RENEW[@]}"; do echo "     - $r"; done
fi
echo "════════════════════════════════════════"

# ── Telegram report (--tg) ──
if [ "${1:-}" = "--tg" ] && [ -x "$TG" ]; then
  if [ "$FAIL_CNT" -eq 0 ] && [ "$WARN_CNT" -eq 0 ]; then
    STATUS="✅ all checks pass"
  elif [ "$FAIL_CNT" -eq 0 ]; then
    STATUS="⚠️ ${WARN_CNT} warning(s)"
  else
    STATUS="❌ ${FAIL_CNT} failure(s)"
  fi
  MSG="🔧 preflight check — $STATUS"
  if [ "${#RENEW[@]}" -gt 0 ]; then
    MSG="$MSG"$'\n'"needs renewal: $(printf '%s; ' "${RENEW[@]}")"
  fi
  bash "$TG" "$MSG" >/dev/null 2>&1 && echo "" && echo "📤 Telegram report sent"
fi

exit $((FAIL_CNT > 0 ? 1 : 0))

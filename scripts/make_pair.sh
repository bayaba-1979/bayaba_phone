#!/usr/bin/env bash
# ==============================================================================
# make_pair.sh — single entry point: raw asset (_notebook/*.md) → PWA + Tistory pair publish
# ==============================================================================
# BOM process, Phase 1 pair generator:
#   PWA lane     : check_webpages_Grok.py(gap) → build_webzine.py → gap=0 gate → push
#   Tistory lane : director_gate.py(review) → history_batch.py --run(publish)
#
# Usage:
#   bash scripts/make_pair.sh              # preflight → PWA + Tistory, both
#   bash scripts/make_pair.sh --pwa        # PWA lane only
#   bash scripts/make_pair.sh --tistory    # Tistory lane only
#   bash scripts/make_pair.sh --skip-preflight
#   bash scripts/make_pair.sh --tg         # report completion (Telegram)
#
# Three-layer verification (the recipe):
#   1. table-setter (preflight.sh) — pre-check sessions·tokens (abort on FAIL)
#   2. quota — abort if Tistory's remaining daily quota is 0
#   3. gap_count=0 — forbid deploy if any PWA page is missing
#
# Scope: content one-person media automation only. Care (Tailscale · care daemon) excluded.
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

DO_PWA=0; DO_TIS=0; SKIP_PRE=0; USE_TG=0
for a in "$@"; do
  case "$a" in
    --pwa)           DO_PWA=1 ;;
    --tistory)       DO_TIS=1 ;;
    --skip-preflight) SKIP_PRE=1 ;;
    --tg)            USE_TG=1 ;;
  esac
done
# if no lane is specified, do both
if [ "$DO_PWA" -eq 0 ] && [ "$DO_TIS" -eq 0 ]; then DO_PWA=1; DO_TIS=1; fi

echo "════════════════════════════════════════"
echo "  🔗 make_pair — PWA + Tistory pair publish"
echo "════════════════════════════════════════"

FAIL=0
MSG=()

# ── 1. session self-heal + table-setter (preflight) ──
if [ "$SKIP_PRE" -eq 0 ]; then
  echo ""
  echo "→ [1/3] session self-heal (auto re-login if Tistory expired)..."
  python3 "$BASE/tistory-naver/renew_sessions.py" --if-needed || true
  echo "→ [1/3] table-setter (preflight) check..."
  if ! bash "$BASE/scripts/preflight.sh"; then
    echo "❌ preflight failed — if self-heal didn't work (captcha) run renew_sessions.py --headed, or re-auth YouTube/GitHub/Telegram"
    exit 1
  fi
fi

# ── 2. PWA lane ──
if [ "$DO_PWA" -eq 1 ]; then
  echo ""
  echo "→ [2/3] PWA webpage build"
  python3 "$BASE/scripts/check_webpages_Grok.py" || true   # report gap before build
  python3 "$BASE/scripts/build_webzine.py" >/dev/null
  GAP=$(python3 "$BASE/scripts/check_webpages_Grok.py" 2>/dev/null | grep -oP 'gap_count=\K\d+' | head -1)
  if [ "${GAP:-1}" -ne 0 ]; then
    echo "❌ PWA gap_count=${GAP} — page missing (fix NOTEBOOK_TITLES) → deploy forbidden"
    FAIL=1
  else
    echo "✅ PWA gap_count=0"
    git add notebook archive.html index.html sitemap.xml \
            assets/webpage-coverage.json assets/catalog.json 2>/dev/null
    if git diff --cached --quiet; then
      echo "ℹ no PWA changes to commit"
    else
      git commit -q -m "translation: PWA pair build — notebook pages + coverage refresh"
      git -c credential.helper='!gh auth git-credential' push >/dev/null 2>&1 \
        && echo "✅ PWA push done" || { echo "❌ PWA push failed"; FAIL=1; }
    fi
    MSG+=("PWA ✅")
  fi
fi

# ── 3. Tistory lane ──
if [ "$DO_TIS" -eq 1 ]; then
  echo ""
  echo "→ [3/3] Tistory director gate + publish"
  BUDGET=$(python3 - "$BASE" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/tistory-naver")
try:
    from history_batch import remaining_budget
    print(remaining_budget())
except Exception:
    print(-1)
PY
)
  if [ "${BUDGET:-0}" -le 0 ]; then
    echo "❌ Tistory remaining daily quota is 0 — re-run tomorrow (after KST midnight)"
    FAIL=1
  else
    echo "ℹ remaining daily quota: ${BUDGET}"
    python3 "$BASE/tistory-naver/director_gate.py" >/dev/null
    python3 "$BASE/tistory-naver/history_batch.py" --run \
      && MSG+=("Tistory ✅") || { echo "❌ Tistory publish failed"; FAIL=1; }
  fi
fi

# ── Summary + Telegram report ──
echo ""
echo "════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo "  ✅ pair publish complete"
else
  echo "  ❌ partial failure — see log above"
fi
echo "════════════════════════════════════════"

if [ "$USE_TG" -eq 1 ] && [ -x "$BASE/tg.sh" ]; then
  if [ "$FAIL" -eq 0 ]; then
    SUMMARY="✅ make_pair done — $(printf '%s ' "${MSG[@]}")"
  else
    SUMMARY="❌ make_pair partial failure — see log"
  fi
  bash "$BASE/tg.sh" --no-button "$SUMMARY" >/dev/null 2>&1 \
    && echo "📤 Telegram report sent"
fi

exit "$FAIL"

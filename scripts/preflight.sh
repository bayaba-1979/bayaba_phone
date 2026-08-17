#!/usr/bin/env bash
# ==============================================================================
# preflight.sh — 테이블 세터 (양산 직전 소모성 자산 사전 점검)
# ==============================================================================
# 목적: 양산(콘텐츠 발행)을 돌리기 전에, 만료되기 쉬운 자산(세션·토큰·키)을
#       미리 점검해서 "지금 갱신해야 하는 것"을 표로 보여준다.
#       → Boss가 수작업으로 갱신하고 나서 양산을 돌리게 하는 사전 게이트.
#
# 사용법:
#   bash scripts/preflight.sh          # 표만 출력
#   bash scripts/preflight.sh --tg     # 결과를 텔레그램으로도 보고 (tg.sh 사용)
#
# 점검 항목 (콘텐츠 양산 스코프만 — 돌봄(Tailscale·돌봄데몬)은 제외):
#   1. 티스토리 세션 (5블로그 state.json 존재 + 최신 여부)
#   2. YouTube OAuth (refresh 토큰으로 실제 갱신 시도)
#   3. GitHub 인증 (gh auth status)
#   4. 텔레그램 봇 (getMe 프로브)
#
# ⚠️ 한계(정직하게): 티스토리 세션은 TSSESSION(expires=-1)이라 "정확한 만료시각"을
#    알 수 없음 → 파일 최신성(기본 24h) 휴리스틱으로 판정. 의심되면
#    verify_accounts.py 나 실제 발행 프로브로 확정.
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="$BASE/.secrets.env"
COOKIES="$BASE/tistory-naver/cookies"
TG="$BASE/tg.sh"
STALE_HOURS="${STALE_HOURS:-24}"

# ── 시크릿 로드 (SSOT) ──
# set -a = 소스된 모든 변수를 자식 프로세스(python/curl)로 export
set -a
[ -f "$SECRETS" ] && source "$SECRETS" 2>/dev/null
set +a

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "  ${RED}❌${NC} $*"; }

FAIL_CNT=0; WARN_CNT=0
RENEW=()   # 갱신 필요 목록

echo "════════════════════════════════════════"
echo "  🔧 양산 전 점검 (Preflight)"
echo "════════════════════════════════════════"

# ── 1. 티스토리 세션 (5블로그) ──
echo ""
echo "[1] 티스토리 세션 (5블로그)"
BLOGS=(galaxys21 piano faith metalcare mynote)
for b in "${BLOGS[@]}"; do
  st="$COOKIES/${b}_state.json"
  if [ ! -f "$st" ]; then
    fail "티스토리 $b — state 없음 → 재로그인 필요"
    FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("티스토리 $b 재로그인")
  elif [ -n "$(find "$st" -mmin +$((STALE_HOURS*60)) 2>/dev/null)" ]; then
    warn "티스토리 $b — 세션 ${STALE_HOURS}h 이상 방치 → 재로그인 권장"
    WARN_CNT=$((WARN_CNT+1)); RENEW+=("티스토리 $b 재로그인 권장")
  else
    ok "티스토리 $b"
  fi
done

# ── 2. YouTube OAuth (refresh 실측) ──
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
  OK) ok "YouTube OAuth — refresh 성공";;
  MISSING) fail "YouTube — 토큰 미설정 → yt_oauth_setup.sh 실행 필요"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("YouTube OAuth 재인증");;
  FAIL) fail "YouTube — refresh 실패(만료/폐기) → 재인증 필요"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("YouTube OAuth 재인증");;
  *) warn "YouTube — 점검 불가 ($YT_RESULT)";;
esac

# ── 3. GitHub 인증 ──
echo ""
echo "[3] GitHub 인증"
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    ok "GitHub — gh 인증 유효"
  else
    fail "GitHub — 인증 없음 → gh auth login 필요"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("GitHub 재인증")
  fi
else
  warn "GitHub — gh CLI 없음 (스킵)"
fi

# ── 4. 텔레그램 봇 ──
echo ""
echo "[4] 텔레그램 봇 (메인 보고)"
if [ -n "${TG_TOKEN:-}" ]; then
  TG_RESP=$(curl -s -m 10 "https://api.telegram.org/bot${TG_TOKEN}/getMe")
  if echo "$TG_RESP" | grep -q '"ok":true'; then
    ok "텔레그램 — 봇 응답 정상"
  else
    fail "텔레그램 — getMe 실패(토큰 폐기?) → BotFather 재발급"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("텔레그램 봇 토큰 재발급")
  fi
else
  fail "텔레그램 — TG_TOKEN 미설정"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("텔레그램 TG_TOKEN")
fi

# ── 요약 ──
echo ""
echo "════════════════════════════════════════"
if [ "$FAIL_CNT" -eq 0 ] && [ "$WARN_CNT" -eq 0 ]; then
  echo -e "  ${GREEN}✅ 전 항목 정상 — 양산 가능${NC}"
elif [ "$FAIL_CNT" -eq 0 ]; then
  echo -e "  ${YELLOW}⚠️  경고 ${WARN_CNT}건 (진행 가능하나 갱신 권장)${NC}"
else
  echo -e "  ${RED}❌ 실패 ${FAIL_CNT}건 — 양산 전 갱신 필요${NC}"
fi
if [ "${#RENEW[@]}" -gt 0 ]; then
  echo ""
  echo "  📋 갱신 필요:"
  for r in "${RENEW[@]}"; do echo "     - $r"; done
fi
echo "════════════════════════════════════════"

# ── 텔레그램 보고 (--tg) ──
if [ "${1:-}" = "--tg" ] && [ -x "$TG" ]; then
  if [ "$FAIL_CNT" -eq 0 ] && [ "$WARN_CNT" -eq 0 ]; then
    STATUS="✅ 전 항목 정상"
  elif [ "$FAIL_CNT" -eq 0 ]; then
    STATUS="⚠️ 경고 ${WARN_CNT}건"
  else
    STATUS="❌ 실패 ${FAIL_CNT}건"
  fi
  MSG="🔧 양산 전 점검 — $STATUS"
  if [ "${#RENEW[@]}" -gt 0 ]; then
    MSG="$MSG"$'\n'"갱신 필요: $(printf '%s; ' "${RENEW[@]}")"
  fi
  bash "$TG" "$MSG" >/dev/null 2>&1 && echo "" && echo "📤 텔레그램 보고 완료"
fi

exit $((FAIL_CNT > 0 ? 1 : 0))

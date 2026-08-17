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
#   1. 티스토리 세션 (manage URL 실측 — 302→login 이면 세션 만료)
#   2. YouTube OAuth (refresh 토큰으로 실제 갱신 시도)
#   3. GitHub 인증 (gh auth status)
#   4. 텔레그램 봇 (getMe 프로브)
#
# ⚠️ 티스토리 세션은 "파일 최신성(24h)"이 아니라 실제 manage URL 프로브로 판정.
#    서버측 세션이 쿠키 expires(클라이언트측, 6일 뒤)보다 먼저 만료되므로
#    mtime 휴리스틱은 놓친다 (실측 2026-08-17: 5개 전부 302→login).
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="$BASE/.secrets.env"
TG="$BASE/tg.sh"

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

# ── 1. 티스토리 세션 (manage URL 실측) ──
echo ""
echo "[1] 티스토리 세션 (5블로그, 실측)"
TISTORY_RESULT=$(python3 - "$BASE" <<'PY'
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1]

# account→blog slug (ecosystem.json SSOT, 없으면 샘플 폴백)
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
    OK)      ok "티스토리 $acct — 세션 유효" ;;
    EXPIRED) fail "티스토리 $acct — 세션 만료(login 리다이렉트) → 재로그인 필요"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("티스토리 $acct 재로그인") ;;
    MISSING) fail "티스토리 $acct — state 없음 → 재로그인 필요"; FAIL_CNT=$((FAIL_CNT+1)); RENEW+=("티스토리 $acct 재로그인") ;;
    *)       warn "티스토리 $acct — 점검 불가 ($status)" ;;
  esac
done <<< "$TISTORY_RESULT"

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

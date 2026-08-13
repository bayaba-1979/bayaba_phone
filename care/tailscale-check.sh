#!/usr/bin/env bash
# ==============================================================================
# tailscale-check.sh — 돌봄 채널(Tailscale) 상태 확인 (on-demand, 비상주)
# ==============================================================================
# 사용법:
#   bash care/tailscale-check.sh              # 상태 확인 (실행할 때만 돎, 상주 없음)
#   bash care/tailscale-check.sh --telegram   # 확인 + 텔레그램 보고
#
# 결과: _notebook/health/tailscale-YYYY-MM-DD_HHMM.json (이력)
#       _notebook/health/tailscale-latest.json      (최신, 대시보드용 고정 경로)
#
# 원칙: 워치독(상주 데몬) 없음. Boss가 원할 때 한 번 실행하는 헬스체크식 스크립트.
#
# 2026-08-14 단일 노드 전환 — helena-proot(41641) 제거. helena-android(41642)만
#   점검. 모든 상태 조회는 bionic 소켓(--socket)으로.
# ==============================================================================

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HEALTH_DIR="${BASE_DIR}/_notebook/health"
NOW="$(date +%Y-%m-%d_%H%M)"
TS="$(date '+%Y-%m-%d %H:%M:%S')"
REPORT_FILE="${HEALTH_DIR}/tailscale-${NOW}.json"
LATEST_FILE="${HEALTH_DIR}/tailscale-latest.json"

# helena-android(bionic) 데몬 소켓 — 단일 노드
BIONIC_SOCK="/data/data/com.termux/files/usr/var/lib/tailscale/tailscaled.sock"

mkdir -p "$HEALTH_DIR"

# .secrets.env (API 키 — 선택적. 없으면 API 검증 생략, 나머지는 그대로 동작)
SECRETS="${BASE_DIR}/.secrets.env"
[ -f "$SECRETS" ] && set -a && source "$SECRETS" 2>/dev/null && set +a

# Termux PATH 선두 (tailscale 등) — native bionic `tailscale status`는 정상 동작
#   (SIGSYS는 `up`/`login` 등 clipboard import 경로만, status는 아님).
export PATH="/data/data/com.termux/files/usr/bin:$PATH"

OK="✅"; WARN="⚠️"; FAIL="❌"; INFO="ℹ️"
PASS_CNT=0; WARN_CNT=0; FAIL_CNT=0
ok()   { echo "  $OK $1"; PASS_CNT=$((PASS_CNT+1)); }
warn() { echo "  $WARN $1"; WARN_CNT=$((WARN_CNT+1)); }
fail() { echo "  $FAIL $1"; FAIL_CNT=$((FAIL_CNT+1)); }
info() { echo "  $INFO $1"; }
sect() { echo ""; echo "━━━ $* ━━━"; }

echo "📡 돌봄 채널(Tailscale) 상태 — $TS"

# 상태 변수 (JSON 보고용)
TERMUX_ALIVE="no"; BACKEND="?"; SSH_AD="no"; PEER_CNT=0

# ============================================================
# 1. tailscaled 프로세스 생존 (단일 노드 — Termux 41642)
# ============================================================

sect "1. tailscaled 프로세스"

# [t] 괄호 트릭: pgrep 자신/bash 자기매칭 방지
TERMUX_PID=$(pgrep -f '[t]ailscaled.*--port=41642' 2>/dev/null | head -1)

if [ -n "$TERMUX_PID" ]; then
  ok "helena-android tailscaled (PID $TERMUX_PID, port 41642)"
  TERMUX_ALIVE="yes"
else
  fail "helena-android tailscaled 죽음 (port 41642)"
fi

# ============================================================
# 2. helena-android 노드 상태 — 백엔드 / 온라인 / 태그 / SSH
# ============================================================

sect "2. helena-android 노드 상태"

if tailscale --socket="$BIONIC_SOCK" status --json > /tmp/ts_check.json 2>/dev/null; then
  eval "$(python3 - <<'PY'
import json
d = json.load(open('/tmp/ts_check.json'))
s = d.get('Self', {})
caps = s.get('Capabilities') or []
backend = d.get('BackendState', '?')
online = s.get('Online', False)
tags = s.get('Tags') or []
ssh = any('cap/ssh' in c for c in caps)
peer_cnt = len(d.get('Peer', {}))
print(f"BACKEND='{backend}'")
print(f"ONLINE='{str(online)}'")
print(f"TAGS='{','.join(tags)}'")
print(f"SSH_AD='{str(ssh)}'")
print(f"PEER_CNT={peer_cnt}")
PY
)"
  # 백엔드
  [ "$BACKEND" = "Running" ] && ok "backend Running" || fail "backend $BACKEND (재접속 필요)"
  # 온라인
  [ "$ONLINE" = "True" ] && ok "노드 온라인" || fail "노드 오프라인"
  # 태그
  [ "$TAGS" = "tag:helena" ] && ok "태그 tag:helena" || warn "태그 불일치: '${TAGS:-없음}'"
  # SSH 광고
  [ "$SSH_AD" = "True" ] && ok "SSH 서버 광고 중 (박씨 접속 가능)" || fail "SSH 광고 안 됨"
else
  fail "tailscale status 실패 (데몬 연결 안 됨)"
  BACKEND="down"
fi

# ============================================================
# 3. 인바운드 채널 — 박씨 기기가 보이는가
# ============================================================

sect "3. 인바운드 채널 (박씨 기기 가시성)"

PEERS=$(tailscale --socket="$BIONIC_SOCK" status 2>/dev/null | grep -cE 'REDACTED@' || true)
if [ "$PEERS" -ge 1 ] 2>/dev/null; then
  ok "박씨 기기 ${PEERS}대 가시 (박씨→S21 채널 정상)"
  PEER_CNT=$PEERS
else
  warn "박씨 기기 가시 0대 (인바운드 채널 의심 — tailnet 확인 필요)"
fi

# ============================================================
# 4. (선택) API — helena-android(Termux) 온라인 확인
# ============================================================

sect "4. helena-android(Termux) tailnet 온라인"

if [ -n "$TAILSCALE_API_KEY" ]; then
  curl -s -u "$TAILSCALE_API_KEY:" "https://api.tailscale.com/api/v2/tailnet/-/devices" \
    -o /tmp/ts_devices_check.json 2>/dev/null
  ANDROID_LASTSEEN=$(python3 - <<'PY'
import json
try:
    d = json.load(open('/tmp/ts_devices_check.json'))
except Exception:
    print(""); raise SystemExit
for dev in d.get('devices', []):
    if dev.get('hostname') == 'helena-android':
        print(dev.get('lastSeen', '')); break
PY
)
  if [ -n "$ANDROID_LASTSEEN" ]; then
    ok "helena-android tailnet 등록 확인 (lastSeen $ANDROID_LASTSEEN)"
  else
    warn "helena-android lastSeen 조회 실패 (API 응답 없음)"
  fi
else
  warn "API 키 없음 — helena-android tailnet 온라인은 프로세스 생존(1번)으로만 확인"
fi

# ============================================================
# 요약 + JSON 저장
# ============================================================

sect "요약"
if [ "$FAIL_CNT" -eq 0 ] && [ "$WARN_CNT" -eq 0 ]; then
  echo "  🟢 전부 정상 (${PASS_CNT}항목 통과)"
elif [ "$FAIL_CNT" -eq 0 ]; then
  echo "  🟡 경고 ${WARN_CNT}개 (통과 ${PASS_CNT})"
else
  echo "  🔴 실패 ${FAIL_CNT}개 (경고 ${WARN_CNT}, 통과 ${PASS_CNT})"
fi

cat > "$REPORT_FILE" <<JSON
{
  "type": "tailscale-check",
  "timestamp": "$TS",
  "pass": $PASS_CNT,
  "warn": $WARN_CNT,
  "fail": $FAIL_CNT,
  "termux_alive": "$TERMUX_ALIVE",
  "backend": "$BACKEND",
  "ssh_advertising": "$SSH_AD",
  "peer_count": $PEER_CNT
}
JSON
cp "$REPORT_FILE" "$LATEST_FILE"
info "이력: $REPORT_FILE"
info "최신: $LATEST_FILE"

# ============================================================
# 텔레그램 보고 (선택)
# ============================================================

if [ "$1" = "--telegram" ] || [ "$2" = "--telegram" ]; then
  if [ "$FAIL_CNT" -eq 0 ]; then
    MSG="✅ 돌봄 채널 정상 — helena-android 생존, backend Running, SSH 광고, 박씨 기기 ${PEER_CNT}대 가시 (통과 ${PASS_CNT})"
  else
    MSG="🔴 돌봄 채널 이상 — 실패 ${FAIL_CNT}개. termux생존=${TERMUX_ALIVE} backend=${BACKEND}"
  fi
  bash "$BASE_DIR/tg.sh" --no-button "$MSG" 2>/dev/null \
    && echo "  $OK 텔레그램 보고 전송" \
    || echo "  $WARN 텔레그램 전송 실패 (TG_TOKEN/TG_CHAT 확인)"
fi

echo ""

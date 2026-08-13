#!/data/data/com.termux/files/usr/bin/sh
# ==============================================================================
# start-tailscale-boot.sh — Tailscale 돌봄 데몬 부팅 자동 연결 (노드 2개)
# ==============================================================================
# 위치: Termux의 ~/.termux/boot/ 에 복사 (Termux:Boot 앱 필요)
#
# 동작: 폰 부팅 → Termux:Boot → 이 스크립트 → tailscaled 2개 기동
#   [1] helena-android — Termux 네이티브(bionic) tailscaled (proot 불필요, 가장 견고)
#   [2] helena-proot   — proot Ubuntu 안의 tailscaled (작업실 셸)
#   → 둘 다 REDACTED@(박씨 GitHub 망)에 저장된 노드키로 자동 재연결
#
# 핵심: proot/Termux 모두 권한 부족 → --tun=userspace-networking 필수.
#   재부팅엔 인증키 불필요 — 저장된 노드키가 자동 재접속 (2026-08-13 검증).
#   포트 분리: helena-android=41642, helena-proot=41641 (같은 네임스페이스 충돌 방지)
# ==============================================================================

# 0) 화면 꺼져도 CPU 깊은 잠 방지
termux-wake-lock 2>/dev/null || true

TS=/data/data/com.termux/files/usr

# [1] Termux 네이티브 tailscaled → helena-android (proot 없이 바로, 가장 견고)
if ! pgrep -f 'tailscaled.*--port=41642' >/dev/null 2>&1; then
  "$TS/bin/tailscaled" \
    --state="$TS/var/lib/tailscale/tailscaled.state" \
    --socket="$TS/var/lib/tailscale/tailscaled.sock" \
    --tun=userspace-networking \
    --port=41642 \
    >"$TS/var/lib/tailscale/tailscaled.log" 2>&1 &
  sleep 3
  "$TS/bin/tailscale" --socket="$TS/var/lib/tailscale/tailscaled.sock" \
    up --ssh --hostname=helena-android 2>/dev/null || true
fi

# [2] proot Ubuntu tailscaled → helena-proot (작업실 셸)
proot-distro login ubuntu -- bash -c '
  if pgrep -f "tailscaled.*--port=41641" >/dev/null 2>&1; then
    exit 0
  fi
  tailscaled --tun=userspace-networking --port=41641 >/var/log/tailscaled.log 2>&1 &
  sleep 3
  tailscale up --ssh --hostname=helena-proot 2>/dev/null || true
'

#!/usr/bin/env bash
# ==============================================================================
# start-proot-tailscale.sh — proot Ubuntu 안에서 실행 (helena-proot 데몬 + `up`)
# ==============================================================================
# boot 스크립트(~/.termux/boot/start-tailscale-boot.sh)가
#   proot-distro login ubuntu --no-kill-on-exit -- bash start-proot-tailscale.sh
# 로 호출. 이 스크립트가 종료된 뒤 proot이 "--no-kill-on-exit"으로 block되어
# glibc 데몬(41641)을 계속 살려둠 → 상주 keep-alive 루프 없이도 데몬 생존(CPU ~0).
#
# 하는 일 (전부 proot/glibc 맥락):
#   [A] helena-proot glibc tailscaled 데몬 기동 (port 41641, stale 소켓 정리)
#   [B] helena-proot `up` — glibc tailscale (기본 소켓)
#
#   (helena-android `up`은 여기서 안 함 — native 부팅 스크립트가 bionic 데몬이
#    살아난 순간 proot glibc CLI로 1회 실행. 정확히 준비된 시점에 up → 타임아웃
#    추측 불필요.)
#
# ==============================================================================
# 2026-08-13 정정 — native bionic `tailscale` CLI는 seccomp(faccessat2→SIGSYS)로
#   결정적으로 죽음. proot의 glibc `tailscale`는 bionic 데몬 소켓까지 제어 가능.
#
#   ⚠️ liveness/종료 판정은 `pgrep -f`/`pkill -f` 금지 — 부모 셸 cmdline에 패턴
#      문자열이 들어가면 오살 위험. → 소켓에 실제 연결(status)로 판정.
# ==============================================================================
# 2026-08-13 배터리 재설계 — 상주 keep-alive(60s wake) 루프 제거:
#   - 기존: helper가 60초마다 wake하며 데몬 유지 + up 재확인 → 상시 배터리 소모.
#   - 변경: proot-distro `--no-kill-on-exit`(proot 기본 block 동작)이 부모로
#     남아 데몬을 유지(CPU ~0). up은 최초 1회 — 성공하면 tailscaled가 netmon으로
#     자동 재연결하므로 재-up 불필요. → 통화 대기 수준(상시 wake 0) 달성.
# ==============================================================================

set -u

PROOT_PORT=41641
PROOT_SOCK=/var/run/tailscale/tailscaled.sock
PROOT_LOG=/var/log/tailscaled.log

# 특정 포트의 tailscaled PID를 찾음 (proot에선 간헐적 놓침 있음 — liveness는
# 아래 ensure_proot_daemon의 socket 연결로 판정하므로 여기선 좀비 정리용으로만).
daemon_pid() {
  pgrep -f "[t]tailscaled.*--port=$1" 2>/dev/null | head -1
}

# [A] proot 데몬 생존 보장 (멱등 — 서빙 중 판정은 소켓 실제 연결)
ensure_proot_daemon() {
  if tailscale --socket="$PROOT_SOCK" status >/dev/null 2>&1; then
    return 0
  fi
  # 좀비(프로세스만 살아있고 소켓 없음) 또는 죽음 → 강제 정리 후 재기동.
  ZPID=$(daemon_pid "$PROOT_PORT" 2>/dev/null)
  [ -n "$ZPID" ] && kill -9 "$ZPID" 2>/dev/null || true
  rm -f "$PROOT_SOCK" 2>/dev/null || true
  nohup tailscaled --tun=userspace-networking --port="${PROOT_PORT}" \
    --socket="$PROOT_SOCK" >> "$PROOT_LOG" 2>&1 &
  sleep 3
}

# node_running — 실제 backend 상태가 Running인지 (up 성공 여부가 아니라 상태가 목표)
node_running() {
  tailscale --socket="$1" status --json 2>/dev/null \
    | grep -qE '"BackendState"[[:space:]]*:[[:space:]]*"Running"'
}

# up_with_retry — 소켓이 준비되고 backend가 Running이 될 때까지 대기 (콜드 부팅 대비)
up_with_retry() {
  local sock="$1" host="$2" label="$3" max_wait="$4" waited=0
  # max_wait: 총 대기(초). 30초 간격으로 up 시도 + Running 확인.
  while [ "$waited" -lt "$max_wait" ]; do
    if [ -S "$sock" ]; then
      # up 실행(exit 무시 — "prefs write access denied"는 이미 Running일 때의 무해 응답).
      # 실제 목표는 backend Running이므로 status로 확인.
      tailscale --socket="$sock" up --ssh --hostname="$host" >/dev/null 2>&1 || true
      if node_running "$sock"; then
        echo "$label Running 확인 (대기 ${waited}s)"
        return 0
      fi
    fi
    sleep 30
    waited=$((waited + 30))
  done
  echo "[warn] $label Running 미도달 (${max_wait}s 경과 — 데몬 기동 확인 필요)"
  return 1
}

# ------------------------------------------------------------------------------
# [A]+[B] proot 데몬 생존 보장 + `up`
# ------------------------------------------------------------------------------
ensure_proot_daemon
up_with_retry "$PROOT_SOCK" "helena-proot" "helena-proot" 120

echo "proot helper 완료 (port ${PROOT_PORT} 데몬 + up)"

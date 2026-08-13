#!/usr/bin/env bash
# ==============================================================================
# start-proot-tailscale.sh — proot Ubuntu 안에서 실행 (helena-proot 데몬 + 양 노드 up)
# ==============================================================================
# boot 스크립트(~/.termux/boot/start-tailscale-boot.sh)가 proot-distro로 호출.
#
# 하는 일 (전부 proot/glibc 맥락):
#   [A] helena-proot  glibc tailscaled 데몬 기동 (port 41641, stale 소켓 정리)
#   [B] helena-proot  `up` — glibc tailscale (기본 소켓)
#   [C] helena-android `up` — glibc tailscale이 **bionic 데몬 소켓**을 직접 제어
#
# ==============================================================================
# 2026-08-13 정정 — native bionic `tailscale` CLI는 seccomp(faccessat2→SIGSYS)로
#   결정적으로 죽음. proot의 glibc `tailscale`는 bionic 데몬 소켓까지 제어 가능
#   (검증: `tailscale --socket=<bionic sock> up` exit=0, 버전 1.102.2 동일).
#   → 두 노드 `up`을 전부 여기서 glibc CLI로 처리해 SIGSYS를 원천 우회.
#
# 별도 파일로 분리한 이유: pgrep -f 패턴을 bash -c 인라인 문자열에서 돌리면
#   그 프로세스 cmdline에 패턴 문자열이 그대로 들어가 자기 자신을 매칭하는 버그.
#   스크립트 파일로 분리하면 cmdline엔 경로만 남아 자기매칭이 안 됨.
# ==============================================================================

set -u

# ------------------------------------------------------------------------------
# [A] helena-proot — glibc tailscaled 데몬 (port 41641)
# ------------------------------------------------------------------------------
PROOT_PORT=41641
PROOT_SOCK=/var/run/tailscale/tailscaled.sock
PROOT_LOG=/var/log/tailscaled.log

if pgrep -f "[t]ailscaled.*--port=${PROOT_PORT}" >/dev/null 2>&1; then
  echo "proot tailscaled 이미 실행 중 (port ${PROOT_PORT})"
else
  # 재부팅 직후 proot /run은 tmpfs 아님(영속) → 재부팅 전 stale 소켓이 바인딩 방해.
  rm -f "$PROOT_SOCK" 2>/dev/null || true
  nohup tailscaled --tun=userspace-networking --port="${PROOT_PORT}" \
    --socket="$PROOT_SOCK" >> "$PROOT_LOG" 2>&1 &
  sleep 3
fi

# ------------------------------------------------------------------------------
# [B] helena-proot `up` — glibc tailscale (기본 소켓)
# ------------------------------------------------------------------------------
tailscale up --ssh --hostname=helena-proot 2>/dev/null \
  && echo "helena-proot up 성공" \
  || echo "[warn] helena-proot up 실패"

# ------------------------------------------------------------------------------
# [C] helena-android `up` — glibc tailscale → bionic 데몬 소켓 직접 제어
#     (native bionic CLI는 SIGSYS로 죽으므로 여기서 glibc로 대체)
# ------------------------------------------------------------------------------
TERMUX_SOCK=/data/data/com.termux/files/usr/var/lib/tailscale/tailscaled.sock
tailscale --socket="$TERMUX_SOCK" up --ssh --hostname=helena-android 2>/dev/null \
  && echo "helena-android up 성공 (glibc CLI → bionic 소켓)" \
  || echo "[warn] helena-android up 실패 (bionic 데몬 기동 확인 필요)"

echo "proot helper 완료 (port ${PROOT_PORT} 데몬 + 양 노드 up)"

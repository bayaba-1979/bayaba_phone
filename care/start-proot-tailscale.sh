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
#   ⚠️ liveness/종료 판정은 `pgrep -f`/`pkill -f` 금지 — 부모 셸 cmdline에 패턴
#      문자열이 들어가면 오살 위험(실측: 테스트 중 내 셸이 pkill에 죽음).
#      → `pgrep -x tailscaled`(프로세스명 정확일치) + `/proc/PID/cmdline`의
#        `--port=` 필터로 안전하게 구분.
#
# 별도 파일로 분리한 이유: 부팅 스크립트와 분리해 cmdline 오염을 최소화.
# ==============================================================================

set -u

# ------------------------------------------------------------------------------
# [A] helena-proot — glibc tailscaled 데몬 (port 41641)
# ------------------------------------------------------------------------------
PROOT_PORT=41641
PROOT_SOCK=/var/run/tailscale/tailscaled.sock
PROOT_LOG=/var/log/tailscaled.log

# 특정 포트의 tailscaled PID를 찾음.
# `pgrep -f '[t]ailscaled.*--port=N'`: proot에서 검증된 신뢰 패턴(tailscale-check.sh와 동일).
#   - `[t]ailscaled` 괄호 트릭: pgrep 자신의 cmdline("[t]ailscaled")엔 "tailscaled"
#     부분문자열이 없어 자기매칭 방지.
#   - `pgrep -x`(프로세스명 일치)는 proot에서 간헐적으로 데몬을 놓침 → 사용 금지.
daemon_pid() {
  pgrep -f "[t]ailscaled.*--port=$1" 2>/dev/null | head -1
}

# 서빙 중 판정 = 소켓에 실제 연결(status) 시도. cmdline 매칭이 아니므로
#   부모/자기 셸 오살·오판 원천 차단 (pgrep -f는 좀비 종료에만 사용).
if tailscale --socket="$PROOT_SOCK" status >/dev/null 2>&1; then
  echo "proot tailscaled 이미 실행 중 (status 응답)"
else
  # 좀비(프로세스만 살아있고 소켓 없음) 또는 죽음 → 강제 정리 후 재기동.
  # 재부팅 직후 proot /run은 tmpfs 아님(영속) → 재부팅 전 stale 소켓이 바인딩 방해.
  ZPID=$(daemon_pid "$PROOT_PORT" 2>/dev/null)
  [ -n "$ZPID" ] && kill -9 "$ZPID" 2>/dev/null || true
  rm -f "$PROOT_SOCK" 2>/dev/null || true
  nohup tailscaled --tun=userspace-networking --port="${PROOT_PORT}" \
    --socket="$PROOT_SOCK" >> "$PROOT_LOG" 2>&1 &
  sleep 3
fi

# ------------------------------------------------------------------------------
# up_with_retry — 소켓이 준비될 때까지 대기하며 `up` 재시도 (콜드 부팅 대비)
#   (참고: SIGSYS와 무관. 여기 재시도는 "데몬이 소켓을 아직 안 만들었을 때"의
#    정상적인 타이밍 대기. native CLI의 결정적 SIGSYS 재시도와는 다름.)
# ------------------------------------------------------------------------------
up_with_retry() {
  local sock="$1" host="$2" label="$3" i
  for i in 1 2 3 4 5 6; do
    if [ -S "$sock" ]; then
      if tailscale --socket="$sock" up --ssh --hostname="$host" 2>&1; then
        echo "$label up 성공 (시도 ${i})"
        return 0
      fi
    fi
    if [ "$i" -lt 6 ]; then
      echo "[warn] $label 소켓 미준비/up 실패 (시도 ${i}/6) — 5초 대기"
      sleep 5
    fi
  done
  echo "[warn] $label up 최종 실패 (데몬 기동 확인 필요)"
  return 1
}

# ------------------------------------------------------------------------------
# [B] helena-proot `up` — glibc tailscale (기본 소켓)
# ------------------------------------------------------------------------------
up_with_retry "$PROOT_SOCK" "helena-proot" "helena-proot"

# ------------------------------------------------------------------------------
# [C] helena-android `up` — glibc tailscale → bionic 데몬 소켓 직접 제어
#     (native bionic CLI는 SIGSYS로 죽으므로 여기서 glibc로 대체)
# ------------------------------------------------------------------------------
TERMUX_SOCK=/data/data/com.termux/files/usr/var/lib/tailscale/tailscaled.sock
up_with_retry "$TERMUX_SOCK" "helena-android" "helena-android"

echo "proot helper 완료 (port ${PROOT_PORT} 데몬 + 양 노드 up)"

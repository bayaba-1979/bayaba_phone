#!/data/data/com.termux/files/usr/bin/sh
# ==============================================================================
# start-tailscale-boot.sh — Tailscale 돌봄 데몬 부팅 자동 연결
# ==============================================================================
# 위치: Termux의 ~/.termux/boot/ 에 복사 (Termux:Boot 앱 필요)
#   cp ~/storage/shared/.../start-tailscale-boot.sh ~/.termux/boot/
#   chmod +x ~/.termux/boot/start-tailscale-boot.sh
#
# 동작: 폰 부팅 → Termux:Boot → 이 스크립트 → proot에서 tailscaled 기동
#   → 저장된 노드키로 자동 재연결 (2026-08-13 재부팅 시뮬레이션으로 증명)
#   → SSH + 호스트명(helena-proot) 설정 자동 복원
#
# 핵심: proot은 권한 0개라 --tun=userspace-networking 필수.
#   인증키/로그인 재입력 불필요 — 저장된 노드키가 자동 재접속.
# ==============================================================================

# 1) 화면 꺼져도 CPU 깊은 잠 방지
termux-wake-lock 2>/dev/null || true

# 2) proot에서 tailscaled 기동 (userspace-networking 필수)
proot-distro login ubuntu -- bash -c '
  # 이미 돌고 있으면 스킵
  if pgrep -x tailscaled >/dev/null 2>&1; then
    exit 0
  fi

  # 데몬 기동
  tailscaled --tun=userspace-networking >/var/log/tailscaled.log 2>&1 &
  sleep 3

  # 설정 보장 (호스트명 + SSH — 비파괴, 이미 설정돼 있으면 no-op)
  tailscale up --ssh --hostname=helena-proot 2>/dev/null || true
'

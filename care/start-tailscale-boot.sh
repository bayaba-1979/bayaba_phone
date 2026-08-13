#!/data/data/com.termux/files/usr/bin/sh
# ==============================================================================
# start-tailscale-boot.sh — Tailscale 돌봄 데몬 부팅 자동 연결 (노드 2개)
# ==============================================================================
# 위치: Termux의 ~/.termux/boot/ 에 복사 (Termux:Boot 앱이 부팅 시 실행)
#
# 동작: 폰 부팅 → Termux:Boot → 이 스크립트 → tailscaled 2개 기동
#   [1] helena-android — Termux 네이티브(bionic) tailscaled **데몬**만 여기서 기동
#   [2] helena-proot   — proot Ubuntu의 glibc 데몬 + 두 노드 `up` 전부 (helper 호출)
#
# ==============================================================================
# 2026-08-13 정정 — "레이어별 재검토"로 밝혀낸 진짜 원인 (이전 fix 전면 교체):
#
#   ❌ 기존 오진: "tailscale up SIGSYS = 1회성" → 3회 재시도로 때우려 함. 틀림.
#   ✅ 실제: SIGSYS는 **결정적**(매 회차). bionic `tailscale` CLI가 init 단계에서
#      `github.com/atotto/clipboard`를 import → `exec.LookPath` → `faccessat2`
#      (syscall 439) 호출 → Android untrusted_app seccomp-bpf가 SIGSYS로 죽임.
#      → CLI는 네이티브에서 무조건 죽음. **proot 경유 필수** (proot이 ptrace로
#        syscall을 번역하므로 seccomp 필터에 안 걸림).
#
#   ✅ 실제: `tailscaled` **데몬**은 clipboard 미사용 → SIGSYS 없음. 죽는 원인은
#      **stale 소켓**(재부팅에도 /var/lib/tailscale/*.sock 잔존 → 데몬이 "TPM: error"
#      직후 멈춤). → 기동 전 `rm -f`로 정리하면 네이티브에서 정상.
#
#   ✅ 두 노드 `up`은 전부 proot의 **glibc tailscale**로 실행. glibc CLI는
#      bionic 데몬 소켓까지 제어 가능(검증: `tailscale --socket=<bionic sock> up` exit=0).
#
#   ⚠️ 데몬 liveness 판정은 `pgrep -f "패턴"` 금지 — 부모 셸 cmdline에 패턴 문자열이
#      들어가면 자기/부모 오살 위험. → `pgrep -x tailscaled`(프로세스명 정확일치)
#      + `/proc/PID/cmdline`의 `--port=` 필터로 안전하게 구분.
# ==============================================================================

TS=/data/data/com.termux/files/usr
# ⚠️ $TS = Termux PREFIX(.../usr). 홈은 .../files/home (PREFIX와 다름!).
#   $TS/home 은 존재하지 않아 redirect 실패 → 로그 유실 + `[2]` proot-distro 자체가
#   실행 안 되는 버그(2026-08-13 19:52 재부팅에서 실측). 절대경로로 고정.
BOOTLOG=/data/data/com.termux/files/home/tailscale-boot.log

# 특정 포트의 tailscaled PID를 찾기 (proot 검증 패턴 `pgrep -f '[t]ailscaled...'`)
find_ts_pid() {
  pgrep -f "[t]ailscaled.*--port=$1" 2>/dev/null | head -1
}

# 0) 부팅 로그 시작 마커 — 이 줄이 남으면 Termux:Boot 정상 수신 확인
UPTIME_S=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
echo "[$(date '+%F %T')] boot script START (uptime ${UPTIME_S:-?}s)" >> "$BOOTLOG" 2>&1

# 화면 꺼져도 CPU 깊은 잠 방지 (실패해도 계속 진행)
"$TS/bin/termux-wake-lock" >> "$BOOTLOG" 2>&1 || echo "[warn] termux-wake-lock 실패" >> "$BOOTLOG"

# ==============================================================================
# [1] helena-android — Termux 네이티브(bionic) tailscaled **데몬** (port 41642)
#     데몬은 clipboard 미사용 → SIGSYS 없음. stale 소켓만 rm -f로 정리.
#     `up`은 여기서 안 함 — proot helper가 glibc CLI로 처리.
# ==============================================================================
TS_STATE="$TS/var/lib/tailscale/tailscaled.state"
TS_SOCK="$TS/var/lib/tailscale/tailscaled.sock"
TS_LOG="$TS/var/lib/tailscale/tailscaled.log"

TS_PID=$(find_ts_pid 41642 | head -1)

if [ -S "$TS_SOCK" ] && [ -n "$TS_PID" ]; then
  echo "[$(date '+%F %T')] [1] Termux tailscaled 이미 실행 중 (소켓+프로세스 정상)" >> "$BOOTLOG"
else
  echo "[$(date '+%F %T')] [1] Termux tailscaled 기동 (port 41642)" >> "$BOOTLOG"
  # 좀비(프로세스만 살아있고 소켓 없음) 또는 죽음 → 강제 정리 후 재기동.
  # 재부팅 전 stale 소켓 제거 (영속 디렉터리라 잔존).
  [ -n "$TS_PID" ] && kill -9 "$TS_PID" 2>/dev/null || true
  rm -f "$TS_SOCK" 2>/dev/null || true
  # nohup: 부팅 스크립트 종료 시 SIGHUP/프로세스그룹 정리로 데몬이 휩쓸리지 않게 탈부착.
  nohup "$TS/bin/tailscaled" \
    --state="$TS_STATE" \
    --socket="$TS_SOCK" \
    --tun=userspace-networking \
    --port=41642 \
    >> "$TS_LOG" 2>&1 &
  sleep 3
fi

# ==============================================================================
# [2] helena-proot glibc 데몬 기동 + 두 노드 `up` 전부 → proot helper에서 처리.
#     (glibc `tailscale` CLI로 bionic/proot 양쪽 소켓 제어 — native bionic CLI는
#      SIGSYS로 죽기 때문에 여기서 절대 `tailscale up` 네이티브 호출 금지)
# ==============================================================================
echo "[$(date '+%F %T')] [2] proot(glibc) 데몬 + 양 노드 up 기동 (helper 호출)" >> "$BOOTLOG"
timeout 90 "$TS/bin/proot-distro" login ubuntu -- \
  bash /root/work/care/start-proot-tailscale.sh >> "$BOOTLOG" 2>&1 \
  || echo "[warn] proot-distro 실행 실패 (시간초과/미설치)" >> "$BOOTLOG"

echo "[$(date '+%F %T')] boot script END" >> "$BOOTLOG" 2>&1

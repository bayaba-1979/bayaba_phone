#!/data/data/com.termux/files/usr/bin/sh
# ==============================================================================
# start-tailscale-boot.sh — Tailscale 돌봄 데몬 부팅 자동 연결 (단일 노드)
# ==============================================================================
# 위치: Termux의 ~/.termux/boot/ 에 복사 (Termux:Boot 앱이 부팅 시 실행)
#
# 2026-08-14 「100점 최적화」 — 듀얼 노드 → 단일 노드 전환:
#   ❌ helena-proot(proot/glibc, 41641) 제거.
#      - 돌봄 목표엔 노드 1개면 충분. 작업실 셸은 helena-android(Termux) 경유로
#        동일 접근 가능 (`proot-distro login ubuntu` 1홉).
#      - proot 노드가 오늘(08-13) 재부팅 버그의 근원 — SIGSYS·--kill-on-exit·
#        keepalive·netmon 타이밍 전부 proot 겹층 탓. 제거 = 고장 여지 최소화.
#   ✅ helena-android(bionic 네이티브, 41642)만 유지.
#   ✅ `up` 의존성 제거 — tailscaled.state가 node key+prefs(hostname·ssh)를 보존
#      → 재기동 시 자동 재연결. (실증 08-14: kill+재기동만으로 up 없이 40초 내
#      BackendState=Running, 동일 identity 복원.)
#
# 결과 상주 프로세스 = tailscaled 1개 + wake-lock 20분 한정.
#   proot · glibc tailscaled · keepalive 루프 전부 제거 → 통화 대기 수준 배터리.
#
# 동작: 부팅 → wake-lock → tailscaled 1개 기동(멱등, netmon 정착까지 재시도) → 끝.
#   - 콜드 부팅 netmon 정착(1~15분) 동안 tailscaled가 netmon.New "netlinkrib:
#     permission denied"로 죽음 → 살아남을 때까지 재시도(무한). 살아남으면 state로
#     자동 재연결하므로 `up` 불필요.
# ==============================================================================

TS=/data/data/com.termux/files/usr
# ⚠️ $TS = Termux PREFIX(.../usr). 홈은 .../files/home (PREFIX와 다름!).
#   $TS/home 은 존재하지 않아 redirect 실패 → 로그 유실. 절대경로로 고정.
BOOTLOG=/data/data/com.termux/files/home/tailscale-boot.log

# 특정 포트의 tailscaled PID를 찾기 (native Termux의 pgrep는 정상 동작)
find_ts_pid() {
  pgrep -f "[t]tailscaled.*--port=$1" 2>/dev/null | head -1
}

# 0) 부팅 로그 시작 마커 — 이 줄이 남으면 Termux:Boot 정상 수신 확인
UPTIME_S=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
echo "[$(date '+%F %T')] boot script START (uptime ${UPTIME_S:-?}s)" >> "$BOOTLOG" 2>&1

# 화면 꺼져도 CPU 깊은 잠 방지 (실패해도 계속 진행)
"$TS/bin/termux-wake-lock" >> "$BOOTLOG" 2>&1 || echo "[warn] termux-wake-lock 실패" >> "$BOOTLOG"

# ⚠️ 배터리: wake-lock은 부팅 정착(최악 ~15분)에만 필요. 20분 후 자동 해제 —
#   무한 유지로 CPU 깊은잠이 막히면 "통화 대기 수준" 배터리를 못 지킴.
(
  trap '' HUP INT TERM 2>/dev/null
  sleep 1200
  "$TS/bin/termux-wake-unlock" >> "$BOOTLOG" 2>&1 || true
  echo "[$(date '+%F %T')] wake-lock 해제 (부팅 정착 20분 경과)" >> "$BOOTLOG"
) >> "$BOOTLOG" 2>&1 &

# ==============================================================================
# [1] helena-android — Termux 네이티브(bionic) tailscaled (port 41642)
#     데몬은 clipboard 미사용 → SIGSYS 없음. stale 소켓만 rm -f로 정리.
#     살아나면 state 파일로 자동 재연결 → `up` 불필요(proot 의존 제거).
# ==============================================================================
TS_STATE="$TS/var/lib/tailscale/tailscaled.state"
TS_SOCK="$TS/var/lib/tailscale/tailscaled.sock"
TS_LOG="$TS/var/lib/tailscale/tailscaled.log"

TS_PID=$(find_ts_pid 41642 | head -1)

if [ -S "$TS_SOCK" ] && [ -n "$TS_PID" ]; then
  echo "[$(date '+%F %T')] [1] tailscaled 이미 실행 중 (소켓+프로세스 정상) — 기동 생략" >> "$BOOTLOG"
else
  echo "[$(date '+%F %T')] [1] tailscaled 기동 (port 41642, netmon 정착까지 무한 재시도)" >> "$BOOTLOG"
  # 콜드 부팅 직후 bionic tailscaled가 netmon.New "netlinkrib: permission denied"로
  # 죽는 일시현상(정착 1~15분 가변). 횟수 제한 없이 성공할 때까지 재시도. 붙으면
  # 루프 자체가 exit → 상주 없음(배터리 임팩 0). nohup+trap으로 부팅 스크립트 종료
  # (~1초)에 휩쓸리지 않게 탈부착.
  (
    trap '' HUP INT TERM 2>/dev/null
    TRY=0
    while true; do
      TRY=$((TRY+1))
      # 좀비(프로세스만 살아있고 소켓 없음) 또는 이전 시도 잔재 → 강제 정리 후 재기동.
      # 재부팅 전 stale 소켓 제거 (영속 디렉터리라 잔존).
      ZPID=$(find_ts_pid 41642 | head -1)
      [ -n "$ZPID" ] && kill -9 "$ZPID" 2>/dev/null || true
      rm -f "$TS_SOCK" 2>/dev/null || true
      nohup "$TS/bin/tailscaled" \
        --state="$TS_STATE" \
        --socket="$TS_SOCK" \
        --tun=userspace-networking \
        --port=41642 \
        >> "$TS_LOG" 2>&1 &
      DAEMON_PID=$!
      sleep 8
      # 생존 확인: 프로세스가 살아있으면 netmon.New 성공 = 이후 자동 재연결(state).
      #   → 루프 종료. 죽었으면(netmon 미정착) 재시도.
      if [ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo "[$(date '+%F %T')] [1] tailscaled 기동 성공 (시도 $TRY, PID $DAEMON_PID) — state 자동 재연결" >> "$BOOTLOG"
        exit 0
      fi
      # 30회마다 1줄 로그 — 영구 실패 판별용(재시도 멈춤 없음).
      if [ $((TRY % 30)) -eq 0 ]; then
        echo "[$(date '+%F %T')] [warn] tailscaled 재시도 $TRY회째 — netmon 미정착 (재시도 지속)" >> "$BOOTLOG"
      fi
    done
  ) >> "$BOOTLOG" 2>&1 &
fi

echo "[$(date '+%F %T')] boot script END" >> "$BOOTLOG" 2>&1

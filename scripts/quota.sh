#!/usr/bin/env bash
# ==============================================================================
# quota.sh — 오늘 남은 쿼터 (콘텐츠 양산 일일 한도 요약)
# ==============================================================================
# 한도 SSOT: configs/quota-manifest.json (history_batch.py 와 공유)
# 티스토리는 RSS 실측(history_batch.today_published_count 재사용)으로
# "오늘 발행 N / 한도 15 → 남은 M"을 동적으로 계산. 나머지는 정적 안내.
#
# 사용법:
#   bash scripts/quota.sh          # 표만 출력
#   bash scripts/quota.sh --tg     # 결과를 텔레그램으로도 보고 (tg.sh 사용)
#
# 스코프: 콘텐츠 1인 미디어 자동화만. 돌봄(Tailscale·돌봄데몬)은 제외.
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
TG="$BASE/tg.sh"

# ── 한 번의 python 실행으로 표 전체 생성 (티스토리 RSS는 1회만 fetch) ──
OUT=$(python3 - "$BASE" <<'PY'
import json
import sys

BASE = sys.argv[1]

with open(f"{BASE}/configs/quota-manifest.json", encoding="utf-8") as f:
    m = json.load(f)

lines = []

# [1] 티스토리 — 동적 (RSS 실측, history_batch 로직 재사용)
sys.path.insert(0, f"{BASE}/tistory-naver")
try:
    from history_batch import today_published_count, DAILY_LIMIT
    used = today_published_count()
    rem = max(0, DAILY_LIMIT - used)
    lines.append(f"[티스토리] 오늘 {used}개 발행 · 한도 {DAILY_LIMIT}개/계정 → 남은 {rem}개")
except Exception as e:
    lines.append(f"[티스토리] 집계 실패: {e}")

# [2] 유튜브 — 정적 (정확한 잔여는 Cloud Console)
yt = m["youtube"]
lines.append(
    f"[유튜브] 업로드당 {yt['units_per_upload']} units · 일일 {yt['units_per_day']} units "
    f"→ 약 {yt['approx_uploads_per_day']}건/일 (잔여=Cloud Console)"
)

# [3] Threads — 정적 (미배선·수작업)
th = m["threads"]
lines.append(f"[Threads] {th['chars_per_post']}자/글 · {th['limit_per_day']} API글/일 (미배선·수작업)")

# [4] 네이버 — 수작업
lines.append(f"[네이버] {m['naver']['note']}")

print("\n".join(lines))
PY
)

echo "════════════════════════════════════════"
echo "  📊 오늘 남은 쿼터 (콘텐츠 양산)"
echo "════════════════════════════════════════"
echo ""
echo "$OUT"
echo ""
echo "════════════════════════════════════════"

# ── 텔레그램 보고 (--tg) ──
if [ "${1:-}" = "--tg" ] && [ -x "$TG" ]; then
  bash "$TG" --no-button "📊 오늘 남은 쿼터 (콘텐츠 양산)

$OUT" >/dev/null 2>&1 && echo "" && echo "📤 텔레그램 보고 완료"
fi

exit 0

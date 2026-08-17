#!/usr/bin/env bash
# ==============================================================================
# make_pair.sh — 원자재(_notebook/*.md) → PWA+티스토리 페어 발행 단일 엔트리
# ==============================================================================
# BOM 공정 Phase 1 페어 생성기:
#   PWA 레인    : check_webpages_Grok.py(gap) → build_webzine.py → gap=0 게이트 → push
#   Tistory 레인: director_gate.py(심사) → history_batch.py --run(발행)
#
# 사용법:
#   bash scripts/make_pair.sh              # preflight → PWA + Tistory 전부
#   bash scripts/make_pair.sh --pwa        # PWA 레인만
#   bash scripts/make_pair.sh --tistory    # 티스토리 레인만
#   bash scripts/make_pair.sh --skip-preflight
#   bash scripts/make_pair.sh --tg         # 완료 보고 (텔레그램)
#
# 검증 3층 (공법):
#   1. 테이블 세터(preflight.sh) — 세션·토큰 사전 점검 (FAIL 이면 중단)
#   2. 쿼터 — 티스토리 남은 일일 한도 0 이면 발행 중단
#   3. gap_count=0 — PWA 페이지 누락 시 배포 금지
#
# 스코프: 콘텐츠 1인 미디어 자동화만. 돌봄(Tailscale·돌봄데몬) 제외.
# ==============================================================================

set -uo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

DO_PWA=0; DO_TIS=0; SKIP_PRE=0; USE_TG=0
for a in "$@"; do
  case "$a" in
    --pwa)           DO_PWA=1 ;;
    --tistory)       DO_TIS=1 ;;
    --skip-preflight) SKIP_PRE=1 ;;
    --tg)            USE_TG=1 ;;
  esac
done
# 아무 레인도 지정 안 하면 둘 다
if [ "$DO_PWA" -eq 0 ] && [ "$DO_TIS" -eq 0 ]; then DO_PWA=1; DO_TIS=1; fi

echo "════════════════════════════════════════"
echo "  🔗 make_pair — PWA+티스토리 페어 발행"
echo "════════════════════════════════════════"

FAIL=0
MSG=()

# ── 1. 테이블 세터 (preflight) ──
if [ "$SKIP_PRE" -eq 0 ]; then
  echo ""
  echo "→ [1/3] 테이블 세터 (preflight) 점검..."
  if ! bash "$BASE/scripts/preflight.sh"; then
    echo "❌ preflight 실패 — 소모성 자산(세션·토큰) 갱신 후 재실행"
    exit 1
  fi
fi

# ── 2. PWA 레인 ──
if [ "$DO_PWA" -eq 1 ]; then
  echo ""
  echo "→ [2/3] PWA 웹페이지 빌드"
  python3 "$BASE/scripts/check_webpages_Grok.py" || true   # 빌드 전 gap 보고
  python3 "$BASE/scripts/build_webzine.py" >/dev/null
  GAP=$(python3 "$BASE/scripts/check_webpages_Grok.py" 2>/dev/null | grep -oP 'gap_count=\K\d+' | head -1)
  if [ "${GAP:-1}" -ne 0 ]; then
    echo "❌ PWA gap_count=${GAP} — 페이지 누락 (NOTEBOOK_TITLES 보완 필요) → 배포 금지"
    FAIL=1
  else
    echo "✅ PWA gap_count=0"
    git add notebook archive.html index.html sitemap.xml \
            assets/webpage-coverage.json assets/catalog.json 2>/dev/null
    if git diff --cached --quiet; then
      echo "ℹ 커밋할 PWA 변경 없음"
    else
      git commit -q -m "translation: PWA 페어 빌드 — notebook 페이지 + 커버리지 갱신"
      git -c credential.helper='!gh auth git-credential' push >/dev/null 2>&1 \
        && echo "✅ PWA 푸시 완료" || { echo "❌ PWA 푸시 실패"; FAIL=1; }
    fi
    MSG+=("PWA ✅")
  fi
fi

# ── 3. Tistory 레인 ──
if [ "$DO_TIS" -eq 1 ]; then
  echo ""
  echo "→ [3/3] 티스토리 디렉터 게이트 + 발행"
  BUDGET=$(python3 - "$BASE" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/tistory-naver")
try:
    from history_batch import remaining_budget
    print(remaining_budget())
except Exception:
    print(-1)
PY
)
  if [ "${BUDGET:-0}" -le 0 ]; then
    echo "❌ 티스토리 오늘 남은 한도 0개 — 내일(KST 자정 이후) 재실행"
    FAIL=1
  else
    echo "ℹ 오늘 남은 한도 ${BUDGET}개"
    python3 "$BASE/tistory-naver/director_gate.py" >/dev/null
    python3 "$BASE/tistory-naver/history_batch.py" --run \
      && MSG+=("Tistory ✅") || { echo "❌ 티스토리 발행 실패"; FAIL=1; }
  fi
fi

# ── 요약 + 텔레그램 보고 ──
echo ""
echo "════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo "  ✅ 페어 발행 완료"
else
  echo "  ❌ 일부 실패 — 위 로그 확인"
fi
echo "════════════════════════════════════════"

if [ "$USE_TG" -eq 1 ] && [ -x "$BASE/tg.sh" ]; then
  if [ "$FAIL" -eq 0 ]; then
    SUMMARY="✅ make_pair 완료 — $(printf '%s ' "${MSG[@]}")"
  else
    SUMMARY="❌ make_pair 일부 실패 — 로그 확인"
  fi
  bash "$BASE/tg.sh" --no-button "$SUMMARY" >/dev/null 2>&1 \
    && echo "📤 텔레그램 보고 완료"
fi

exit "$FAIL"

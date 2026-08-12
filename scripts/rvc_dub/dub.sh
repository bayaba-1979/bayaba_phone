#!/usr/bin/env bash
# ============================================================
# RVC 성우 더빙 파이프라인
#   Edge TTS (여성 베이스) → RVC 음색 변환 → MP3
#
# 사용법:
#   bash scripts/rvc_dub/dub.sh <텍스트파일> [출력이름]
#   bash scripts/rvc_dub/dub.sh -t "안녕하세요" [출력이름]
#
# 예시:
#   bash scripts/rvc_dub/dub.sh apostles.txt apostles
#   bash scripts/rvc_dub/dub.sh -p taesoon 대본.txt
#
# 환경변수 (선택):
#   DUB_PROFILE      → 음성 프로필명 (~/rvc_models/<name>/profile.json)
#   DUB_RVC_MODEL    → RVC .onnx 모델 경로 (--profile 있으면 무시됨)
#   DUB_RVC_INDEX    → RVC .index 경로 (--profile 있으면 무시됨)
#   DUB_EDGE_VOICE   → Edge TTS 음성 (기본값: ko-KR-SunHiNeural)
#   DUB_EDGE_RATE    → Edge TTS 속도 (기본값: -8%)
#   DUB_SEND_TG      → 완료 후 텔레그램 전송 (기본값: 1)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── 설정 ──────────────────────────────────────────────────
TEXT=""
NAME="dub_output"

if [ "${1:-}" = "-t" ]; then
    TEXT="${2:?텍스트를 입력하세요}"
    NAME="${3:-dub_output}"
elif [ "${1:-}" = "-p" ]; then
    PROFILE="${2:?프로필명을 입력하세요}"
    TEXT_FILE="${3:?텍스트 파일을 입력하세요}"
    NAME="${4:-$(basename "$TEXT_FILE" .txt)}"
    TEXT="$(cat "$TEXT_FILE")"
else
    TEXT_FILE="${1:?텍스트 파일 또는 -t '텍스트' 또는 -p <프로필> <파일>}"
    NAME="${2:-$(basename "$TEXT_FILE" .txt)}"
    TEXT="$(cat "$TEXT_FILE")"
fi

# 프로필
PROFILE="${DUB_PROFILE:-${PROFILE:-}}"

# 음성 설정 (기본: 여성 베이스)
VOICE="${DUB_EDGE_VOICE:-ko-KR-SunHiNeural}"
RATE="${DUB_EDGE_RATE:--8%}"

# RVC 모델
RVC_MODEL="${DUB_RVC_MODEL:-}"
RVC_INDEX="${DUB_RVC_INDEX:-}"

# 출력 디렉토리
OUT_DIR="$REPO_ROOT/_dub/${NAME}"
mkdir -p "$OUT_DIR"

# ── 실행 ──────────────────────────────────────────────────
echo "🎙️  RVC 더빙: ${NAME}"
echo "    베이스 음성: ${VOICE} (${RATE})"
echo "    RVC 모델:    $(basename "$RVC_MODEL")"
echo ""

PROFILE_ARG=""
RVC_MODEL_ARG=""
RVC_INDEX_ARG=""
if [ -n "${PROFILE:-}" ]; then
    PROFILE_ARG="--profile $PROFILE"
else
    RVC_MODEL="${RVC_MODEL:-$REPO_ROOT/voice_models/rvc/parksy.onnx}"
    RVC_INDEX="${RVC_INDEX:-$HOME/rvc_models/parksy_rvc/parksy_rvc.index}"
    RVC_MODEL_ARG="--rvc-model $RVC_MODEL"
    RVC_INDEX_ARG="--rvc-index $RVC_INDEX"
fi

python3 "$SCRIPT_DIR/dub.py" \
    --text "$TEXT" \
    --name "$NAME" \
    --out-dir "$OUT_DIR" \
    --voice "$VOICE" \
    --rate "$RATE" \
    $PROFILE_ARG \
    $RVC_MODEL_ARG \
    $RVC_INDEX_ARG

# ── 텔레그램 ──────────────────────────────────────────────
if [ "${DUB_SEND_TG:-1}" = "1" ]; then
    FINAL_MP3="$OUT_DIR/${NAME}.mp3"
    if [ -f "$FINAL_MP3" ]; then
        # 텍스트 보고
        MSG="🎙️ ${NAME} 더빙 완료!\n베이스: ${VOICE} (${RATE})\nRVC: $(basename "$RVC_MODEL")"
        bash "$REPO_ROOT/tg.sh" "$MSG" 2>/dev/null || true

        # 오디오 파일
        export $(grep -v '^#' "$REPO_ROOT/.secrets.env" | xargs) 2>/dev/null || true
        python3 -c "
import requests, os
token = os.environ.get('TG_TOKEN', '')
chat_id = os.environ.get('TG_CHAT', '')
if token and chat_id:
    with open('$FINAL_MP3', 'rb') as f:
        r = requests.post(f'https://api.telegram.org/bot{token}/sendAudio', data={
            'chat_id': chat_id,
            'title': '${NAME}',
            'caption': '🎙️ ${NAME} 더빙\n${VOICE} → RVC\n#더빙 #RVC'
        }, files={'audio': ('${NAME}.mp3', f, 'audio/mpeg')})
    print('✅ 텔레그램 전송 완료' if r.status_code == 200 else f'❌ {r.status_code}')
" 2>/dev/null || echo "(텔레그램 전송 스킵 — 토큰 없음)"
    fi
fi

echo ""
echo "━━━ 완료: $OUT_DIR/${NAME}.mp3 ━━━"

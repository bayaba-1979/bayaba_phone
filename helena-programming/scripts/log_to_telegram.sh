#!/bin/bash
# 📨 log_to_telegram.sh — helana_log .md → Telegram 전송 (표준: 마크다운, 선택: HTML)
#
# 사용 위치: GitHub Actions (helana_log repo) 또는 S21 로컬
# 요구: TG_TOKEN, TG_CHAT 환경변수
#
# 사용법:
#   # 기본: .md 파일을 Telegram 첨부파일(sendDocument)로 전송
#   bash log_to_telegram.sh logs/2026/08/some-log.md
#
#   # HTML 모드: MD→HTML 변환 → .txt 원본 첨부 전송 (v5.1: 안드로이드 텍스트 편집기 열림)
#   bash log_to_telegram.sh --html logs/2026/08/some-log.md
#
#   # git diff로 변경된 .md 파일 전부 처리
#   bash log_to_telegram.sh --diff
#   bash log_to_telegram.sh --diff --html
#
#   # workflow_dispatch에서 파일 목록 받아 처리
#   bash log_to_telegram.sh --files '["a.md","b.md"]'
#   bash log_to_telegram.sh --files '["a.md","b.md"]' --html

set -euo pipefail

# ── 설정 ──────────────────────────────────────────
TOKEN="${TG_TOKEN:-}"
CHAT="${TG_CHAT:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONVERTER="${SCRIPT_DIR}/parksy_to_html.py"
CHUNK_SIZE=3800

# ── 색상 ──────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ── 인자 파싱 ─────────────────────────────────────
MODE="file"
FILES_JSON=""
HTML_MODE=false

# 인자 순회하며 --html 플래그와 파일 목록 분리
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --html) HTML_MODE=true; shift ;;
    --diff) MODE="diff"; shift ;;
    --files) MODE="files"; FILES_JSON="$2"; shift 2 ;;
    *) args+=("$1"); shift ;;
  esac
done

if [ ${#args[@]} -gt 0 ]; then
  MODE="file"
  INPUT_FILE="${args[0]}"
fi

if [ "$MODE" = "file" ] && [ -z "${INPUT_FILE:-}" ]; then
  echo "사용법: bash log_to_telegram.sh [--html] <file.md> | --diff | --files '[...]'"
  echo "  기본: .md 파일을 Telegram 첨부파일로 전송 (Tistory 마크다운 모드)"
  echo "  --html: HTML 변환 후 .html 원본 첨부 전송 (Tistory HTML 모드)"
  exit 1
fi

# ── 의존성 확인 ──────────────────────────────────
if [ -z "$TOKEN" ] || [ -z "$CHAT" ]; then
  echo -e "${RED}❌ TG_TOKEN 또는 TG_CHAT 환경변수 없음${NC}"
  exit 1
fi

if $HTML_MODE; then
  if [ ! -f "$CONVERTER" ]; then
    CONVERTER="./_converter/scripts/parksy_to_html.py"
    if [ ! -f "$CONVERTER" ]; then
      echo -e "${RED}❌ parksy_to_html.py 찾을 수 없음 (--html 모드 필요)${NC}"
      exit 1
    fi
  fi
fi

# ── 파일 목록 수집 ────────────────────────────────
get_files() {
  if [ "$MODE" = "diff" ]; then
    git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -E '\.md$' | grep -E '^(logs/|docs/dialogue/)' || true
  elif [ "$MODE" = "files" ]; then
    echo "$FILES_JSON" | python3 -c "
import sys, json
files = json.load(sys.stdin)
for f in files:
    print(f)
" 2>/dev/null || true
  else
    echo "$INPUT_FILE"
  fi
}

# ── 공통: 텍스트 청크 분할 → Telegram 전송 ─────────
# 내부 헬퍼: stdin에서 텍스트를 읽어 청크 분할 후 Telegram 전송
_send_chunks_py() {
  local header_text="$1"
  python3 -c "
import sys, requests, time

token = '${TOKEN}'
chat = '${CHAT}'
header = '''${header_text}'''
chunk_size = ${CHUNK_SIZE}

text = sys.stdin.read()

# split at newline boundaries
chunks = []
remaining = text
while len(remaining) > chunk_size:
    cut = remaining.rfind('\n', 0, chunk_size)
    if cut < chunk_size // 2:
        cut = chunk_size
    chunks.append(remaining[:cut])
    remaining = remaining[cut:]
chunks.append(remaining)

total = len(chunks)

# header
resp = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={
    'chat_id': chat, 'text': header, 'parse_mode': 'HTML',
}).json()
if not resp.get('ok'):
    print(f'HEADER FAIL: {resp.get(\"description\",\"?\")}')

for i, chunk in enumerate(chunks):
    tag = f'/* PART {i+1}/{total} */\\n' if i > 0 else ''
    resp = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={
        'chat_id': chat, 'text': tag + chunk,
    }, timeout=15).json()
    ok = resp.get('ok')
    print(f'{\"✅\" if ok else \"❌\"} PART {i+1}/{total}')
    if not ok:
        print(f'   ERROR: {resp.get(\"description\",\"?\")}')
    if i < total - 1:
        time.sleep(0.35)

print(f'DONE {total} chunks')
"
}

send_text_chunks() {
  local content_file="$1"
  local header="$2"
  cat "$content_file" | _send_chunks_py "$header"
}

# ── 모드 1: 마크다운 파일 첨부 전송 (기본) ─────────
send_markdown() {
  local md_file="$1"
  local fname
  fname="$(basename "$md_file")"

  echo "📝 마크다운 첨부 전송: $fname"

  # 메타데이터 추출
  local title line_count
  title=$(head -30 "$md_file" | grep -m1 '^# ' | sed 's/^# //' || echo "$fname")
  line_count=$(wc -l < "$md_file")

  # 헤더 메시지 + 파일 첨부 (sendDocument)
  python3 -c "
import requests

token = '${TOKEN}'
chat = '${CHAT}'
fname = '${fname}'
title = '''${title}'''
line_count = ${line_count}
file_path = '${md_file}'

# 헤더 메시지
requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={
    'chat_id': chat,
    'text': f'📄 <b>{title}</b>\\n📝 마크다운 · {line_count}줄 · Tistory 마크다운 모드 붙여넣기\\n⬇️ 아래 첨부파일 다운로드 → 전체 복사 → 붙여넣기',
    'parse_mode': 'HTML',
})

# 파일 첨부
with open(file_path, 'rb') as f:
    resp = requests.post(
        f'https://api.telegram.org/bot{token}/sendDocument',
        data={'chat_id': chat, 'caption': f'{fname} — {line_count}줄'},
        files={'document': (fname, f, 'text/markdown')},
        timeout=30
    ).json()

if resp.get('ok'):
    print('✅ 파일 첨부 전송 완료')
else:
    print(f'❌ {resp.get(\"description\",\"?\")}')
    sys.exit(1)
"
  echo -e "${GREEN}✅ 마크다운 전송 완료: $fname${NC}"
}

# ── 모드 2: HTML 변환 → 원본 .html 첨부 (--html) ─
send_html() {
  local md_file="$1"
  # v5.1: .txt 확장자 — 안드로이드에서 텍스트 편집기로 열림 (브라우저 렌더링 방지)
  local fname
  fname="$(basename "$md_file" .md).txt"
  local out_file="/tmp/${fname}"

  echo "🔧 HTML 변환: $md_file → $out_file"

  if ! python3 "$CONVERTER" "$md_file" --out "$out_file" 2>&1; then
    echo -e "${RED}❌ HTML 변환 실패: $md_file${NC}"
    return 1
  fi

  local turn_count line_count title
  turn_count=$(grep -c '<details class="turn' "$out_file" 2>/dev/null || echo "?")
  line_count=$(wc -l < "$out_file")
  title=$(head -30 "$md_file" | grep -m1 '^# ' | sed 's/^# //' || echo "$fname")

  # HTML 원본 파일 첨부 전송
  python3 -c "
import requests

token = '${TOKEN}'
chat = '${CHAT}'

requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={
    'chat_id': chat,
    'text': f'📄 <b>{title}</b>\\n🔄 {turn_count}턴 · ${line_count}줄 · Tistory <b>HTML 모드</b> 붙여넣기\\n⬇️ 아래 첨부파일 다운로드 → 전체 복사 → Tistory HTML 모드에 붙여넣기',
    'parse_mode': 'HTML',
})

with open('${out_file}', 'rb') as f:
    resp = requests.post(
        f'https://api.telegram.org/bot{token}/sendDocument',
        data={'chat_id': chat, 'caption': f'${fname} — 전체 복사 → Tistory HTML 모드 붙여넣기'},
        files={'document': ('${fname}', f, 'text/plain')},
        timeout=30
    ).json()

if resp.get('ok'):
    print('✅ HTML 첨부 전송 완료')
else:
    print(f'❌ {resp.get(\"description\",\"?\")}')
    sys.exit(1)
"
  echo -e "${GREEN}✅ HTML 전송 완료: $fname${NC}"
}

# ── 메인 ───────────────────────────────────────────
FILES=$(get_files)

if [ -z "$FILES" ]; then
  echo -e "${YELLOW}⚠️  변경된 .md 파일 없음 — 건너뜀${NC}"
  exit 0
fi

PROCESSED=0
FAILED=0

while IFS= read -r md_file; do
  [ -z "$md_file" ] && continue
  [ ! -f "$md_file" ] && { echo -e "${YELLOW}⚠️  파일 없음: $md_file${NC}"; continue; }

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📄 파일: $md_file ($($HTML_MODE && echo 'HTML 모드' || echo 'MD 모드'))"

  if $HTML_MODE; then
    if send_html "$md_file"; then
      PROCESSED=$((PROCESSED + 1))
    else
      FAILED=$((FAILED + 1))
    fi
  else
    send_markdown "$md_file"
    PROCESSED=$((PROCESSED + 1))
  fi

done <<< "$FILES"

# ── 최종 보고 ─────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
MODE_LABEL=$($HTML_MODE && echo "HTML" || echo "마크다운")
FINAL_MSG="📊 <b>로그 → Telegram 전송 완료</b> (${MODE_LABEL})%0A✅ ${PROCESSED}건 성공"
if [ "$FAILED" -gt 0 ]; then
  FINAL_MSG="${FINAL_MSG} · ❌ ${FAILED}건 실패"
fi
FINAL_MSG="${FINAL_MSG}%0A🔗 <a href='https://github.com/helena751107/helana_log'>helana_log</a>"

curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id="$CHAT" \
  -d text="$FINAL_MSG" \
  -d parse_mode="HTML" \
  -d disable_web_page_preview="true" \
  > /dev/null

echo -e "${GREEN}완료. 모드=${MODE_LABEL} 처리=${PROCESSED} 실패=${FAILED}${NC}"

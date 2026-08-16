#!/usr/bin/env bash
# ==============================================================================
# navigator.sh — S21 생태계 설정 마법사 (내비게이터)
# ==============================================================================
# "복사붙여넣기하면 바로 구동" 의 출발점.
# 이 스크립트가 하는 일:
#   ① GitHub 계정 확인 (`gh auth`)
#   ② owner(명의) · 5블로그 slug · 2채널 handle 수집
#   ③ BotFather / Google Cloud Console / Discord 발급법 안내 + 값 붙여넣기
#   ④ configs/ecosystem.json + .secrets.env 생성 (둘 다 gitignore)
#   ⑤ 스폰 전 dry-run 요약 (실제 스폰은 g/spawn.sh 가 수행)
#
# 사용법:
#   bash navigator.sh            # 대화형 마법사
#   bash navigator.sh --check    # 비대화형 dry-run (기존 ecosystem.json 검증+스폰 목록)
#   bash navigator.sh --secrets  # 시크릿만 다시 입력 (.secrets.env 재생성)
#
# 원칙: 시크릿은 .secrets.env 에만, 매핑은 ecosystem.json 에만. PAT 는 gh auth 로.
# ==============================================================================

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$BASE/configs"
TEMPLATE="$CONFIG_DIR/ecosystem.json.template"
REAL="$CONFIG_DIR/ecosystem.json"
SECRETS="$BASE/.secrets.env"
SECRETS_TEMPLATE="$CONFIG_DIR/secrets-template.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${BLUE}📌${NC} $*"; }
step() { echo ""; echo -e "${CYAN}${BOLD}── $* ──${NC}"; }

banner() {
  echo ""
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  🧭 S21 생태계 내비게이터${NC}"
  echo -e "${BOLD}  GitHub 사용자명 + 슬러그 몇 개 + 시크릿 → 바로 구동${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo ""
}

# ── 대화형 입력 헬퍼 (기본값 있음) ──────────────────────────────────────────
# prompt "질문" "기본값" → 표준출력으로 답 출력 (빈 입력 = 기본값)
prompt() {
  local q="$1" def="$2" ans=""
  if [ -n "$def" ]; then
    printf "  ${BOLD}%s${NC} [%s]: " "$q" "$def"
  else
    printf "  ${BOLD}%s${NC}: " "$q"
  fi
  IFS= read -r ans || true
  if [ -z "$ans" ] && [ -n "$def" ]; then ans="$def"; fi
  printf '%s' "$ans"
}

# 비밀번호 등 화면에 안 보이게
prompt_secret() {
  local q="$1" ans=""
  printf "  ${BOLD}%s${NC} (입력 안 보임): " "$q"
  IFS= read -rs ans || true
  echo ""
  printf '%s' "$ans"
}

# ── 0단계: gh auth ──────────────────────────────────────────────────────────
ensure_gh_auth() {
  step "0. GitHub 인증"
  if ! command -v gh >/dev/null 2>&1; then
    warn "gh CLI 없음. 설치: https://cli.github.com/  (또는 apt install gh)"
    warn "PAT 를 파일에 넣지 않는 유일한 안전한 길은 gh auth 입니다."
    return 0
  fi
  if gh auth status >/dev/null 2>&1; then
    ok "gh 인증됨: $(gh auth status 2>&1 | grep -oE 'Logged in to [^ ]+' | head -1 || echo 'ok')"
  else
    warn "gh 미인증 — 로그인을 안내합니다."
    echo "  브라우저가 열리면 코드 입력:"
    echo "  $ gh auth login"
    echo ""
    if [ -t 0 ]; then
      printf "  지금 실행할까요? [Y/n]: "
      read -r do_auth || true
      if [ "$do_auth" != "n" ] && [ "$do_auth" != "N" ]; then
        gh auth login
      fi
    fi
  fi
}

# ── 1단계: owner + 매핑 ─────────────────────────────────────────────────────
collect_mapping() {
  step "1. 명의(owner) + 블로그/채널 매핑"

  local owner_default
  owner_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE')).get('owner','helena751107'))" 2>/dev/null || echo helena751107)"
  OWNER="$(prompt "GitHub 사용자명/조직 (명의)" "$owner_default")"
  ok "owner = $OWNER"

  echo ""
  info "블로그/채널 slug 를 지금 바꿀까요? (템플릿엔 헬레나 실측 샘플값이 들어 있음)"
  printf "  ${BOLD}바꿀까요?${NC} [N/y]: "
  read -r do_map || true
  if [ "$do_map" = "y" ] || [ "$do_map" = "Y" ]; then
    ADVANCED=1
  else
    ADVANCED=0
    warn "샘플 매핑 유지 — configs/ecosystem.json 생성 후 직접 편집 가능"
  fi
}

# 대화형으로 각 레포 blog, 각 채널 handle 수집 (python 이 순서로 읽음)
collect_map_details() {
  [ "$ADVANCED" = "1" ] || return 0
  step "1a. 블로그 slug 5개"

  local repo_names blogs="" h="" c
  repo_names="$(python3 -c "import json;print('\n'.join(r['repo'] for r in json.load(open('$TEMPLATE'))['repos']))")"
  NAV_BLOGS=""
  while IFS= read -r c; do
    [ -z "$c" ] && continue
    local cur
    cur="$(python3 -c "import json;[print(r['blog']) for r in json.load(open('$TEMPLATE'))['repos'] if r['repo']=='$c']")"
    h="$(prompt "  ${c} → 티스토리 블로그 slug" "$cur")"
    NAV_BLOGS="${NAV_BLOGS}${h}"$'\n'
  done <<< "$repo_names"

  step "1b. 채널 handle 2개"
  local ch_names
  ch_names="$(python3 -c "import json;print('\n'.join(c['key']+': '+c['handle'] for c in json.load(open('$TEMPLATE'))['channels']))")"
  NAV_HANDLES=""
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    local key="${line%%:*}" cur_h="${line#*: }"
    h="$(prompt "  ${key} 채널 handle" "$cur_h")"
    NAV_HANDLES="${NAV_HANDLES}${h}"$'\n'
  done <<< "$ch_names"
}

# ── 2단계: git 신원 (선택) ──────────────────────────────────────────────────
collect_git() {
  step "2. git 봇 신원 (커밋 작성자 — 보통 기본값 유지)"
  local gname_default gemail_default
  gname_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE'))['git']['name'])")"
  gemail_default="$(python3 -c "import json;print(json.load(open('$TEMPLATE'))['git']['email'])")"
  GIT_NAME="$(prompt "  커밋 작성자 이름" "$gname_default")"
  GIT_EMAIL="$(prompt "  커밋 작성자 이메일" "$gemail_default")"
}

# ── 3단계: 시크릿 ───────────────────────────────────────────────────────────
collect_secrets() {
  step "3. 시크릿 (발급 안내 후 붙여넣기 — 빈 칸 = 스킵, 나중에 채움)"

  echo ""
  info "── 3a. Telegram 봇 (보고 무전기) ──"
  echo "  1) 텔레그램에서 @BotFather 검색 → /newbot"
  echo "  2) 봇 이름/아이디(끝이 bot) 지정 → 'Use this token' 토큰 복사"
  echo "  3) 내 봇에게 아무 메시지 전송 → @userinfobot 에게 '내 id' 물어 숫자 ID 확인"
  SECRET_TG_TOKEN="$(prompt_secret "  TG_TOKEN (BotFather 토큰)")"
  SECRET_TG_CHAT="$(prompt_secret "  TG_CHAT (채팅방 숫자 ID)")"

  echo ""
  info "── 3b. 티스토리 (자동 발행 로그인) ──"
  echo "  카카오 계정 이메일/비번 — post.py 가 세션 쿠키 발급에 사용"
  SECRET_TISTORY_EMAIL="$(prompt "  TISTORY_EMAIL" "")"
  SECRET_TISTORY_PW="$(prompt_secret "  TISTORY_PW")"

  echo ""
  info "── 3c. YouTube (Google Cloud Console) ──"
  echo "  1) https://console.cloud.google.com → 프로젝트 생성"
  echo "  2) 'API 및 서비스' → 라이브러리 → 'YouTube Data API v3' 사용 설정"
  echo "  3) 'OAuth 동의 화면' 구성(외부) → '사용자 인증 정보' → 'OAuth 2.0 클라이언트 ID'"
  echo "     애플리케이션 유형 = 데스크톱 앱 → 클라이언트 ID/시크릿 복사"
  echo "  (액세스/리프레시 토큰은 최초 업로드 시 scripts/yt_oauth_setup.sh 가 자동 발급)"
  SECRET_YT_CLIENT_ID="$(prompt "  YOUTUBE_CLIENT_ID" "")"
  SECRET_YT_CLIENT_SECRET="$(prompt_secret "  YOUTUBE_CLIENT_SECRET")"

  echo ""
  info "── 3d. Discord (선택 — 보고 웹훅/봇) ──"
  echo "  1) https://discord.com/developers/applications → New Application → Bot → Reset Token"
  echo "  2) Discord 설정 → 고급 → 개발자 모드 ON → 채널/서버 우클릭 → ID 복사"
  SECRET_DISCORD_BOT_TOKEN="$(prompt_secret "  DISCORD_BOT_TOKEN")"
  SECRET_DISCORD_CHANNEL_ID="$(prompt "  DISCORD_CHANNEL_ID" "")"
  SECRET_DISCORD_SERVER_ID="$(prompt "  DISCORD_SERVER_ID" "")"

  echo ""
  info "── 3e. Tailscale (선택 — 원격 접속) ──"
  echo "  https://login.tailscale.com/admin → Settings → Keys → Generate auth key"
  SECRET_TAILSCALE_AUTH_KEY="$(prompt_secret "  TAILSCALE_AUTH_KEY")"
}

# ── 4단계: 파일 생성 ────────────────────────────────────────────────────────
write_ecosystem() {
  step "4. configs/ecosystem.json 생성"
  NAV_OWNER="$OWNER" \
  NAV_GIT_NAME="$GIT_NAME" \
  NAV_GIT_EMAIL="$GIT_EMAIL" \
  NAV_BLOGS="${NAV_BLOGS:-}" \
  NAV_HANDLES="${NAV_HANDLES:-}" \
  NAV_TEMPLATE="$TEMPLATE" \
  NAV_REAL="$REAL" \
  python3 << 'PYEOF'
import json, os
tmpl = json.load(open(os.environ["NAV_TEMPLATE"], encoding="utf-8"))
tmpl["owner"] = os.environ.get("NAV_OWNER", tmpl.get("owner", "")).strip()

if os.environ.get("NAV_GIT_NAME"):
    tmpl.setdefault("git", {})["name"] = os.environ["NAV_GIT_NAME"].strip()
if os.environ.get("NAV_GIT_EMAIL"):
    tmpl.setdefault("git", {})["email"] = os.environ["NAV_GIT_EMAIL"].strip()

blogs = [l for l in os.environ.get("NAV_BLOGS", "").splitlines() if l.strip()]
if blogs:
    for r, b in zip(tmpl.get("repos", []), blogs):
        r["blog"] = b.strip()

handles = [l for l in os.environ.get("NAV_HANDLES", "").splitlines() if l.strip()]
if handles:
    for c, h in zip(tmpl.get("channels", []), handles):
        # handle 이 바뀌면 기존 channel id 는 무효 → 비우고 후속 안내
        if c.get("handle", "").strip() != h.strip():
            c["id"] = ""
        c["handle"] = h.strip()

os.makedirs(os.path.dirname(os.environ["NAV_REAL"]), exist_ok=True)
with open(os.environ["NAV_REAL"], "w", encoding="utf-8") as f:
    json.dump(tmpl, f, ensure_ascii=False, indent=2)
print(f"  ✅ {os.environ['NAV_REAL']} 작성")
PYEOF
  ok "ecosystem.json 생성 완료"
}

write_secrets() {
  step "5. .secrets.env 생성"
  # 스키마를 읽고, 입력받은 값만 채워 넣는다 (나머지 키는 빈 자리 유지)
  SECRET_TG_TOKEN="${SECRET_TG_TOKEN:-}" \
  SECRET_TG_CHAT="${SECRET_TG_CHAT:-}" \
  SECRET_TISTORY_EMAIL="${SECRET_TISTORY_EMAIL:-}" \
  SECRET_TISTORY_PW="${SECRET_TISTORY_PW:-}" \
  SECRET_YT_CLIENT_ID="${SECRET_YT_CLIENT_ID:-}" \
  SECRET_YT_CLIENT_SECRET="${SECRET_YT_CLIENT_SECRET:-}" \
  SECRET_DISCORD_BOT_TOKEN="${SECRET_DISCORD_BOT_TOKEN:-}" \
  SECRET_DISCORD_CHANNEL_ID="${SECRET_DISCORD_CHANNEL_ID:-}" \
  SECRET_DISCORD_SERVER_ID="${SECRET_DISCORD_SERVER_ID:-}" \
  SECRET_TAILSCALE_AUTH_KEY="${SECRET_TAILSCALE_AUTH_KEY:-}" \
  SECRETS_TEMPLATE="$SECRETS_TEMPLATE" \
  SECRETS="$SECRETS" \
  python3 << 'PYEOF'
import os, re
src = open(os.environ["SECRETS_TEMPLATE"], encoding="utf-8").read()
overrides = {
    "TG_TOKEN": os.environ.get("SECRET_TG_TOKEN", ""),
    "TG_CHAT": os.environ.get("SECRET_TG_CHAT", ""),
    "TISTORY_EMAIL": os.environ.get("SECRET_TISTORY_EMAIL", ""),
    "TISTORY_PW": os.environ.get("SECRET_TISTORY_PW", ""),
    "YOUTUBE_CLIENT_ID": os.environ.get("SECRET_YT_CLIENT_ID", ""),
    "YOUTUBE_CLIENT_SECRET": os.environ.get("SECRET_YT_CLIENT_SECRET", ""),
    "DISCORD_BOT_TOKEN": os.environ.get("SECRET_DISCORD_BOT_TOKEN", ""),
    "DISCORD_CHANNEL_ID": os.environ.get("SECRET_DISCORD_CHANNEL_ID", ""),
    "DISCORD_SERVER_ID": os.environ.get("SECRET_DISCORD_SERVER_ID", ""),
    "TAILSCALE_AUTH_KEY": os.environ.get("SECRET_TAILSCALE_AUTH_KEY", ""),
}
for key, val in overrides.items():
    if val:
        src = re.sub(rf'^({key}=)(".*"|)$', rf'\g<1>"{val}"', src, flags=re.M)
with open(os.environ["SECRETS"], "w", encoding="utf-8") as f:
    f.write(src)
print(f"  ✅ {os.environ['SECRETS']} 작성 (빈 키는 나중에 직접 채움)")
PYEOF
  chmod 600 "$SECRETS" 2>/dev/null || true
  ok ".secrets.env 생성 완료 (권한 600)"
}

# ── 5단계: dry-run 요약 ─────────────────────────────────────────────────────
dry_run_summary() {
  step "6. 스폰 전 요약 (dry-run)"
  echo -e "  ${BOLD}owner:${NC} $(python3 "$CONFIG_DIR/../scripts/load_ecosystem.py" --json owner 2>/dev/null || echo "$OWNER")"
  echo ""
  python3 - << PYEOF
import json, subprocess, sys, os
sys.path.insert(0, "$BASE/scripts")
from load_ecosystem import repos, channels
print("  스폰될 레포:")
for r in repos():
    print(f"    gh repo create $OWNER/{r['repo']} --template helena751107/{r['repo']} --public   # {r['blog']} → {r['channel']}")
print("")
print("  시크릿 배선 (gh secret set -R):")
print("    TG_TOKEN · TG_CHAT · TISTORY_EMAIL · TISTORY_PW · YOUTUBE_CLIENT_ID · YOUTUBE_CLIENT_SECRET")
print("")
print("  다음 단계:")
print("    bash g/spawn.sh        # 위성 4레포 생성 + 시크릿 배선 (gh CLI 필요)")
print("    bash g/install.sh      # 워크스페이스 구축 (Termux/proot/Claude)")
PYEOF
  echo ""
  info "스폰은 g/spawn.sh, 워크스페이스는 g/install.sh 가 수행합니다 (navigator 는 '설정'만)."
  warn "시크릿은 절대 git 에 올라가지 않도록 .gitignore 확인 (git status)."
}

# ── --check (비대화형 dry-run) ──────────────────────────────────────────────
mode_check() {
  banner
  info "비대화형 dry-run — ecosystem.json 검증 + 스폰 목록"
  echo ""
  if [ -f "$REAL" ]; then
    ok "configs/ecosystem.json 존재 (사용자 설정)"
  else
    warn "configs/ecosystem.json 없음 → 템플릿(샘플) 사용"
  fi
  echo ""
  python3 "$BASE/scripts/load_ecosystem.py" --check
  echo ""
  if [ -f "$SECRETS" ]; then
    local filled
    filled="$(grep -cE '="[^"]+"' "$SECRETS" 2>/dev/null || echo 0)"
    ok ".secrets.env 존재 (값 채워진 키 ${filled}개)"
  else
    warn ".secrets.env 없음 → bash navigator.sh 로 생성"
  fi
  echo ""
  info "스폰 명령 미리보기 (owner 기준):"
  local own
  own="$(python3 "$BASE/scripts/load_ecosystem.py" --json owner)"
  python3 - << PYEOF
import sys
sys.path.insert(0, "$BASE/scripts")
from load_ecosystem import repos
own = "$own"
for r in repos():
    print(f"  gh repo create {own}/{r['repo']} --template helena751107/{r['repo']} --public")
PYEOF
}

# ── main ────────────────────────────────────────────────────────────────────
main() {
  case "${1:-}" in
    --check) mode_check; return 0 ;;
    --secrets) banner; ensure_gh_auth; collect_secrets; write_secrets; return 0 ;;
  esac

  banner
  ensure_gh_auth
  collect_mapping
  collect_map_details
  collect_git
  collect_secrets
  write_ecosystem
  write_secrets
  dry_run_summary
}

main "$@"

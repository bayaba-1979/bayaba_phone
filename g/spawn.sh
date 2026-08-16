#!/usr/bin/env bash
# ==============================================================================
# g/spawn.sh — 스폰 엔진 (ecosystem.json → GitHub 레포 생성 + 시크릿 배선)
# ==============================================================================
# navigator.sh 가 만든 configs/ecosystem.json 을 읽어:
#   ① 허브(helena_phone) 를 GitHub Template Repo 로 표시
#   ② 위성 4레포(piano/metalcare/faith/log) 를 템플릿에서 복사 생성 (--public)
#   ③ .secrets.env 의 TG_TOKEN/TG_CHAT 을 각 레포 GitHub Actions 시크릿으로 배선
#
# 사용법:
#   bash g/spawn.sh              # 실행 (idempotent — 이미 있으면 스킵)
#   bash g/spawn.sh --dry-run    # 무엇을 할지 미리보기만 (실행 안 함)
#
# 원칙: PAT 를 넣지 않음 — gh auth 로 인증. 시크릿은 gh secret set (값은 파일에 안 남김).
# ==============================================================================

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$BASE/scripts"
REAL="$BASE/configs/ecosystem.json"
SECRETS="$BASE/.secrets.env"
TEMPLATE_OWNER="${TEMPLATE_OWNER:-helena751107}"   # 보일러플레이트 원본 소유자

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${BLUE}📌${NC} $*"; }

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

# ── 로더: owner / hub / 위성 목록 ───────────────────────────────────────────
owner()   { python3 "$SCRIPTS/load_ecosystem.py" --json owner; }
hub_repo() { python3 -c "import sys;sys.path.insert(0,'$SCRIPTS');from load_ecosystem import hub_repo;print(hub_repo())"; }

# 위성 레포(role != hub) 목록을 "repo<TAB>blog" 로 출력
satellites() {
  python3 - "$SCRIPTS" << 'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[1])
from load_ecosystem import repos
for r in repos():
    if r.get("role") != "hub":
        print(f"{r['repo']}\t{r.get('blog','')}")
PYEOF
}

require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    fail "gh CLI 없음 — https://cli.github.com/ 설치 후 gh auth login"
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    fail "gh 미인증 — 먼저 'gh auth login' 실행 (PAT 파일 비커밋 원칙)"
    exit 1
  fi
  ok "gh 인증 확인"
}

exists() { gh repo view "$1" >/dev/null 2>&1; }

mark_hub_template() {
  local hub="$1"
  if [ "$DRY" = "1" ]; then
    info "dry-run: gh repo edit ${OWNER}/${hub} --template"
    return 0
  fi
  if exists "${OWNER}/${hub}"; then
    gh repo edit "${OWNER}/${hub}" --template 2>/dev/null \
      && ok "템플릿 표시: ${OWNER}/${hub}" \
      || warn "템플릿 표시 실패(이미 표시됐을 수 있음): ${OWNER}/${hub}"
  else
    warn "허브 레포 없음: ${OWNER}/${hub} (use-this-template 으로 먼저 생성하세요)"
  fi
}

spawn_satellites() {
  while IFS=$'\t' read -r repo blog; do
    [ -z "$repo" ] && continue
    if [ "$DRY" = "1" ]; then
      info "dry-run: gh repo create ${OWNER}/${repo} --template ${TEMPLATE_OWNER}/${repo} --public   # → ${blog}"
      continue
    fi
    if exists "${OWNER}/${repo}"; then
      ok "이미 있음: ${OWNER}/${repo} (스킵)"
    else
      info "생성: ${OWNER}/${repo} ← ${TEMPLATE_OWNER}/${repo}"
      gh repo create "${OWNER}/${repo}" --template "${TEMPLATE_OWNER}/${repo}" --public \
        && ok "생성 완료: ${OWNER}/${repo}" \
        || warn "생성 실패(권한/템플릿 확인): ${OWNER}/${repo}"
    fi
  done < <(satellites)
}

set_secrets() {
  # .secrets.env 에서 TG 값 읽기 (없으면 스킵)
  local tg_token="" tg_chat=""
  if [ -f "$SECRETS" ]; then
    tg_token="$(sed -nE 's/^TG_TOKEN="?([^"]*)"?$/\1/p' "$SECRETS")"
    tg_chat="$(sed -nE 's/^TG_CHAT="?([^"]*)"?$/\1/p' "$SECRETS")"
  fi
  [ -z "$tg_token" ] && { warn "TG_TOKEN 없음 — 시크릿 배선 스킵 (bash navigator.sh --secrets)"; return 0; }

  # 배선 대상 = 허브 + 모든 위성
  local repos_list="$1
$(satellites | cut -f1)"
  local repo
  while IFS= read -r repo; do
    [ -z "$repo" ] && continue
    if [ "$DRY" = "1" ]; then
      info "dry-run: gh secret set TG_TOKEN -R ${OWNER}/${repo} / TG_CHAT -R ${OWNER}/${repo}"
      continue
    fi
    exists "${OWNER}/${repo}" || { warn "레포 없음(스킵): ${OWNER}/${repo}"; continue; }
    printf '%s' "$tg_token" | gh secret set TG_TOKEN -R "${OWNER}/${repo}" \
      && printf '%s' "$tg_chat" | gh secret set TG_CHAT -R "${OWNER}/${repo}" \
      && ok "시크릿 배선: ${OWNER}/${repo} (TG_TOKEN/TG_CHAT)" \
      || warn "시크릿 배선 실패: ${OWNER}/${repo}"
  done <<< "$repos_list"
}

# ── main ────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BOLD}═══ 스폰 엔진 (ecosystem.json → GitHub) ═══${NC}"
  echo ""

  if [ ! -f "$REAL" ]; then
    warn "configs/ecosystem.json 없음 — bash navigator.sh 로 먼저 생성"
    warn "템플릿(${REAL}.template) 기준으로 진행합니다."
  fi

  OWNER="$(owner)"
  HUB="$(hub_repo)"
  info "owner=${OWNER}  hub=${HUB}  template_owner=${TEMPLATE_OWNER}"

  if [ "$DRY" = "1" ]; then
    info "── dry-run (실행 안 함) ──"
    echo ""
  else
    require_gh
  fi

  mark_hub_template "$HUB"
  echo ""
  spawn_satellites
  echo ""
  set_secrets "$HUB"

  echo ""
  if [ "$DRY" = "1" ]; then
    info "위 내용을 실제로 하려면: bash g/spawn.sh"
  else
    ok "스폰 완료. 각 레포의 Pages/워크플로는 GitHub 에서 확인."
    info "드리프트 동기화는 중앙 reusable workflow(uses: helena751107/...) 가 자동 처리."
  fi
}

main "$@"

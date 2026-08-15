#!/usr/bin/env python3
"""
director_gate.py — 디렉터 게이트 (Phase 2 품질)

Phase 1(배선 인프라) 끝 → Phase 2(품질). 업로드 "이전"에 디렉터(출판부 _Claude)가
각 원고를 심사하고 판정·제목·태그·카테고리를 확정한다.

판정(verdict):
  PASS    — 그대로 발행 (제목·태그 자동정리만)
  CLEAN   — 제목 자동정리(번호 프리픽스 등) 후 발행
  REVISE  — 제목 재작성 필요 (내부용어·영문 전용·H1 없음) → 보류, 디렉터 override 대기
  HOLD    — 발행 보류 (세션·연대기·중복 구버전·진단 로그 등 교재 아님)

산출물:
  assets/director-overrides.json   — SSOT (판정·최종제목·태그·카테고리)
  assets/director-gate-report.md   — 사람용 심사표

소비처:
  history_batch.py  — HOLD/REVISE 건너뛰고 PASS/CLEAN 만 발행, override 제목·태그 사용

실행:
  python3 director_gate.py              # 전체 110개 심사 + overrides 갱신
  python3 director_gate.py --report     # 사람용 markdown 심사표만 출력
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent
ROUTE = ROOT / "assets" / "publish-route.json"
OVERRIDES = ROOT / "assets" / "director-overrides.json"
REPORT = ROOT / "assets" / "director-gate-report.md"

sys.path.insert(0, str(BASE))
from history_category_map import history_category_for  # noqa: E402

# ── 판정 규칙 (디렉터의 편집 기준) ──────────────────────────────────────────
# 내부 전용어 — 교재 제목에 있으면 외부 검색 의도와 불일치 → 제목 재작성(REVISE)
INTERNAL_JARGON = [
    "dtslib", "REDACTED", "helena751107", "mynote11605",
    "Director PRO", "Director Community", "Director Plan", "Director Vision",
    "Scout v", "A-bar", "리줌", "허들", "재발일지", "세션", "플러그인 영상 파이프",
    "Video Plugin Standard", "Imagine 프롬프트", "Perfect Ship",
    "세션 복구", "session", "노트북", "업무 수첩",
]

# 발행 보류(HOLD) — 교재가 아니라 내부 산출물·진단·중복 구버전
HOLD_REASONS: dict[str, str] = {
    "17-merged-chronicle.md":        "민감 병합 연대기",
    "99-devlog.md":                  "원시 세션 devlog",
    "session-2026-07-26_Grok.md":    "세션 로그",
    "61-session-deepseek-cc-2026-08-02_Grok.md": "세션 복구 로그",
    "69-session-resume-pd-bridge-v1_Grok.md":    "세션 리줌 로그",
    "13-midterm-eval.md":            "v1 구버전 — v2 재평가가 최신",
    "18-workcenters.md":             "구버전 — 20-workcenters-final 이 최신",
    "19-final-strategy.md":          "구버전 — 20-workcenters-final 이 최신",
    "32-ecosystem-whitepaper.md":    "v1.0 구버전 — 35 v1.1 이 최신",
    "39-self-platform-justification.md": "H1 없음(파일명=제목)",
    "40-lecture-draft-s21-voice-vol0_Grok.md": "강의 초안(draft)",
    "47-human-ai-dialogue-crisis.md": "인간-AI 대화 기록(사적) — 게시 여부 디렉터 판단",
    "ai-agents-cc-ds-grok-comparison-2026-07-25.md": "영문 내부 비교 노트",
    "allocation-rate-2026-07-28.md": "영문 내부 지표 노트",
    "rvc-environment-gap_Claude.md": "내부 진단 로그",
    "rvc-failure-analysis_Claude.md": "내부 진단 로그",
    "supergrok-community-research-2026-07-25.md": "영문 커뮤니티 리서치",
}

# 제목 재작성(REVISE) — 내부용어 → 검색 가능한 교재 제목 (디렉터 확정치)
TITLE_REWRITES: dict[str, str] = {
    "12-dtslib-gift.md":
        "갤럭시 S21 → 1인 미디어 스튜디오로: 무료 도구 패키지 완전 해부",
    "13-midterm-eval-v2.md":
        "갤럭시 S21 AI 워크스테이션 중간평가 — 5년 된 폰으로 어디까지 왔나",
    "16-textbook-methodology.md":
        "개발 일지를 교재로 바꾸는 방법 — 무질서 덤프를 커리큘럼으로",
    "28-grok-github-bridge.md":
        "AI 이미지 생성기와 GitHub를 잇는 인터프리터 만들기",
    "29-grok-cli-installed.md":
        "폰에서 Grok CLI 돌리기 — Termux + proot Ubuntu 설치",
    "30-agent-file-marks.md":
        "AI 에이전트 파일 소유권 규약 — 누가 어떤 파일을 썼는지 표시하기",
    "31-agent-roles_Grok.md":
        "AI 에이전트 역할 분장 — 디자이너·PD·반장·출판부·감사",
    "43-ui-less-architect.md":
        "메뉴를 몰라도 되는 이유 — AI 시대의 진짜 사용자",
    "46-fridge-architecture_Claude.md":
        "두 GitHub 계정 자산 공유 체계 — 냉장고 아키텍처",
    "48-director-video-recurrence_Grok.md":
        "소개 영상 품질 사고 재발일지 — 무엇이 잘못됐나",
    "54-director-pro-v5-five-act_Grok.md":
        "소개 영상 연출 5막 구조 — 스토리보드로 만드는 법",
    "59-grok-video-process-whitepaper_Grok.md":
        "AI로 제품 투어 영상 만드는 백서",
    "83-momentum-2026-08-14_Grok.md":
        "AI 이미지 생성기의 역할 재조정 — 두 가지 일만 시키기",
    "00-INDEX.md":
        "갤럭시 S21 1인 미디어 스튜디오 — 전체 글 목차",
    "04-github-pages.md":
        "무료 웹사이트 만들기 — GitHub Pages · 댓글 · 챗봇",
    "46-node-protocol-architecture.md":
        "이 프로젝트의 진짜 생산물은 소프트웨어가 아니라 사람 — 노드 아키텍처 선언",
    "50-director-pro-v3-visual-proof_Grok.md":
        "AI 영상 디렉팅 프롬프트 v3 — 근거 이미지 강제하기",
    "51-scout-v2-community-research_Grok.md":
        "AI 영상 도구 조사 — 커뮤니티 리서치로 최신 기능 찾기",
    "52-director-vision-qa-loop_Grok.md":
        "AI 영상 품질 검사 루프 — 만점까지 반복하기",
    "53-director-plan-settings_Grok.md":
        "AI 영상 연출 설정 — 계획을 먼저 세우기",
    "55-director-pro-v6-perfect_Grok.md":
        "AI 영상 디렉팅 프롬프트 v6 — 만점 받는 연출",
    "56-director-perfect-ship-process_Grok.md":
        "AI 영상 완성도 체크리스트 — 만점 프로세스 코드화",
    "57-director-community-a-bar_Grok.md":
        "AI 영상 커뮤니티 기능 — A-bar 구현하기",
    "60-director-pro-v8-wish_Grok.md":
        "AI 영상 디렉팅 프롬프트 v8 — 프로급 연출",
    "62-grok-plugin-video-pipe_Grok.md":
        "AI 이미지 생성기의 영상 파이프라인 플러그인",
    "63-video-plugin-standard-v1_Grok.md":
        "AI 영상 플러그인 표준 v1 — 커뮤니티 코드 고정",
    "67-grok-subscribe-voice-bgm-hurdle_Grok.md":
        "AI 소개 영상의 벽 넘기 — 성우와 배경음악",
    "68-imagine-prompt-standard-v1_Grok.md":
        "AI 이미지 프롬프트 표준 v1 — 초A 브릿지 스틸",
    "73-pd-grok-notebook-report_Grok.md":
        "AI 영상 제작 워크플로 — 종합 리포트",
}

# 제목 자동정리 규칙
NUMBER_PREFIX = re.compile(r"^\s*\d+\s*[—–\-·:.\s]+\s*")
LEADING_EMOJI = re.compile(r"^[^\w가-힣(]+\s*")  # 이모지·기호 프리픽스 (일부 보존은 제목 재작성에서 처리)


def clean_title(raw: str, fname: str) -> str:
    """번호·이모지 프리픽스 제거. (H1 없음·영문 전용은 판정 단계에서 REVISE 처리)"""
    t = NUMBER_PREFIX.sub("", raw.strip())
    return t


def is_english_dominant(s: str) -> bool:
    if not s:
        return True
    alpha = sum(1 for c in s if c.isascii() and c.isalpha())
    hangul = sum(1 for c in s if "가" <= c <= "힣")
    return alpha >= 8 and hangul == 0


def classify(fname: str, raw_title: str) -> tuple[str, str, list[str]]:
    """파일명+원제목 → (verdict, final_title, issues)."""
    issues: list[str] = []

    if fname in HOLD_REASONS:
        return "HOLD", "", [f"발행 보류: {HOLD_REASONS[fname]}"]

    if fname in TITLE_REWRITES:
        return "CLEAN", TITLE_REWRITES[fname], ["제목 재작성(디렉터 확정)"]

    # 세션·연대기·민감 (history_batch 의 SKIP 과 동일 기준 + 강화)
    if re.search(r"session", fname, re.I):
        return "HOLD", "", ["세션 로그"]
    if fname in ("17-merged-chronicle.md", "99-devlog.md"):
        return "HOLD", "", ["민감 연대기/devlog"]

    # H1 없음(제목이 파일명 그대로)
    if raw_title == fname or raw_title.endswith(fname):
        return "REVISE", "", ["H1 제목 없음 — 디렉터 재작성 필요"]

    if is_english_dominant(raw_title):
        return "REVISE", "", ["영문 전용 제목 — 한글 검색 제목 필요"]

    if any(j in raw_title for j in INTERNAL_JARGON):
        return "REVISE", "", ["내부 전용어 포함 — 검색 의도와 불일치"]

    cleaned = clean_title(raw_title, fname)
    if cleaned != raw_title.strip():
        issues.append("번호/이모지 프리픽스 정리")
        return "CLEAN", cleaned, issues

    return "PASS", raw_title.strip(), issues


# ── 태그 자동 생성 ─────────────────────────────────────────────────────────
TOPIC_TAGS: dict[str, list[str]] = {
    "arch": ["아키텍처"], "discord": ["디스코드"], "telegram": ["텔레그램"],
    "github": ["깃허브", "GitHub Pages"], "tistory": ["티스토리", "블로그"],
    "youtube": ["유튜브"], "cli": ["명령어", "터미널"], "secret": ["보안", "비밀관리"],
    "mcp": ["MCP", "자동화"], "health": ["건강검진", "돌봄"], "tts": ["TTS", "음성"],
    "rvc": ["RVC", "성우"], "voice": ["음성", "성우"], "video": ["영상", "숏폼"],
    "grok": ["AI", "이미지 생성"], "pd": ["영상", "자동화"], "whitepaper": ["백서"],
    "naver": ["네이버", "블로그"], "book": ["교재", "문서화"], "benchmark": ["성능", "벤치마크"],
    "daemon": ["데몬", "자동화"], "proot": ["proot", "리눅스"], "eval": ["회고", "평가"],
}

BASE_TAGS = ["S21", "업무수첩"]


def gen_tags(fname: str, title: str, h2s: list[str]) -> list[str]:
    tags = list(BASE_TAGS)
    hay = (fname + " " + title + " " + " ".join(h2s)).lower()
    for key, vals in TOPIC_TAGS.items():
        if key in hay:
            for v in vals:
                if v not in tags:
                    tags.append(v)
        if len(tags) >= 5:
            break
    return tags[:5]


def extract_headings(md_path: Path) -> tuple[str, str, list[str]]:
    raw = md_path.read_text(encoding="utf-8")
    title = ""
    deck = ""
    h2s = []
    body_len = 0
    for ln in raw.splitlines():
        if not title and ln.startswith("# "):
            title = ln[2:].strip()
        elif ln.startswith("## "):
            h2s.append(ln[3:].strip())
        elif not deck and ln.strip().startswith(">"):
            deck = ln.strip().lstrip("> ").strip()
    # body_len 근사 (코드/빈줄 제외)
    body_len = sum(1 for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith("#"))
    return title, deck, h2s, body_len


def run() -> dict:
    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    posts = {}
    stats = {"PASS": 0, "CLEAN": 0, "REVISE": 0, "HOLD": 0, "missing": 0}

    for e in route["tistory"]:
        fname = e["file"]
        raw_title = e.get("title", fname)
        md = ROOT / "_notebook" / fname
        if not md.exists():
            stats["missing"] += 1
            posts[fname] = {"verdict": "HOLD", "title": "", "tags": [],
                            "category": "", "issues": ["원본 파일 없음"]}
            continue

        h1, deck, h2s, body_len = extract_headings(md)
        title_src = h1 or raw_title
        verdict, final_title, issues = classify(fname, raw_title)

        if verdict == "REVISE" and h1 and h1 != fname and not is_english_dominant(h1) \
                and not any(j in h1 for j in INTERNAL_JARGON):
            # H1 이 정상이면(route 제목은 부풀려졌을 뿐) H1 을 쓰고 PASS 로 승격
            verdict, final_title, issues = "PASS", h1, ["route 제목 → H1 사용"]

        if verdict in ("PASS", "CLEAN") and not final_title:
            final_title = h1 or raw_title

        tags = gen_tags(fname, final_title or raw_title, h2s) if verdict not in ("HOLD",) else []
        stats[verdict] += 1

        posts[fname] = {
            "verdict": verdict,
            "title": final_title,
            "tags": tags,
            "category": history_category_for(fname),  # history_category_map SSOT
            "deck": deck,
            "body_lines": body_len,
            "issues": issues,
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "phase": 2,
        "stats": stats,
        "posts": posts,
    }
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def render_report(data: dict) -> str:
    stats = data["stats"]
    lines = [
        "# 디렉터 게이트 심사표 (Phase 2 품질)",
        "",
        f"생성: {data['generated']} · "
        f"PASS {stats['PASS']} / CLEAN {stats['CLEAN']} / REVISE {stats['REVISE']} / "
        f"HOLD {stats['HOLD']} / 누락 {stats['missing']}",
        "",
        "| verdict | file | 최종 제목 | issues |",
        "|---|---|---|---|",
    ]
    for fname, p in data["posts"].items():
        v = p["verdict"]
        title = (p.get("title") or "")[:52]
        issues = "; ".join(p.get("issues", []))[:60]
        lines.append(f"| {v} | `{fname}` | {title} | {issues} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="사람용 markdown 심사표만 출력")
    ap.add_argument("--json", action="store_true", help="overrides JSON 을 stdout 으로")
    args = ap.parse_args()

    data = run()
    REPORT.write_text(render_report(data), encoding="utf-8")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.report:
        print(render_report(data))
        return 0

    print(f"=== 디렉터 게이트 (Phase 2) ===")
    print(f"overrides -> {OVERRIDES}")
    print(f"report    -> {REPORT}")
    s = data["stats"]
    print(f"PASS {s['PASS']} / CLEAN {s['CLEAN']} / REVISE {s['REVISE']} / HOLD {s['HOLD']} / 누락 {s['missing']}")
    print("\nREVISE(제목 재작성 대기) 목록:")
    for fname, p in data["posts"].items():
        if p["verdict"] == "REVISE":
            print(f"  - {fname}  ({'; '.join(p['issues'])})")
    print("\nHOLD(발행 보류) 목록:")
    for fname, p in data["posts"].items():
        if p["verdict"] == "HOLD":
            print(f"  - {fname}  ({'; '.join(p['issues'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

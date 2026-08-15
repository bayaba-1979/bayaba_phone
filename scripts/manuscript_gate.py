#!/usr/bin/env python3
"""
manuscript_gate.py — 돌봄 데몬 채널 원고 품질 게이트 (Step 0).

규격 원천: helana_log/docs/care-daemon/_templates/SPEC.md
이 스크립트는 그 규격을 기계로 검사한다.

검사 항목 (SPEC §6):
  1. 한 편 = 하나의 질문 + 하나의 답
  2. 실물 원천 인용 (sources 경로 존재)
  3. 비단정 표현 (확인 창구 섹션 + 단정 마커 WARN)
  4. 민감정보 차단 (주민번호·토큰·API키 FAIL, 전화·계좌·GPS WARN)
  5. (페어 동기화는 발행 단계에서 별도 검증)

출력: [PASS]/[WARN]/[FAIL] 라인 + 상세. exit 0 = PASS/WARN, 1 = FAIL.

실행:
  python3 scripts/manuscript_gate.py <원고경로>
  python3 scripts/manuscript_gate.py --all      # care-daemon/ 전체 스캔
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# ── 편 → (카테고리 이름, 카테고리 id) 고정 맵 (SPEC §3, 실측값) ─────────────
CATEGORY_MAP: dict[str, tuple[str, int]] = {
    "01": ("매니페스토 — 기술로 돌보는 법", 1307301),
    "02": ("DW — 장애·정신건강 복지", 1307305),
    "03": ("DC — 치매·노인 돌봄", 1307306),
    "04": ("BL — 기초생활 보장", 1307307),
    "05": ("대화록 — 하루 스토리", 1307303),
    "06": ("아키텍처", 1307308),
    "07": ("배터리·온도", 1307309),
    "08": ("위치·GPS", 1307310),
    "09": ("원격 돌봄망", 1307311),
    "10": ("보고 무전기", 1307312),
}

# id → 예상 type
TYPE_BY_ID: dict[str, str] = {
    "01": "manifesto",
    "02": "track", "03": "track", "04": "track",
    "05": "dialogue",
    "06": "solution", "07": "solution", "08": "solution",
    "09": "solution", "10": "solution",
}

# type → 필수 섹션 키워드 (본문 헤더에 존재해야 함)
REQUIRED_SECTIONS: dict[str, list[str]] = {
    "manifesto": ["선언", "데몬", "지도", "읽는 법"],
    "track": ["가정 맥락", "비는 틈", "개선 방향", "확인 창구"],
    "dialogue": ["상황", "느낀", "빈틈", "솔루션", "다음"],
    "solution": ["질문", "원리", "실물", "임계값", "한계"],
}

# type → 필수 "확인 창구" 섹션 여부 (비단정 규칙 대리)
REQUIRES_CHECKPOINT = {"track", "solution"}

# care 블록 v1 레지스트리: type → 필수 페이로드 키 (SPEC §5)
BLOCK_REGISTRY: dict[str, list[str]] = {
    "callout": ["level", "text"],
    "threshold-table": ["rows"],
    "bar-chart": ["bars"],
    "timeline": ["events"],
    "flow": ["nodes", "edges"],
    "checklist": ["items"],
    "demo": ["desc", "code"],
}

REQUIRED_FIELDS = [
    "id", "type", "title", "question", "answer",
    "category", "category_id", "track", "sources",
    "interactive", "date", "민감정보",
]

# ── 민감정보 패턴 (SPEC §4-6) ───────────────────────────────────────────────
SENSITIVE_FAIL = [
    (re.compile(r"\d{6}\s*[-–]\s*[1-4]\d{6}"), "주민등록번호"),
    (re.compile(r"\d{8,10}:[A-Za-z0-9_-]{30,}"), "텔레그램 봇 토큰"),
    (re.compile(r"\b(?:sk|ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"), "API 키/토큰"),
]
SENSITIVE_WARN = [
    (re.compile(r"\b0\d{1,2}[-–]\d{3,4}[-–]\d{4}\b"), "전화번호"),
    (re.compile(r"\b\d{2,4}[-–]\d{2,4}[-–]\d{4,7}\b"), "계좌번호 유사"),
    (re.compile(r"\b(?:3[0-9]\.\d{4,}|1[0-3]\d\.\d{4,})\b"), "실 GPS 좌표 유사(위·경도)"),
]

# 단정 표현 마커 (WARN, 비단정 규칙 대리) — SPEC §6 규칙 3
ASSERT_MARKERS = [
    "무조건", "반드시 받을 수", "100% 보장", "법적으로 보장",
    "당연히 받는다", "확정", "무조건 지급", "받을 수 있습니다",
]

# ── 원천 경로 해석 (SPEC §3: "레포:경로") ────────────────────────────────────
HELENA_PHONE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOTS = {
    "helena_phone": HELENA_PHONE_ROOT,
    "helana_log": HELENA_PHONE_ROOT / "helana_log",
}


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def ok(msg: str) -> None:
    print(f"  [ok]   {msg}")


def parse_care_blocks(body: str) -> list[dict]:
    """fenced ```care type=... id=... 블록 추출 → [{type,id,payload}]. """
    blocks: list[dict] = []
    # info-string: care type="threshold-table" id="battery-thresholds"
    pattern = re.compile(
        r'```care\s+type="(?P<type>[^"]+)"\s+id="(?P<id>[^"]+)"\s*\n'
        r"(?P<payload>.*?)```",
        re.DOTALL,
    )
    for m in pattern.finditer(body):
        try:
            payload = yaml.safe_load(m.group("payload")) or {}
        except yaml.YAMLError as e:
            fail(f"care 블록 '{m.group('id')}' 페이로드 YAML 오류: {e}")
            payload = {}
        blocks.append({"type": m.group("type"), "id": m.group("id"), "payload": payload})
    return blocks


def check_sources(sources: list[str], manuscript_dir: Path) -> tuple[int, int]:
    """각 source 가 존재하는 파일을 가리키는지. (존재, 누락) 반환."""
    found = missing = 0
    for s in sources:
        if ":" in s:
            repo, _, rel = s.partition(":")
            base = REPO_ROOTS.get(repo.strip())
            if base is None:
                warn(f"알 수 없는 원천 레포 '{repo}' → '{s}' (해석 불가, 확인 필요)")
                missing += 1
                continue
            target = base / rel.strip()
        else:
            target = manuscript_dir / s.strip()
        if target.exists():
            found += 1
        else:
            fail(f"원천 파일 없음: {s} → {target}")
            missing += 1
    return found, missing


def check_manuscript(path: Path) -> int:
    """원고 1개 검사. 반환: 0=PASS/WARN, 1=FAIL."""
    print(f"\n=== {path} ===")
    fails = 0
    text = path.read_text(encoding="utf-8")

    # ── frontmatter ──
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        fail("frontmatter(`---` 블록) 없음")
        return 1
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        fail(f"frontmatter YAML 오류: {e}")
        return 1
    if not isinstance(fm, dict):
        fail("frontmatter가 YAML 매핑이 아님")
        return 1

    for f in REQUIRED_FIELDS:
        if f not in fm:
            fail(f"frontmatter 필드 누락: {f}")
            fails += 1
    if fails:
        return 1  # 필드 누락이면 이후 검사 의미 없음

    eid = str(fm["id"])
    etype = str(fm["type"])
    body = text[m.end():]

    # ── 규칙 1: 질문/답 ──
    if not str(fm["question"]).strip():
        fail("question 비어있음")
        fails += 1
    answer = str(fm["answer"]).strip()
    if not answer:
        fail("answer 비어있음")
        fails += 1
    elif answer.count(".") + answer.count("。") > 1:
        warn(f"answer가 한 문장 초과 가능성: {answer!r}")

    # ── id/type/category 일관성 ──
    if not re.fullmatch(r"\d{2}", eid):
        fail(f"id 형식 오류: {eid!r} (두 자리 01~10)")
        fails += 1
    elif eid not in CATEGORY_MAP:
        fail(f"id가 편 번호 범위 밖: {eid}")
        fails += 1
    else:
        if TYPE_BY_ID[eid] != etype:
            fail(f"type 불일치: id={eid} 는 {TYPE_BY_ID[eid]} 여야 하는데 {etype}")
            fails += 1
        cat_name, cat_id = CATEGORY_MAP[eid]
        if int(fm["category_id"]) != cat_id:
            fail(f"category_id 불일치: id={eid} 는 {cat_id} 여야 하는데 {fm['category_id']}")
            fails += 1
        if str(fm["category"]).strip() != cat_name:
            fail(f"category 이름 불일치: '{fm['category']}' ≠ '{cat_name}'")
            fails += 1

    if etype not in REQUIRED_SECTIONS:
        fail(f"type 오류: {etype!r} (manifesto|track|dialogue|solution)")
        fails += 1

    # ── 규칙 3: 필수 섹션 ──
    for kw in REQUIRED_SECTIONS.get(etype, []):
        if kw not in body:
            fail(f"필수 섹션 누락: '{kw}'")
            fails += 1
    if etype in REQUIRES_CHECKPOINT and "확인 창구" not in body:
        fail("비단정 규칙: '확인 창구' 섹션 없음 (track·solution 필수)")
        fails += 1

    # ── 규칙 2: sources ──
    sources = fm["sources"] or []
    if not sources:
        fail("sources 비어있음 (실물 원천 필수)")
        fails += 1
    else:
        found, missing = check_sources(sources, path.parent)
        ok(f"sources {found}/{len(sources)} 존재" + (" (누락 있음)" if missing else ""))

    # ── care 블록 ──
    blocks = parse_care_blocks(body)
    block_ids = [b["id"] for b in blocks]
    if len(block_ids) != len(set(block_ids)):
        fail("care 블록 id 중복")
        fails += 1
    for b in blocks:
        if b["type"] not in BLOCK_REGISTRY:
            fail(f"미등록 care 블록 타입: {b['type']!r} (id={b['id']})")
            fails += 1
            continue
        for key in BLOCK_REGISTRY[b["type"]]:
            if key not in b["payload"]:
                fail(f"care 블록 '{b['id']}' 페이로드 키 누락: {key}")
                fails += 1

    # frontmatter interactive ↔ 블록 id 일치
    declared = [str(x) for x in (fm["interactive"] or [])]
    if set(declared) != set(block_ids):
        fail(f"interactive 목록과 care 블록 id 불일치: declared={declared}, blocks={block_ids}")
        fails += 1

    # ── 규칙 4: 민감정보 ──
    full = text
    for pat, label in SENSITIVE_FAIL:
        if pat.search(full):
            fail(f"민감정보 발견: {label}")
            fails += 1
    for pat, label in SENSITIVE_WARN:
        if pat.search(full):
            warn(f"민감정보 의심(확인 필요): {label}")

    # ── 규칙 3 보조: 단정 마커 ──
    for marker in ASSERT_MARKERS:
        if marker in body:
            warn(f"단정 표현 의심: '{marker}' (확인 창구로 돌릴 것)")
            break

    if fails:
        print(f"  → 결과: FAIL ({fails}건)")
        return 1
    print("  → 결과: PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="돌봄 데몬 원고 품질 게이트")
    ap.add_argument("path", nargs="?", help="원고 md 경로")
    ap.add_argument("--all", action="store_true", help="care-daemon/ 전체 원고 스캔")
    args = ap.parse_args()

    if args.all:
        root = HELENA_PHONE_ROOT / "helana_log" / "docs" / "care-daemon"
        files = sorted(p for p in root.rglob("*.md") if "_templates" not in str(p))
        if not files:
            print("원고 없음 — care-daemon/ 아래 발행 원고가 아직 없다.")
            return 0
        total = sum(check_manuscript(f) for f in files)
        print(f"\n=== 전체 결과: {'FAIL' if total else 'PASS'} (실패 {total}/{len(files)}) ===")
        return 1 if total else 0

    if not args.path:
        ap.error("원고 경로 또는 --all 필요")
    return check_manuscript(Path(args.path))


if __name__ == "__main__":
    raise SystemExit(main())

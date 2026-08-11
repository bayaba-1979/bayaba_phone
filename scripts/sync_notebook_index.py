#!/usr/bin/env python3
"""
🔄 sync_notebook_index.py — 업무수첩 INDEX 자율주행

00-INDEX.md와 실제 _notebook/*.md 파일을 비교하여:
- INDEX에 없는 신규 파일 발견
- INDEX에 있지만 디스크에 없는 파일 발견
- 선택적으로 INDEX 자동 갱신

사용법:
  python3 scripts/sync_notebook_index.py           # 갭 보고만
  python3 scripts/sync_notebook_index.py --sync    # 갭 보고 + INDEX 자동 갱신
  python3 scripts/sync_notebook_index.py --json    # JSON 출력 (MCP/파이프용)
"""

import json, os, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/root/work")
NOTEBOOK = ROOT / "_notebook"
INDEX_FILE = NOTEBOOK / "00-INDEX.md"


def scan_notebook() -> set[str]:
    """Scan _notebook/ for all .md files."""
    files = set()
    for md in NOTEBOOK.rglob("*.md"):
        rel = str(md.relative_to(NOTEBOOK))
        files.add(rel)
    return files


def parse_index_entries() -> set[str]:
    """Extract file references from 00-INDEX.md."""
    if not INDEX_FILE.exists():
        return set()
    text = INDEX_FILE.read_text()
    # Match `file.md` patterns in markdown
    entries = set()
    for m in re.finditer(r'`([^`]+\.md)`', text):
        entries.add(m.group(1))
    return entries


def quick_summary(path: str) -> str:
    """Extract first heading from a .md file as summary."""
    f = NOTEBOOK / path
    if not f.exists():
        return "(파일 없음)"
    try:
        content = f.read_text()[:2000]
        for line in content.splitlines():
            m = re.match(r'^#+\s+(.+)', line)
            if m:
                return m.group(1).strip()[:80]
    except Exception:
        pass
    return ""


def sync(json_mode=False):
    disk = scan_notebook()
    indexed = parse_index_entries()

    new_files = disk - indexed
    missing_files = indexed - disk
    total = len(disk)

    result = {
        "timestamp": datetime.now().isoformat(),
        "total_on_disk": total,
        "total_indexed": len(indexed),
        "new_files": sorted(new_files),
        "missing_files": sorted(missing_files),
    }

    if json_mode:
        # Add summaries for new files
        result["new_with_summaries"] = [
            {"file": f, "summary": quick_summary(f)} for f in sorted(new_files)
        ]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    print(f"\n{'='*55}")
    print(f"  🔄 업무수첩 INDEX 동기화 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")
    print(f"  디스크: {total}개 · INDEX 등록: {len(indexed)}개")

    if not new_files and not missing_files:
        print(f"\n  ✅ 완전 동기화 — 갭 없음")
    else:
        if new_files:
            print(f"\n  🆕 INDEX에 없는 신규 파일 ({len(new_files)}건):")
            for f in sorted(new_files):
                summary = quick_summary(f)
                print(f"     📄 {f}")
                if summary:
                    print(f"        → {summary}")

        if missing_files:
            print(f"\n  ⚠️  INDEX에는 있지만 디스크에 없는 파일 ({len(missing_files)}건):")
            for f in sorted(missing_files):
                print(f"     ❌ {f}")

    print(f"\n  💡 갱신: python3 scripts/sync_notebook_index.py --sync")
    print(f"{'='*55}\n")

    return result


def sync_and_update():
    """Report + update INDEX with new entries."""
    result = sync(json_mode=False)

    new_files = result.get("new_files", [])
    if not new_files:
        print("  ✅ 갱신할 항목 없음")
        return

    print(f"\n  🔧 INDEX에 {len(new_files)}건 추가 중...")

    # Build new entries
    new_entries = []
    for f in sorted(new_files):
        summary = quick_summary(f)
        if summary:
            new_entries.append(f"| `{f}` | {summary} |")
        else:
            new_entries.append(f"| `{f}` |  |")

    # Append to INDEX
    with open(INDEX_FILE, "a") as fh:
        fh.write("\n")
        for entry in new_entries:
            fh.write(entry + "\n")

    print(f"  ✅ {len(new_entries)}건 추가 완료 → {INDEX_FILE}")
    print(f"  ⚠️  카테고리 분류는 수동으로 이동해줘야 함 (자동 추가는 하단에 쌓임)")


if __name__ == "__main__":
    if "--sync" in sys.argv:
        sync_and_update()
    elif "--json" in sys.argv:
        sync(json_mode=True)
    else:
        sync(json_mode=False)

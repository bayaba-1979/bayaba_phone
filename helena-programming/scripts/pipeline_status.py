#!/usr/bin/env python3
"""
📊 pipeline_status.py — PD Pipeline + Log Publisher 통합 상태 체크

한눈에 모든 파이프라인·로그·작업 상태를 보여준다.

사용법:
  python3 pipeline_status.py          # 전체 상태
  python3 pipeline_status.py --json   # JSON 출력 (MCP용)
  python3 pipeline_status.py --watch  # 5초마다 갱신 (Ctrl+C 종료)
"""

import json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path("/root/work")
OUT_BASE = ROOT / "out"
LOG_REPO = ROOT / "helana_log"


def get_pd_jobs():
    """PD Pipeline jobs from /tmp/pd_mcp_jobs.json."""
    jobs_file = Path("/tmp/pd_mcp_jobs.json")
    if not jobs_file.exists():
        return []
    try:
        data = json.loads(jobs_file.read_text())
        return list(data.values()) if isinstance(data, dict) else data
    except Exception:
        return []


def get_pd_episodes():
    """List completed PD episodes in out/."""
    out = OUT_BASE
    if not out.exists():
        return []
    episodes = []
    for d in sorted(out.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir():
            mp4s = list(d.glob("*.mp4"))
            bible = d / "shot_bible.json"
            ver = ""
            dur = ""
            if bible.exists():
                try:
                    b = json.loads(bible.read_text())
                    ver = b.get("version", "")
                except Exception:
                    pass
            size_mb = round(sum(f.stat().st_size for f in mp4s) / (1024 * 1024), 1) if mp4s else 0
            episodes.append({
                "id": d.name,
                "version": ver,
                "size_mb": size_mb,
                "files": len(mp4s),
                "modified": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
            })
    return episodes[:5]


def get_log_files():
    """List recent ParksyLog files."""
    logs_dir = LOG_REPO / "logs"
    if not logs_dir.exists():
        return []
    files = []
    for md in sorted(logs_dir.rglob("ParksyLog_*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = md.stat()
        files.append({
            "name": md.name,
            "path": str(md.relative_to(LOG_REPO)),
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return files[:10]


def get_disk():
    """Disk usage."""
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            parts = r.stdout.strip().split("\n")[-1].split()
            return {"used": parts[2], "avail": parts[3], "pct": parts[4]}
    except Exception:
        pass
    return {}


def status(json_mode=False):
    data = {
        "timestamp": datetime.now().isoformat(),
        "pd_jobs": get_pd_jobs(),
        "pd_episodes": get_pd_episodes(),
        "log_files": get_log_files(),
        "disk": get_disk(),
    }

    if json_mode:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"\n{'='*55}")
    print(f"  📊 PD Pipeline + Log 상태 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")

    # PD jobs
    jobs = data["pd_jobs"]
    print(f"\n🔧 PD 작업 ({len(jobs)}건):")
    if not jobs:
        print("   (진행 중인 작업 없음)")
    else:
        for j in jobs:
            status_icon = {"running": "🟢", "done": "✅", "error": "❌", "killed": "💀"}.get(j.get("status", ""), "⏳")
            print(f"   {status_icon} {j.get('ep_id','?')} [{j.get('status','?')}] — {j.get('url','')[:50]}")

    # PD episodes
    eps = data["pd_episodes"]
    print(f"\n🎬 최근 에피소드 ({len(eps)}건):")
    if not eps:
        print("   (에피소드 없음)")
    else:
        for ep in eps:
            print(f"   📦 {ep['id']} — {ep['version']} · {ep['size_mb']}MB · {ep['modified'][:16].replace('T',' ')}")

    # Log files
    logs = data["log_files"]
    print(f"\n📝 최근 ParksyLog ({len(logs)}건):")
    if not logs:
        print("   (로그 없음)")
    else:
        for lf in logs[:5]:
            print(f"   📄 {lf['name']} — {lf['size_kb']}KB · {lf['modified'][:16].replace('T',' ')}")

    # Disk
    disk = data["disk"]
    if disk:
        print(f"\n💾 디스크: {disk['used']} 사용 / {disk['avail']} 남음 ({disk['pct']})")

    print(f"\n💡 체크 방법:")
    print(f"   Claude Code: '야 파이프라인 상태 어때?' → 내가 이 스크립트 실행")
    print(f"   직접: python3 scripts/pipeline_status.py")
    print(f"   MCP:  pd_list + log_list + pd_status")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    json_mode = "--json" in sys.argv
    watch = "--watch" in sys.argv

    if watch:
        try:
            while True:
                os.system("clear" if os.name != "nt" else "cls")
                status(json_mode=False)
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 종료")
    else:
        status(json_mode=json_mode)

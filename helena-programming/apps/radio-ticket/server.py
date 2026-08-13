#!/usr/bin/env python3
"""라디오 초대권 PWA 서버 — 로컬 HTTP + API (port 8766)

사용법:
  python3 server.py              # 포그라운드
  python3 server.py --daemon     # 백그라운드
  python3 server.py --port 8766  # 포트 지정

API:
  GET  /              → PWA 대시보드
  GET  /api/crawl     → 공연 크롤링 실행
  POST /api/dispatch  → 파이프라인 실행 (body: {"dry_run": true})
  GET  /api/status    → 로그 + 상태
  GET  /api/venues    → 캐시된 공연 목록
"""
import http.server, json, sys, os, subprocess, threading, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parent
PWA = BASE / "pwa"
PIPELINE = BASE.parent.parent / "pipelines" / "radio_ticket"

# 캐시
_cache = {"venues": [], "log": [], "last_run": None}

def run_pipeline(dry_run=False):
    """파이프라인 실행 → 결과 반환"""
    cmd = [sys.executable, str(PIPELINE / "dispatch.py")]
    if dry_run:
        cmd.append("--dry-run")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(PIPELINE))
        return {"ok": True, "dry_run": dry_run, "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout (5분 초과)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def load_log():
    """dispatch.log 읽기"""
    logf = PIPELINE / "dispatch.log"
    if logf.exists():
        lines = logf.read_text().strip().split("\n")
        return lines[-30:]
    return []

def load_venues():
    """최근 dispatch JSON에서 공연 목록 로드"""
    files = sorted(PIPELINE.glob("dispatch_*.json"), reverse=True)
    if files:
        try:
            data = json.loads(files[0].read_text())
            return data if isinstance(data, list) else []
        except:
            pass
    # 크롤링 직접 실행
    sys.path.insert(0, str(PIPELINE))
    from crawl import crawl_all
    return crawl_all()

def load_giftbox():
    """선물함(giftbox.json) 로드"""
    gb = PIPELINE / "giftbox.json"
    if gb.exists():
        try:
            return json.loads(gb.read_text())
        except:
            pass
    return []

def mark_sent(story_id: str):
    """스토리를 '제출 완료'로 표시"""
    gb = PIPELINE / "giftbox.json"
    if not gb.exists():
        return False
    try:
        data = json.loads(gb.read_text())
        for item in data:
            if item.get("id") == story_id:
                item["sent"] = True
                item["sent_at"] = datetime.now().isoformat()
        gb.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except:
        return False

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PWA), **kwargs)

    def log_message(self, format, *args):
        pass  # 조용히

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path):
        fp = PWA / path
        if fp.exists() and fp.is_file():
            body = fp.read_bytes()
            ct = "text/html" if fp.suffix == ".html" else \
                 "application/json" if fp.suffix == ".json" else \
                 "application/javascript" if fp.suffix == ".js" else \
                 "text/plain"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_GET(self):
        p = urlparse(self.path).path

        if p == "/" or p == "/index.html":
            return self._static("index.html")
        if p in ["/manifest.json", "/sw.js"]:
            return self._static(p[1:])

        if p == "/api/crawl":
            import sys; sys.path.insert(0, str(PIPELINE))
            from crawl import crawl_all
            venues = crawl_all()
            _cache["venues"] = venues
            return self._json({"ok": True, "count": len(venues), "venues": venues})

        if p == "/api/status":
            log = load_log()
            return self._json({"ok": True, "log": log, "last_run": _cache.get("last_run")})

        if p == "/api/venues":
            if not _cache["venues"]:
                import sys; sys.path.insert(0, str(PIPELINE))
                from crawl import crawl_all
                _cache["venues"] = crawl_all()
            return self._json({"ok": True, "venues": _cache["venues"]})

        if p == "/api/stories" or p == "/api/giftbox":
            stories = load_giftbox()
            return self._json({"ok": True, "stories": stories, "count": len(stories)})

        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        p = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if p == "/api/dispatch":
            dry = body.get("dry_run", False)
            result = run_pipeline(dry_run=dry)
            _cache["last_run"] = time.strftime("%H:%M")
            _cache["log"] = load_log()
            return self._json(result)

        if p == "/api/generate":
            title = body.get("title", "백건우 리사이틀")
            location = body.get("location", "예술의전당")
            date = body.get("date", "")
            channel = body.get("channel", "classic")
            import sys; sys.path.insert(0, str(PIPELINE))
            from generate import generate_story
            story = generate_story(channel, {"title": title, "location": location, "date": date})
            return self._json({"ok": True, "story": story})

        if p.startswith("/api/stories/") and p.endswith("/sent"):
            story_id = p.split("/")[3]
            ok = mark_sent(story_id)
            return self._json({"ok": ok, "id": story_id})

        return self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--daemon", "-d", action="store_true")
    args = parser.parse_args()

    print(f"🎙 라디오 초대권 PWA 서버")
    print(f"   http://localhost:{args.port}")
    print(f"   API: /api/crawl | /api/dispatch | /api/status | /api/venues | /api/generate")

    if args.daemon:
        # subprocess로 백그라운드 실행
        subprocess.Popen([sys.executable, __file__, "--port", str(args.port)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   백그라운드 시작됨 → http://localhost:{args.port}")
        return

    httpd = http.server.HTTPServer(("0.0.0.0", args.port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 종료")

if __name__ == "__main__":
    main()

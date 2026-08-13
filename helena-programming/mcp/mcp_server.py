"""
Helena Studio MCP Server — Python (로컬/WSL/phone)

parksy-audio MCP voice 패턴 계승.
온디바이스 MCP 서버: 다이어그램 렌더링, 음성 더빙, SVG 합성,
Paste Pipeline → Telegram 클립보드 전송.
"""

import json
import os
import re
import subprocess
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # helena-programming/
TEMPLATE_DIR = BASE_DIR / "templates"
SCRIPTS_DIR = BASE_DIR / "scripts"

# MCP 도구 정의
TOOLS = [
    {
        "name": "render_diagram",
        "description": "Mermaid 다이어그램을 SVG로 렌더링 (온디바이스)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Mermaid 다이어그램 코드"},
                "theme": {"type": "string", "enum": ["default", "dark", "forest"], "default": "default"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "voice_dub",
        "description": "텍스트 → RVC 음성 더빙 트랙 생성 (온디바이스)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "더빙할 텍스트"},
                "voice": {"type": "string", "default": "parksy"},
                "output_format": {"type": "string", "enum": ["wav", "mp3"], "default": "wav"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "compose_page",
        "description": "SVG/HTML 조각을 웹페이지로 합성",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "components": {"type": "array", "items": {"type": "string"}},
                "template": {"type": "string", "default": "default"}
            },
            "required": ["title", "components"]
        }
    },
    {
        "name": "fetch_fridge",
        "description": "냉장고(REDACTED)에서 자산 가져오기",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "냉장고 레포 이름 (예: parksy-audio)"},
                "path": {"type": "string", "description": "레포 내 경로"}
            },
            "required": ["repo"]
        }
    },
    {
        "name": "publish_html_clipboard",
        "description": "HTML 파일을 .txt 확장자로 Telegram에 전송 — 안드로이드 텍스트 편집기로 열려서 전체복사→Tistory HTML 모드 붙여넣기 가능 (Paste Pipeline v5.1)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "html_file": {"type": "string", "description": "HTML 파일 경로"},
                "caption": {"type": "string", "description": "텔레그램 캡션 (생략 시 파일명 사용)"},
                "minify": {"type": "boolean", "default": True, "description": "압축 여부 (기본 true)"}
            },
            "required": ["html_file"]
        }
    },
    {
        "name": "publish_ecosystem_workflow",
        "description": "지식관리 생태계 워크플로우 HTML 생성 → .txt로 Telegram 전송 (Paste Pipeline 표준)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caption": {"type": "string", "description": "텔레그램 캡션 (기본: 표준 캡션)"},
                "template": {"type": "string", "default": "ecosystem-knowledge-workflow", "description": "템플릿 이름"}
            },
            "required": []
        }
    },
    {
        "name": "radio_ticket_crawl",
        "description": "Yes24 티켓 클래식 카테고리에서 공연 정보 크롤링 — 제목·날짜·장소·PerfID 반환",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "radio_ticket_generate",
        "description": "공연 정보로 라디오 초대권 사연 생성 (DeepSeek API). channel: classic/gayo/pop",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "공연 제목"},
                "location": {"type": "string", "description": "공연장"},
                "date": {"type": "string", "description": "공연 날짜"},
                "channel": {"type": "string", "enum": ["classic", "gayo", "pop"], "default": "classic"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "radio_ticket_dispatch",
        "description": "라디오 초대권 전체 파이프라인 실행 — 크롤링→사연생성→TG배달",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "default": False, "description": "TG 전송 없이 생성만"}
            },
            "required": []
        }
    },
    {
        "name": "radio_ticket_status",
        "description": "최근 dispatch 로그 조회 — 마지막 실행 시간·결과",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


class HelenaMCP:
    """Helena Studio MCP Server"""

    def __init__(self):
        self.name = "helena-studio-mcp"
        self.version = "0.2.0"

    # ── Paste Pipeline v5.1 도구 ────────────────────────

    def _load_secrets(self):
        """.secrets.env에서 TG_TOKEN, TG_CHAT 로드"""
        secrets_file = Path("/root/work/.secrets.env")
        if not secrets_file.exists():
            return None, None
        token = chat = None
        for line in secrets_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("TG_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("TG_CHAT="):
                chat = line.split("=", 1)[1].strip().strip('"').strip("'")
        return token, chat

    def _minify_html(self, html: str) -> str:
        """HTML 압축: 빈 줄 제거 + 선행 공백 제거 (라인 구조는 유지)"""
        lines = [l.strip() for l in html.split("\n") if l.strip()]
        return "\n".join(lines)

    def _send_to_telegram(self, content: str, filename: str, caption: str) -> dict:
        """HTML 내용을 .txt 파일로 Telegram sendDocument 전송"""
        token, chat = self._load_secrets()
        if not token or not chat:
            return {"ok": False, "error": "TG_TOKEN/TG_CHAT not found in .secrets.env"}

        import tempfile, requests

        # .txt 확장자 — 안드로이드 텍스트 편집기로 열림
        fname = filename.replace(".html", ".txt")
        tmp = Path(tempfile.gettempdir()) / fname
        tmp.write_text(content, encoding="utf-8")

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat, "caption": caption},
                files={"document": (fname, tmp.read_bytes(), "text/plain")},
                timeout=30,
            ).json()

            tmp.unlink(missing_ok=True)

            if resp.get("ok"):
                doc = resp.get("result", {}).get("document", {})
                return {
                    "ok": True,
                    "message_id": resp["result"]["message_id"],
                    "file_name": doc.get("file_name", fname),
                    "file_size": doc.get("file_size", len(content)),
                }
            else:
                return {"ok": False, "error": resp.get("description", "?")}
        except Exception as e:
            tmp.unlink(missing_ok=True)
            return {"ok": False, "error": str(e)}

    def _tool_publish_html_clipboard(self, args: dict) -> dict:
        """HTML 파일 → .txt → Telegram 전송"""
        html_file = args.get("html_file", "")
        caption = args.get("caption", "")
        do_minify = args.get("minify", True)

        p = Path(html_file)
        if not p.exists():
            return {"ok": False, "error": f"File not found: {html_file}"}

        content = p.read_text(encoding="utf-8")
        original_lines = content.count("\n") + 1
        original_bytes = len(content)

        if do_minify:
            content = self._minify_html(content)

        final_lines = content.count("\n") + 1
        final_bytes = len(content)

        if not caption:
            caption = (
                f"📄 {p.name} → .txt (Paste Pipeline v5.1)\n"
                f"📐 {final_lines}줄 · {final_bytes}바이트"
                f"{' · 압축됨' if do_minify else ''}\n"
                f"⬇️ 다운로드 → 텍스트 편집기 열림 → 전체복사 → Tistory HTML 모드"
            )

        result = self._send_to_telegram(content, f"{p.stem}.txt", caption)
        result["original"] = {"lines": original_lines, "bytes": original_bytes}
        result["delivered"] = {"lines": final_lines, "bytes": final_bytes, "extension": ".txt"}
        return result

    def _tool_publish_ecosystem_workflow(self, args: dict) -> dict:
        """지식관리 생태계 워크플로우 → .txt → Telegram 전송"""
        caption = args.get("caption", "")
        template_name = args.get("template", "ecosystem-knowledge-workflow")

        tmpl = TEMPLATE_DIR / f"{template_name}.html"
        if not tmpl.exists():
            return {"ok": False, "error": f"Template not found: {tmpl}"}

        content = tmpl.read_text(encoding="utf-8")
        content = self._minify_html(content)

        lines = content.count("\n") + 1
        bsize = len(content)

        if not caption:
            caption = (
                f"🧠 S21 지식관리 생태계 — Paste Pipeline v5.1\n"
                f"📐 {lines}줄 · {bsize}바이트 · .txt 클립보드 표준\n"
                f"⬇️ 다운로드 → 텍스트 편집기 → 전체복사 → Tistory HTML 모드"
            )

        return self._send_to_telegram(content, f"{template_name}.txt", caption)

    # ── Radio Ticket 도구 ─────────────────────────────

    def _tool_radio_ticket_crawl(self, args: dict) -> dict:
        """Yes24 클래식 공연 크롤링"""
        import sys
        ticket_dir = str(BASE_DIR / "pipelines" / "radio_ticket")
        if ticket_dir not in sys.path:
            sys.path.insert(0, ticket_dir)
        from crawl import crawl_all
        results = crawl_all()
        return {
            "ok": True,
            "count": len(results),
            "performances": results,
            "dateful": [r for r in results if r.get("date")]
        }

    def _tool_radio_ticket_generate(self, args: dict) -> dict:
        """공연 정보로 사연 생성"""
        import sys
        ticket_dir = str(BASE_DIR / "pipelines" / "radio_ticket")
        if ticket_dir not in sys.path:
            sys.path.insert(0, ticket_dir)
        from generate import generate_story

        perf = {
            "title": args.get("title", ""),
            "location": args.get("location", ""),
            "date": args.get("date", ""),
        }
        channel = args.get("channel", "classic")
        result = generate_story(channel, perf)
        return {"ok": True, "story": result}

    def _tool_radio_ticket_dispatch(self, args: dict) -> dict:
        """전체 파이프라인 실행"""
        import sys, subprocess
        dry = args.get("dry_run", False)
        ticket_dir = BASE_DIR / "pipelines" / "radio_ticket"
        cmd = [sys.executable, str(ticket_dir / "dispatch.py")]
        if dry:
            cmd.append("--dry-run")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {
                "ok": True,
                "dry_run": dry,
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-500:] if proc.stderr else ""
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _tool_radio_ticket_status(self, args: dict) -> dict:
        """dispatch 로그 조회"""
        log_file = BASE_DIR / "pipelines" / "radio_ticket" / "dispatch.log"
        if not log_file.exists():
            return {"ok": True, "status": "no runs yet", "log": []}

        lines = log_file.read_text().strip().split("\n")
        # 마지막 20줄
        recent = lines[-20:]
        # 마지막 실행 찾기
        last_start = None
        last_end = None
        for line in reversed(lines):
            if "✅ 디스패처 완료" in line and not last_end:
                last_end = line[:19]
            if "🚀" in line and not last_start:
                last_start = line[:19]

        return {
            "ok": True,
            "total_lines": len(lines),
            "last_run_start": last_start,
            "last_run_end": last_end,
            "recent_log": recent
        }

    # ── MCP 핸들러 ─────────────────────────────────────

    async def handle_request(self, method: str, params: dict = None) -> dict:
        if method == "tools/list":
            return {"tools": TOOLS}

        if method == "tools/call":
            tool_name = params.get("name") if params else None
            arguments = params.get("arguments", {}) if params else {}

            if tool_name == "publish_html_clipboard":
                return self._tool_publish_html_clipboard(arguments)

            if tool_name == "publish_ecosystem_workflow":
                return self._tool_publish_ecosystem_workflow(arguments)

            if tool_name == "radio_ticket_crawl":
                return self._tool_radio_ticket_crawl(arguments)

            if tool_name == "radio_ticket_generate":
                return self._tool_radio_ticket_generate(arguments)

            if tool_name == "radio_ticket_dispatch":
                return self._tool_radio_ticket_dispatch(arguments)

            if tool_name == "radio_ticket_status":
                return self._tool_radio_ticket_status(arguments)

            # 나머지 도구 — scaffold 상태
            return {
                "result": f"[placeholder] {tool_name} 호출됨. "
                          f"인자: {json.dumps(arguments, ensure_ascii=False)[:200]}",
                "tool": tool_name,
                "status": "scaffold"
            }

        return {"error": f"Unknown method: {method}"}

    def run_stdio(self):
        """STDIO 모드 — Claude Code 직접 연결용"""
        import sys
        print(f"[Helena MCP] {self.name} v{self.version} — STDIO mode", file=sys.stderr)
        print("[Helena MCP] Waiting for MCP requests...", file=sys.stderr)

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                result = asyncio.run(self.handle_request(
                    request.get("method", ""),
                    request.get("params")
                ))
                print(json.dumps(result), flush=True)
            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    server = HelenaMCP()
    server.run_stdio()

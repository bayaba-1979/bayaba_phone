#!/usr/bin/env python3
"""
📨 log_to_tg.py — .md → HTML 변환 → Telegram 전송 → Tistory 복붙

ParksyLog(.md)를 Tistory HTML 모드용으로 변환해
Telegram으로 전송한다. 받은 파일을 열어 전체 복사 →
Tistory HTML 모드에 붙여넣기만 하면 발행 완료.

사용법:
  # 단일 파일
  python3 scripts/log_to_tg.py helana_log/logs/2026/08/ParksyLog_20260811_094250.md

  # HTML 모드 (Tistory HTML 모드 붙여넣기용)
  python3 scripts/log_to_tg.py --html helana_log/logs/2026/08/ParksyLog_20260811_094250.md

  # MCP에서 호출
  python3 scripts/log_to_tg.py --html --json helana_log/logs/2026/08/ParksyLog_20260811_094250.md

환경변수: TG_TOKEN, TG_CHAT (또는 HELANA_LOG_TG_TOKEN, HELANA_LOG_TG_CHAT)
"""
from __future__ import annotations

import json, os, subprocess, sys
from pathlib import Path


ROOT = Path("/root/work")
CONVERTER = ROOT / "helena-programming" / "scripts" / "parksy_to_html.py"
LOG_REPO = ROOT / "helana_log"


def get_secrets() -> tuple[str, str]:
    """Load TG secrets from .secrets.env or environment."""
    token = os.environ.get("TG_TOKEN") or os.environ.get("HELANA_LOG_TG_TOKEN") or ""
    chat = os.environ.get("TG_CHAT") or os.environ.get("HELANA_LOG_TG_CHAT") or ""

    if not token or not chat:
        secrets_file = ROOT / ".secrets.env"
        if secrets_file.exists():
            for line in secrets_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                # skip export prefix
                if line.startswith("export "):
                    line = line[7:]
                key, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                if key == "TG_TOKEN" and not token:
                    token = val
                elif key == "HELANA_LOG_TG_TOKEN" and not token:
                    token = val
                elif key == "TG_CHAT" and not chat:
                    chat = val
                elif key == "HELANA_LOG_TG_CHAT" and not chat:
                    chat = val

    return token, chat


def md_to_html(md_path: Path) -> tuple[Path, str, int, int]:
    """Convert .md to Tistory-compatible HTML (.txt extension for Android)."""
    out_path = Path("/tmp") / (md_path.stem + ".txt")

    r = subprocess.run(
        ["python3", str(CONVERTER), str(md_path), "--out", str(out_path)],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"HTML 변환 실패: {r.stderr[-300:]}")

    html = out_path.read_text(encoding="utf-8")
    turn_count = html.count('<details class="turn')
    line_count = html.count("\n")

    # Extract title from markdown
    title = ""
    content = md_path.read_text(encoding="utf-8")
    for line in content.splitlines()[:30]:
        m = __import__('re').match(r'^#\s+(.+)', line)
        if m:
            title = m.group(1).strip()
            break
    if not title:
        title = md_path.stem

    return out_path, title, turn_count, line_count


def send_to_telegram(token: str, chat: str, html_path: Path,
                     title: str, turn_count: int, line_count: int) -> dict:
    """Send HTML content as .txt file attachment to Telegram."""
    import requests

    results = {}

    # Header message
    header = (
        f'📄 <b>{title}</b>\n'
        f'🔄 {turn_count}턴 · {line_count}줄 · Tistory <b>HTML 모드</b> 붙여넣기\n'
        f'⬇️ 아래 첨부파일 다운로드 → 전체 복사 → Tistory HTML 모드에 붙여넣기'
    )
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": header, "parse_mode": "HTML"},
        timeout=15,
    )
    results["header"] = r.json()

    # File attachment
    fname = html_path.name
    with open(html_path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={
                "chat_id": chat,
                "caption": f"{fname} — 전체 복사 → Tistory HTML 모드 붙여넣기",
            },
            files={"document": (fname, f, "text/plain")},
            timeout=60,
        )
    results["file"] = r.json()

    return results


def main() -> int:
    html_mode = "--html" in sys.argv
    json_mode = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage: python3 log_to_tg.py [--html] [--json] <file.md>", file=sys.stderr)
        return 1

    md_path = Path(args[0])
    if not md_path.is_absolute():
        # Relative to helana_log or cwd
        if (LOG_REPO / md_path).exists():
            md_path = LOG_REPO / md_path
        elif not md_path.exists():
            print(f"❌ 파일 없음: {md_path}", file=sys.stderr)
            return 1

    if not md_path.exists():
        print(f"❌ 파일 없음: {md_path}", file=sys.stderr)
        return 1

    token, chat = get_secrets()
    if not token or not chat:
        print("❌ TG_TOKEN / TG_CHAT 미설정", file=sys.stderr)
        return 1

    if not html_mode:
        # Simple mode: send markdown as document
        import requests
        fname = md_path.name
        title = ""
        for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
            m = __import__('re').match(r'^#\s+(.+)', line)
            if m:
                title = m.group(1).strip()
                break
        if not title:
            title = fname

        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat,
                "text": f'📄 <b>{title}</b>\n📝 마크다운 · Tistory 마크다운 모드 붙여넣기\n⬇️ 아래 첨부파일 다운로드 → 전체 복사 → 붙여넣기',
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        with open(md_path, "rb") as f:
            r2 = requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat, "caption": f"{fname}"},
                files={"document": (fname, f, "text/markdown")},
                timeout=60,
            )
        ok = r.json().get("ok") and r2.json().get("ok")
        result = {"ok": ok, "mode": "markdown", "file": str(md_path)}
        if json_mode:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f'{"✅" if ok else "❌"} MD 전송: {md_path.name}')
        return 0 if ok else 1

    # HTML mode
    print(f"🔧 변환 중: {md_path.name} → HTML ...", file=sys.stderr)
    html_path, title, turn_count, line_count = md_to_html(md_path)
    print(f"   {turn_count}턴 · {line_count}줄 → {html_path}", file=sys.stderr)

    print(f"📨 TG 전송 중 ...", file=sys.stderr)
    results = send_to_telegram(token, chat, html_path, title, turn_count, line_count)

    ok = results.get("file", {}).get("ok", False)
    result = {
        "ok": ok,
        "mode": "html",
        "file": str(md_path),
        "title": title,
        "turns": turn_count,
        "lines": line_count,
        "tg_header": results.get("header", {}).get("ok"),
        "tg_file": results.get("file", {}).get("ok"),
    }
    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'{"✅" if ok else "❌"} HTML 전송: {title} · {turn_count}턴 · {line_count}줄')

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

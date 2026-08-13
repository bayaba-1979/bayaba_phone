#!/usr/bin/env python3
"""parksy-distributor MCP v1.0 — 통합 멀티채널 송출 (Layer 5).

박씨 의도 (2026-05-11):
  "에이전트 모델 바뀌어도 MCP 고정 = 결정적 동작"
  "1편 만들면 39채널 자동 송출"

채널 풀세트 (channel_map.json 단일 진실):
  - YouTube  15채널 × 4계정 (a/b/c/d, d만 OAuth 만료)
  - Naver    3블로그 (parksy_kr / dtslib / eae_kr)
  - Tistory  21블로그 × 5계정
  - Telegram 봇 1개 (default chat)

도구 풀세트 (v1.0):
  - parksy_distribute_telegram(mp4_path, caption, chat_id?)
  - parksy_distribute_telegram_photo(img_path, caption?, chat_id?)
  - parksy_distribute_telegram_text(text, chat_id?)
  - parksy_distribute_youtube(mp4_path, title, description, channel|account, ...)
  - parksy_distribute_naver(account, title, content, tags?)
  - parksy_distribute_tistory(account, blog, title, content_html, tags?, visibility?)
  - parksy_distribute_discord(mp4_path|message, webhook_url?)
  - parksy_distribute_all(content_spec) — 4채널 라우터
  - parksy_distribute_status() — 채널별 가동/만료 상태
  - parksy_distribute_list_channels(platform?) — 채널 카탈로그
  - parksy_distribute_refresh_tokens(account?) — YouTube 토큰 자동 갱신

박씨 헌법:
  - reset --hard 금지: v0.1 도구 이름 전부 유지
  - BOM: channel_map.json (단일 진실)
  - 증빙: 매 호출 result에 platform/account/channel/cmd 박음
"""
from __future__ import annotations
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("parksy-distributor")

# ── 박씨 자산 경로 (단일 진실) ────────────────────────────────────────
HERE = Path(__file__).parent
CHANNEL_MAP_PATH = HERE / "channel_map.json"
PAPYRUS = Path.home() / "dtslib-papyrus"
YT_DIR = PAPYRUS / "tools" / "youtube"
NAVER_DIR = PAPYRUS / "tools" / "naver"
TISTORY_DIR = PAPYRUS / "tools" / "tistory"

# ── 박씨 텔레그램 (.env 또는 OS env) ──────────────────────────────────
def _load_env():
    """`.env` 파일이 있으면 로드 (보안: 토큰 커밋 금지)."""
    envp = HERE / ".env"
    if envp.exists():
        for line in envp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env()
TG_BOT_TOKEN = os.environ.get("PARKSY_TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("PARKSY_TG_CHAT_ID", "")


def _load_map() -> dict:
    """channel_map.json 매 호출 새로 읽음 (박씨가 직접 갱신 가능)."""
    try:
        return json.loads(CHANNEL_MAP_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"channel_map.json 로드 실패: {e}"}


# ── _probe_mp4 (v0.1 그대로) ────────────────────────────────────────
def _probe_mp4(path: str) -> Dict[str, Any]:
    out = {"path": path, "exists": Path(path).exists()}
    if not out["exists"]:
        return out
    out["size_mb"] = round(Path(path).stat().st_size / 1024 / 1024, 2)
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            out["duration_sec"] = round(float(r.stdout.strip()), 2)
    except Exception as e:
        out["probe_error"] = str(e)[:120]
    return out


# ─────────────────────────────────────────────────────────────────────
#  TELEGRAM (3종 도구)
# ─────────────────────────────────────────────────────────────────────
def _resolve_tg_token(bot_token: Optional[str], bot: str = "") -> str:
    """bot_token 직접 / bot 이름 (parksy_air, book_papyrus...) / 기본값."""
    if bot_token:
        return bot_token
    if bot:
        m = _load_map().get("telegram", {}).get("bots", {})
        info = m.get(bot)
        if info:
            env_key = info.get("token_env", "")
            tok = os.environ.get(env_key, "")
            if tok:
                return tok
    return TG_BOT_TOKEN


@mcp.tool()
def parksy_distribute_telegram(
    mp4_path: str,
    caption: str = "",
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    bot: str = "",
) -> dict:
    """박씨 mp4 → Telegram sendVideo. (bot 선택 가능)

    bot: parksy_air / parksy_bridge / parksy_bridges / parksy_song /
         book_papyrus / book_eae_univ / book_branch / book_espiritu / book_gohsy_fashion
    비우면 default (parksy_air).
    """
    if not Path(mp4_path).exists():
        return {"status": "fail", "error": f"mp4 없음: {mp4_path}"}
    meta = _probe_mp4(mp4_path)
    cid = chat_id or TG_CHAT_ID
    tok = _resolve_tg_token(bot_token, bot)
    cmd = [
        "curl", "-s",
        "-F", f"chat_id={cid}",
        "-F", f"video=@{mp4_path}",
        "-F", f"caption={caption}",
        "-F", "supports_streaming=true",
        f"https://api.telegram.org/bot{tok}/sendVideo",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"status": "fail", "error": f"curl rc={r.returncode}",
                    "stderr": r.stderr[-200:]}
        data = json.loads(r.stdout)
        if not data.get("ok"):
            return {"status": "fail", "error": data.get("description"), "meta": meta}
        return {"status": "ok", "platform": "telegram", "bot": bot or "default",
                "message_id": data["result"]["message_id"], "chat_id": cid, "meta": meta}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_distribute_telegram_photo(
    img_path: str,
    caption: str = "",
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> dict:
    """이미지 → Telegram sendPhoto."""
    if not Path(img_path).exists():
        return {"status": "fail", "error": f"image 없음: {img_path}"}
    cid = chat_id or TG_CHAT_ID
    tok = bot_token or TG_BOT_TOKEN
    cmd = [
        "curl", "-s", "-F", f"chat_id={cid}",
        "-F", f"photo=@{img_path}", "-F", f"caption={caption}",
        f"https://api.telegram.org/bot{tok}/sendPhoto",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        data = json.loads(r.stdout)
        if not data.get("ok"):
            return {"status": "fail", "error": data.get("description")}
        return {"status": "ok", "platform": "telegram_photo",
                "message_id": data["result"]["message_id"], "chat_id": cid}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_distribute_telegram_text(
    text: str,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> dict:
    """텍스트 → Telegram sendMessage."""
    cid = chat_id or TG_CHAT_ID
    tok = bot_token or TG_BOT_TOKEN
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{tok}/sendMessage",
        "--data-urlencode", f"chat_id={cid}",
        "--data-urlencode", f"text={text}",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(r.stdout)
        if not data.get("ok"):
            return {"status": "fail", "error": data.get("description")}
        return {"status": "ok", "platform": "telegram_text",
                "message_id": data["result"]["message_id"], "chat_id": cid}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  YOUTUBE
# ─────────────────────────────────────────────────────────────────────
def _resolve_yt_channel(channel_or_account: str) -> Optional[Dict]:
    """`@handle` → 매핑 lookup. `a|b|c|d` → 계정 그대로. 둘 다 dict 반환."""
    m = _load_map().get("youtube", {})
    chans = m.get("channels", {})
    if channel_or_account in chans:
        info = dict(chans[channel_or_account])
        info["handle"] = channel_or_account
        return info
    if channel_or_account in ("a", "b", "c", "d"):
        return {"account": channel_or_account, "handle": None}
    return None


@mcp.tool()
def parksy_distribute_youtube(
    mp4_path: str,
    title: str,
    description: str = "",
    channel: str = "",
    account: str = "",
    tags: Optional[List[str]] = None,
    category_id: str = "22",
    privacy: str = "private",
    thumbnail: str = "",
    chapters: Optional[List[Dict]] = None,
) -> dict:
    """박씨 mp4 → YouTube. (v1.0 — upload.cjs 실제 호출)

    채널 결정 우선순위:
      1. channel="@blogger-parksy" → channel_map에서 account 자동
      2. account="a" 직접 지정 → 첫 번째 채널 (계정 단위 업로드)
      3. 둘 다 비우면 fail

    upload.cjs 큐 구조:
      uploads/pending/{ts}.json 박음 → node upload.cjs <account> {ts}.json → done/ 이동
    """
    if not Path(mp4_path).exists():
        return {"status": "fail", "error": f"mp4 없음: {mp4_path}"}

    target = channel or account
    info = _resolve_yt_channel(target)
    if not info:
        return {"status": "fail", "error": f"channel/account 미식별: {target}"}

    acc = info["account"]
    # description에 chapters 자동 부착
    if chapters:
        lines = ["", "Chapters:"]
        cum = 0.0
        for c in chapters:
            mm = int(cum // 60); ss = int(cum % 60)
            lines.append(f"{mm:02d}:{ss:02d} {c.get('title','')}")
            cum += float(c.get("duration_sec", 0))
        description = (description + "\n".join(lines)).strip()

    # pending/{ts}.json 박음
    pending_dir = YT_DIR / "uploads" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    spec = {
        "account": acc, "title": title[:100], "description": description,
        "tags": tags or [], "category_id": category_id, "privacy": privacy,
        "file": str(Path(mp4_path).resolve()),
    }
    if thumbnail and Path(thumbnail).exists():
        spec["thumbnail"] = str(Path(thumbnail).resolve())
    if info.get("channel_id"):
        spec["target_channel_id"] = info["channel_id"]
        spec["target_handle"] = info.get("handle")
    spec_file = pending_dir / f"parksy_{ts}.json"
    spec_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    # upload.cjs 호출
    try:
        r = subprocess.run(
            ["node", "upload.cjs", acc, spec_file.name],
            cwd=YT_DIR, capture_output=True, text=True, timeout=1800,
        )
        ok = r.returncode == 0
        # done 확인 — upload.cjs는 _video_id 키 사용 (underscore prefix)
        done_file = YT_DIR / "uploads" / "done" / spec_file.name
        video_id = None
        if done_file.exists():
            done_spec = json.loads(done_file.read_text(encoding="utf-8"))
            video_id = (done_spec.get("_video_id") or done_spec.get("video_id")
                        or done_spec.get("result", {}).get("video_id"))
        return {
            "status": "ok" if ok else "fail",
            "platform": "youtube",
            "account": acc, "handle": info.get("handle"),
            "channel_id": info.get("channel_id"),
            "video_id": video_id,
            "video_url": f"https://youtu.be/{video_id}" if video_id else None,
            "spec_file": str(spec_file),
            "stdout_tail": r.stdout[-500:],
            "stderr_tail": r.stderr[-200:] if r.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"status": "fail", "error": "upload.cjs 30분 초과", "spec_file": str(spec_file)}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  NAVER
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_distribute_naver(
    account: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    category: str = "",
) -> dict:
    """박씨 글 → Naver 블로그. (post.cjs 호출, Playwright + 쿠키)

    account: parksy_kr / dtslib / eae_kr
    """
    m = _load_map().get("naver", {}).get("blogs", {})
    if account not in m:
        return {"status": "fail", "error": f"naver account 미식별: {account}",
                "available": list(m.keys())}

    posts_dir = NAVER_DIR / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    spec = {
        "account": account, "title": title, "content": content,
        "tags": tags or [], "category": category,
    }
    spec_file = posts_dir / f"parksy_{ts}.json"
    spec_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    try:
        r = subprocess.run(
            ["node", "post.cjs", account, spec_file.name],
            cwd=NAVER_DIR, capture_output=True, text=True, timeout=600,
        )
        return {
            "status": "ok" if r.returncode == 0 else "fail",
            "platform": "naver", "account": account,
            "blog_url": f"https://blog.naver.com/{m[account]['naver_id']}",
            "spec_file": str(spec_file),
            "stdout_tail": r.stdout[-500:],
            "stderr_tail": r.stderr[-200:] if r.stderr else "",
        }
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  TISTORY
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_distribute_tistory(
    account: str,
    blog: str,
    title: str,
    content_html: str,
    tags: Optional[List[str]] = None,
    category: str = "",
    visibility: str = "public",
) -> dict:
    """박씨 글 → Tistory 블로그. (post.py 호출, Playwright + 카카오 세션)

    account: parksy_kr / dtslib / eae_kr / dtslib1k / dtslib2k
    blog: blogger-parksy / philosopher-parksy / ... (총 21블로그)
    """
    m = _load_map().get("tistory", {}).get("blogs", {})
    if blog not in m:
        return {"status": "fail", "error": f"tistory blog 미식별: {blog}",
                "available_count": len(m)}
    if m[blog]["account"] != account:
        return {"status": "fail",
                "error": f"account 불일치: blog={blog} 는 account={m[blog]['account']} 소유"}

    posts_dir = TISTORY_DIR / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    spec = {
        "account": account, "blog": blog, "title": title,
        "content": content_html, "tags": tags or [],
        "category": category, "visibility": visibility,
    }
    spec_file = posts_dir / f"parksy_{ts}.json"
    spec_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    # 직접 Playwright (post.py 우회 — 셀렉터 깨짐 fix됨)
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from _tistory_publish import publish_tistory
        r = publish_tistory(
            account=account, blog=blog, title=title,
            content_html=content_html, tags=tags or [], visibility=visibility,
        )
        r["spec_file"] = str(spec_file)
        return r
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}",
                "spec_file": str(spec_file)}


# ─────────────────────────────────────────────────────────────────────
#  DISCORD (v1.0 — 28 webhook, 박씨 28레포 1:1)
# ─────────────────────────────────────────────────────────────────────
def _resolve_discord_webhook(channel_or_url: str) -> Optional[str]:
    """레포명(`dtslib-papyrus`) 또는 webhook URL 직접 → URL 반환."""
    if channel_or_url.startswith("http"):
        return channel_or_url
    m = _load_map().get("discord", {}).get("channels", {})
    return m.get(channel_or_url)


@mcp.tool()
def parksy_distribute_discord(
    channel: str = "",
    message: str = "",
    mp4_path: str = "",
    img_path: str = "",
    webhook_url: Optional[str] = None,
    username: str = "Parksy",
    avatar_url: str = "",
) -> dict:
    """박씨 28레포 ↔ Discord 28채널 webhook 송출.

    channel: 레포명 (dtslib-papyrus, parksy-image, koosy, ...) 또는 webhook URL
    Discord 8MB(non-Nitro) / 25MB(Boost) 한도. 초과 시 link만 박음.
    """
    url = webhook_url or _resolve_discord_webhook(channel)
    if not url:
        return {"status": "fail",
                "error": f"discord channel/webhook 미식별: {channel}",
                "available": list((_load_map().get("discord", {}).get("channels", {})).keys())[:10]}

    # 파일 첨부 or 텍스트
    if mp4_path and Path(mp4_path).exists():
        meta = _probe_mp4(mp4_path)
        if meta.get("size_mb", 0) > 25:
            return {"status": "fail",
                    "error": f"Discord 25MB 초과: {meta['size_mb']}MB",
                    "next_step": "압축 또는 외부 호스팅 + link"}
        files_arg = ["-F", f"file=@{mp4_path}"]
    elif img_path and Path(img_path).exists():
        files_arg = ["-F", f"file=@{img_path}"]
    else:
        files_arg = []

    payload = {"username": username, "content": message[:2000]}
    if avatar_url:
        payload["avatar_url"] = avatar_url
    cmd = ["curl", "-s", "-X", "POST", url,
           "-F", f"payload_json={json.dumps(payload, ensure_ascii=False)}"] + files_arg

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        # Discord webhook: 성공 시 빈 응답(204) 또는 메시지 JSON
        out = r.stdout.strip()
        if r.returncode != 0:
            return {"status": "fail", "error": f"curl rc={r.returncode}",
                    "stderr": r.stderr[-200:]}
        msg_id = None
        if out:
            try:
                data = json.loads(out)
                msg_id = data.get("id")
                if data.get("code"):  # error code
                    return {"status": "fail", "error": data.get("message"),
                            "discord_code": data.get("code"), "channel": channel}
            except Exception:
                pass
        return {"status": "ok", "platform": "discord", "channel": channel,
                "message_id": msg_id, "webhook_url_masked": url[:60] + "..."}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  ALL (4채널 라우터)
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_distribute_all(
    mp4_path: str = "",
    title: str = "",
    description: str = "",
    plan: Optional[Dict] = None,
    platforms: Optional[List[str]] = None,
    youtube_channel: str = "",
    naver_account: str = "",
    tistory_account: str = "",
    tistory_blog: str = "",
    text_content: str = "",
    img_path: str = "",
    chat_id: Optional[str] = None,
) -> dict:
    """박씨 1편 → N채널 송출. 박씨 콘텐츠 한 줄 → 다 박음.

    platforms: ["telegram", "youtube", "naver", "tistory", "discord"]
    plan: parksy-actor compile_timeline (chapters 자동 추출)
    """
    platforms = platforms or ["telegram"]
    plan = plan or {}
    sections = plan.get("sections", [])

    # plan에서 title/description 자동 추출
    auto_title = (sections[0].get("heading") if sections else title)[:80]
    final_title = title or auto_title
    desc_lines = []
    if sections:
        desc_lines.append("Chapters:")
        cum = 0.0
        for s in sections:
            mm = int(cum // 60); ss = int(cum % 60)
            desc_lines.append(f"{mm:02d}:{ss:02d} {s.get('heading','')}")
            cum += float(s.get("duration_sec", 0))
    final_desc = description or "\n".join(desc_lines)
    caption = f"{final_title} · {len(sections)} chapters" if sections else final_title

    results = {"channels": {}, "mp4_meta": _probe_mp4(mp4_path) if mp4_path else None}

    if "telegram" in platforms and mp4_path:
        results["channels"]["telegram"] = parksy_distribute_telegram(
            mp4_path, caption=caption, chat_id=chat_id)
    elif "telegram_photo" in platforms and img_path:
        results["channels"]["telegram_photo"] = parksy_distribute_telegram_photo(
            img_path, caption=caption, chat_id=chat_id)
    elif "telegram_text" in platforms and text_content:
        results["channels"]["telegram_text"] = parksy_distribute_telegram_text(
            text_content, chat_id=chat_id)

    if "youtube" in platforms and mp4_path and youtube_channel:
        chapters = [{"title": s.get("heading"), "duration_sec": s.get("duration_sec")}
                    for s in sections]
        results["channels"]["youtube"] = parksy_distribute_youtube(
            mp4_path, title=final_title, description=final_desc,
            channel=youtube_channel, chapters=chapters)

    if "naver" in platforms and naver_account and text_content:
        results["channels"]["naver"] = parksy_distribute_naver(
            naver_account, title=final_title, content=text_content)

    if "tistory" in platforms and tistory_account and tistory_blog and text_content:
        results["channels"]["tistory"] = parksy_distribute_tistory(
            tistory_account, tistory_blog, title=final_title, content_html=text_content)

    if "discord" in platforms:
        results["channels"]["discord"] = parksy_distribute_discord(
            mp4_path=mp4_path, message=caption)

    ok_count = sum(1 for r in results["channels"].values() if r.get("status") == "ok")
    results["status"] = "ok" if ok_count > 0 else "partial"
    results["sent_count"] = ok_count
    results["platforms_attempted"] = list(results["channels"].keys())
    return results


# ─────────────────────────────────────────────────────────────────────
#  메타 도구 (status / list / refresh)
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_distribute_status() -> dict:
    """채널별 가동 / 토큰 만료 / 환경 상태."""
    m = _load_map()
    out = {"version": "v1.0", "channel_map_path": str(CHANNEL_MAP_PATH)}

    # Telegram
    out["telegram"] = {
        "configured": bool(TG_BOT_TOKEN and TG_CHAT_ID),
        "default_chat_id": TG_CHAT_ID,
    }

    # YouTube — 토큰 4개 만료 체크
    yt_status = {"channels": len(m.get("youtube", {}).get("channels", {})), "accounts": {}}
    now_ms = int(time.time() * 1000)
    for tid in ("a", "b", "c", "d"):
        tpath = YT_DIR / "accounts" / f"token_{tid}.json"
        if not tpath.exists():
            yt_status["accounts"][tid] = {"status": "missing"}
            continue
        try:
            tok = json.loads(tpath.read_text())
            exp = tok.get("expiry_date", 0)
            has_refresh = bool(tok.get("refresh_token"))
            yt_status["accounts"][tid] = {
                "access_valid": exp > now_ms,
                "expiry_in_min": (exp - now_ms) // 60000 if exp > now_ms else None,
                "refresh_token": has_refresh,
                "scope_count": len((tok.get("scope") or "").split()),
            }
        except Exception as e:
            yt_status["accounts"][tid] = {"status": "error", "error": str(e)[:80]}
    out["youtube"] = yt_status

    # Naver — 쿠키 파일 체크
    out["naver"] = {
        "blogs": len(m.get("naver", {}).get("blogs", {})),
        "cookies": {},
    }
    for nid in ("parksy_kr", "dtslib", "eae_kr"):
        p = NAVER_DIR / "accounts" / "cookies" / f"{nid}.json"
        out["naver"]["cookies"][nid] = "exists" if p.exists() else "missing"

    # Tistory
    out["tistory"] = {
        "blogs": len(m.get("tistory", {}).get("blogs", {})),
        "accounts": 5,
        "cookies_dir": str(TISTORY_DIR / "cookies"),
    }

    # Discord — channel_map에서 webhook 28개 카운트
    dc = m.get("discord", {})
    out["discord"] = {
        "guild_id": dc.get("guild_id"),
        "channels_count": len(dc.get("channels", {})),
        "configured": len(dc.get("channels", {})) > 0,
    }
    # Telegram 봇 9개 카운트 + 토큰 환경변수 valid 체크
    tg = m.get("telegram", {})
    bots = tg.get("bots", {})
    bot_status = {}
    for bname, binfo in bots.items():
        env_key = binfo.get("token_env", "")
        bot_status[bname] = {
            "username": binfo.get("username"),
            "token_loaded": bool(os.environ.get(env_key)),
        }
    out["telegram"]["bots_count"] = len(bots)
    out["telegram"]["bots"] = bot_status
    return out


@mcp.tool()
def parksy_distribute_list_channels(platform: str = "") -> dict:
    """채널 카탈로그 — YouTube/Naver/Tistory 풀세트 노출."""
    m = _load_map()
    if platform:
        return {platform: m.get(platform, {"error": f"unknown platform: {platform}"})}
    return {
        "youtube": {h: v for h, v in m.get("youtube", {}).get("channels", {}).items()},
        "naver":   m.get("naver", {}).get("blogs", {}),
        "tistory": m.get("tistory", {}).get("blogs", {}),
        "telegram": m.get("telegram", {}),
    }


@mcp.tool()
def parksy_distribute_refresh_tokens(account: str = "") -> dict:
    """YouTube access_token 갱신 (refresh_token 사용).

    account: a/b/c/d 단일 또는 빈 문자열(전체).
    """
    refresh_script = YT_DIR / "refresh.cjs"
    if not refresh_script.exists():
        return {"status": "fail", "error": f"refresh.cjs 없음: {refresh_script}"}
    try:
        r = subprocess.run(
            ["node", "refresh.cjs"],
            cwd=YT_DIR, capture_output=True, text=True, timeout=60,
        )
        return {
            "status": "ok" if r.returncode == 0 else "fail",
            "stdout": r.stdout,
            "stderr_tail": r.stderr[-200:] if r.stderr else "",
        }
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────
#  v2 — YouTube 메타/플레이리스트/통계 (직접 API)
# ─────────────────────────────────────────────────────────────────────
def _yt_resolve_account(channel_or_account: str) -> tuple:
    """`@handle` 또는 `a|b|c|d` → (account_id, channel_id_or_None, channel_slug_or_None)

    channel_slug는 `token_{account}__{slug}.json` 채널별 토큰 파일명에
    쓰는 값 — 계정 기본 채널이 아닌 브랜드 관리 채널은 이 슬러그가 있어야
    올바른 토큰으로 쓰기 작업이 통과한다 (2026-07-22 확인, 계정 기본
    토큰으로는 브랜드 채널 쓰기가 403 뜸).
    """
    info = _resolve_yt_channel(channel_or_account)
    if not info:
        return None, None, None
    handle = info.get("handle")
    slug = handle.lstrip("@") if handle else None
    return info["account"], info.get("channel_id"), slug


@mcp.tool()
def parksy_youtube_update_video(
    account: str, video_id: str,
    title: str = "", description: str = "",
    tags: Optional[List[str]] = None,
    category_id: str = "", privacy: str = "",
    channel: str = "",
) -> dict:
    """기존 영상 메타 수정 (title/desc/tags/category/privacy).

    channel: @handle 지정 시 채널별 토큰(token_{account}__{slug}.json)
    우선 사용 — 브랜드 관리 채널 쓰기에 필요 (2026-07-22).
    """
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import update_video
        return update_video(
            account, video_id,
            title=title or None, description=description or None,
            tags=tags, category_id=category_id or None,
            privacy=privacy or None,
            channel=channel.lstrip("@") or None,
        )
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_list_videos(
    channel: str = "", account: str = "", max_results: int = 10,
) -> dict:
    """채널 최근 영상 N개. channel=@handle 또는 account=a/b/c."""
    acc, cid, slug = _yt_resolve_account(channel or account)
    if not acc:
        return {"status": "fail", "error": f"channel/account 미식별: {channel or account}"}
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import list_videos
        return list_videos(acc, channel_id=cid, max_results=max_results, channel=slug)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_list_playlists(
    channel: str = "", account: str = "",
) -> dict:
    """채널 플레이리스트 카탈로그."""
    acc, cid, slug = _yt_resolve_account(channel or account)
    if not acc:
        return {"status": "fail", "error": f"미식별: {channel or account}"}
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import list_playlists
        return list_playlists(acc, channel_id=cid, channel=slug)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_create_playlist(
    channel: str = "", account: str = "",
    title: str = "", description: str = "", privacy: str = "private",
) -> dict:
    """플레이리스트 생성."""
    acc, _, slug = _yt_resolve_account(channel or account)
    if not acc:
        return {"status": "fail", "error": f"미식별: {channel or account}"}
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import create_playlist
        return create_playlist(acc, title, description, privacy, channel=slug)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_add_to_playlist(
    account: str, playlist_id: str, video_id: str,
    channel: str = "",
) -> dict:
    """영상을 플레이리스트에 추가. channel: @handle 지정 시 채널별 토큰 사용."""
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import add_to_playlist
        return add_to_playlist(account, playlist_id, video_id, channel=channel.lstrip("@") or None)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_get_analytics(
    channel: str = "", account: str = "", days: int = 7,
) -> dict:
    """채널 통계 (views/watchTime/subs gained/lost) N일."""
    acc, cid, slug = _yt_resolve_account(channel or account)
    if not acc:
        return {"status": "fail", "error": f"미식별"}
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import get_analytics
        return get_analytics(acc, channel_id=cid, days=days, channel=slug)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_get_channel_info(
    channel: str = "", account: str = "",
) -> dict:
    """채널 정보 (구독자/영상수/조회수/설명)."""
    acc, cid, slug = _yt_resolve_account(channel or account)
    if not acc:
        return {"status": "fail", "error": f"미식별"}
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import get_channel_info
        return get_channel_info(acc, channel_id=cid, channel=slug)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_youtube_update_branding(
    account: str, channel_id: str,
    description: str = "", keywords: str = "", country: str = "",
    channel: str = "",
) -> dict:
    """채널 브랜딩 설정 변경 (description/keywords/country).

    channel: @handle 지정 시 채널별 토큰 우선 사용 — 브랜드 관리 채널은
    이게 없으면 403 뜬다 (2026-07-22 확인).
    """
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).parent))
        from _youtube_api import update_channel_branding
        return update_channel_branding(
            account, channel_id,
            description=description or None,
            channel=channel.lstrip("@") or None,
            keywords=keywords or None,
            country=country or None,
        )
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  v2 — Discord 관리
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_discord_edit_message(
    channel: str, message_id: str, new_content: str,
) -> dict:
    """webhook으로 보낸 메시지 편집."""
    url = _resolve_discord_webhook(channel)
    if not url:
        return {"status": "fail", "error": f"channel 미식별: {channel}"}
    edit_url = f"{url}/messages/{message_id}"
    payload = json.dumps({"content": new_content[:2000]})
    cmd = ["curl", "-s", "-X", "PATCH", edit_url,
           "-H", "Content-Type: application/json", "-d", payload]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(r.stdout) if r.stdout else {}
        if "code" in data and data.get("code"):
            return {"status": "fail", "error": data.get("message"), "code": data.get("code")}
        return {"status": "ok", "channel": channel, "message_id": message_id}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_discord_delete_message(
    channel: str, message_id: str,
) -> dict:
    """webhook 메시지 삭제."""
    url = _resolve_discord_webhook(channel)
    if not url:
        return {"status": "fail", "error": f"channel 미식별: {channel}"}
    del_url = f"{url}/messages/{message_id}"
    try:
        r = subprocess.run(["curl", "-s", "-X", "DELETE", del_url],
                          capture_output=True, text=True, timeout=30)
        return {"status": "ok" if r.returncode == 0 else "fail",
                "channel": channel, "message_id": message_id,
                "response": r.stdout[:200]}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────
#  v2 — 매핑 검증
# ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def parksy_validate_mapping(platform: str = "youtube") -> dict:
    """channel_map.json vs 실제 API 응답 비교.
    YouTube: 각 채널 channel_id가 실제 존재하는지 확인.
    """
    m = _load_map()
    if platform == "youtube":
        results = {"matched": [], "mismatched": [], "errors": []}
        for handle, info in m.get("youtube", {}).get("channels", {}).items():
            try:
                import sys as _s
                _s.path.insert(0, str(Path(__file__).parent))
                from _youtube_api import get_channel_info
                r = get_channel_info(info["account"], info["channel_id"])
                if r.get("status") == "ok" and r.get("channels"):
                    actual_title = r["channels"][0]["title"]
                    results["matched"].append({
                        "handle": handle, "channel_id": info["channel_id"],
                        "actual_title": actual_title, "subs": r["channels"][0]["subs"],
                    })
                else:
                    results["mismatched"].append({"handle": handle, "channel_id": info["channel_id"]})
            except Exception as e:
                results["errors"].append({"handle": handle, "error": str(e)[:120]})
        return {"status": "ok", "platform": "youtube",
                "matched_count": len(results["matched"]),
                "mismatched_count": len(results["mismatched"]),
                "error_count": len(results["errors"]),
                "details": results}
    return {"status": "fail", "error": f"platform 미지원: {platform}"}


# ─────────────────────────────────────────────────────────────────────
#  v3 — Tistory/Naver 콘솔 (카테고리/스킨/통계/글리스트)
# ─────────────────────────────────────────────────────────────────────
def _t_console():
    import sys as _s
    _s.path.insert(0, str(Path(__file__).parent))
    from _tistory_console import (
        list_categories as t_cats, create_category as t_create_cat,
        list_skins as t_skins, get_statistics as t_stats, list_posts as t_posts,
    )
    return t_cats, t_create_cat, t_skins, t_stats, t_posts


def _n_console():
    import sys as _s
    _s.path.insert(0, str(Path(__file__).parent))
    from _naver_console import (
        list_categories as n_cats, get_statistics as n_stats, list_posts as n_posts,
    )
    return n_cats, n_stats, n_posts


@mcp.tool()
def parksy_tistory_list_categories(account: str, blog: str) -> dict:
    """Tistory 블로그 카테고리 + post_count."""
    try:
        t_cats, *_ = _t_console()
        return t_cats(account, blog)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_tistory_create_category(account: str, blog: str, name: str) -> dict:
    """Tistory 카테고리 신규 추가."""
    try:
        _, t_create, *_ = _t_console()
        return t_create(account, blog, name)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_tistory_list_skins(account: str, blog: str) -> dict:
    """Tistory 스킨 카탈로그."""
    try:
        _, _, t_skins, *_ = _t_console()
        return t_skins(account, blog)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_tistory_get_statistics(account: str, blog: str) -> dict:
    """Tistory 방문자/조회수 통계."""
    try:
        *_, t_stats, _ = _t_console()
        return t_stats(account, blog)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_tistory_list_posts(account: str, blog: str, max_count: int = 20) -> dict:
    """Tistory 글 리스트."""
    try:
        *_, t_posts = _t_console()
        return t_posts(account, blog, max_count)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_naver_list_categories(account: str) -> dict:
    """Naver 블로그 카테고리 (parksy_kr / dtslib / eae_kr)."""
    try:
        n_cats, *_ = _n_console()
        return n_cats(account)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_naver_get_statistics(account: str) -> dict:
    """Naver 블로그 방문자/조회수 통계."""
    try:
        _, n_stats, _ = _n_console()
        return n_stats(account)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def parksy_naver_list_posts(account: str, max_count: int = 20) -> dict:
    """Naver 블로그 글 리스트."""
    try:
        *_, n_posts = _n_console()
        return n_posts(account, max_count)
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


def main():
    print("[parksy-distributor v1.0] stdio 박음 — 11도구 가동", flush=True)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

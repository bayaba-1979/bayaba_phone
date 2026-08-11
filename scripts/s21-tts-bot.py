#!/usr/bin/env python3
"""
S21 TTS Bot — 🔊 읽어주기 버튼 처리 (최소형)
버튼 탭 → 음성 생성 → 전송. 중간 메시지 없음. 로그 최소화.

사용법:
  python3 s21-tts-bot.py --daemon
  bash s21-tts-bot.sh start
"""

import sys, os, json, time, signal, asyncio, tempfile, requests, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_token():
    env_file = os.path.join(os.path.dirname(SCRIPT_DIR), ".secrets.env")
    t = os.environ.get("TG_TOKEN", "")
    if not t and os.path.exists(env_file):
        for line in open(env_file):
            if line.startswith("TG_TOKEN="):
                t = line.split("=", 1)[1].strip().strip('"')
                break
    return t or os.environ.get("TG_TOKEN", "")

TG_TOKEN = load_token()
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

VOICES = {"injoon": "ko-KR-InJoonNeural", "sunhi": "ko-KR-SunHiNeural"}
DEFAULT_VOICE = "sunhi"

async def text_to_voice(text: str, voice_key: str = "sunhi") -> str | None:
    voice = VOICES.get(voice_key, VOICES["sunhi"])
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp.name)
        if os.path.getsize(tmp.name) > 100:
            return tmp.name
    except Exception as e:
        pass
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)
    return None

def tg_send_voice(chat_id: int, mp3_path: str):
    with open(mp3_path, "rb") as f:
        requests.post(f"{TG_API}/sendVoice",
                      data={"chat_id": chat_id},
                      files={"voice": (os.path.basename(mp3_path), f)},
                      timeout=30)

def tg_answer(cb_id: str):
    requests.post(f"{TG_API}/answerCallbackQuery",
                  json={"callback_query_id": cb_id}, timeout=5)

# ── /radio 명령어 처리 ─────────────────────────────
async def handle_radio(msg: dict) -> str | None:
    """텍스트 메시지에서 /radio 명령 감지 → 파이프라인 실행 → 결과 반환"""
    text = msg.get("text", "").strip()
    if not text.startswith("/radio"):
        return None

    chat_id = msg.get("chat", {}).get("id", 0)
    cmd = text.split()[0] if text else "/radio"

    import sys, subprocess, json
    pipeline_dir = "/root/work/helena-programming/pipelines/radio_ticket"
    pipeline = f"{pipeline_dir}/dispatch.py"

    if cmd == "/radio_status":
        # 로그 요약
        logf = f"{pipeline_dir}/dispatch.log"
        if os.path.exists(logf):
            lines = open(logf).readlines()[-10:]
            requests.post(f"{TG_API}/sendMessage",
                         json={"chat_id": chat_id, "text": "📋 최근 로그:\n" + "".join(lines[-8:])},
                         timeout=10)
        else:
            requests.post(f"{TG_API}/sendMessage",
                         json={"chat_id": chat_id, "text": "📋 아직 실행 기록이 없습니다."},
                         timeout=10)
        return "ok"

    if cmd == "/radio_box":
        # 선물함 조회
        gb_file = f"{pipeline_dir}/giftbox.json"
        if os.path.exists(gb_file):
            try:
                gb = json.loads(open(gb_file).read())
                unsent = [s for s in gb if not s.get("sent")]
                msg_lines = [f"🎁 선물함 (총 {len(gb)}건, 미제출 {len(unsent)}건)\n"]
                for s in gb[-5:]:
                    icon = {"classic":"🎻","gayo":"🎤","pop":"🎸"}.get(s.get("channel_type",""),"🎙")
                    status = "✅" if s.get("sent") else "📤"
                    link = s.get("apply_url","")[:60]
                    msg_lines.append(f"{icon} {status} {s.get('channel','')} | {s.get('performance','')[:30]}")
                    if link:
                        msg_lines.append(f"   🔗 {link}")
                    msg_lines.append("")
                requests.post(f"{TG_API}/sendMessage",
                             json={"chat_id": chat_id, "text": "\n".join(msg_lines)},
                             timeout=10)
            except Exception as e:
                requests.post(f"{TG_API}/sendMessage",
                             json={"chat_id": chat_id, "text": f"❌ 선물함 오류: {e}"},
                             timeout=10)
        else:
            requests.post(f"{TG_API}/sendMessage",
                         json={"chat_id": chat_id, "text": "📭 아직 생성된 사연이 없어요. /radio_test 로 첫 사연을 만들어보세요!"},
                         timeout=10)
        return "ok"

    # /radio 또는 /radio_test
    dry = (cmd == "/radio_test")
    requests.post(f"{TG_API}/sendMessage",
                 json={"chat_id": chat_id, "text": "🎙 Helena Ticket 실행 중..." + (" (dry-run)" if dry else "")},
                 timeout=10)

    try:
        c = [sys.executable, pipeline]
        if dry:
            c.append("--dry-run")
        p = subprocess.run(c, capture_output=True, text=True, timeout=300)

        if dry:
            # 사연 내용을 TG로 전송 (stdout에 제출 링크 포함됨)
            out = p.stdout[-3500:]
            for chunk in [out[i:i+3500] for i in range(0, len(out), 3500)]:
                if chunk.strip():
                    requests.post(f"{TG_API}/sendMessage",
                                 json={"chat_id": chat_id, "text": "📝 사연:\n" + chunk},
                                 timeout=10)
        else:
            # 전체 실행 완료 — 선물함 링크 추가
            gb_file = f"{pipeline_dir}/giftbox.json"
            tip = ""
            if os.path.exists(gb_file):
                try:
                    gb = json.loads(open(gb_file).read())
                    latest = [s for s in gb if not s.get("sent")][-3:]
                    if latest:
                        tip = "\n\n📬 제출 링크:\n"
                        for s in latest:
                            tip += f"• {s.get('channel','')}: {s.get('apply_url','')}\n"
                except:
                    pass
            requests.post(f"{TG_API}/sendMessage",
                         json={"chat_id": chat_id, "text": f"✅ Helena Ticket 실행 완료! 3채널 사연이 전송되었습니다.{tip}\n\n💡 /radio_box 로 선물함을 확인하세요."},
                         timeout=10)
    except subprocess.TimeoutExpired:
        requests.post(f"{TG_API}/sendMessage",
                     json={"chat_id": chat_id, "text": "⏰ 시간 초과 (5분). 파이프라인이 너무 오래 걸립니다."},
                     timeout=10)
    except Exception as e:
        requests.post(f"{TG_API}/sendMessage",
                     json={"chat_id": chat_id, "text": f"❌ 오류: {e}"},
                     timeout=10)

    return "ok"

# ── 콜백 처리 ──────────────────────────────────────
async def handle_callback(cb: dict):
    cb_id = cb["id"]
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id", 0)
    text = msg.get("text", "")
    data = cb.get("data", "")

    if data != "tts_read" or not text:
        tg_answer(cb_id)
        return

    # 로딩 표시만 짧게 (버튼 멈춤 방지)
    requests.post(f"{TG_API}/answerCallbackQuery",
                  json={"callback_query_id": cb_id}, timeout=5)

    mp3 = await text_to_voice(text[:1200])
    if mp3:
        tg_send_voice(chat_id, mp3)
        os.unlink(mp3)

# ── 폴링 ───────────────────────────────────────────
async def poll_once(offset: int = 0) -> int:
    try:
        resp = requests.get(f"{TG_API}/getUpdates",
                           params={"offset": offset, "limit": 5, "timeout": 10},
                           timeout=15)
        for u in resp.json().get("result", []):
            offset = max(offset, u["update_id"] + 1)
            cb = u.get("callback_query")
            if cb:
                await handle_callback(cb)
            msg = u.get("message", {})
            txt = msg.get("text", "")
            if txt.startswith("/radio") or txt.startswith("/radio_"):
                await handle_radio(msg)
    except Exception:
        pass
    return offset

async def main_loop():
    try:
        r = requests.get(f"{TG_API}/getUpdates", params={"limit": 1}, timeout=10)
        offset = max([u["update_id"] + 1 for u in r.json().get("result", [])], default=0)
    except:
        offset = 0

    while True:
        offset = await poll_once(offset)
        await asyncio.sleep(3)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", "-d", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    asyncio.run(main_loop())
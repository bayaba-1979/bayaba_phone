#!/usr/bin/env bash
# 🎬 produce_doc.sh — 레인 B · 구독 다큐 (누나 사진 1장 → 딥페이크 10초 클립 → 더빙 → 이어붙이기)
# 표준: _notebook/86-pd-two-lanes-free-vs-grok_Claude.md §3·§5
# 레인 A(produce_pd.sh)와 분리. 이 스크립트는 Grok 구독 있을 때만 켠다.
# 공용 꼬리(concat·BGM·TG)는 레인 A와 동일 → 패턴·상수 재사용.
#
# 입력 → 출력 (기점 83 §3):
#   [안드로이드] 누나 얼굴 사진 1장
#         │  (안드로이드↔proot 브릿지, 이미 있음)
#         ▼
#   [비전]  얼굴 참조 고정 + 장면 인식
#   [합성]  image_edit — 얼굴이 장면 안에 앉는다
#   [클립]  image_to_video duration=10
#   [더빙]  프롬프트(=대사) → Edge TTS + RVC
#   [조립]  FFmpeg concat — 10초 + 10초 + …
#
# 사용:
#   GROK_SUB=on bash scripts/produce_doc.sh doc_01 "/sdcard/DCIM/Camera/누나.jpg" 대사.txt
#   GROK_SUB=on bash scripts/produce_doc.sh doc_01 --script out/doc_01/shot_bible.json
#
# 저작권 3단 (§4): source / ref_composition / content_origin 메타를 shot_bible에 박는다.
# 공개 범위 (§5②): PUBLISH=private|public — 헌법 15조는 Boss 결정.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EP="${1:?사용법: produce_doc.sh <ep_id> [photo_path] [dialog.txt] | --script shot_bible.json}"
shift

OUTDIR="${OUTDIR:-$ROOT/out/$EP}"
export OUTDIR EP ROOT
export BGM_VOLUME="${BGM_VOLUME:-0.025}"   # Golden whisper (레인 A와 동일)
export VOICE="${VOICE:-ko-KR-SunHiNeural}"  # Edge TTS 베이스 (RVC로 음색 변환)
export PUBLISH="${PUBLISH:-private}"        # §5② 공개 범위 — public/private

# ── 게이트 0: 구독 스위치 (§5①) ──
GROK_SUB="${GROK_SUB:-off}"
if [[ "$GROK_SUB" != "on" ]]; then
  echo "⛔ Grok 구독 없음 — 레인 B 스킵. 레인 A(produce_pd.sh)는 그대로."
  exit 0
fi
echo "=== 🎬 produce_doc · $EP (레인 B · 구독) ==="
echo "  PUBLISH=$PUBLISH  VOICE=$VOICE  BGM_VOLUME=$BGM_VOLUME"

if [[ -f "$ROOT/.secrets.env" ]]; then
  set -a; source "$ROOT/.secrets.env"; set +a
fi
mkdir -p "$OUTDIR"/{inbox,clips,voice,work}

# ── P0 intake: 사진 1장 + 대사(shot_bible) ──
PHOTO=""
DIALOG_FILE=""
if [[ "${1:-}" == "--script" ]]; then
  BIBLE="${2:?--script 다음에 shot_bible.json 경로}"; shift 2
  [[ -f "$BIBLE" ]] || { echo "❌ shot_bible 없음: $BIBLE"; exit 1; }
else
  PHOTO="${1:-}"
  DIALOG_FILE="${2:-}"
  [[ -n "$PHOTO" ]] || PHOTO="$(ls -t "$HOME"/inbox/*.{jpg,jpeg,png} 2>/dev/null | head -1 || true)"
  [[ -n "$PHOTO" ]] || { echo "❌ 사진 1장 필요 — 인자로 주거나 ~/inbox 에 넣어라"; exit 1; }
  cp "$PHOTO" "$OUTDIR/inbox/photo.jpg"
  PHOTO="$OUTDIR/inbox/photo.jpg"
  BIBLE="$OUTDIR/shot_bible.json"
  python3 - "$ROOT" "$OUTDIR" "$PHOTO" "$DIALOG_FILE" <<'PY'
import json, os, sys
from pathlib import Path
root, outdir, photo, dialog_file = sys.argv[1], Path(sys.argv[2]), sys.argv[3], (sys.argv[4] if len(sys.argv) > 4 else "")
out = Path(outdir)
# 대사: 파일(한 줄=한 컷) 없으면 데모 1컷
if dialog_file and Path(dialog_file).exists():
    dialogs = [l.strip() for l in Path(dialog_file).read_text(encoding="utf-8").splitlines() if l.strip()]
else:
    dialogs = ["안녕하세요, 저는 헬레나입니다."]
beats = [{"id": f"{i:02d}", "dialog": d, "scene": "", "emotion": "calm",
          "duration": 10} for i, d in enumerate(dialogs, 1)]
bible = {
    "id": os.environ.get("EP", "doc"),
    "standard": "produce_doc_v1",
    # 저작권 3단 메타 (§4) — 포맷 자유/표현 보호
    "source": "own_photo",                        # own_photo | public_domain
    "ref_composition": "80s_jp_magazine_frame_only",
    "content_origin": "self",                     # self | 누나
    "publish": os.environ.get("PUBLISH", "private"),
    "photo": photo,
    "resolution": "1080:1920",
    "beats": beats,
}
(out / "shot_bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
print("  wrote shot_bible.json · beats=%d · publish=%s" % (len(beats), bible["publish"]))
PY
fi
echo "[P0] photo=$PHOTO  bible=$BIBLE"

# ── P1 Grok 합성 + I2V 10초 클립 ──
# TODO(STUB): grok_api.py 에 image_edit(얼굴 합성) + image_to_video(duration=10) 추가 후 교체.
#   지금은 사진을 10초 정지화면 placeholder 로 — 파이프 end-to-end 테스트용.
echo "[P1] 클립 생성 (STUB — Grok I2V 미연결, 10초 정지화면 대체)..."
python3 - "$ROOT" "$OUTDIR" "$BIBLE" <<'PY'
import json, os, subprocess, sys
from pathlib import Path
root, out, bible_path = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
bible = json.loads(Path(bible_path).read_text(encoding="utf-8"))
photo = bible.get("photo", "")
for beat in bible["beats"]:
    bid = beat["id"]
    v = out / "clips" / f"{bid}_v.mp4"
    dur = str(beat.get("duration", 10))
    # placeholder: 사진을 1080x1920 으로 10초 루프 (실제로는 image_edit → image_to_video)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", photo, "-t", dur,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "30", str(v)], check=True, capture_output=True)
    print(f"  [{bid}] placeholder clip OK ({dur}s)")
print("  P1 done (Grok I2V 는 STUB)")
PY

# ── P2 더빙 (Edge TTS → RVC 음색) ──
# 표준: _notebook/81-helena-rvc-dubbing-standard_Claude.md
echo "[P2] 더빙 (Edge TTS + RVC)..."
python3 - "$ROOT" "$OUTDIR" "$BIBLE" <<'PY'
import json, os, subprocess, sys
from pathlib import Path
root, out, bible_path = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
bible = json.loads(Path(bible_path).read_text(encoding="utf-8"))
voice = os.environ.get("VOICE", "ko-KR-SunHiNeural")
for beat in bible["beats"]:
    bid, dialog, dur = beat["id"], beat["dialog"], float(beat.get("duration", 10))
    txt = out / "voice" / f"{bid}.txt"
    mp3 = out / "voice" / f"{bid}.mp3"
    txt.write_text(dialog, encoding="utf-8")
    subprocess.run(["edge-tts", "--voice", voice, "--rate=-8%", "-f", str(txt),
                    "--write-media", str(mp3)], check=True, capture_output=True)
    print(f"  [{bid}] TTS: {dialog[:18]}...")
print("  P2 done")
PY

# ── P4 조립: 비디오(10초) + 더빙(10초 패딩) mux → concat ──
echo "[P4] 클립 mux + concat..."
python3 - "$OUTDIR" "$BIBLE" <<'PY'
import json, subprocess, sys
from pathlib import Path
out, bible_path = Path(sys.argv[1]), sys.argv[2]
bible = json.loads(Path(bible_path).read_text(encoding="utf-8"))
for beat in bible["beats"]:
    bid, dur = beat["id"], str(beat.get("duration", 10))
    v = out / "clips" / f"{bid}_v.mp4"
    mp3 = out / "voice" / f"{bid}.mp3"
    a = out / "voice" / f"{bid}.m4a"
    clip = out / "clips" / f"{bid}.mp4"
    # 더빙을 10초로 패딩 (앞 0.3초 여백 + 무음)
    subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-af", "adelay=300|300,apad",
                    "-t", dur, "-c:a", "aac", str(a)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(v), "-i", str(a),
                    "-c:v", "copy", "-c:a", "aac", "-t", dur, str(clip)], check=True, capture_output=True)
    print(f"  [{bid}] muxed {dur}s")
# concat demuxer (레인 A와 동일 조립)
lines = [f"file '{out/'clips'/(b['id']+'.mp4')}'" for b in bible["beats"]]
(out / "work" / "concat.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(out / "work" / "concat.txt"), "-c", "copy",
                str(out / f"{os.environ['EP']}_body.mp4")], check=True, capture_output=True)
print("  P4 done → body")
PY

# ── P5 BGM (best-effort — helena-piano 자작 렌더) ──
echo "[P5] BGM (선택)..."
BODY="$OUTDIR/${EP}_body.mp4"
PLAY="$OUTDIR/${EP}_playable.mp4"
BGM_PATH="${BGM_PATH:-}"
if [[ -z "$BGM_PATH" ]]; then
  for c in "$ROOT/helena-piano/bgm/output/satie_gymnopedie1.mp3" \
           "$ROOT/helena-piano/bgm/output/clair_de_lune.mp3" \
           "$OUTDIR/bgm.m4a"; do
    [[ -f "$c" ]] && BGM_PATH="$c" && break
  done
fi
if [[ -n "$BGM_PATH" ]]; then
  ffmpeg -y -i "$BODY" -stream_loop -1 -i "$BGM_PATH" \
    -filter_complex "[1:a]volume=${BGM_VOLUME}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -shortest "$PLAY" 2>/dev/null
  echo "  BGM=$BGM_PATH (vol=$BGM_VOLUME)"
else
  cp "$BODY" "$PLAY"
  echo "  (BGM 스킵 — 없음)"
fi

# ── P6 TG 720p ──
echo "[P6] TG 720p..."
TG720="$OUTDIR/${EP}_tg.mp4"
ffmpeg -y -i "$PLAY" \
  -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p -preset veryfast -crf 23 \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \
  -c:a aac -b:a 128k -ar 48000 -ac 2 -movflags +faststart "$TG720" 2>/dev/null

if [[ -n "${TG_TOKEN:-}" && -n "${TG_CHAT:-}" && -f "$TG720" ]]; then
  curl -sS --connect-timeout 30 --max-time 240 -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendVideo" \
    -F chat_id="$TG_CHAT" -F video=@"$TG720" -F supports_streaming=true \
    -F caption="🎬 ${EP} · 레인 B 구독 다큐 (scaffold v1)
👤 source=$(python3 -c "import json;print(json.load(open('$BIBLE'))['source'])" 2>/dev/null) · publish=${PUBLISH}
⏱ 10초×N · Edge TTS + RVC · concat · BGM vol=${BGM_VOLUME}
— produce_doc.sh v1 · Grok I2V 는 STUB" \
    -o /tmp/tg_doc.json -w "\nhttp=%{http_code}\n" || echo "  ⚠️ [P6] TG send failed" >&2
else
  echo "  (TG skip — no token or no file)"
fi

echo "=== DONE ==="
ls -lah "$PLAY" "$TG720" 2>/dev/null || true
echo "bible: $BIBLE"
echo "📌 TODO: P1 Grok image_edit + image_to_video 연결 (grok_api.py)"

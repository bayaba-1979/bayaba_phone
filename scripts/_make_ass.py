#!/usr/bin/env python3
"""ASS typewriter subtitle generator V10 — 타이핑 타자기 스타일

Per-character typewriter reveal: 글자가 한 글자씩 "탁탁탁" 나타나는 효과.
No background box — 깔끔한 흰색 글자 + 검은 그림자만.

V10: Per-character typing (scale pop 130%→100% over 60ms) · white text · no banner bg
V9.1: _timing.json xfade-aware per-beat timestamps.

Usage:
  OUTDIR=/root/work/out/pd_intro EP=pd_intro python3 scripts/_make_ass.py
"""
from __future__ import annotations

import json, os, subprocess, sys
from pathlib import Path


def format_ass_time(seconds: float) -> str:
    """Convert float seconds to ASS timestamp: H:MM:SS.cc (centiseconds)"""
    cs = int(seconds * 100)
    h = cs // 360000
    m = (cs % 360000) // 6000
    s = (cs % 6000) // 100
    c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


# ═══════════════════════════════════════════════════════════════
#  Typewriter Style Tokens
# ═══════════════════════════════════════════════════════════════

FONT_SIZE    = 72          # pt
POP_SCALE    = 130         # % — start at 130% when char appears
POP_MS       = 60          # ms — quick "tak" snap to 100%
MARGIN_V     = 180         # px from bottom
PLAY_RES_X   = 1080
PLAY_RES_Y   = 1920
CENTER_X     = 540
SUBTITLE_Y   = PLAY_RES_Y - MARGIN_V  # 1740
LINE_SPACING = int(FONT_SIZE * 1.45)  # px between baselines
MAX_LINE_W   = PLAY_RES_X - 120       # 960px — leave side margins
CHAR_GAP     = 3            # px gap between characters


def char_width_px(ch: str) -> int:
    """Rough pixel width for a single character at FONT_SIZE pt."""
    cp = ord(ch)
    if cp == 0x20:
        return int(FONT_SIZE * 0.30)   # space
    elif 0xAC00 <= cp <= 0xD7AF:       # Hangul syllable
        return int(FONT_SIZE * 0.88)
    elif 0x3131 <= cp <= 0x318E:       # Hangul jamo
        return int(FONT_SIZE * 0.55)
    elif cp < 0x80:                    # ASCII / Latin / digits
        return int(FONT_SIZE * 0.52)
    else:                              # CJK punctuation etc.
        return int(FONT_SIZE * 0.55)


def main() -> int:
    outdir = Path(os.environ.get("OUTDIR", "/root/work/out/pd_intro"))
    ep     = os.environ.get("EP", "pd_intro")

    bible_path = outdir / "shot_bible.json"
    if not bible_path.exists():
        print("  ⚠️  no shot_bible.json — ASS skip")
        return 0

    bible = json.loads(bible_path.read_text(encoding="utf-8"))
    beats = bible.get("beats") or []

    # ── Read _timing.json for frame-accurate per-beat timestamps ──
    timing_path = outdir / "work" / "_timing.json"
    beat_timing = {}
    body_duration = 0.0
    use_timing = False
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        for tb in timing.get("beats", []):
            beat_timing[tb["id"]] = tb
        body_duration = timing.get("body_duration", 0)
        use_timing = True
        print(f"  ⏱️  _timing.json: {len(beat_timing)} beats, body={body_duration:.1f}s")
    else:
        print("  ⚠️  no _timing.json — falling back to ffprobe")

    # ── ASS Header ──────────────────────────────────────────
    # V10: BorderStyle=1 (outline+shadow only — NO opaque background box)
    #      Outline=3.5 (thick black outline for readability)
    #      Shadow=1.5 (subtle drop shadow)
    #      BackColour transparent (no banner)
    ass_header = [
        "[Script Info]",
        f"Title: {ep} — Typewriter Subtitles",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_RES_X}",
        f"PlayResY: {PLAY_RES_Y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # V10: clean white text, black outline, no background box
        # Primary=white, Outline=black, BackColour=transparent, BorderStyle=1
        f"Style: Type,Noto Sans CJK KR,{FONT_SIZE},&H00FFFFFF,&H00666666,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,0,0,1,3.5,1.5,2,{MARGIN_V},{MARGIN_V},{MARGIN_V},1",
        # Caption style: small warm label at top
        "Style: Caption,Noto Serif CJK KR,24,&H00FFB060,&H00000000,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,2,0,8,80,80,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    dialogues = []

    # ── Fallback: probe MP3 durations ──
    def _fallback_beat_dur(beat):
        bid = beat["id"]
        mp3 = outdir / f"{bid}.mp3"
        if mp3.exists():
            try:
                return float(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", str(mp3),
                ], text=True).strip() or "3.0")
            except Exception:
                pass
        return 3.0

    fallback_cursor = 0.0
    if not use_timing:
        bridges = bible.get("bridges") or []
        for br in bridges:
            if (br.get("id") or "").startswith("b_open") or "open" in (br.get("id") or ""):
                fallback_cursor = 5.5
                break

    total_chars_all_beats = 0
    for beat in beats:
        bid      = beat["id"]
        vo_text  = beat.get("vo") or beat.get("caption") or bid
        caption  = beat.get("caption") or ""
        pause    = float(beat.get("pause", 0))

        if use_timing and bid in beat_timing:
            bt = beat_timing[bid]
            beat_start = bt["start"]
            beat_end   = bt["end"]
            dur        = bt["duration"]
        else:
            dur = _fallback_beat_dur(beat)
            beat_start = fallback_cursor
            beat_end   = fallback_cursor + dur

        # ── Split into characters (preserve spaces for layout) ──
        chars = list(vo_text)
        if not chars:
            chars = [" "]

        # Count NON-SPACE characters for timing
        visible_indices = [i for i, ch in enumerate(chars) if ch != " "]
        n_visible = len(visible_indices)
        if n_visible == 0:
            n_visible = 1
            visible_indices = [0]

        char_dur = dur / n_visible  # time between each visible char appearing

        # ── Layout: wrap chars into lines ──
        # Build list of (char, width, is_visible)
        char_info = [(ch, char_width_px(ch), ch != " ") for ch in chars]

        # Group into lines
        lines = []  # list of (start_char_idx, end_char_idx, line_width, visible_count_in_line)
        line_start = 0
        line_w = 0
        vis_in_line = 0
        for i, (ch, cw, vis) in enumerate(char_info):
            gap = CHAR_GAP if line_w > 0 else 0
            if line_w + gap + cw > MAX_LINE_W and line_w > 0:
                lines.append((line_start, i, line_w, vis_in_line))
                line_start = i
                line_w = cw
                vis_in_line = 1 if vis else 0
            else:
                if line_w > 0:
                    line_w += gap
                line_w += cw
                if vis:
                    vis_in_line += 1
        if line_start < len(chars):
            lines.append((line_start, len(chars), line_w, vis_in_line))

        n_lines = len(lines)
        # y positions
        line_base_ys = [SUBTITLE_Y - (n_lines - 1 - li) * LINE_SPACING
                        for li in range(n_lines)]

        # ── Per-character typewriter events ──
        # Track which visible char index we're at globally
        global_vis_idx = 0

        for li, (l_start, l_end, l_width, l_vis) in enumerate(lines):
            # Center this line horizontally
            start_x = CENTER_X - l_width // 2
            x_cursor = start_x
            line_y = line_base_ys[li]

            for ci in range(l_start, l_end):
                ch = chars[ci]
                cw = char_info[ci][1]
                is_vis = char_info[ci][2]

                char_x = x_cursor + cw // 2  # center of character

                if is_vis:
                    # This character appears at its typing time
                    char_appear_time = beat_start + global_vis_idx * char_dur
                    global_vis_idx += 1

                    # Typewriter "tak" — quick scale pop 130%→100% over 60ms
                    # Using \t() for scale snap
                    tag = (
                        f"{{\\an2\\pos({char_x},{line_y})"
                        f"\\fscx{POP_SCALE}\\fscy{POP_SCALE}"
                        f"\\t(0,{POP_MS},\\fscx100\\fscy100)}}"
                        f"{ch}"
                    )

                    dialogues.append(
                        f"Dialogue: {li * 200 + ci},{format_ass_time(char_appear_time)},"
                        f"{format_ass_time(beat_end)},"
                        f"Type,,0,0,0,,{tag}"
                    )
                # Spaces and non-visible chars are NOT rendered as events
                # (they just eat horizontal space in layout)

                x_cursor += cw + CHAR_GAP

        # ── Caption line (small, top area, faint) ──
        if caption and use_timing:
            dialogues.append(
                f"Dialogue: 9999,{format_ass_time(beat_start)},{format_ass_time(beat_end)},"
                f"Caption,,0,0,0,,{caption}"
            )

        total_chars_all_beats += global_vis_idx

        if not use_timing:
            fallback_cursor = fallback_cursor + dur + pause

    # ── Write .ass ──────────────────────────────────────────
    ass_lines = ass_header + dialogues + [""]
    ass_path = outdir / f"{ep}.ass"
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8")

    last_end = beat_timing[beats[-1]["id"]]["end"] if use_timing and beats and beats[-1]["id"] in beat_timing else (fallback_cursor if not use_timing else 0)
    print(f"  ⌨️  ASS Typewriter: {len(beats)} beats · {total_chars_all_beats} chars · total={last_end:.1f}s · {ass_path}")
    print(f"  💬 Per-char typing: {POP_SCALE}%→100% snap over {POP_MS}ms")
    print(f"  🖊️  {FONT_SIZE}pt white · black outline · no background box")
    timing_src = "xfade _timing.json" if use_timing else "ffprobe fallback"
    print(f"  ⏱️  timing source: {timing_src}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

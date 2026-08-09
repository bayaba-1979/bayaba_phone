#!/usr/bin/env python3
"""P0.6 Directing Map — 콘텐츠 기반 연출 자동 결정 (V12)

VO 길이, caption, role, beat 위치를 분석해 per-beat 연출 결정:
- zoom type (in/out/pan_right/pan_left/pan_up/pan_down)
- color_tag (gold/warm/teal/cool/cinematic/natural)
- scroll_sel 검증

Rule-based — LLM 불필요. V12: pan_up/down 추가, zoom 분배 다양화 (pan_right ≤40%).

Usage:
  python3 scripts/_direct_map.py <OUTDIR>
  python3 scripts/_direct_map.py /root/work/out/pd_tistory_v3
"""
from __future__ import annotations

import json, sys
from pathlib import Path


# ── Valid color tags (matching _render_video.py COLOR_GRADES) ──
VALID_COLORS = {"warm", "cinematic", "natural", "cool", "gold", "teal"}

# ── Valid zoom types ──
VALID_ZOOMS = {"in", "out", "pan_right", "pan_left", "pan_up", "pan_down"}

# ── Color cycle across all beats (6 types, 순환) ──
COLOR_CYCLE = ["gold", "warm", "teal", "cool", "cinematic", "natural"]


def choose_zoom(beat: dict, page_idx: int, page_total: int) -> dict:
    """Choose zoom type based on role, position, and content length."""
    role = beat.get("role", "build")
    vo_text = beat.get("vo", "")
    vo_len = len(vo_text)

    # Position in sequence (0.0 ~ 1.0)
    progress = page_idx / max(page_total - 1, 1)

    if role == "hook":
        return {"type": "out", "pan": "none"}

    if role == "resolve":
        return {"type": "out", "pan": "none"}

    if role == "climax":
        # Climax: pan_right for long text, in for short
        if vo_len > 60:
            return {"type": "pan_right", "pan": "none"}
        else:
            return {"type": "in", "pan": "none"}

    # ── Build beats: distribute zoom types evenly ──
    # Use position to cycle through 4 zoom types: in, pan_right, pan_up, pan_down
    zoom_cycle = ["in", "pan_right", "pan_up", "in", "pan_down", "pan_right"]
    zoom_type = zoom_cycle[page_idx % len(zoom_cycle)]

    # Override: very short text → out (establishing shot)
    if vo_len <= 25:
        zoom_type = "out"
    # Override: very long text → prefers pan for readability
    elif vo_len > 100 and zoom_type == "in":
        zoom_type = "pan_right"

    return {"type": zoom_type, "pan": "none"}


def choose_color(beat: dict, page_idx: int, page_total: int) -> str:
    """Choose color grade — cycle through all 6 types."""
    role = beat.get("role", "build")

    # Hook and climax always get gold (attention-grabbing)
    if role in ("hook", "climax"):
        return "gold"

    # Resolve gets warm or cinematic
    if role == "resolve":
        return "warm" if page_idx % 2 == 0 else "cinematic"

    # Build beats: cycle through all colors, skip gold (reserved for hook/climax)
    build_colors = ["warm", "teal", "cool", "cinematic", "natural", "warm"]
    return build_colors[page_idx % len(build_colors)]


def choose_pause(beat: dict) -> float:
    """Choose breathing pause between beats."""
    role = beat.get("role", "build")
    vo_len = len(beat.get("vo", ""))

    # Longer text → slightly longer pause for reading
    base_map = {"hook": 0.8, "build": 0.4, "climax": 0.6, "resolve": 1.0}
    base = base_map.get(role, 0.5)

    if vo_len > 80:
        base += 0.1
    if vo_len > 120:
        base += 0.1

    return round(base, 1)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 _direct_map.py <OUTDIR>")
        return 1

    outdir = Path(sys.argv[1])
    bible_path = outdir / "shot_bible.json"

    if not bible_path.exists():
        print(f"❌ No shot_bible.json in {outdir}")
        return 1

    bible = json.loads(bible_path.read_text(encoding="utf-8"))
    beats = bible.get("beats") or []

    if not beats:
        print("⚠️  No beats in shot_bible — skip directing")
        return 0

    total = len(beats)
    print(f"🎬 P0.6 Directing Map (V12) — {total} beats")

    page_beats = [b for b in beats if b.get("kind") != "bridge"]
    page_total = len(page_beats)

    for i, beat in enumerate(beats):
        if beat.get("kind") == "bridge":
            continue

        # Position among page beats
        page_idx_list = [j for j, b in enumerate(page_beats) if b["id"] == beat["id"]]
        page_idx = page_idx_list[0] if page_idx_list else i

        # ── Zoom ──
        beat["zoom"] = choose_zoom(beat, page_idx, page_total)

        # ── Color ──
        beat["color_tag"] = choose_color(beat, page_idx, page_total)

        # ── Pause ──
        beat["pause"] = choose_pause(beat)

        # ── Emotion ──
        role = beat.get("role", "build")
        emotion_map = {
            "hook": "hook", "build": "trust",
            "climax": "rise", "resolve": "handoff",
        }
        beat["emotion"] = emotion_map.get(role, "trust")

        # ── Validate scroll_sel ──
        sel = beat.get("scroll_sel") or beat.get("section_selector")
        if sel:
            if sel in ("body", "html", "*", ""):
                beat["scroll_sel"] = None
            else:
                beat["scroll_sel"] = sel

        zoom_str = beat["zoom"]["type"]
        vo_len = len(beat.get("vo", ""))
        print(f"  {beat['id']:25s} | {beat['role']:7s} | zoom={zoom_str:10s} | color={beat['color_tag']:10s} | pause={beat['pause']:.1f}s | vo_len={vo_len}")

    # ── Zoom diversity report ──
    zoom_counts = {}
    for b in beats:
        if b.get("kind") == "bridge":
            continue
        zt = b["zoom"]["type"]
        zoom_counts[zt] = zoom_counts.get(zt, 0) + 1
    total_page = sum(zoom_counts.values())
    pan_right_pct = round(zoom_counts.get("pan_right", 0) / max(total_page, 1) * 100)
    unique_zooms = len(zoom_counts)
    print(f"  📊 Zoom diversity: {zoom_counts} | pan_right={pan_right_pct}% | unique={unique_zooms} types")

    # ── Save ──
    bible["version"] = "v12"
    bible_path.write_text(
        json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  ✅ Directing complete — ready for P1 capture")
    print(f"  Next: bash scripts/produce_pd.sh {bible['id']} {bible.get('url','')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

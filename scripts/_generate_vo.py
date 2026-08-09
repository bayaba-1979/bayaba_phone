#!/usr/bin/env python3
"""P0.5 VO Generator — 콘텐츠 기반 한국어 내레이션 생성 (V12)

P0가 추출한 context 문장을 그대로 VO로 사용합니다.
템플릿 매꾸기 대신, 페이지에서 실제로 읽은 문장이 VO가 됩니다.
Grok API가 사용 가능하면 LLM이 다듬고, 없으면 context를 그대로 씁니다.

Usage:
  python3 scripts/_generate_vo.py <OUTDIR>
  python3 scripts/_generate_vo.py /root/work/out/pd_tistory_v3
"""
from __future__ import annotations

import json, os, sys, subprocess
from pathlib import Path


def grok_generate(prompt: str) -> str | None:
    """Try Grok CLI for VO polishing. Returns None if unavailable."""
    try:
        r = subprocess.run(
            ["grok", "한국어로 2-3문장의 짧은 내레이션을 만들어줘. 원문을 살리되 자연스럽게. " + prompt],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            text = r.stdout.strip()
            if text and len(text) > 5:
                return text[:200]
    except Exception:
        pass
    return None


def content_vo(beat: dict, bible: dict) -> str:
    """Use P0-extracted context directly as VO — no template filling.

    Strategy:
    1. P0 stored raw context text in beat["vo"]
    2. Extract first 1-2 meaningful sentences from that context
    3. If context is empty, fall back to caption
    """
    context = beat.get("vo", "")  # P0 put raw context here
    caption = beat.get("caption", "")
    title = bible.get("title", "")

    # Remove heading repetition from context
    if context.startswith(caption):
        context = context[len(caption):].strip()
        if context.startswith("."):
            context = context[1:].strip()

    # Extract meaningful sentences (8자 이상, 마침표/느낌표/물음표 기준)
    raw_sentences = context.replace("\n", " ").replace("  ", " ")
    sentences = []
    for s in raw_sentences.split("."):
        s = s.strip()
        if len(s) > 8:
            sentences.append(s)

    if len(sentences) >= 2:
        return f"{sentences[0]}. {sentences[1]}."
    elif len(sentences) == 1:
        return sentences[0] + "."
    else:
        # No useful context — use caption as the VO itself
        return caption


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 _generate_vo.py <OUTDIR>")
        return 1

    outdir = Path(sys.argv[1])
    bible_path = outdir / "shot_bible.json"

    if not bible_path.exists():
        print(f"❌ No shot_bible.json in {outdir}")
        return 1

    bible = json.loads(bible_path.read_text(encoding="utf-8"))
    beats = bible.get("beats") or []

    if not beats:
        print("⚠️  No beats in shot_bible — skip VO generation")
        return 0

    print(f"🎙  P0.5 VO Generator (content-based) — {len(beats)} beats")

    # ── Try Grok for first beat only (hook — sets the tone) ──
    use_llm = False
    for i, beat in enumerate(beats):
        caption = beat.get("caption", "")
        context_raw = beat.get("vo", "")

        if i == 0:
            # Try LLM for the hook beat (sets overall tone)
            prompt = f"제목: {bible.get('title','')}. 첫 섹션: {caption}. 내용: {context_raw[:200]}"
            llm_vo = grok_generate(prompt)
            if llm_vo:
                use_llm = True
                beat["vo"] = llm_vo
                continue

        # Content-based VO (no template filling)
        beat["vo"] = content_vo(beat, bible)

    if use_llm:
        print("  🤖 Hook VO polished via Grok LLM")
    else:
        print("  📝 VO from extracted content (Grok unavailable)")

    # ── Save ──
    bible["version"] = "v12"
    bible_path.write_text(
        json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for b in beats:
        vo_text = b.get("vo", "")
        print(f"  {b['id']:25s} | {vo_text[:80]}{'...' if len(vo_text)>80 else ''}")

    print(f"  ✅ shot_bible updated — Next: python3 scripts/_direct_map.py {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

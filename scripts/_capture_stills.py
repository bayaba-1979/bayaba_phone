#!/usr/bin/env python3
"""P1 Still Capture — Playwright page screenshots per beat (V13)

Reads shot_bible.json scroll_sel per beat, scrolls to each section, captures viewport.
Fallback chain: CSS :has-text() → Playwright text locator → progressive scroll.

Usage:
  python3 scripts/_capture_stills.py <OUTDIR> [--url URL]
  python3 scripts/_capture_stills.py /root/work/out/pd_tistory_v3
"""
from __future__ import annotations

import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> int:
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("OUTDIR", "/root/work/out/intro"))
    url = ""
    for i, a in enumerate(sys.argv):
        if a == "--url" and i + 1 < len(sys.argv):
            url = sys.argv[i + 1]
    if not url:
        url = os.environ.get("URL", "https://bayaba-1979.github.io/bayaba_phone/")

    stills = outdir / "stills"
    stills.mkdir(exist_ok=True)

    bible_path = outdir / "shot_bible.json"
    if not bible_path.exists():
        print(f"❌ No shot_bible.json in {outdir}")
        return 1

    bible = json.loads(bible_path.read_text(encoding="utf-8"))
    beats = bible.get("beats") or []

    # Build beat list: filter page kind, track sequential index
    page_beats = [(i, b) for i, b in enumerate(beats) if b.get("kind") != "bridge"]
    if not page_beats:
        page_beats = [(i, b) for i, b in enumerate(beats)]

    print(f"[P1] Playwright scroll captures — {len(page_beats)} beats")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=5)
        page.goto(url, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)

        # Remove custom cursors / floating UI
        page.evaluate("""() => {
          document.querySelectorAll('.cursor,.cursor-dot,.floating-btn,.scroll-top').forEach(e => e.remove());
        }""")

        # Hide fixed nav bars by scrolling past them
        try:
            nav_h = page.evaluate("""() => {
              const nav = document.querySelector('nav,header,.navbar,.tistory-header,.top-bar');
              return nav ? nav.offsetHeight : 0;
            }""")
            if nav_h and nav_h > 40:
                page.evaluate(f"window.scrollBy(0, {nav_h + 10})")
                page.wait_for_timeout(400)
        except Exception:
            pass

        selector_success = 0
        text_fallback_success = 0
        progressive_fallback = 0

        for beat_idx, (orig_idx, beat) in enumerate(page_beats):
            bid = beat["id"]
            sel = beat.get("scroll_sel") or beat.get("section_selector")
            sel_used = None

            # ── Fallback chain ──
            if sel:
                # Step 1: Try CSS :has-text() selector
                try:
                    el = page.locator(sel).first
                    el.scroll_into_view_if_needed(timeout=8000)
                    page.wait_for_timeout(600)
                    page.evaluate("window.scrollBy(0, -60)")
                    page.wait_for_timeout(300)
                    sel_used = sel
                    selector_success += 1
                except Exception:
                    # Step 2: Try Playwright text locator
                    heading_text = beat.get("caption", "")
                    if heading_text and len(heading_text) > 2:
                        try:
                            short = heading_text[:30]
                            page.get_by_text(short, exact=False).first.scroll_into_view_if_needed(timeout=5000)
                            page.wait_for_timeout(400)
                            page.evaluate("window.scrollBy(0, -60)")
                            page.wait_for_timeout(300)
                            sel_used = f'text("{short[:20]}")'
                            text_fallback_success += 1
                        except Exception:
                            sel_used = None
                    else:
                        sel_used = None

                    if not sel_used:
                        print(f"  ! scroll {bid}: CSS timeout → text locator also failed → fallback progressive")

            if not sel_used:
                # Step 3: Progressive scroll
                scroll_y = beat_idx * int(page.evaluate("window.innerHeight")) * 0.75
                page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
                page.wait_for_timeout(700)
                sel_used = "scroll-y"
                progressive_fallback += 1

            dest = stills / f"{bid}.png"
            page.screenshot(path=str(dest), full_page=False)
            # Legacy name for _render_video.py compat
            page.screenshot(path=str(outdir / f"{bid}.png"), full_page=False)
            print(f"  📸 {bid} ({dest.stat().st_size} bytes)  sel={sel_used}")

        browser.close()

    total = len(page_beats)
    print(f"  ✅ P1 done — CSS:{selector_success}/{total} text:{text_fallback_success}/{total} scroll-y:{progressive_fallback}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

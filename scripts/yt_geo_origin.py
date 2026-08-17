#!/usr/bin/env python3
"""
S21 Phone — YouTube GEO 원조 라인 주입 (헌법 제17조)

YouTube는 남의 루트라 llms.txt를 못 박음 → 두 채널의
  (1) 채널 About(설명)과 (2) 모든 영상 설명에 "원조 · Origin — github.com/helena751107"
  라인을 멱등 추가해, LLM 크롤러가 "본체 = GitHub Helena Park"로 재구성하게.

멱등: 설명에 'github.com/helena751107' 이 이미 있으면 건너뜀.

사용법:
  python3 scripts/yt_geo_origin.py --inspect      # 읽기 전용 — 뭐가 바뀔지 미리 보기
  python3 scripts/yt_geo_origin.py --apply        # 실제 반영 (About + 영상 설명)
  python3 scripts/yt_geo_origin.py --apply --channel main --about-only

의존성: 시스템 python3(googleapiclient). 인증은 yt_upload.get_credentials 재사용.
"""

import sys, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yt_upload as Y

ORIGIN_URL = "https://github.com/helena751107"
ORIGIN_LINE = "원조 · Origin — https://github.com/helena751107"


def _append_origin(desc: str) -> tuple[str, bool]:
    """원조 라인을 이미 포함하면 그대로, 아니면 푸터로 추가. (새설명, 변경여부)"""
    if ORIGIN_URL in (desc or ""):
        return desc, False
    base = (desc or "").rstrip()
    new = f"{base}\n\n{ORIGIN_LINE}\n" if base else f"{ORIGIN_LINE}\n"
    return new, True


def inspect_channel(yt, key):
    ch = Y.CHANNELS[key]
    cid = ch["id"]
    info = yt.channels().list(part="snippet,brandingSettings,contentDetails", id=cid).execute()
    it = info["items"][0]
    cur = it.get("brandingSettings", {}).get("channel", {}).get("description", "")
    new_desc, changed = _append_origin(cur)
    upl = it["contentDetails"]["relatedPlaylists"]["uploads"]
    videos = yt.playlistItems().list(part="snippet", playlistId=upl, maxResults=50).execute().get("items", [])

    vids = []
    for v in videos:
        vid = v["snippet"]["resourceId"]["videoId"]
        detail = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
        nd, vc = _append_origin(detail.get("description", ""))
        vids.append({"id": vid, "title": detail["title"], "cur_has": ORIGIN_URL in (detail.get("description", "") or ""), "changed": vc, "new": nd})

    return {"key": key, "handle": ch["handle"], "title": it["snippet"]["title"],
            "about_cur": cur, "about_changed": changed, "about_new": new_desc,
            "videos": vids}


def apply_channel(yt, key, about_only=False):
    ch = Y.CHANNELS[key]
    cid = ch["id"]
    r = inspect_channel(yt, key)
    print(f"\n=== [{r['key']}] {r['title']} ({r['handle']}) ===")

    # (1) 채널 About
    if r["about_changed"]:
        info = yt.channels().list(part="brandingSettings", id=cid).execute()["items"][0]
        bs = info.get("brandingSettings", {})
        chan = bs.get("channel", {})
        body = {"id": cid, "brandingSettings": {"channel": {
            "description": r["about_new"],
            "keywords": chan.get("keywords", "") if "keywords" in chan else r["about_new"].replace("\n", " "),
        }}}
        yt.channels().update(part="brandingSettings", body=body).execute()
        print(f"  ✅ 채널 About 원조 라인 추가 ({len(r['about_cur'])} → {len(r['about_new'])}자)")
    else:
        print(f"  ⏭ 채널 About — 이미 원조 라인 포함 (건너뜀)")

    # (2) 영상 설명
    if about_only:
        print("  (--about-only: 영상 설명 생략)")
        return
    done = skip = 0
    for v in r["videos"]:
        if not v["changed"]:
            skip += 1
            continue
        detail = yt.videos().list(part="snippet", id=v["id"]).execute()["items"][0]["snippet"]
        body = {"id": v["id"], "snippet": {
            "title": detail["title"],
            "description": v["new"],
            "categoryId": detail.get("categoryId", "22"),
        }}
        if "tags" in detail:
            body["snippet"]["tags"] = detail["tags"]
        yt.videos().update(part="snippet", body=body).execute()
        done += 1
        print(f"  ✅ 영상 설명 원조 라인 추가: {v['title'][:40]}")
    print(f"  영상 {len(r['videos'])}개 중 {done}개 추가 / {skip}개 이미 포함(건너뜀)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inspect", action="store_true", help="읽기 전용 미리보기")
    p.add_argument("--apply", action="store_true", help="실제 반영")
    p.add_argument("--channel", default="all", help="main|phone|all")
    p.add_argument("--about-only", action="store_true", help="채널 About만, 영상 설명 제외")
    a = p.parse_args()

    Y._load_secrets()
    yt = Y.get_authenticated_service()
    keys = ["main", "phone"] if a.channel == "all" else [a.channel]

    if a.inspect:
        for k in keys:
            r = inspect_channel(yt, k)
            print(f"\n=== [{r['key']}] {r['title']} ({r['handle']}) — 미리보기 ===")
            print(f"  About: {'변경' if r['about_changed'] else '이미 포함'} ({len(r['about_cur'])}자)")
            if r["about_changed"]:
                print(f"    + {ORIGIN_LINE}")
            n_add = sum(1 for v in r["videos"] if v["changed"])
            n_have = sum(1 for v in r["videos"] if not v["changed"])
            print(f"  영상 {len(r['videos'])}개: {n_add}개 추가 예정 / {n_have}개 이미 포함")
            for v in r["videos"]:
                mark = "＋추가" if v["changed"] else "·보유"
                print(f"    {mark} {v['title'][:42]}")
        return

    if a.apply:
        for k in keys:
            apply_channel(yt, k, a.about_only)
        return

    p.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
S21 Phone — YouTube 통제 CLI v2 (업로드 + 플레이리스트 + 브랜딩 + 애널리틱스)
OAuth(Device Code) → Data API v3 · Analytics v2

사용법:
  # 업로드 (제목/설명/태그/카테고리/공개설정/채널)
  python3 scripts/yt_upload.py --title "제목" --file video.mp4 --privacy public
  # 채널 조회
  python3 scripts/yt_upload.py --channel phone --list
  python3 scripts/yt_upload.py --stats
  # 플레이리스트
  python3 scripts/yt_upload.py --playlist-list
  python3 scripts/yt_upload.py --playlist-create "새 재생목록"
  python3 scripts/yt_upload.py --playlist-add <플리ID> <영상ID>
  # 브랜딩 / 통계
  python3 scripts/yt_upload.py --branding "새 채널 설명"
  python3 scripts/yt_upload.py --analytics 28

환경: proot Ubuntu
의존성: google-auth-oauthlib, google-api-python-client
전제: OAuth 토큰이 .secrets.env(YOUTUBE_*) 또는 yt_tokens.json에 존재할 것
"""

import os, sys, json, subprocess, argparse, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SECRETS = BASE / ".secrets.env"
TOKEN_FILE = BASE / "configs" / "yt_tokens.json"

# ── 설정 ────────────────────────────────────────────────────────────────────

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
ACCESS_TOKEN = os.environ.get("YOUTUBE_ACCESS_TOKEN", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

# 생태계 SSOT(configs/ecosystem.json)에서 2채널·프로젝트 로드.
# (구 6채널 하드코딩 → 2채널 정합: main=돌봄, phone=도구)
from load_ecosystem import channels as _ecosystem_channels, youtube as _ecosystem_youtube

PROJECT_ID = _ecosystem_youtube().get("project_id", "")

CHANNELS = {
    c["key"]: {"id": c.get("id", ""), "handle": c["handle"], "topic": c.get("topic", "")}
    for c in _ecosystem_channels()
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# ── 인증 ────────────────────────────────────────────────────────────────────

def get_credentials():
    """OAuth 자격증명 로드(1순위 .secrets.env, 2순위 yt_tokens.json) + 만료 시 리프레시"""
    try:
        from google.auth.transport.requests import Request
    except ImportError:
        print("❌ 필요 패키지 설치:")
        print("   pip3 install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    from google.oauth2.credentials import Credentials
    credentials = None

    # 토큰 로드 — 1순위 .secrets.env(YOUTUBE_ACCESS/REFRESH), 2순위 yt_tokens.json
    if ACCESS_TOKEN or REFRESH_TOKEN:
        credentials = Credentials(
            token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES,
        )
    elif TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            credentials = Credentials(
                token=data.get('access_token'),
                refresh_token=data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=SCOPES,
            )

    # 만료 시 리프레시
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_tokens(credentials)
        print("🔄 토큰 리프레시 완료")

    if not credentials or not credentials.valid:
        print("❌ 유효한 토큰 없음. OAuth 재인증 필요:")
        print("   bash scripts/yt_oauth_setup.sh")
        sys.exit(1)

    return credentials


def get_authenticated_service():
    """YouTube Data API v3 클라이언트 반환"""
    from googleapiclient.discovery import build
    return build('youtube', 'v3', credentials=get_credentials(), cache_discovery=False)

def _save_tokens(credentials):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)

# ── 업로드 ───────────────────────────────────────────────────────────────────

def upload_video(youtube, file_path, title, description, tags, category_id, privacy_status):
    """YouTube Data API v3 — videos.insert (1,600유닛)"""

    from googleapiclient.http import MediaFileUpload

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or [],
            'categoryId': category_id or '22',  # 22=People & Blogs
        },
        'status': {
            'privacyStatus': privacy_status or 'private',  # private/unlisted/public
            'selfDeclaredMadeForKids': False,
        },
    }

    media = MediaFileUpload(file_path, mimetype='video/*', resumable=True)

    print(f"📤 업로드 시작: {title}")
    print(f"   파일: {file_path}")
    print(f"   상태: {privacy_status or 'private'}")

    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None

    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   진행률: {int(status.progress() * 100)}%")

    video_id = response['id']
    url = f"https://youtu.be/{video_id}"
    print(f"✅ 업로드 완료: {url}")
    return video_id, url

# ── 채널 정보 ────────────────────────────────────────────────────────────────

def list_channel_videos(youtube, channel_id, max_results=10):
    """채널 동영상 목록 (playlistItems.list = 1유닛) ⚡️"""
    # 채널의 uploads 플레이리스트 ID 조회
    resp = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    uploads_id = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    # playlistItems.list 사용 (search.list 대비 100배 저렴)
    results = youtube.playlistItems().list(
        part='snippet',
        playlistId=uploads_id,
        maxResults=min(max_results, 50),
    ).execute()

    print(f"\n📺 채널 동영상 ({len(results.get('items', []))}개):")
    for item in results.get('items', []):
        title = item['snippet']['title']
        video_id = item['snippet']['resourceId']['videoId']
        published = item['snippet']['publishedAt'][:10]
        print(f"   [{published}] {title}")
        print(f"   https://youtu.be/{video_id}")

    return results

def get_channel_stats(youtube, channel_id):
    """채널 통계 (Analytics API 없이 기본 통계)"""
    resp = youtube.channels().list(
        part='statistics,snippet',
        id=channel_id,
    ).execute()

    if not resp.get('items'):
        print("❌ 채널 없음")
        return None

    item = resp['items'][0]
    stats = item['statistics']
    print(f"\n📊 채널 통계:")
    print(f"   이름: {item['snippet']['title']}")
    print(f"   구독자: {stats.get('subscriberCount', '?')}")
    print(f"   동영상: {stats.get('videoCount', '?')}")
    print(f"   조회수: {stats.get('viewCount', '?')}")
    return resp

# ── 플레이리스트 ─────────────────────────────────────────────────────────────

def list_playlists(youtube, channel_id):
    """채널 플레이리스트 목록 (playlists.list = 1유닛)"""
    results = youtube.playlists().list(
        part='snippet',
        channelId=channel_id,
        maxResults=50,
    ).execute()
    items = results.get('items', [])
    print(f"\n📚 플레이리스트 ({len(items)}개):")
    for it in items:
        print(f"   {it['id']}  {it['snippet']['title']}")
    return results


def create_playlist(youtube, title, privacy='public'):
    """플레이리스트 생성"""
    resp = youtube.playlists().insert(
        part='snippet,status',
        body={
            'snippet': {'title': title, 'description': title},
            'status': {'privacyStatus': privacy},
        },
    ).execute()
    print(f"✅ 플레이리스트 생성: {resp['id']}  {resp['snippet']['title']}")
    return resp


def add_playlist_item(youtube, playlist_id, video_id):
    """플레이리스트에 영상 추가"""
    resp = youtube.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {'kind': 'youtube#video', 'videoId': video_id},
            },
        },
    ).execute()
    print(f"✅ 추가: https://youtu.be/{video_id} → {playlist_id}")
    return resp


# ── 브랜딩 ───────────────────────────────────────────────────────────────────

def update_branding(youtube, channel_id, description):
    """채널 설명/키워드 갱신 (brandingSettings.update)"""
    keywords = description.replace('\n', ' ')
    resp = youtube.channels().update(
        part='brandingSettings',
        body={
            'id': channel_id,
            'brandingSettings': {
                'channel': {'description': description, 'keywords': keywords},
            },
        },
    ).execute()
    print("✅ 채널 브랜딩 갱신 완료")
    return resp


# ── 애널리틱스 ───────────────────────────────────────────────────────────────

def get_analytics(channel_id, days=28):
    """YouTube Analytics v2 — 조회/시청시간/구독자 통계"""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    creds = get_credentials()
    yta = build('youtubeAnalytics', 'v2', credentials=creds, cache_discovery=False)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    try:
        r = yta.reports().query(
            ids=f'channel=={channel_id}',
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics='views,estimatedMinutesWatched,subscribersGained',
            dimensions='day',
        ).execute()
    except HttpError as e:
        if getattr(getattr(e, 'resp', None), 'status', None) == 403:
            print("❌ 애널리틱스 스코프(yt-analytics.readonly) 없음.")
            print("   Device Code Flow는 이 스코프를 지원하지 않음 → 브라우저 OAuth 필요.")
            print("   → google-api/yt_oauth_channel.cjs 로 브라우저 인증 후 재시도")
            sys.exit(1)
        raise
    rows = r.get('rows', [])
    print(f"\n📊 최근 {days}일 통계:")
    if not rows:
        print("   (데이터 없음)")
        return r
    tot_v = tot_m = tot_s = 0
    for row in rows:
        v, m, s = int(row[1]), int(row[2]), int(row[3])
        tot_v += v; tot_m += m; tot_s += s
        print(f"   {row[0]}  조회 {v:>7}  시청분 {m:>7}  구독+{s}")
    print("   ───────────────────────────────")
    print(f"   합계     조회 {tot_v:>7}  시청분 {tot_m:>7}  구독+{tot_s}")
    return r

# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='S21 YouTube 통제 CLI v2')
    parser.add_argument('--title', help='영상 제목')
    parser.add_argument('--description', help='영상 설명', default='')
    parser.add_argument('--file', help='영상 파일 경로')
    parser.add_argument('--tags', nargs='*', help='태그 (공백 구분)')
    parser.add_argument('--category', default='22', help='카테고리 ID (기본: 22=People)')
    parser.add_argument('--privacy', default='private', choices=['private', 'unlisted', 'public'])
    parser.add_argument('--channel', default='main', help=f'채널 키: {", ".join(CHANNELS.keys())}')
    parser.add_argument('--list', action='store_true', help='채널 동영상 목록')
    parser.add_argument('--stats', action='store_true', help='채널 통계')
    parser.add_argument('--playlist-list', action='store_true', help='플레이리스트 목록')
    parser.add_argument('--playlist-create', metavar='TITLE', help='플레이리스트 생성')
    parser.add_argument('--playlist-add', nargs=2, metavar=('PLAYLIST_ID', 'VIDEO_ID'), help='플레이리스트에 영상 추가')
    parser.add_argument('--branding', nargs='+', metavar='DESC', help='채널 설명/키워드 갱신 (따옴표로 묶기)')
    parser.add_argument('--analytics', nargs='?', const=28, type=int, metavar='DAYS', help='N일 애널리틱스 (기본 28일)')
    args = parser.parse_args()

    # OAuth 토큰 로드
    _load_secrets()

    youtube = get_authenticated_service()
    channel = CHANNELS.get(args.channel, CHANNELS['main'])

    if not channel['id']:
        print(f"❌ 채널 '{args.channel}'의 ID가 설정되지 않았습니다.")
        print("   configs/yt_tokens.json 또는 yt_upload.py의 CHANNELS 딕셔너리 확인")
        sys.exit(1)

    if args.list:
        list_channel_videos(youtube, channel['id'])
        return

    if args.stats:
        get_channel_stats(youtube, channel['id'])
        return

    if args.playlist_list:
        list_playlists(youtube, channel['id'])
        return

    if args.playlist_create:
        create_playlist(youtube, args.playlist_create)
        return

    if args.playlist_add:
        add_playlist_item(youtube, args.playlist_add[0], args.playlist_add[1])
        return

    if args.branding:
        update_branding(youtube, channel['id'], ' '.join(args.branding))
        return

    if args.analytics is not None:
        get_analytics(channel['id'], args.analytics)
        return

    if not args.title or not args.file:
        parser.error("--title과 --file은 필수입니다")
        return

    if not os.path.exists(args.file):
        print(f"❌ 파일 없음: {args.file}")
        sys.exit(1)

    desc = args.description or f"{channel['topic']}\n\n🤖 @S21Phone_Bot 자동 업로드"

    video_id, url = upload_video(
        youtube, args.file, args.title, desc,
        args.tags, args.category, args.privacy,
    )

    # tg.sh로 보고
    tg = BASE / "tg.sh"
    if tg.exists():
        msg = f"📺 YouTube 업로드 완료\n제목: {args.title}\n{url}"
        subprocess.run(["bash", str(tg), msg], check=False)

def _load_secrets():
    """환경변수에서 OAuth 정보 로드 (.secrets.env = SSOT, YOUTUBE_* 키)"""
    global CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN

    if SECRETS.exists():
        with open(SECRETS) as f:
            for line in f:
                line = line.strip()
                if line.startswith('YOUTUBE_CLIENT_ID='):
                    CLIENT_ID = line.split('=', 1)[1].strip('"\'')
                elif line.startswith('YOUTUBE_CLIENT_SECRET='):
                    CLIENT_SECRET = line.split('=', 1)[1].strip('"\'')
                elif line.startswith('YOUTUBE_ACCESS_TOKEN='):
                    ACCESS_TOKEN = line.split('=', 1)[1].strip('"\'')
                elif line.startswith('YOUTUBE_REFRESH_TOKEN='):
                    REFRESH_TOKEN = line.split('=', 1)[1].strip('"\'')

    CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID', CLIENT_ID)
    CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', CLIENT_SECRET)
    ACCESS_TOKEN = os.environ.get('YOUTUBE_ACCESS_TOKEN', ACCESS_TOKEN)
    REFRESH_TOKEN = os.environ.get('YOUTUBE_REFRESH_TOKEN', REFRESH_TOKEN)

if __name__ == '__main__':
    main()

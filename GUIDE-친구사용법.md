# 📱 친구 사용법 — 숏폼 영상 + TTS 성우 더빙

> 이 폰(Galaxy Z Fold4)에 이미 다 깔려 있는 기능을 쓰는 법만 정리했다.
> 어려운 건 없다. 아래 명령어 한 줄만 복사해서 붙여넣으면 된다.

---

## 1. 숏폼 영상 만들기 (웹페이지 → 자동 영상)

**뭐 하는 거냐:** URL 하나 주면, 그 웹페이지를 자동으로 읽고 → 섹션별로 화면 캡처 → 한국어 내레이션 → 자막 → 배경음악까지 붙여서 숏폼 영상을 만들어준다.

**한 줄로 쓰기:**
```bash
bash scripts/produce_pd.sh [영상이름] [페이지주소]
```

**예시 (족발 랜딩을 영상으로):**
```bash
bash scripts/produce_pd.sh jokbal_intro "https://bayaba-1979.github.io/bayaba-jokbal/"
```

**예시 (치킨 랜딩):**
```bash
bash scripts/produce_pd.sh chicken_intro "https://bayaba-1979.github.io/bayaba-chicken/"
```

**배경음악 넣고 싶으면:**
```bash
bash scripts/produce_pd.sh jokbal_intro "https://bayaba-1979.github.io/bayaba-jokbal/" --bgm "https://youtu.be/영상ID" --bgm-volume 0.015
```

**결과물 위치:** `out/영상이름/` 폴더에 mp4가 생긴다.

**뭐가 자동으로 되는지:**
- P0: 페이지 읽어서 내용 파악
- P1: 섹션별로 화면 스크롤 캡처
- P2: 한국어 여성 목소리(유진)로 내레이션
- P3: 갤러리에서 브릿지 영상 자동 감지
- P4: FFmpeg로 Ken Burns 효과(줌/팬) 렌더링
- P4b: CNN 스타일 자막
- P6: 텔레그램으로 전송

---

## 2. TTS — 텍스트를 음성으로 읽기

**뭐 하는 거냐:** 텍스트를 한국어 음성으로 읽어주는 것. 무료(Edge TTS).

**한 줄로 쓰기:**
```bash
python3 scripts/tts-speak.py "읽어줄 텍스트"
```

**예시:**
```bash
python3 scripts/tts-speak.py "오늘의 족발은 진짜 맛있었어요"
```

**파일로 읽기:**
```bash
python3 scripts/tts-speak.py --file 글.txt
```

**목소리 바꾸기 (남성/여성):**
```bash
# 남성 목소리 (인준)
python3 scripts/tts-speak.py --voice ko-KR-InJoonNeural "안녕하세요"

# 여성 목소리 (선히)
python3 scripts/tts-speak.py --voice ko-KR-SunHiNeural "안녕하세요"

# 여성 목소리 (유진 — 차분한 내레이션)
python3 scripts/tts-speak.py --voice ko-KR-YuJinNeural "안녕하세요"
```

**가능한 목소리 전부 보기:**
```bash
python3 scripts/tts-speak.py --list-voices
```

---

## 3. 성우 더빙 (텍스트 → 성우 음성 → 영상에 입히기)

> ⚠️ 이건 구버전(RVC)이고, 지금은 `synth_voice_pro.sh`가 정답이다. 새 더빙은 아래 경로를 쓴다.

**뭐 하는 거냐:** 텍스트를 성우 목소리로 변환해서 더빙. Edge TTS(여성 베이스) → RVC 음색 변환 → mp3.

**참고 문서:**
- `_notebook/81-helena-rvc-dubbing-standard_Claude.md` (표준)
- `_notebook/82-helena-rvc-baseline-lords-prayer_Grok.md` (잠금)

---

## 4. 자주 쓰는 것만 정리

| 하고 싶은 것 | 명령어 |
|---|---|
| 숏폼 영상 만들기 | `bash scripts/produce_pd.sh 이름 "URL"` |
| 텍스트 음성으로 읽기 | `python3 scripts/tts-speak.py "텍스트"` |
| 목소리 바꾸기 | `python3 scripts/tts-speak.py --voice ko-KR-유진Neural "텍스트"` |
| 가능한 목소리 보기 | `python3 scripts/tts-speak.py --list-voices` |

---

## ⚠️ 주의사항

1. **숏폼 생성은 시간이 좀 걸린다** — FFmpeg 렌더링이 CPU로 돌아서 몇 분 걸릴 수 있다. 멈춘 것 같아도 기다린다.
2. **배경음악은 YouTube 링크** — `--bgm` 뒤에 YouTube URL을 넣는다.
3. **TTS는 인터넷 필요** — Edge TTS가 온라인 API라서 와이파이/데이터 연결 필요.
4. **결과물은 `out/` 폴더** — 영상 다 만들면 `out/영상이름/`에 mp4가 있다.

---

*친구 사용법 가이드 · Claude Code · 2026-08-19*

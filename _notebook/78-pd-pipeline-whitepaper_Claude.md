# 🎬 PD Pipeline 기술 백서 — URL 하나로 숏폼 자동 제작

**버전:** V12 · **일자:** 2026-08-09 · **위치:** S21 Phone (aarch64 proot Ubuntu)  
**저자:** Boss + Claude Code · **라이선스:** MIT · **TG:** @S21Phone_Bot

---

## 1. 개요 — 이게 뭐냐

웹페이지 URL 하나만 주면 AI가 **페이지를 읽고, 이해하고, 스크린샷 찍고, 한국어 내레이션을 입혀서 9:16 숏폼 영상(1080×1920, ~2분)을 자동 제작**하는 파이프라인이다.

일반 숏폼 도구(템플릿 끼워맞추기)와 근본적으로 다르다:  
→ **실제 페이지를 Playwright로 열어서 섹션별로 다른 위치를 스크롤·캡처**하고,  
→ **추출된 콘텐츠 문장을 그대로 내레이션(VO)으로 사용**하며,  
→ **FFmpeg Ken Burns(줌/팬) + CNN Breaking News 자막 + BGM 더킹**까지 전자동.

**차별점:** "같은 그림 6번 우려먹기"가 아니라, 진짜 다른 8장면을 캡처하고 진짜 페이지 내용을 읽는다.

---

## 2. 아키텍처 — P0 → P6 파이프라인

```
P0 (_parse_url.py)          Playwright로 URL 열기 → DOM 파싱 → 섹션 추출
  │                           제목·heading·본문 추출, :has-text() CSS selector 생성
  ▼
P0.5 (_generate_vo.py)      추출된 콘텐츠 문장 → 한국어 내레이션(VO) 초안
  │                           템플릿 NO. 실제 페이지 문장을 그대로 VO로 사용
  ▼
P0.6 (_direct_map.py)       VO 길이·역할 기반 zoom/color_tag/pause 자동 결정
  │                           zoom: out, in, pan_right, pan_left, pan_up, pan_down (6종)
  │                           color: gold, warm, teal, cool, cinematic, natural (6종)
  ▼
P1 (_capture_stills.py)     Playwright로 beat마다 scroll_sel 요소로 스크롤 → viewport 캡처
  │                           Fallback chain: :has-text() → text locator → progressive scroll
  ▼
P2 (voice_engine.py)        Edge TTS (YuJinNeural) / Sherpa-ONNX → MP3 음성 합성
  │                           우선순위: local → edge (Grok TTS 폐기 — API 403, SuperGrok 미포함)
  ▼
P3 (_bridge_pickup.sh)      Android 갤러리에서 bridge 영상(오프닝/클로징) 자동 감지
  │
  ▼
P4 (_render_video.py)       755줄 FFmpeg 제작 엔진:
  │                           • Ken Burns zoom/pan (코사인 easing, 6방향)
  │                           • LUFS -16 오디오 정규화 (loudnorm 필터)
  │                           • 6종 color grade (FFmpeg eq+colorbalance)
  │                           • xfade multi-transition (fade/wipe/slide/dissolve)
  │                           • channel stinger (0.5s 로고 비프)
  │                           • pattern interrupt (0.4s 화이트 플래시)
  │                           • BGM sidechain ducking (sidechaincompress)
  │                           • 하단 pseudo-gradient 오버레이 (2-layer drawbox)
  │                           • end card (loop_match color + fade-in 텍스트)
  │                           • 소스 해상도 5x DPI (390×844@5x → 1950×4220, width 1.81x 출력)
  │
  ▼
P4b (_make_ass.py)          CNN Breaking News 스타일 ASS 자막
  │                           72pt Bold · per-word scale pop (200%→100%) · 레드 배경바
  ▼
P4c (ffmpeg)                ASS 자막을 VO body에 burn-in
  │
  ▼
P5 (_pd_assemble.py)        Bridge(오프닝/클로징) 연결 + full-timeline BGM mix + QA gate
  │                           LUFS -16 VO 정규화 → sidechain ducking → slide diversity check
  ▼
P5b (_make_srt.py)          YouTube caption용 SRT 생성
  │
  ▼
P6 (ffmpeg + curl)          720p TG 인코딩 → @S21Phone_Bot 전송
```

---

## 3. 저장소 구조 — 어디에 뭐가 있나

### 주 저장소: `helena751107/helena_phone` (`/root/work/`)
```
scripts/
  produce_pd.sh          ← 메인 진입점 (CLI)
  _parse_url.py          ← P0: URL → shot_bible
  _generate_vo.py        ← P0.5: 콘텐츠 → VO
  _direct_map.py         ← P0.6: VO → 연출 결정
  _capture_stills.py     ← P1: scroll_sel → 스크린샷
  _render_video.py       ← P4: FFmpeg Ken Burns 렌더러
  _make_ass.py           ← P4b: CNN 자막
  _make_srt.py           ← P5b: YouTube SRT
  _pd_assemble.py        ← P5: 최종 조립 + BGM
  _bridge_pickup.sh      ← P3: Android bridge 감지
  _qa_video_slides.py    ← QA: 슬라이드 다양성 검증

configs/
  video_pd_pipeline_v2.json  ← 표준 설정 (1080×1920, BGM vol=0.025, role_pacing)

out/
  pd_intro/              ← helena_phone 소개 (기본, 6 beats)
  pd_magic/              ← 마술·매직 숏폼 시험
  pd_tistory_v3/         ← 티스토리 활용법 (V11 최신, 8 beats)
  ...                    ← pd_<domain>_<path> 자동 생성

helena-piano/bgm/output/ ← Boss 자작 BGM (Satie Gymnopédie, Clair de Lune 등)
```

### MCP 저장소: `helena751107/helena-programming` (`/root/work/helena-programming/`)
```
mcp/
  pd_pipeline_mcp.py     ← PD Pipeline MCP 서버 v1.0 (STDIO + HTTP)
  mcp_server.py          ← Helena Studio MCP 서버 (기존)
  pyproject.toml

tools/voice/
  voice_engine.py        ← TTS 멀티프로바이더 (local Sherpa-ONNX / Grok / Edge)

director/
  run_director.py        ← 헬레나 스튜디오 연출 엔진
  voice_engine.py
  subtitles.py           ← 자막 렌더링
```

---

## 4. 실행 방법 — 에이전트가 이걸 어떻게 부르나

### 방법 A: CLI (직접 호출)
```bash
# URL 하나로 끝까지
bash /root/work/scripts/produce_pd.sh <ep_id> <url>

# 예시
bash /root/work/scripts/produce_pd.sh pd_my_blog "https://mynote11605.tistory.com/m/2"

# 환경변수 오버라이드
BGM_VOLUME=0.03 VOICE=ko-KR-SunHiNeural bash scripts/produce_pd.sh ...
```

### 방법 B: MCP (Claude Code가 호출)
```json
// ~/.claude.json → mcpServers
"pd-pipeline": {
  "command": "python3",
  "args": ["/root/work/helena-programming/mcp/pd_pipeline_mcp.py"]
}
```

**MCP 6도구:**
| 도구 | 인자 | 설명 |
|------|------|------|
| `pd_parse_url` | `url`, `ep?`, `generate_vo?` | URL → shot_bible 자동 생성 (P0~P0.6) |
| `pd_produce` | `ep_id`, `url?`, `bgm_volume?`, `voice?`, `force?` | 풀파이프라인 실행 (P1~P6) |
| `pd_status` | `job_id?` | 작업 상태 확인 + 로그 tail |
| `pd_list` | — | 완료된 에피소드 목록 |
| `pd_stop` | `job_id?` | 실행 중인 작업 중지 |
| `pd_output` | `job_id?` | 출력 파일 경로·크기 확인 |

**에이전트 워크플로 예시:**
```
1. pd_parse_url(url="https://타겟페이지주소")
   → shot_bible.json 자동 생성 (섹션·VO·연출 포함)
2. (선택) shot_bible 수동 편집
3. pd_produce(ep_id="pd_타겟")
   → 백그라운드 실행, job_id 반환
4. pd_status(job_id) → 완료 확인
5. pd_output(job_id) → TG 링크 확인
```

### 방법 C: HTTP (curl로 직접)
```bash
# pd-pipeline MCP 서버 HTTP 모드 기동
python3 /root/work/helena-programming/mcp/pd_pipeline_mcp.py --http --port 8765 &

# URL 파싱
curl -s -X POST http://localhost:8765/ \
  -d '{"method":"tools/call","params":{"name":"pd_parse_url","arguments":{"url":"https://..."}}}'

# 파이프라인 실행
curl -s -X POST http://localhost:8765/ \
  -d '{"method":"tools/call","params":{"name":"pd_produce","arguments":{"ep_id":"pd_xxx"}}}'
```

---

## 5. 핵심 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| 브라우저 자동화 | **Playwright** (Chromium) | 페이지 로드·DOM 파싱·스크롤 캡처, viewport=390×844@5x (1950×4220 소스) |
| 음성 합성 | **Edge TTS** (YuJinNeural), Sherpa-ONNX (Kokoro) | local 우선, Grok TTS 폐기 (API 403) |
| 영상 인코딩 | **FFmpeg** (libx264 High@L4.0, 30fps) | Ken Burns zoompan · xfade · sidechaincompress · loudnorm · drawtext · vignette |
| 자막 | **ASS** (Advanced SubStation Alpha) | CNN Breaking News 스타일, per-word `\t()` scale pop |
| BGM | FluidSynth → 헬레나 피아노 렌더 | Satie Gymnopédie №1, Clair de Lune 등 (Boss 자작, Content ID 회피) |
| MCP 프로토콜 | **JSON-RPC 2.0** (STDIO/HTTP) | Python 3 stdlib only, 외부 의존성 0 |
| Job 관리 | `/tmp/pd_mcp_jobs.json` | PID·상태·로그 경로 저장 |
| 메신저 | **Telegram Bot API** (`sendVideo`) | 720p H.264 + 128k AAC, `supports_streaming=true` |

---

## 6. 환경 — 어디서 돌아가나

```
하드웨어:   Galaxy S21 (SM-G991N) · Exynos 2100 · Mali-G78 GPU · NPU
OS:         Android 14 → Termux → proot Ubuntu (aarch64 glibc)
런타임:     Python 3.14 · FFmpeg 6.x · Playwright 1.x
저장소:     /root/work/ (helena_phone) + /root/work/helena-programming/

⚠️ CPU-only. Ken Burns 인코딩 beat당 1~3분, 총 15~20분.
   GPU(Mali-G78)/NPU(Exynos) 가속은 proot glibc↔Android bionic ABI 충돌로 구조적 한계.
   Termux bionic 브릿지 실험 보류 → S25 업그레이드 시 재검토 (2026-08-09).
```

---

## 7. 설정 파일 — `configs/video_pd_pipeline_v2.json`

```json
{
  "standard": "video_pd_pipeline_v2",
  "bgm_volume": 0.025,
  "resolution": "1080:1920",
  "version": "v12",
  "channel_stinger": {"enabled": true, "duration": 0.5, "text": "S21 Phone"},
  "pattern_interrupt": {"enabled": true, "duration": 0.4},
  "loop_match": {"enabled": true, "open_color": "gold", "close_color": "gold"},
  "role_pacing": {"hook": 2.5, "build": 3.5, "climax": 4.5, "resolve": 3.0}
}
```

---

## 8. shot_bible.json 구조 — 파이프라인의 두뇌

```json
{
  "id": "pd_mynote11605_m-2",
  "url": "https://mynote11605.tistory.com/m/2",
  "title": "티스토리 활용법",
  "standard": "video_pd_pipeline_v2",
  "bgm_volume": 0.025,
  "resolution": "1080:1920",
  "version": "v12",
  "page_bg_color": "rgb(244, 229, 201)",
  "beats": [
    {
      "id": "01_티스토리활용법",
      "kind": "page",
      "role": "hook",
      "emotion": "hook",
      "zoom": {"type": "out", "pan": "none"},
      "color_tag": "gold",
      "pause": 0.8,
      "caption": "티스토리 활용법",
      "vo": "티스토리 활용법",                    // ← P0.5가 채움 (실제 콘텐츠 문장)
      "scroll_sel": "h3:has-text(\"티스토리 활용법\")"  // ← P0가 생성 (:has-text() 포맷)
    }
    // ... 6~10 beats
  ],
  "bridges": [
    {"id": "b_open",  "file": "bridge/b_open.mp4"},
    {"id": "b_close", "file": "bridge/b_close.mp4"}
  ]
}
```

---

## 9. 현재 상태 (V12, 2026-08-09)

### 9.1 안정성 지표 (파이프라인이 깨지지 않는가)

| 지표 | 값 | 검증 방법 |
|------|-----|-----------|
| CSS selector 성공률 | **100%** (8/8) | `:has-text()` 포맷, zero fallback |
| Fallback chain | CSS → Playwright text locator → progressive scroll | 3단계, 단계별 성공 카운트 리포트 |
| VO 품질 | 콘텐츠 추출 문장 직접 사용 | 템플릿 NO, context 기반 1~2문장 자동 추출 |
| Zoom 다양성 | 6종 (out/in/pan_right/pan_left/pan_up/pan_down) | `_direct_map.py` diversity report |
| Color grade | 6종 (gold/warm/teal/cool/cinematic/natural) | position-based cycle |
| 에러 처리 | `|| echo "⚠️ [step] failed" >&2` | 모든 단계 실패 원인 stderr 기록 |
| Code modularity | P1 heredoc → `_capture_stills.py` 독립 파일 | Bash 인라인 Python 제거 |
| QA gate | Slide diversity ≥ 10 unique frames, black frames = 0 | `_qa_video_slides.py` + P5 gate |
| 전체 소요시간 | ~20분 | S21 CPU-only, 8-beat 123초 영상 기준 |

### 9.2 전문가 품질 지표 (결과물이 프로급인가)

| 지표 | V12 값 | 기준 | 적용 위치 |
|------|--------|------|-----------|
| **Easing** | ✅ Cosine ease-in-out | `zoom_expr = base + amount*(1-cos(PI*on/nframes))/2` | `_render_video.py` P4 |
| **소스 해상도 헤드룸** | **1.81x width** (1950×4220 소스, 1080×1920 출력) | Ken Burns zoom 최대 1.8x까지 무손실 (통상 1.2x 사용, 여유 충분) | `_capture_stills.py` P1, `_parse_url.py` P0 |
| **오디오 LUFS** | ✅ **-16 LUFS** (TP=-1.5, LRA=11) | YouTube 권장 -14~-16 LUFS, `ffmpeg loudnorm` 필터 | `_render_video.py` P4, `_pd_assemble.py` P5 |
| **Frame rate** | **30fps** | 숏폼 표준 30fps, FFmpeg `fps=30` + `-r 30` | `_render_video.py`, `_pd_assemble.py` normalize_av |
| **BGM 저작권** | ✅ Boss 자작 피아노 (Content ID 회피) | FluidSynth → Satie Gymnopédie, Clair de Lune | `helena-piano/bgm/output/` |
| **자막 가독성** | 72pt Bold + per-word scale pop + 레드 배경바 | CNN Breaking News 스타일, `\t()` 애니메이션 | `_make_ass.py` P4b |
| **Transition** | 4종 xfade cycle (fade/wipeleft/slideright/dissolve) | 0.4s duration, `_timing.json` 보정 | `_render_video.py` P4 |

> **V11→V12 변경사항:** ① device_scale_factor 3x→5x (소스 해상도 260% 헤드룸) ② `volume=1.0` → `loudnorm=I=-16:TP=-1.5:LRA=11` (P4+P5, 4개소) ③ Grok TTS 공식 폐기 ④ GPU/NPU 구조적 한계로 보류

---

## 10. 한계와 다음 과제

| 과제 | 상태 |
|------|------|
| LLM 기반 VO (Grok) | **폐기 확정.** Grok TTS API 403, SuperGrok 구독에 TTS 미포함. 콘텐츠 추출 VO로 대체 완료 |
| GPU/NPU 가속 | **구조적 한계로 보류.** proot glibc↔Android bionic ABI 충돌. S25 업그레이드 시 재검토 |
| `_timing.json` 생성 | xfade 정확 타이밍 데이터 누락 시 SRT 부정확 → 버그 수정 필요 |
| 다중 페이지 지원 | 현재 단일 URL만. "시리즈" 모드 (목차 → 각 글) 구상. GitHub Pages linked-repos 아이디어 연결 |
| YouTube Shorts 직접 업로드 | OAuth 완료. API 연동 대기 중 |
| 에이전트 자동 발행 | Boss가 URL만 던지면 → 파싱 → 제작 → TG 검수 → 발행 승인 |
| NPU 추론 (장기) | Exynos NPU NCP v24 커널 확인, Termux에서 DRM/NPU sysfs 접근 가능. ParksyTTS 471초→실시간 목표 |

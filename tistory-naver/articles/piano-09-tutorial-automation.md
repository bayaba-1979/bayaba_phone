---
kicker: 스튜디오 · Tutorial 4/4
title: push하면 음악이 된다 — 자동화와 S21 로컬 렌더링
dek: MIDI를 넣고 push하기만 하면 GitHub Actions가 렌더링해 준다. 클라우드 없이, 폰 한 대로도 같은 일이 가능하다.
hero: piano
byline: 웹진 디렉터 · 스튜디오
date: 2026년 8월
category: 스튜디오
tags: GitHub Actions, 자동화, S21, fluidsynth, 렌더링, 튜토리얼
---

지금까지의 과정 — MIDI 소싱, SoundFont 선택, 렌더링, 인간화, 마스터링 — 을 매번 손으로 하면 지루하다. 그래서 스튜디오는 이 전 과정을 자동화했다. 두 갈래가 있다. 클라우드(GitHub Actions)와 로컬(갤럭시 S21)이다.

## 갈래 1 — GitHub Actions: push가 곧 렌더링

`bgm/midi/`에 `.mid` 파일을 넣고 push하기만 하면 된다. `.github/workflows/render-bgm.yml`이 다음 순서로 돌아간다.

1. Salamander 샘플 캐시 (또는 Fluid R3 폴백)
2. `fluidsynth`로 MIDI → WAV
3. `ffmpeg`로 WAV → MP3 (320kbps + loudnorm 마스터링)
4. 렌더링된 MP3를 `[skip ci]` 커밋으로 push

```text
MIDI push → Actions 트리거 → fluidsynth 렌더 → MP3 커밋 → CDN 배포
```

결과물은 곧바로 CDN 주소로 접근할 수 있다.

```text
https://bayaba-1979.github.io/helena-piano/bgm/output/곡제목.mp3
```

이 웹진의 모든 음원이 이 주소를 통해 스트리밍된다. 감상 기사에 박힌 `<audio>` 플레이어도 이 CDN을 가리킨다.

## 갈래 2 — S21 로컬: 폰 안에서 직접

클라우드 없이, 갤럭시 S21(proot Ubuntu) 안에서 직접 렌더링할 수도 있다. SoundFont를 한 번 받아두면 이후엔 폰 하나로 충분하다.

```bash
apt install fluidsynth ffmpeg fluid-soundfont-gm

# Salamander SoundFont 다운로드 (1회, 244MB)
wget -O bgm/salamander.sf2 \
  https://github.com/sfzinstruments/SalamanderGrandPiano/releases/download/v3/salamander-grand-piano-v3.sf2

bash bgm/scripts/render.sh
```

S21은 aarch64 CPU다. GPU(Mali-G78)와 NPU(Exynos 2100, 26 TOPS)를 지녔지만, 현재 렌더링은 CPU의 fluidsynth로 충분하다. MIDI → WAV는 실시간보다 빠르게 돈다. 다만 이 웹진의 진짜 병목은 렌더링이 아니라 "편집"이다. 기계가 연주하는 데는 1초면 족하지만, 어떤 곡을 고르고 어떻게 다듬을지는 사람의 판단이 필요하다.

## 파이프라인 전체 지도

```text
MIDI 소싱 ──▶ SoundFont 선택 ──▶ fluidsynth 렌더 ──▶ 인간화 ──▶ 마스터링
   │                                                                │
   ├─ Mutopia/IMSLP/bitMidi                                        ├─ GitHub Actions (클라우드)
   ├─ YouTube → basic-pitch                                        └─ S21 proot (로컬)
   └─ AI 작곡 (composer_v2)
                                    │
                                    ▼
                          bgm/output/*.mp3 → CDN → 웹진/유튜브
```

이것이 `helena-piano/bgm/` 스튜디오의 전모다. "연주자 없는 피아노 음악"을 폰 하나로 만드는 설계도.

:::figure debussy|드뷔시 — 이 파이프라인이 가장 먼저 연주한 작곡가 중 하나

---

이 시리즈는 `helena-piano` 레포의 `bgm/` 스튜디오 파이프라인을 해설하는 4부작입니다. 코드와 워크플로는 GitHub에 전부 공개되어 있습니다.

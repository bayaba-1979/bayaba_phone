---
kicker: 스튜디오 · Tutorial 2/4
title: SoundFont를 고르는 일 — 어떤 "피아노"를 고를 것인가
dek: 같은 MIDI도 어떤 SoundFont를 쓰느냐에 따라 전혀 다른 곡이 된다. Salamander부터 Fluid R3, SGM-HQ, TOH까지 실제 비교를 담았다.
hero: piano
byline: 웹진 디렉터 · 스튜디오
date: 2026년 8월
category: 스튜디오
tags: SoundFont, Salamander, FluidR3, SGM-HQ, fluidsynth, 튜토리얼
---

SoundFont(SF2)는 악기 음색의 표본집이다. 건반 하나하나를 여러 강약으로 녹음해 둔 샘플 묶음이라고 보면 된다. MIDI라는 지시서가 "이 음을 이 강약으로"라고 말하면, SoundFont가 그에 맞는 실제 녹음 샘플을 꺼내 재생한다. 그래서 같은 MIDI도 SoundFont에 따라 결과물이 완전히 달라진다.

## 피아노 특화 vs 범용

SoundFont는 크게 두 부류로 나뉜다. 피아노 하나에 특화된 것과, 오케스트라 전체를 담은 범용(GM)이다.

| SoundFont | 음색 | 크기 | 라이선스 | 용도 |
|-----------|------|------|----------|------|
| **Salamander Grand Piano** | Yamaha C5 | 244MB | MIT | 피아노 특화 (기본값) |
| **Fluid R3 GM** | Steinway 계열 | 141MB | MIT | 128악기 범용 |
| **SGM-HQ** | 범용 고품질 | 250MB+ | 무료 | 오케스트라 |
| **TOH / TOH4** | 범용 | 100MB+ | 무료 | 경량 대안 |
| **TimGM6mb** | GM 기본 | 6MB | GPL | 저사양 폴백 |

피아노 웹진의 기본값은 **Salamander Grand Piano**다. Yamaha C5 그랜드 피아노를 건반별 16단계 벨로서티로 녹음한 244MB 샘플로, 범용 SoundFont가 흉내 낼 수 없는 강약의 뉘앙스를 준다.

## 백조의 호수로 해 본 A/B 비교

SoundFont 선택이 얼마나 중요한지는 실제 비교가 가장 잘 보여 준다. parksy-audio 레포의 `pre-season/`에는 차이콥스키 《백조의 호수》를 다섯 SoundFont로 각각 렌더링한 결과가 남아 있다.

```text
swan_lake_fluidsynth.mp4  — FluidSynth 기본 (평면적)
swan_lake_fluidr3.mp4     — Fluid R3 (Steinway 색채)
swan_lake_sgm_hq.mp4      — SGM-HQ (오케스트라 질감)
swan_lake_toh.mp4         — TOH (경량)
swan_lake_toh4.mp4        — TOH4 (경량 개선)
```

같은 악보를 넣어도 음색의 "깊이"가 다르다. 피아노 독주라면 Salamander, 오케스트라 편성이라면 SGM-HQ가 낫다. 이 선택이 곧 "어떤 콘서트홀에서 연주할 것인가"를 정하는 일이다.

## 렌더링 한 줄

SoundFont를 정했으면 렌더링은 사실상 두 줄이다. `-ni`는 오디오 드라이버 없이 파일로 직접 렌더링하라는 뜻, `-g`는 게인, `-r`은 샘플레이트다.

```bash
fluidsynth -ni -g 1.5 -r 44100 salamander.sf2 input.mid -F output.wav
ffmpeg -i output.wav -b:a 192k output.mp3
```

이걸 감싼 스크립트가 `bgm/scripts/render.sh`다.

```bash
bash bgm/scripts/render.sh                    # 전체 렌더링
bash bgm/scripts/render.sh moonlight.mid       # 특정 파일만
bash bgm/scripts/render.sh --soundfont fluidr3 # Fluid R3 로 전환
```

:::figure satie|사티 — 피아노 독주에서는 Salamander 같은 특화 SoundFont가 유리하다

다음 튜토리얼에서는 렌더링 결과를 더 "사람답게" 만드는 인간화와 마스터링을 다룬다.

---

이 시리즈는 `helena-piano` 레포의 `bgm/` 스튜디오 파이프라인을 해설하는 4부작입니다.

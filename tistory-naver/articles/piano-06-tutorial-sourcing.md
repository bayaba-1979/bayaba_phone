---
kicker: 스튜디오 · Tutorial 1/4
title: MIDI를 어디서 구하는가 — 악보·음원·AI의 세 갈래
dek: 렌더링 파이프라인의 첫 단계는 음원이 아니라 악보(MIDI)다. 공개 도메인 악보부터 유튜브 음원, AI 작곡까지 세 가지 소싱 경로를 정리한다.
hero: piano
byline: 웹진 디렉터 · 스튜디오
date: 2026년 8월
category: 스튜디오
tags: MIDI, 소싱, IMSLP, Mutopia, bitMidi, 튜토리얼, 클래식
---

피아노 음악을 렌더링하려면 먼저 "지시서"가 필요하다. MIDI 파일이 바로 그것이다. 몇 킬로바이트에 불과한 이 지시서가 어떤 음을 어떤 강약으로 칠지 전부 담고 있다. 이 튜토리얼은 `helena-piano/bgm/` 스튜디오가 실제로 쓰는 세 가지 MIDI 소싱 경로를 다룬다.

## 갈래 1 — 공개 도메인 악보에서 직접

가장 깨끗한 경로는 공개 도메인 악보를 MIDI로 옮기는 것이다. 작곡가 사후 70년이 지난 클래식 악보는 저작권이 없다. 이 악보를 전자화한 MIDI도 마찬가지로 자유롭게 쓸 수 있다.

| 소스 | 곡 수 | 특징 |
|------|-------|------|
| **Mutopia Project** | 2,000+ | LilyPond로 조판, MIDI 동봉 |
| **IMSLP** | 전체 클래식 | PDF 악보, 일부 MIDI |
| **Kunst der Fuge** | 1,000+ | MIDI 특화 |

```bash
# Mutopia/IMSLP에서 받은 MIDI를 bgm/midi/ 에 저장
cp clair_de_lune.mid bgm/midi/
```

## 갈래 2 — 유튜브 음원에서 채보

공개 도메인 MIDI가 없는 곡은 유튜브 음원에서 역으로 MIDI를 뽑아낸다. `yt_fetch.py`가 음원을 받고, Demucs가 악기별로 분리한 뒤, basic-pitch가 피아노 음을 MIDI로 채보한다.

```bash
# YouTube URL → 음원 → 소스 분리 → MIDI 추출
python3 steal.py "https://youtube.com/watch?v=..."
python3 steal.py --search "brahms intermezzo op 118 no 2"
python3 steal.py "URL" --start 0:30 --end 3:00   # 구간 지정
```

필요 의존성은 `yt-dlp`, `demucs`, `basic-pitch`, `mido`. Demucs는 첫 실행 시 모델을 받아 오는데 약 300MB다.

## 갈래 3 — AI 작곡

아예 새로운 곡을 만들 수도 있다. parksy-audio 파이프라인의 `composer_v2.py`가 감정과 스타일을 지정해 새 곡을 생성한다.

```bash
python3 composer_v2.py --emotion "peaceful" --style "chopin" --output new_piece.mid
```

## 소싱 전 라이선스 체크리스트

MIDI를 추가하기 전에 꼭 확인할 것:

- [ ] 작곡가 사망 후 70년 경과? (공개 도메인)
- [ ] MIDI 파일 자체가 CC0/CC-BY?
- [ ] 편곡에 새 저작권이 없는가? (원곡 그대로)
- [ ] SoundFont 라이선스 확인 (Salamander = MIT)

이 체크리스트를 통과한 MIDI만 `bgm/midi/`에 들어간다. 현재 스튜디오에는 Bach, Chopin, Debussy, Satie, Fauré, Delibes의 공개 도메인 곡 11개가 쌓여 있다.

:::figure bach|바흐 — 공개 도메인 악보의 대표 주자

다음 튜토리얼에서는 이 MIDI를 실제 음색으로 바꾸는 SoundFont 선택과 렌더링을 다룬다.

---

이 시리즈는 `helena-piano` 레포의 `bgm/` 스튜디오 파이프라인을 해설하는 4부작입니다.

# 손바닥 위의 그랜드 피아노 — S21에서 MIDI를 렌더링하는 방법

> MIDI 한 장을 넣으면 Salamander Grand Piano의 음색으로 렌더링된 MP3가 나온다. 갤럭시 S21과 GitHub Actions가 연주하는 작은 콘서트홀의 설계도.

레퍼토리 저장소 `helena-piano`의 `bgm/` 스튜디오는 하나의 질문에서 출발했다. **"연주자 없는 피아노 음악을, 폰 하나로 만들 수 있을까?"** 답은 MIDI라는 악보와, 실제로 녹음된 Yamaha C5의 샘플 244MB를 합쳐 재생하는 **샘플 기반 합성(sample-based synthesis)** 이다. 이 글은 그 파이프라인을 처음부터 끝까지 — MIDI 소싱에서 SoundFont 선택, 렌더링 명령, 자동화, 그리고 폰 안에서의 로컬 렌더링까지 — 펼쳐 보인다.

## 왜 폰으로 피아노를 렌더링하는가

유튜브 배경음악은 보통 저작권이 걸려 있다. 하지만 **클래식 악보(작곡가 사후 70년 이상 경과)는 공개 도메인**이고, MIDI 파일은 그 악보를 전자적으로 옮긴 것에 불과하다. 여기에 MIT 라이선스의 SoundFont를 얹으면, 저작권 걱정 없이 채널 어디서든 쓸 수 있는 음악이 만들어진다.

핵심은 "연주"가 아니라 "합성"이라는 점이다. 우리는 사람 피아니스트를 녹음하는 게 아니라, Yamaha C5 그랜드 피아노의 건반 하나하나를 16단계 강약으로 녹음해 둔 샘플을 **MIDI라는 지시서에 따라 조합**한다. 지시서(MIDI)는 몇 킬로바이트에 불과하고, 음색(SoundFont)은 한 번 받아두면 계속 쓸 수 있다.

## 파이프라인: MIDI에서 MP3까지

```
MIDI 파일 (Public Domain 악보)
        │
        ▼
fluidsynth + Salamander Grand Piano SF2   ← Yamaha C5, 16단계 벨로서티
        │  (MIDI → WAV, 44.1kHz)
        ▼
ffmpeg  (WAV → MP3)
        │
        ▼
bgm/output/*.mp3  →  GitHub Pages CDN
```

스튜디오의 디렉토리는 단순하게 세 층이다.

```
bgm/
├── midi/     ← 공개 도메인 MIDI 저장소 (11곡)
├── output/   ← 렌더링된 MP3 (GitHub Actions 자동 생성)
└── scripts/  ← render.sh · extract_midi.py · humanizer.py 등
```

## 사운드폰트: 어떤 "피아노"를 고를 것인가

SoundFont(SF2)는 악기 음색의 표본집이다. 같은 MIDI를 넣어도 어떤 SoundFont를 쓰느냐에 따라 결과물이 완전히 달라진다.

| SoundFont | 음색 | 크기 | 라이선스 | 특징 |
|-----------|------|------|----------|------|
| **Salamander Grand Piano** | Yamaha C5 | 244MB | MIT | 16단계 벨로서티, 실제 녹음 |
| Fluid R3 GM | Steinway 샘플 | 141MB | MIT | 128악기, 범용 |
| TimGM6mb | GM 기본 | 6MB | GPL | 경량, 저품질 |

피아노 웹진의 기본값은 당연히 **Salamander Grand Piano**다. 일반 GM SoundFont와 달리 피아노 하나에 특화되어, 벨로서티 16단계가 강약의 뉘앙스를 살려 준다. 범용 악기가 필요할 때만 Fluid R3로 전환한다.

## MIDI 소싱: 악보와 음원, 그리고 AI

MIDI는 세 갈래로 수집한다.

1. **공개 도메인 악보 → MIDI** — IMSLP, Mutopia Project, Kunst der Fuge에서 클래식 악보를 MIDI로.
2. **유튜브 음원 → MIDI 추출** — `yt_fetch.py`로 음원을 받고, Demucs로 소스 분리 후 basic-pitch가 MIDI를 추출한다.
3. **AI 작곡** — parksy-audio 파이프라인으로 감정·스타일을 지정해 새 곡을 생성한다.

```bash
python3 steal.py "https://youtube.com/watch?v=..."   # 음원 → MIDI 추출
python3 composer_v2.py --emotion "peaceful" --style "chopin" --output new_piece.mid
```

## 렌더링: 한 줄이면 충분하다

가장 단순한 형태는 단 두 줄이다. `-ni`는 오디오 드라이버 없이 파일로 직접 렌더링하라는 뜻이고, `-g 1.5`는 게인, `-r 44100`은 샘플레이트다.

```bash
fluidsynth -ni -g 1.5 -r 44100 salamander.sf2 input.mid -F output.wav
ffmpeg -i output.wav -b:a 192k output.mp3
```

이걸 자동화한 스크립트가 `bgm/scripts/render.sh`다. 전체를 돌릴 수도, 한 곡만 지정할 수도 있다.

```bash
bash bgm/scripts/render.sh                    # 전체 렌더링
bash bgm/scripts/render.sh moonlight.mid       # 특정 파일만
bash bgm/scripts/render.sh --soundfont fluidr3 # Fluid R3 로 전환
```

## GitHub Actions: push하면 음악이 된다

`bgm/midi/`에 `.mid` 파일을 넣고 push하기만 하면, GitHub Actions가 알아서 렌더링해 `bgm/output/`에 MP3를 커밋해 준다.

1. Salamander 샘플을 캐시(또는 Fluid R3 폴백)
2. `fluidsynth`로 MIDI → WAV
3. `ffmpeg`로 WAV → MP3 (320kbps + loudnorm 마스터링)
4. 렌더링된 MP3를 `[skip ci]` 커밋으로 push

결과물은 곧바로 CDN 주소로 접근 가능하다.

```
https://bayaba-1979.github.io/helena-piano/bgm/output/곡제목.mp3
```

## S21 로컬 렌더링: 폰 안에서 직접

클라우드 없이, 갤럭시 S21(proot Ubuntu) 안에서 직접 렌더링할 수도 있다. SoundFont를 한 번 받아두면 이후엔 폰 하나로 충분하다.

```bash
apt install fluidsynth ffmpeg fluid-soundfont-gm

# Salamander SoundFont 다운로드 (1회)
wget -O bgm/salamander.sf2 \
  https://github.com/sfzinstruments/SalamanderGrandPiano/releases/download/v3/salamander-grand-piano-v3.sf2

bash bgm/scripts/render.sh
```

"연주"가 컴퓨팅이 되는 순간, 콘서트홀은 손바닥 위로 들어온다.

## 지금 렌더링된 레퍼토리

현재 스튜디오에는 공개 도메인 클래식 11곡의 MIDI가 있고, 그중 렌더링이 완료된 곡은 다음과 같다.

- **Bach** — Prelude in C major, BWV 846
- **Debussy** — Clair de Lune
- **Satie** — Gymnopédie No.1 · No.3
- **Delibes** — Lakmé, Flower Duet (여러 버전)
- (Chopin Nocturne Op.9 No.2 · Fauré Pavane은 MIDI 수집 완료, 렌더 대기)

실제로 들어보려면 아래 주소에서 스트리밍할 수 있다.

```
https://bayaba-1979.github.io/helena-piano/bgm/output/bach_prelude_bwv846.mp3
https://bayaba-1979.github.io/helena-piano/bgm/output/clair_de_lune.mp3
https://bayaba-1979.github.io/helena-piano/bgm/output/satie_gymnopedie1.mp3
```

## 이 음악은 어디로 흘러가는가

렌더링된 BGM은 유튜브 채널의 배경음악으로 공급된다. 찬양·클래식 채널(@남성훈-f7i)과 연주·브이로그 채널(@남성훈-f7i)에서 같은 곡이 서로 다른 문맥으로 울린다. 다음 기사에서는 레인 2로 넘어가, 이 곡들을 **"감상"의 관점에서** 다시 읽어 볼 예정이다.

---

이 문서는 `helena-piano` 레포의 `bgm/README.md`를 기사로 재구성한 것입니다. 코드와 파이프라인은 GitHub에 전부 공개되어 있습니다.

# 헬레나 성우 더빙 — 기술명세서 (자연스러운 연출 버전)

**날짜:** 2026-08-13
**작성:** Claude Code (출판부·시공)
**상태:** 표준 (supersedes `scripts/rvc_dub/dub.py` 의 RvcPyInfer/ONNX 경로)
**검증:** S21 proot Ubuntu (aarch64) 실측 완료

---

## 0. 왜 이 문서가 필요한가 (요약)

- 예전 `scripts/rvc_dub/dub.py` 는 **RvcPyInfer(ONNX) + ContentVec** 경로 → "못 들어줄 정도로 망가짐" (금속성/로봇소리). 근거: `_notebook/rvc-failure-analysis_Claude.md`.
- 정답 경로는 **RVC WebUI PyTorch 네이티브 코드 + HuBERT + rmvpe.pt**.
- 이 문서는 그 정답 경로를 5단계 파이프라인으로 고정하고, S21 CPU 실측 파라미터·검증 기준을 표준화한다.
- **검증 기준:** WSL·S25·S21 어느 환경이든 동일 파라미터면 동일 결과.

---

## 1. 사전 준비 (파일 배치)

```
~/rvc_models/helena_rvc/helena_rvc.pth        (57.6MB)
~/rvc_models/helena_rvc/helena_rvc.index      (116.6MB)
~/rvc_models/synth_voice_pro.sh               (아래 스크립트)
~/rvc_models/rvc_convert.py                   (Stage 3 단독 변환 — 이 문서에서 신설)
~/rvc-webui-local/                            (엔진 코드 전체)
~/rvc-webui-local/assets/hubert_base/pytorch_model.bin  (377MB)
~/rvc-webui-local/assets/rmvpe/rmvpe.pt       (181MB)
```

symlink (필수):
```bash
mkdir -p ~/rvc-webui-local/assets/weights ~/rvc-webui-local/logs/helena_rvc
ln -sf ~/rvc_models/helena_rvc/helena_rvc.pth   ~/rvc-webui-local/assets/weights/helena_rvc.pth
ln -sf ~/rvc_models/helena_rvc/helena_rvc.index ~/rvc-webui-local/logs/helena_rvc/helena_rvc.index
```

---

## 2. 파이프라인 5단계 (전체 흐름)

```
[1/5] Edge TTS          → tts_raw.mp3
[2/5] 침묵제거+정규화    → tts_clean.wav (16kHz mono)
[3/5] RVC 변환          → rvc_raw.wav
[4/5] 노이즈게이트+마스터링 → 출력.mp3 (192k)
[5/5] 품질 리포트
```

---

## 3. [1/5] Edge TTS — 운율(딕션·악센트·호흡) 담당

| 항목 | 값 |
|------|-----|
| Voice | ko-KR-SunHiNeural |
| Rate | -15% |
| Pitch | -3Hz |
| 출력 | tts_raw.mp3 |

```bash
edge-tts --voice ko-KR-SunHiNeural --rate=-15% --pitch=-3Hz \
  --text "TEXT" --write-media tts_raw.mp3
```

⚠️ rate/pitch 값이 음수(-)면 `=` 로 붙여야 함 (예: `--rate=-15%`)

---

## 4. [1/5] 입력 텍스트 (호흡 포인트 포함 — 그대로 복사)

> 여호와는 나의 목자시니, 내게 부족함이 없으리로다. 그가 나를 푸른 풀밭에 누이시며, 쉴 만한 물가로 인도하시는도다. 내 영혼을 소생시키시고, 자기 이름을 위하여, 의의 길로 인도하시는도다. 내가 사망의 음침한 골짜기로 다닐지라도, 해를 받지 않을 것은... 주께서 나와 함께 하심이라. 주의 지팡이와 막대기가, 나를 안위하시나이다. 주께서 내 원수 앞에서, 내게 상을 차려 주시고, 기름을 내 머리에 부으셨으니, 내 잔이 넘치나이다. 내 평생에, 선하심과 인자하심이, 반드시 나를 따르리니, 내가 여호와의 집에, 영원히 살리로다.

- 쉼표(,) = 짧은 호흡 / 마침표(.) = 문장 끝 쉼 / ... = 극적 쉼
- 이 부호가 운율을 만들므로 **임의로 바꾸지 말 것**

---

## 5. [2/5] 침묵 제거 + 정규화

```bash
ffmpeg -y -i tts_raw.mp3 \
  -af "silenceremove=stop_periods=-1:stop_duration=0.3:stop_threshold=-50dB, loudnorm=I=-16:LRA=11:TP=-1.5" \
  -ar 16000 -ac 1 tts_clean.wav
```

---

## 6. [3/5] RVC 변환 — 음색 담당 (핵심 파라미터)

```python
vc.vc_single(
    sid=0,
    input_audio_path='tts_clean.wav',
    f0_up_key=0,          # 키 그대로
    f0_method='rmvpe',    # 피치 추출 방식 (필수: rmvpe)
    file_index='~/rvc-webui-local/logs/helena_rvc/helena_rvc.index',
    index_rate=0.75,      # 목소리 유사도 (0.75 고정)
    resample_sr=40000,    # 출력 샘플레이트
    rms_mix_rate=0.25,    # 볼륨 엔벨로프 보존율
    protect=0.33,         # 무성음 보호
)
```

환경변수 (RVC 엔진이 참조):
```python
os.environ['weight_root']        = '~/rvc-webui-local/assets/weights'
os.environ['index_root']         = '~/rvc-webui-local/logs'
os.environ['outside_index_root'] = '~/rvc-webui-local/logs'
os.environ['rmvpe_root']         = '~/rvc-webui-local/assets/rmvpe'
```

출력은 int16 → float32로 변환해 `rvc_raw.wav`로 저장.

> **재사용:** `~/rvc_models/rvc_convert.py <in.wav> <out.wav> [model] [index_rate]` 로 Stage 3 단독 실행 가능 (아래 §11 참조).

---

## 7. [4/5] 노이즈 게이트 + 마스터링

```bash
ffmpeg -y -i rvc_raw.wav \
  -af "highpass=f=80, lowpass=f=15000, silenceremove=stop_periods=-1:stop_duration=0.2:stop_threshold=-45dB, loudnorm=I=-14:LRA=11:TP=-1.0, volume=1.2" \
  -b:a 192k psalm23_natural.mp3
```

| 필터 | 값 | 목적 |
|------|-----|------|
| highpass | 80Hz | 저역 잡음 제거 |
| lowpass | 15000Hz | 치찰·고역 자극 제거 |
| silenceremove | -45dB / 0.2s | 라인 사이 삑삑·무음 제거 |
| loudnorm | I=-14 LUFS | 방송 표준 라우드니스 |
| volume | 1.2 | 최종 게인 보정 |

---

## 8. [5/5] 최종 결과 스펙 (검증 기준)

| 항목 | 목표값 | 허용범위 |
|------|--------|----------|
| 길이 | 43.87초 | ±0.5초 |
| RMS | 0.1425 | ±0.01 |
| 평균볼륨 | -12.7dB | ±0.5dB |
| 비트레이트 | 192k mp3 | 고정 |

검증 명령:
```bash
ffmpeg -i psalm23_natural.mp3 -af volumedetect -f null /dev/null 2>&1 | grep mean_volume
```

---

## 9. 전체 실행 명령 (1커맨드)

```bash
cd ~/rvc_models
bash synth_voice_pro.sh helena_rvc ko-KR-SunHiNeural "TEXT" psalm23_natural "-15%" "-3Hz"
```
- 4번째 인자: 출력명 / 5번째: rate / 6번째: pitch
- TEXT 자리에 §4의 텍스트 전체를 그대로 넣으면 됨

---

## 10. 주의사항 (기존 3건)

1. `rmvpe.pt` 없으면 [3/5]에서 피치 추출 실패 (에이전트가 누락했던 파일)
2. `parselmouth`는 `f0_method='pm'`에서만 필요 → rmvpe에선 불필요, import 주석처리해도 무방
3. rate/pitch 음수값은 `--rate=-15%` 형태로 `=` 필수
4. 텍스트의 쉼표/마침표/말줄임표를 지우면 호흡이 사라져 "AI 티"가 남 → **절대 변경 금지**

---

## 11. 신규 추가 — 세션 드롭 회피 & 코드 함정 (2026-08-13 실측)

이 작업이 **왜 자꾸 세션이 끊겼는가** + 그 해법.

### (1) 세션 드롭 원인: CPU 장시간 추론 타임아웃

- S21 CPU 실측: **오디오 1초당 약 14초** 소요 (rmvpe 피치 추출 + HuBERT 특징 추출 + RVC forward).
- 45초 음성 → **약 10~11분** 추론 + 모델 로드 ~1분 = 총 ~12분.
- 이는 Claude Code Bash 도구의 포그라운드 타임아웃(최대 10분)을 초과 → **중간에 세션 종료**.
- (CLAUDE.md 에 이미 기록된 "ParksyTTS 7분+ 타임아웃" 과 동일 계열 문제)

**해법:** Stage 3(RVC)를 `setsid nohup` 으로 **detach 실행** → 세션 드롭과 무관하게 진행 + 로그 파일로 진행 상황 모니터링.

```bash
setsid nohup bash run_stage345.sh > synth_out/run_full2.log 2>&1 < /dev/null &
# 이후: grep -qE "DONE|FAILED|Traceback" 로 종료 상태 폴링
```

### (2) 코드 함정 2건 (발견·수정)

| 함정 | 증상 | 수정 |
|------|------|------|
| `os.chdir(RVC_WEBUI)` 후 **상대경로** 입력 | `load_audio` ffmpeg error (파일 못 찾음) | 입력/출력을 `os.path.abspath()` 로 변환 |
| `config.py` 가 **모듈 레벨 argparse** 호출 | 스탠드얼론 스크립트 argv와 충돌 (`unrecognized arguments`) | `sys.argv = [sys.argv[0]]` 로 비우고 import |

> `synth_voice_pro.sh` 는 heredoc(`python3 -`) + 절대경로를 써서 두 함정을 이미 회피하고 있었음. 하지만 재사용 가능한 **Stage 3 단독 스크립트 `rvc_convert.py`** 를 분리하면서 이 함정들이 드러남 → 위 표대로 수정.

### (3) "final_proj.weight/bias MISSING" 경고는 무해

- HuBERT base checkpoint에는 최종 projection 레이어가 없어서 transformers가 출력하는 **정상 경고**.
- RVC Generator는 base HuBERT 특징(768차원)을 쓰므로 무시해도 됨. **실패 원인이 아님.**

### (4) 실측 처리속도 참고 (S21 aarch64, torch 2.13.0 CPU)

| 단계 | 시간 |
|------|------|
| torch import + VC init | ~55s |
| 가중치 로드 (211 tensors) | ~2s |
| RVC 추론 (45s 음성) | ~10~11분 |
| 마스터링 (ffmpeg) | 수 초 |

---

## 12. 관련 문서

- `_notebook/rvc-failure-analysis_Claude.md` — ONNX/RvcPyInfer 경로 실패 원인
- `_notebook/rvc-environment-gap_Claude.md` — Python 3.14 vs rvc-python 차단 분석
- `scripts/rvc_dub/dub.py` — ~~구 표준 (RvcPyInfer ONNX)~~ → 본 문서로 대체됨

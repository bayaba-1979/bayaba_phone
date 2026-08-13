# 헬레나 성우 더빙 — 베이스라인 잠금 + 주의 기도 적용 (_Grok)

**날짜:** 2026-08-13  
**작성:** Grok (디자이너 · 파싱/잠금)  
**상태:** CURRENT 표준 잠금. 기술 원본은 `_notebook/81-helena-rvc-dubbing-standard_Claude.md`  
**검증 원칙:** WSL · S25 · S21 어느 환경이든 **동일 파라미터면 동일 결과**

---

## 0. 한 줄 결론

누나 성우 더빙의 정답은 **운율은 Edge TTS, 음색은 Helena RVC(PyTorch 네이티브)** 다.  
오늘 시편 23편으로 검증된 5단계 파이프라인을 **성우 더빙 베이스라인**으로 잠근다.  
이 문서의 첫 적용작은 **주의 기도(주기도문, 개역개정)**.

---

## 1. 수첩에서 파싱한 성우 이력 (실패 → 정답)

수첩·번들·홈 디렉터리를 전부 훑어 시간순으로 정리하면, 경로는 한 방향으로만 수렴한다.

| 시기 | 시도 | 결과 | 지금 쓸 수 있나 |
|------|------|------|------------------|
| 08-06 | `voice_engine` 로컬 프로바이더, Grok/Ara 6비트 더빙 | PD 인트로용. 신원(누나) 아님 | PD 전용 |
| 08-07 | **ParksyTTS (GPT-SoVITS)** | 3.5초 음성에 471초. 실사용 불가 | ❌ 생산 금지 |
| 08-07 | Kokoro-82M FP32 + `jf_alpha` | 한국어에 일본인 억양. 임시 폴백 | ❌ 신원 더빙 금지 |
| 08-07 | 경량 TTS + **RVC ONNX INT8** (`74`) | 속도 가설만. 귀로 검증 전 | ❌ |
| 08-08 | 성우 우선순위 grok→openai→edge (`69`) | PD/쇼츠용 정책. 누나 신원과 별개 | PD 전용 |
| 08-11 | Edge TTS InJoon + parksy_rvc (속도 계산) | “RVC는 음색만 바꾼다” 통찰은 맞음 | 통찰만 유지 |
| 08-12 | S21에서 `.pth`→ONNX + RvcPyInfer (사도신경) | 숫자는 정상, **금속성/로봇 소리** | ❌ 폐기 |
| 08-12 | 실패 분석 (`rvc-failure-analysis_Claude`) | 아키텍처 버전 불일치 + ContentVec≠HuBERT | 근거 문서 |
| 08-12 | 환경 갭 (`rvc-environment-gap_Claude`) | Python 3.14 → `rvc-python` 설치 불가 | pip 우회가 정답 |
| 08-13 | **RVC WebUI PyTorch + HuBERT + rmvpe.pt** | 시편 23편 43.87초 / RMS 0.1425 / −12.7dB | ✅ **베이스라인** |

### 절대 다시 타지 말 길

- `scripts/rvc_dub/dub.py` 의 RvcPyInfer/ONNX 경로 — 조용히 실패한다. 파형 숫자는 맞아도 귀가 거부한다.
- ContentVec ONNX로 Helena `.pth`를 돌리는 것 — 768차원이 같아도 분포가 다르다.
- ParksyTTS/GPT-SoVITS를 폰 CPU에서 본편 더빙에 쓰는 것.
- 호흡 부호(쉼표·마침표·말줄임표)를 “예쁘게” 고치는 것 — 고치는 순간 AI 티가 남는다.

### 역할 분리 (백서 `80` + 오늘 스펙이 같은 말을 함)

- **Edge TTS (`ko-KR-SunHiNeural`)** = 딕션·악센트·호흡. 운율 담당.
- **Helena RVC (`.pth` + `.index`)** = 음색. 신원 담당.
- 목소리는 폰트가 아니라 **로고급 신원 자산**이다 (`80-ai-voice-actor-whitepaper_Boss.md`).

---

## 2. 베이스라인 잠금 — 시편 23편 파라미터를 불변값으로

기술 명세의 원본은 Claude가 시공·실측한 `81`.  
Grok은 그 값을 **콘텐츠 표준으로 잠근다.** 값 변경은 Boss 승인 없이 금지.

### 파일 배치 (이미 이 머신에 존재)

```
~/rvc_models/helena_rvc/helena_rvc.pth          57.6MB
~/rvc_models/helena_rvc/helena_rvc.index        116.6MB
~/rvc_models/synth_voice_pro.sh
~/rvc_models/rvc_convert.py                     Stage 3 단독
~/rvc-webui-local/                              엔진 전체
~/rvc-webui-local/assets/hubert_base/pytorch_model.bin   377MB
~/rvc-webui-local/assets/rmvpe/rmvpe.pt                  181MB
```

symlink는 이미 연결됨 (`assets/weights`, `logs/helena_rvc`).

### 5단계

```
[1/5] Edge TTS            → tts_raw.mp3
[2/5] 침묵제거+정규화      → tts_clean.wav (16kHz mono)
[3/5] RVC 변환             → rvc_raw.wav
[4/5] 노이즈게이트+마스터링 → 출력.mp3 (192k)
[5/5] 품질 리포트
```

### 불변 파라미터

| 층 | 키 | 값 | 왜 고정인가 |
|----|----|-----|-------------|
| TTS | Voice | `ko-KR-SunHiNeural` | 한국어 여성, 낭독 톤 |
| TTS | Rate | `-15%` (`--rate=-15%`) | 기도/낭독 호흡. 음수는 `=` 필수 |
| TTS | Pitch | `-3Hz` (`--pitch=-3Hz`) | 살짝 낮춰 안정감 |
| RVC | `f0_method` | `rmvpe` | `rmvpe.pt` 없으면 즉시 실패 |
| RVC | `f0_up_key` | `0` | 키 변조 금지 |
| RVC | `index_rate` | `0.75` | 목소리 유사도 |
| RVC | `resample_sr` | `40000` | 모델 네이티브 |
| RVC | `rms_mix_rate` | `0.25` | 원본 엔벨로프 일부 보존 |
| RVC | `protect` | `0.33` | 무성음 보호 |
| Master | HPF / LPF | 80 / 15000 | 저역 잡음·치찰 제거 |
| Master | loudnorm | `I=-14:LRA=11:TP=-1.0` | 방송 라우드니스 |
| Master | volume | `1.2` | 최종 게인 |
| Master | bitrate | `192k` mp3 | 고정 |

### 시편 23편 검증 기준 (레퍼런스 클립)

| 항목 | 목표 | 허용 |
|------|------|------|
| 길이 | 43.87초 | ±0.5초 |
| RMS | 0.1425 | ±0.01 |
| 평균볼륨 | −12.7dB | ±0.5dB |
| 비트레이트 | 192k mp3 | 고정 |

주의 기도는 텍스트 길이가 다르므로 **길이 목표만 시편과 다르다.**  
RMS·평균볼륨·192k는 같은 마스터링이므로 같은 창에 들어와야 한다.

### 실행 원라이너

```bash
cd ~/rvc_models
bash synth_voice_pro.sh helena_rvc ko-KR-SunHiNeural "TEXT" OUTPUT_NAME "-15%" "-3Hz"
```

S21 CPU는 오디오 1초당 약 14초. 30초 클립이면 Stage 3만 7~10분.  
**포그라운드에서 돌리지 말 것.** `setsid nohup` + 로그 폴링 (81 §11).

---

## 3. 첫 적용 — 주의 기도 (개역개정, 호흡 고정)

시편 23편과 같은 부호 규약:

- `,` = 짧은 호흡
- `.` = 문장 끝 쉼
- `...` = 극적 쉼 (시험 → 구원의 전환)

```
하늘에 계신 우리 아버지여, 이름이 거룩히 여김을 받으시오며, 나라가 임하시오며, 뜻이 하늘에서 이루어진 것 같이, 땅에서도 이루어지이다. 오늘날 우리에게 일용할 양식을 주시옵고, 우리가 우리에게 죄 지은 자를 사하여 준 것 같이, 우리 죄를 사하여 주시옵고, 우리를 시험에 들게 하지 마시옵고... 다만 악에서 구하시옵소서. 나라와 권세와 영광이, 아버지께 영원히 있사옵나이다. 아멘.
```

원문 파일: `~/rvc_models/lords_prayer.txt`  
출력명: `lords_prayer_natural.mp3`

이 텍스트의 쉼표/마침표/말줄임표는 **시편 23편과 동일하게 임의 변경 금지.**

---

## 4. 관련 문서 (읽기 순서)

1. `CONSTITUTION.md` — 왜 누나 목소리인가 (대필작가·신원)
2. `80-ai-voice-actor-whitepaper_Boss.md` — 목소리 ≠ 폰트
3. `81-helena-rvc-dubbing-standard_Claude.md` — 기술 원본·실측
4. `rvc-failure-analysis_Claude.md` — ONNX가 왜 폐기됐는가
5. 이 문서 — 잠금 + 주의 기도 적용

구 경로: `scripts/rvc_dub/dub.py` 는 더 이상 표준이 아니다.

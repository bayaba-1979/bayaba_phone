# RVC 환경 차이 진단 — WSL vs S21

**날짜:** 2026-08-12

---

## WSL 성공 환경 (Boss 브리핑 기반)

| 항목 | WSL | S21 | 호환? |
|------|-----|-----|-------|
| Python | 3.12 | 3.14 | ❌ |
| torch | 2.10.0+cu128 | 2.13.0+cu130 | ✅ (무관) |
| rvc-python | 0.1.5 (pip) | 설치 불가 | ❌ |
| fairseq | ✅ | 미설치 | ⏳ |
| pyworld | ✅ | 미설치 | ⏳ |
| torchcrepe | ✅ | 미설치 | ⏳ |
| faiss-cpu | ✅ | 미설치 | ⏳ |
| edge-tts | 7.2.7 | 7.2.8 | ✅ |
| soundfile | ✅ | ✅ | ✅ |
| parksy_rvc.pth | 55MB | 있음 | ✅ |
| parksy_rvc.index | 180MB | 있음 | ✅ |

## 핵심 차단기: Python 3.14

`rvc-python 0.1.5`는 Python 3.10~3.11 시대 패키지.
- `pkgutil.ImpImporter` → Python 3.12에서 deprecated, 3.14에서 **제거됨**
- `distutils.msvccompiler` → Python 3.12에서 **제거됨**
- numpy 구형 빌드 시스템 의존

S21 proot에는 Python 3.14만 존재. 3.12 설치는 가능할 수 있으나 proot ARM 환경에서 deadsnakes PPA가 aarch64를 지원하지 않을 가능성 높음.

## 해결책: rvc-python 우회

`rvc-python`은 RVC WebUI 코드의 **얇은 래퍼**일 뿐. 실제 추론은 PyTorch로 직접 할 수 있음.

S21에는 이미 PyTorch 2.13.0이 설치돼 있고, parksy_rvc.pth 가중치도 있음.
필요한 것은:

```
WSL → S21로 전송할 것:
├── synth_voice.sh           ← Boss의 실제 inference 스크립트
├── rvc-venv/                ← (선택) venv 통째로 or requirements.txt
├── hubert_base.pt           ← HuBERT 특징 추출 모델 (rvc-python이 자동 다운로드한 것)
└── RVC 프로젝트 infer/ 디렉토리 (rvc-python 내부에서 import하는 코드)
```

## S21에서 구동 시 예상 차이

| 항목 | WSL | S21 (예상) |
|------|-----|-----------|
| torch | 2.10.0 CUDA | 2.13.0 CPU |
| RTF | ~2 (GPU) | ~4-5 (CPU) |
| 출력 품질 | 기준 | **동일해야 함** (같은 가중치, 같은 연산) |

PyTorch forward pass는 CPU/GPU 구분 없이 **수치적으로 동일한 결과**를 내야 함.
GPU에서 CPU로 옮겨도 음질이 달라지지 않음. 속도만 다름.

## 결론

**rvc-python pip 패키지는 못 쓴다.** 하지만 **rvc-python 없이도 RVC 추론은 가능하다.**
Boss가 WSL의 inference 스크립트 + HuBERT 모델 + RVC 코드를 tar로 묶어서 보내주면,
S21 PyTorch로 직접 구동해서 동일한 출력을 낼 수 있다.

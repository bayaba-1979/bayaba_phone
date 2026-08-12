# RVC 합성 실패 분석 — WSL vs S21 proot 환경 차이

**날짜:** 2026-08-12
**결론:** Boss Ultra25(WSL)에서 성공한 RVC 파이프라인을 S21(proot Ubuntu)에서 재현하지 못함. 근본 원인: RVC 아키텍처 버전 불일치 + ContentVec/HuBERT 차이.

---

## 실패 경위

| 시도 | 방법 | 결과 |
|------|------|------|
| 1차 | `.pth` → ONNX 변환 (최신 RVC 코드 + monkeypatch) | 변환 성공, RTF 3.3, RMS 정상 |
| 2차 | RvcPyInfer로 ONNX 추론 | Boss 귀 확인 → **못 들어줄 정도로 망가짐** |

숫자는 다 맞았지만 실제 음질은 금속성/로봇소리 — RVC inference의 전형적인 "조용한 실패" 패턴.

## 근본 원인 분석

### 1. RVC 아키텍처 버전 불일치 (가장 의심)

**S21에서 내가 한 것:**
- GitHub 최신 `RVC-Project/Retrieval-based-Voice-Conversion-WebUI` 클론 (`81eed5e`)
- `infer/module/models.py` → `SynthesizerTrnMs768NSFsid` (신형 아키텍처)
- `parksy_rvc.pth` 가중치를 신형 모델에 `strict=False`로 강제 로드
- 103개 `enc_q.*` 키 누락 → "ContentVec이 따로 있으니 괜찮다"고 가정

**문제:**
- `parksy_rvc.pth`의 `config` 버전은 `"v2"`지만, 이 v2는 **옛날 v2**(`SynthesizerTrnMsNSFsidM` 용)일 가능성 높음
- RVC는 시간이 지나면서 "v2"라는 같은 이름 아래 내부 아키텍처가 여러 번 바뀜
- `strict=False`가 "남는 건 무시하고 없는 건 기본값" → 미묘한 구조 차이가 출력 품질을 완전히 망가뜨림

### 2. ContentVec vs HuBERT

| | WSL (추정) | S21 (실제) |
|------|-----------|-----------|
| 특징 추출기 | HuBERT (`hubert_base.pt`, PyTorch) | ContentVec (`vec-768-layer-12.onnx`, ONNX) |
| 임베딩 차원 | 768 (HuBERT) | 768 (ContentVec) |
| 벡터 분포 | HuBERT 분포 | ContentVec 분포 (다름!) |

RVC Generator는 HuBERT 특징에 맞춰 학습됨. ContentVec으로 추출한 특징은 **같은 768차원이지만 분포가 달라서** Generator가 전혀 다른 결과를 냄.

### 3. index_rate 구현 차이

- WSL PyTorch: FAISS index 검색 후 `feats = index_feats * index_rate + orig * (1 - index_rate)` (Pipeline.vc() L193-196)
- S21 RvcPyInfer: `index_rate`가 같은 의미지만 내부 구현 다를 수 있음

### 4. ONNX export monkeypatch

- RvcPyInfer 템플릿의 monkeypatch는 **구형 RVC**(`infer.lib.infer_pack.attentions`) 기준
- 내가 **신형 RVC**(`infer.module.attentions`)에 맞춰 주먹구구로 수정
- 상대위치 임베딩 reshape가 frame sequence 길이마다 달라지는 걸 monkeypatch가 제대로 처리 못 했을 가능성

## WSL 성공 환경에서 필요한 것

Boss가 Ultra25에서 성공한 환경을 통째로 S21로 가져오려면:

### 필수 (우선순위 높음)
```
[ ] RVC 프로젝트 전체 폴더 (또는 정확한 git commit hash)
[ ] hubert_base.pt 경로
[ ] 실제 사용한 inference 명령어/스크립트
[ ] pip freeze > requirements_rvc.txt (PyTorch, fairseq, onnxruntime 버전)
```

### 선택 (있으면 좋음)
```
[ ] WSL에서 생성한 참조 출력 (apostles_parksy.mp3 등)
[ ] .pth 학습 시 사용한 config.json 또는 하이퍼파라미터
[ ] f0 추출 방식 (RMVPE .pt 모델? pm? dio?)
```

## S21에서 구동 가능한지 — 환경 차이

| | WSL (Ultra25) | S21 proot Ubuntu |
|------|--------------|-------------------|
| CPU | x86_64 (Intel/AMD) | aarch64 (Exynos 2100) |
| PyTorch | x86_64 wheel | aarch64 wheel (`torch==2.6.0`) |
| CUDA/GPU | 가능 (NVIDIA GPU) | 불가 (Mali GPU, glibc/bionic ABI 불일치) |
| onnxruntime | x86_64 | aarch64 |
| RAM | 넉넉 (32GB+ 추정) | 8GB |
| fairseq | x86_64 | aarch64 (컴파일 필요 가능성) |

**핵심 질문:** Boss의 WSL 추론이 **PyTorch 네이티브**인가, 아니면 **ONNX Runtime**인가?

- PyTorch 네이티브면: S21에서도 `pip install torch`만으로 동작 가능 (CPU 모드). ARM PyTorch는 mature함.
- ONNX Runtime이면: aarch64 onnxruntime이 이미 설치돼 있음. `.onnx` 모델만 복사.

**둘 다 S21에서 가능.** 문제는 RVC "버전"과 "HuBERT 모델"이지, 런타임이 아님.

## 다음 스텝 — Boss가 Ultra25에서 가져올 것

```
# Ultra25에서 실행:
# 1. RVC 프로젝트 경로 확인
echo $RVC_ROOT

# 2. git commit hash
cd $RVC_ROOT && git log --oneline -1

# 3. 패키지 버전
pip freeze | grep -iE "torch|onnx|fairseq|librosa|soundfile|numpy"

# 4. inference 명령어
cat ~/infer.sh  # 또는 사용한 명령어

# 5. 프로젝트 압축 (S21로 전송)
tar czf rvc_wsl.tar.gz $RVC_ROOT/infer/ $RVC_ROOT/venv/requirements.txt
```

S21에 도착하면 → Claude Code가 분석 → 같은 버전 설치 → inference 재현 → A/B 검증.

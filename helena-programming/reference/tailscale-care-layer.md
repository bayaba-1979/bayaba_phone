# Tailscale — 돌봄 인프라의 액션 레이어

> **포지션:** Telegram = 감지(Detection) | Tailscale = 액션(Action)  
> 감지만 있으면 속수무책, 액션만 있으면 눈먼 대응. 둘이 같이 있어야 진짜 돌봄.

---

## 실제 아키텍처

**핵심: Control(명령)과 Compute(계산)는 다르다.**

```
명령 계통:  S25(Boss 폰) → "이 텍스트 더빙해" → WSL에 명령
              ↑ 리모컨                              │
              │                                     ↓ 계산
            Tailscale                          WSL(팩토리)
              │                              SoVITS 314MB
              │                              RVC 55MB
              │                              Kokoro 311MB
              ↓                              Chatterbox
결과 전달:  S21(누나 폰) ←──── 음성 파일 ────┘
              ↑ 스피커
```

**WSL이 유일한 컴퓨트 허브인 이유:**
- SoVITS(314MB) + RVC(55MB) + Kokoro(311MB) + Chatterbox
- CPU 164%, RAM 4GB 소비 — 폰 AP·태블릿으로 절대 불가능
- WSL 빼면 SoVITS도 RVC도 못 돌린다. 태블릿도 마찬가지.

## 각 디바이스 역할

| 디바이스 | 역할 | 하는 일 | Tailscale 이유 |
|----------|------|---------|---------------|
| **WSL PC** | 🏭 **팩토리** | 모든 ML 추론·모델 저장·학습 | 명령 수신 + 결과 전송 |
| **S25** | 🎮 **리모컨** | WSL에 더빙 명령·상태 확인 | SSH로 `synth_voice()` 호출 |
| **S21** | 🔊 **출력기** | 음성 재생·건강 데이터 수집 | WSL로부터 결과 파일 받기 |
| **태블릿** | 📺 **디스플레이** (옵션) | 캐시·가벼운 UI | 무거운 건 전부 WSL에 위임 |

## 돌봄 워크플로우

```
[사건 발생] → Telegram 알림(감지) → Tailscale SSH(액션) → 진단·수정·복구
```

### 구체적 시나리오

| 상황 | 감지 (Telegram) | 액션 (Tailscale) |
|------|-----------------|-------------------|
| 배터리 12% | 긴급 알림 발송 | S25에서 `ssh wsl "scp fix.sh s21:"` → 실행 |
| TTS 모델 깨짐 | 음성 생성 실패 알림 | WSL에서 S21로 모델 재전송 |
| 디스크 풀 | health check 경고 | SSH로 로그/캐시 원격 정리 |
| 더빙 요청 | — | S25 → WSL `synth_voice()` → 결과 → S21 |

### 핵심 워크플로우 예시

```bash
# 1. S25에서 WSL에 더빙 명령
ssh wsl "synth_voice '안녕 누나, 약 드셨어요?'"

# 2. WSL이 SoVITS+RVC 추론 (471s or Edge+RVC 3s)

# 3. 결과를 S21로 전송
ssh wsl "scp result.wav s21:~/audio/today/"

# 4. S21에서 재생
ssh s21 "termux-media-player play ~/audio/today/result.wav"
```

## 기존 파이프와의 관계 (충돌 제로)

```
┌─────────────────────────────────────────┐
│  care-daemon.sh  send_models.sh  say.py  │  ← 기존 그대로
├─────────────────────────────────────────┤
│  SSH / SCP / rsync / curl                │  ← 기존 그대로
├─────────────────────────────────────────┤
│  Tailscale (WireGuard mesh)              │  ← 여기만 추가
│  ts_host:helena-s21 → 항상 같은 주소     │
└─────────────────────────────────────────┘
```

## tailnet 구성

| 디바이스 | 역할 | Tailscale 호스트명 |
|----------|------|-------------------|
| **WSL PC** | 팩토리 (ML 컴퓨트) | wsl-factory |
| **S25** | 리모컨 (명령 발행) | boss-phone |
| **S21** | 출력기 + 센서 (누나 폰) | helena-s21 |
| **태블릿** | 보조 디스플레이 (옵션) | helena-display |

---

## 알려진 제약

| 제약 | 설명 | 우회 방법 |
|------|------|-----------|
| proot ↔ Tailscale 직결 불가 | glibc 환경이 Android VPN 라우팅 못 탐 | S21 받는 쪽은 Termux를 게이트웨이로 |
| Tailscale 완전 장애 시 | 액션 레이어 전체 마비 | 재래식 SSH over WiFi fallback 유지 |
| WSL이 꺼지면 | 모든 컴퓨트 중단 | GitHub Actions를 cold standby로 |

---

## 앞으로

- [ ] `synth_voice()` — S25 → WSL 원격 더빙 호출 원라이너
- [ ] WSL → S21 음성 자동 푸시 (`scp result.wav s21:`)
- [ ] care-daemon에 Tailscale heartbeat 모니터링 추가
- [ ] WSL 장애 시 GitHub Actions fallback 파이프

---

_마지막 갱신: 2026-08-12 · Boss + Claude Code_

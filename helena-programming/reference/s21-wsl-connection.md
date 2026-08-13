# S21 ↔ WSL 통신 레이어 — 돌봄 인프라 표준 연결

> **목적:** S21(누나 폰)과 WSL(내 PC)을 항상 연결된 디바이스로 만들어,  
> 모델·데이터·설정·로그·원격 제어가 자유롭게 흐르게 한다.  
> 일회성 파일 전송이 아니라 **돌봄(care) 인프라의 신경계**다.

---

## 현재 아키텍처 (2026-08-11)

```
[WSL PC] ←→ [Tailscale] ←→ [Android Tailscale VPN] ←→ [Termux] ←→ [proot Ubuntu]
   ↑                              ↑
 100.x.y.z                   tun0 (Tailscale IP)
 SSH:2222                    curl/SSH client
 HTTP:8888
```

**통신 방식:** Tailscale mesh VPN → SSH(포트 2222) + HTTP(포트 8888)  
**계정:** Boss Tailscale 계정 (양쪽 같은 tailnet)

---

## 설정 방법

### 1. Tailscale 설치

**WSL:** `curl -fsSL https://tailscale.com/install.sh | sh`  
**S21:** Android Play Store에서 Tailscale 설치 + proot Ubuntu에 CLI 설치

```bash
# proot Ubuntu (CLI만 필요할 경우)
curl -fsSL https://tailscale.com/install.sh | sh
```

### 2. 같은 계정으로 로그인

양쪽 다 **같은 Tailscale 계정**이어야 P2P 연결 성립.

```bash
# WSL
sudo tailscale up

# S21 Android
# Tailscale 앱에서 Boss 계정으로 로그인
```

### 3. 연결 확인

```bash
# WSL에서
tailscale status          # S21 노드 보이는지 확인
tailscale ip -4           # WSL 자신의 IP 확인

# S21 proot에서 (또는 Termux에서)
ssh -p 2222 dtsli@<WSL_TAILSCALE_IP>   # SSH 연결 테스트
curl -O http://<WSL_TAILSCALE_IP>:8888/filename  # HTTP 전송
```

---

## 알려진 이슈

| 이슈 | 현상 | 해결 |
|------|------|------|
| Android VPN 라우팅 | `tun0` IP는 보이지만 proot에서 Tailscale peer로 라우팅 안 됨 | proot에 tailscaled 직접 설치·인증 (userspace-networking) |
| 계정 불일치 | S21(누나 계정) ↔ WSL(Boss 계정) P2P 실패 | 양쪽 Boss 계정으로 통일 |
| HTTP 서버 바인딩 | Tailscale IP 바뀌면 기존 서버 접근 불가 | `--bind 0.0.0.0` 사용 |

---

## 사용 예시

```bash
# WSL → S21로 모델 파일 전송 (WSL에서 실행)
scp -P 2222 parksy_rvc.pth dtsli@<S21_IP>:~/rvc_models/parksy_rvc/

# S21 → WSL에서 파일 받기 (proot에서 실행)
curl -O http://<WSL_IP>:8888/parksy_rvc.pth

# WSL 원격 명령 실행
ssh -p 2222 dtsli@<S21_IP> 'bash ~/work/phone-health.sh'
```

---

## 이 통신 레이어 위에 올라갈 것들

- [ ] RVC 모델 전송 및 업데이트
- [ ] health check 결과 WSL로 동기화
- [ ] devlog 원격 백업
- [ ] care 데몬 원격 제어
- [ ] git push/pull 브릿지

---

_마지막 갱신: 2026-08-11 · Boss + Claude Code_

# Tailscale 돌봄 데몬 백서 — 원격 접속 채널 확립

> 작성: 2026-08-13 · 작성자: `_Claude`
> 위치: `care/` (트랙 1 돌봄 데몬)
> 상태: **✅ 계정 통일 완료 · proot → `REDACTED` tailnet 접속 성공 · SSH 채널 개통**
> 연관: `care/care-daemon.sh` (아웃바운드 알림) · `care/tailscale-care-daemon_Claude.md` (진단 상세)

---

## ✅ 최종 결과 (2026-08-13)

| 항목 | 값 |
|------|-----|
| tailnet | `REDACTED` (누나 Google 계정) |
| proot 노드 | `helena-proot` · `100.108.147.53` · MagicDNS `helena-proot.tailb4c349.ts.net` |
| SSH | ✅ 광고됨 (`tailscale ssh` 동작 — userspace 모드에서 ProxyCommand 경유 확인) |
| 안드로이드 앱 | `thomas-gall21-1` · `100.90.57.69` (온라인) |
| 같은 망 여부 | ✅ 두 기기 모두 같은 tailnet |

**핵심 성과:** proot이 GitHub(`REDACTED@github`)에서 누나 Google(`REDACTED`)로
계정 통일 완료 → 아웃바운드(텔레그램) + 인바운드(Tailscale) 두 축이 모두 갖춰진 최초 상태.

### 🔁 자동 재연결 증명 (재부팅 시뮬레이션)
tailscaled를 완전 종료 → 재시작해보니 **인증/로그인 없이 저장된 노드키로 자동 재접속**됨.
SSH 광고·호스트명(`helena-proot`) 설정도 재시작 후 그대로 복원.
→ **"폰 켜지면 자동 연결"이 성립.** 재부팅에 인증키는 불필요 (인증키는 노드 해제 시에만 쓰는 안전장치).
→ 부팅 스크립트: `care/start-tailscale-boot.sh` (Termux:Boot → `~/.termux/boot/`에 복사)

---

## 0. 한 장 요약 (TL;DR)

돌봄 데몬은 **"밖으로 보고하는 채널(텔레그램)"만 있고 "안으로 들어오는 채널"이 없었다.**
그 빈 구멍을 채우는 게 Tailscale 원격 접속인데, 지금 4가지 원인이 겹쳐 안 잡히고 있었다:

1. 배터리 최적화 → 데몬 살해 (✅ 해결)
2. proot 권한 0개 → 기본 TUN 모드 불가 → `--tun=userspace-networking` 필수 (✅ 해결책 확정)
3. 노드 해제(deauthorized) → 재인증 필요
4. **계정 불일치** — 안드로이드 앱=Google, proot=GitHub → 서로 다른 tailnet (✅ 근본 원인 확정)

**지금 할 일 하나:** proot을 GitHub에서 로그아웃하고 **Google 계정(`REDACTED`)으로 재로그인**하면 같은 tailnet에 들어간다.

---

## 1. 목적 — 왜 Tailscale이 돌봄 데몬의 핵심인가

CONSTITUTION.md의 돌봄 성공 기준은 **"절대 안 깨질 것"** 이다.
기존 `care-daemon.sh`는 폰의 배터리·위치·움직임을 **텔레그램으로 밖으로 보고**만 한다.
보고만 하고 손이 없으면, 이상 신호가 와도 간병인이 원격으로 들어가 조치할 수 없다.

```
돌봄 데몬 = 아웃바운드(텔레그램, ✅ 기존) + 인바운드(Tailscale 원격 접속, 🚧 본 백서)
```

Tailscale은 간병인이 "안으로" 들어오는 문이다. 문이 있어야 수호천사가 손이 생긴다.

---

## 2. 진단 — 증상과 원인 4가지

### 증상
- `tailscale status` → `Logged out` / 노드가 tailnet에 안 잡힘
- 다른 에이전트는 "배터리 최적화 때문"이라 진단 → 부분만 맞음

### 원인 ① — 배터리 최적화(Doze)가 Termux를 죽임
- Android가 백그라운드 앱을 잠재워 Termux→proot→tailscaled 통째로 죽음.
- **조치 완료:** 배터리 "제한 없음" 변경.

### 원인 ② — proot 권한 0개 → 기본 TUN 모드 불가 (핵심)
실측 증거:
```
CapEff:  0000000000000000   ← 가짜 root, capability 0개
tstun.New("tailscale0"): permission denied
iptables: Failed to initialize nft: Permission denied
```
→ `--tun=userspace-networking`으로 우회 (v1.102.2에서 실측 동작 확인).

### 원인 ③ — 노드 해제(deauthorized)
상태 파일: `machineAuthorized=false` + `authURL=true` → 재인증 필요.

### 원인 ④ — 계정 불일치 (근본 원인, 이번에 확정)
| | 안드로이드 앱 | proot |
|---|---|---|
| 로그인 | **Google** `REDACTED` | **GitHub** `REDACTED@github` |
| tailnet | (구글 계정망) | `REDACTED.github` |
| 상태 | 접속 중 (100.85.232.54) | Logged out |

**두 계정 = 서로 다른 두 개의 tailnet.** 아무리 둘 다 켜져도 서로 안 보인다.
이게 "안 잡히는" 최종 원인.

---

## 3. 솔루션

### 3-1. 계정 통일 (즉시 실행)
기준: **진짜 tailnet = Google(`REDACTED`)**, 누나 폰이 여기 있음.
```bash
tailscale logout          # GitHub 정체성 제거 (완료)
tailscale up              # 새 로그인 URL → Google로 로그인
# 또는 인증키(영구화): tailscale up --auth-key tskey-... --ssh
```

### 3-2. proot 실행 (userspace 필수)
```bash
tailscaled --tun=userspace-networking &
tailscale up --auth-key tskey-... --ssh
```

### 3-3. 안드로이드 레이어 자동시작 체크리스트 (삼성 S21)
| # | 설정 | 상태 |
|---|------|------|
| 1 | 배터리 제한 없음 | ✅ |
| 2 | Termux:Boot 설치 | ⬜ |
| 3 | 자동 실행 허용 | ⬜ |
| 4 | 절전 예외 등록 | ⬜ |
| 5 | Phantom process killer 끄기 | ⬜ (주범) |
| 6 | termux-wake-lock | ⬜ |

### 3-4. ⚠️ userspace 모드 한계
`tailscale0` 인터페이스가 안 생김 → 직접 IP 접속 불가, **`tailscale ssh`/`tailscale serve`로 접속**.

---

## 4. 아키텍처 — 3겹 탑

```
[안드로이드 부팅] → [Termux] → [proot Ubuntu] → [tailscaled userspace → tailscale up]
```
아무 한 겹이라도 자동 시작이 안 되면 데몬 죽음 → 재부팅 대비 자동시작 체인 필수.

---

## 5. 실행 계획

| 단계 | 내용 | 상태 |
|------|------|------|
| 1 | proot → 누나 Google(`REDACTED`) 재로그인 | ✅ 완료 |
| 2 | `--ssh` 활성화 + tailnet 노드 확인 | ✅ 완료 |
| 3 | 자동 재연결 증명 + 부팅 스크립트(`start-tailscale-boot.sh`) | ✅ 완료 (재부팅은 인증키 불필요) |
| 4 | Termux:Boot 설치 + `~/.termux/boot/` 배치 (안드로이드 1개 수동 조치) | ⬜ 대기 |
| 5 | 안드로이드 자동시작 체크리스트(팬텀킬러 등) + 하트비트 워치독 | ⬜ 대기 |

---

## 6. 리스크 / 다음 단계

- [ ] Google 계정 인증 완료 → proot이 앱과 같은 tailnet에 드는지 검증
- [ ] 재사용 인증키로 OAuth 반복 제거
- [ ] Termux 네이티브 vs proot (돌봄 경로 최적화) 검토
- [ ] "죽으면 알아차리는" 하트비트/워치독 구현

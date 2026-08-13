# Tailscale — 돌봄 데몬의 원격 접속 핵심 (인바운드 채널)

> 작성: 2026-08-13 · 작성자: `_Claude` (출판부/진단)
> 위치: `care/` — 트랙 1 돌봄 데몬
> 성격: 오늘(2026-08-13) Boss와 함께한 Tailscale 진단·솔루션 스터디의 전 과정 기록
> 연관: `care/care-daemon.sh` (아웃바운드 알림 데몬) · `reference/s21-wsl-connection.md` (기존 WSL↔S21 연결)

---

## 1. 한 줄 요약

기존 돌봄 데몬(`care-daemon.sh`)은 **폰이 "밖으로" 보고하는 채널**(텔레그램)만 있다.
돌봄에 필요한 나머지 절반 — **간병인이 "안으로" 들어오는 채널**(원격 셸·제어) — 이 비어 있었고,
그 빈 구멍을 채우는 것이 **Tailscale**이다.

> 돌봄 데몬 = **아웃바운드(텔레그램, 이미 있음) + 인바운드(Tailscale, 새로 추가)** 두 축.
> "제일 중요한 게 테일스케일"이라는 말은 정확하다 — 데몬이 아무리 잘 보고해도,
> 간병인이 원격으로 들어가 조치할 수 없으면 수호천사는 "보고만 하고 손이 없는" 상태다.

---

## 2. 오늘 진단 — 왜 폰이 안 잡혔는가 (원인 3개)

### 증상
- `tailscale status` → `tailscaled` 미실행
- tailnet 관리콘솔에서 노드가 오프라인 / 아예 목록에서 사라짐
- 다른 에이전트가 "배터리 최적화 때문"이라 진단 → **부분적으로만 맞음**

### 원인 ① — 배터리 최적화(Doze)가 Termux를 죽임 (맞음)
- Android가 백그라운드 앱을 잠재우면 Termux → proot → tailscaled가 통째로 내려감.
- **조치 완료:** 배터리 → "제한 없음"으로 변경.
- 이건 *"왜 오프라인이 됐는지"*를 설명하지만, *"왜 안 뜨는지"*의 근본 원인은 아니다.

### 원인 ② — proot은 권한 0개라 기본 TUN 모드로는 절대 안 뜸 (진짜 핵심 원인)
실측 증거:
```
CapEff:  0000000000000000   ← proot의 root는 가짜 root, capability 0개
CapBnd:  0000000000000000
tstun.New("tailscale0"): permission denied   ← TUN 디바이스 생성 불가
iptables: Failed to initialize nft: Permission denied
modprobe: command not found (tun 커널 모듈 로드 불가)
```
→ proot(glibc)은 CAP_NET_ADMIN이 없어서 **기본 `tailscaled`는 영원히 안 뜬다.**
→ 해결은 `--tun=userspace-networking` (아래 §4). 이건 *필수*이지 *선택*이 아니다.

### 원인 ③ — 노드가 tailnet에서 해제(deauthorized)됨 (맞음)
- 상태 파일(`/var/lib/tailscale/tailscaled.state`) 실측:
  - 계정: `REDACTED@github` · NodeID `nR8Jt3XNv421CNTRL`
  - `machineAuthorized=false` + `authURL=true` → **승인 해제 상태**
  - 등록일: 2026-08-12 (어제) → 오늘 이미 해제됨
- → `tailscale up`만 치면 인증 링크가 튀어나와 조용히 연결되지 않는다.
- → 재승인은 **인증키(auth key)** 로 (proot엔 링크 클릭할 GUI 브라우저가 없으므로).

---

## 3. 아키텍처 — "항상 구동"은 3겹 탑 문제

```
[안드로이드 OS 부팅]            ← 재부팅하면 여기서부터 다시 시작해야 함
      │  Termux 앱이 살아있어야 함
      ▼
[Termux 프로세스]               ← 죽으면 proot 통째로 죽음
      │  proot-distro login 이 실행돼야 함
      ▼
[proot Ubuntu]                  ← tailscaled가 도는 곳
      ▼
[tailscaled --tun=userspace-networking + tailscale up --auth-key ... --ssh]
```

**핵심 인사이트:** proot의 tailscaled는 혼자 존재하지 않는다.
아래 3겹 중 어느 하나라도 자동 시작이 안 되면 데몬은 죽어 있다.
→ "재부팅 이슈"는 proot에서 해결되는 게 아니라 **상위 안드로이드 레이어의 자동시작 체인이 통째로 필요**하다.

---

## 4. 솔루션

### 4-1. proot에서 Tailscale 실행 (userspace-networking 필수)

```bash
# 반드시 userspace 모드로 실행 (기본 TUN 모드는 권한 0이라 불가)
tailscaled --tun=userspace-networking &
sleep 2

# 인증키로 재승인 + 원격 셸 광고
tailscale up --auth-key tskey-XXXX --ssh
```

- `--tun=userspace-networking` — **v1.102.2에서 실측 동작 확인.**
  TUN 에러를 우회하고 컨트롤 플레인 도달 + `AuthURL` 수신까지 확인함.
- `--auth-key` — 관리콘솔(Settings → Keys)에서 발급. 무인 재접속 필수.
- `--ssh` — 현재 `RunSSH=false`. 원격 셸 쓰려면 켜야 함.

### 4-2. 안드로이드 레이어 설정 체크리스트 (삼성 S21 기준)

| # | 설정 | 왜 필요 | 상태 |
|---|------|---------|------|
| 1 | 배터리 → 제한 없음 | Doze가 백그라운드 얼림 방지 | ✅ 완료 |
| 2 | Termux:Boot 앱 설치 | 부팅 시 `~/.termux/boot/` 자동 실행 | ⬜ 필요 |
| 3 | 자동 실행 허용 | 삼성이 부팅 자동시작 막는 것 해제 | ⬜ 필요 |
| 4 | 절전 예외 등록 | "사용하지 않는 앱 절전" 해제 | ⬜ 필요 |
| 5 | Phantom process killer 끄기 | 안드 12+가 tailscaled 자식 프로세스 살해 | ⬜ 필요(주범) |
| 6 | termux-wake-lock | 화면 꺼져도 깊은 잠 방지 | ⬜ 필요 |

> **5번이 삼성+안드 12+에서 진짜 주범.**
> `adb shell settings put global settings_enable_monitor_phantom_procs false`
> (개발자옵션 또는 adb). 이거 안 끄면 "연결은 됐는데 몇 시간 뒤 조용히 사라짐".

### 4-3. 부팅 자동시작 스크립트 (Termux:Boot)

`~/.termux/boot/start-tailscale.sh`:
```sh
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
proot-distro login ubuntu -- bash -c '
  tailscaled --tun=userspace-networking &
  sleep 2
  tailscale up --auth-key tskey-XXXX --ssh
'
```

### 4-4. ⚠️ userspace 모드의 한계 (반드시 알아야 함)

`--tun=userspace-networking`은 **`tailscale0` 인터페이스를 만들지 않는다.**
- ❌ `ping 100.x.x.x` / tailnet IP 직접 접속 — **불가**
- ✅ `tailscale ssh` / `tailscale serve` — 로컬 백엔드 직접 사용, **가능**

→ 돌봄 원격 접속은 **직접 IP가 아니라 `tailscale ssh` 또는 `tailscale serve`(포트 노출)** 로 가야 한다.

---

## 5. "절대 안 깨질 것" 원칙 — 하트비트/워치독

CONSTITUTION.md의 돌봄 성공 기준은 **"절대 안 깨질 것"**.
삼성이 극단 상황(메모리 압박 등)에선 여전히 앱을 죽일 수 있으므로,
**"안 죽게 하는 것" + "죽으면 알아차리는 것"** 두 축이 필요하다.

기존 자산을 재활용:
- `care-daemon.sh` (매 15분 크론) + `_notebook/health/*.json` + `_notebook/watchdog-state.json`

설계(예정):
- **하트비트:** 데몬이 주기적으로 텔레그램/헬스체크에 "살아있음" 신호.
- **사망 감지:** 일정 시간 신호 없으면 "데몬 죽음" 경고 발송.
- 효과: "연결 끊겨 SSH도 안 되는데 알 방법이 없음" → "텔레그램으로 '죽었어' 알림 옴".

---

## 6. 실행 단계 (지금 당장 → 영구 자동화)

### 지금 (수동, 검증용)
```bash
tailscaled --tun=userspace-networking &
sleep 2
tailscale up --auth-key tskey-XXXX --ssh
tailscale status          # 노드가 tailnet에 뜨는지 확인
```

### 영구 자동화 (돌봄 데몬으로 승격)
1. 관리콘솔에서 **재사용 가능한 auth key** 발급 (만료 정책 확인)
2. Termux:Boot 설치 + `~/.termux/boot/start-tailscale.sh` 배치
3. 안드로이드 체크리스트(§4-2) 2~6번 완료
4. 하트비트/워치독을 `care-daemon.sh`에 통합
5. 재부팅 테스트로 자동시작 체인 검증

---

## 7. 남은 리스크 / 열린 질문

- **Termux 네이티브 vs proot:** 돌봄 핵심 경로는 "절대 안 깨질 것"이 목표이므로,
  glibc/proot 겹층을 빼고 **Termux에 `pkg install tailscale`로 네이티브 실행**이
  더 견고할 수 있음(설치 가능 여부 실기 확인 필요). 기존 `care-daemon.sh`도
  Termux 네이티브 철학이라 방향 일치. → 다음 스터디 주제.
- **auth key 만료 주기** → 재사용/만료 없음 정책 확인 필요.
- **userspace 모드 성능/호환성** — `tailscale serve` 포트 노출 실기 테스트 필요.
- **헬레나 누나가 직접 조작 가능한가** — 재부팅 시 자동복구가 전제.

---

## 8. 다음 단계

- [ ] Termux 네이티브 Tailscale vs proot Tailscale 결정 (돌봄 경로 최적화)
- [ ] auth key 발급 + `tailscale up --ssh` 실기 연결 검증
- [ ] Termux:Boot 자동시작 + Phantom process killer 해제
- [ ] 하트비트 워치독을 `care-daemon.sh`에 통합
- [ ] 재부팅 → 자동복구 사이클 테스트

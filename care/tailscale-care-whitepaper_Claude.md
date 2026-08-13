# 돌봄 시스템 백서 — Tailscale 인바운드 채널 (완결판)

> 작성: 2026-08-13 · 작성자: `_Claude` (출판부)
> 위치: `care/` (트랙 1 돌봄 데몬)
> 상태: **✅ 완결** — 인바운드(원격접속) 채널 구축·ACL 단방향·부팅 자동화·수동 체크까지 전부 확정
> 본 문서는 `tailscale-care-daemon_Claude.md`(진단 상세)·`tailscale-situation-report_Claude.md`(계정 불일치 보고)·`_notebook/99-devlog.md` §84~§88 을 하나로 합친 **최종 단일 백서**다. 이 문서가 최신 상태의 기준.

---

## 0. 한 줄 요약 (TL;DR)

돌봄 시스템에는 두 축이 필요하다.
- **아웃바운드** — 폰이 "밖으로" 보고 (텔레그램): `care-daemon.sh` (기존 스크립트, 현재 크론 미등록 → 수동)
- **인바운드** — 간병인이 "안으로" 들어옴 (원격 셸·제어): **Tailscale** (이번에 완성)

기존엔 보고만 있고 손이 없었다. 이제 박씨가 어디서든 `tailscale ssh`로 누나 폰에 들어올 수 있고, 반대로 누나 폰은 밖으로 나가지 못한다(**ACL 단방향**).

```
돌봄 시스템 = 아웃바운드(텔레그램 보고) + 인바운드(Tailscale 원격 접속)
```

---

### 용어 정리 — "데몬"은 상주(24시간 RAM)를 뜻한다

이 시스템에서 정확한 용어는 셋으로 나뉜다:

| 용어 | 대상 | 성격 |
|------|------|------|
| **상주 데몬** | `tailscaled` | 24시간 RAM 상주 (진짜 데몬은 이것 하나뿐) |
| **미사용 스크립트(크론 미등록)** | `care-daemon.sh` | 아웃바운드 보고용이었으나 크론 미등록 — 현재 수동으로만 (2026-08-13) |
| **온디맨드 체크** | `tailscale-check.sh`·`phone-health.sh` | 요청 시에만 실행 (상주 아님) |

> "온디맨드 데몬"은 형용모순. 따라서 전체를 가리킬 땐 "데몬"이 아니라 **"돌봄 시스템"**으로 통일한다.

---

## 1. 최종 확정 상태 (2026-08-13)

| 항목 | 값 |
|------|-----|
| tailnet | `REDACTED@github` (박씨 GitHub 망) — **계정 통일 완료** |
| 노드 1 | `helena-proot` · `100.87.229.125` · glibc/proot · 포트 **41641** · `tag:helena` |
| 노드 2 | `helena-android` · `100.97.231.3` · Termux(bionic) · 포트 **41642** · `tag:helena` |
| 박씨 기기 | 5대 (windows·linux·Tab S9·S25 Ultra 등) — 전부 같은 망 |
| ACL | **단방향** — 박씨→S21 허용, S21→밖 차단 (`grants` + `ssh` + `tagOwners`) |
| Phantom killer | **해제** — `getprop`로 `false` 확인 |
| 부팅 자동화 | `~/.termux/boot/start-tailscale-boot.sh` — 노드 2개 자동 기동 |
| 상태 체크 | `care/tailscale-check.sh` — on-demand (상주 없음) |
| SSH | `tailscale ssh` 광고 중 — 박씨 접속 가능 |

---

## 2. 아키텍처 — 노드 2개를 나눈 이유

한 폰(S21)에 Tailscale 클라이언트가 **2개** 있다. 둘을 나눈 건 **차등 진단** 때문이다.

| 노드 | 정체 | 역할 |
|------|------|------|
| `helena-android` (Termux, bionic) | 안드로이드 네이티브 | **기기 생존 신호** — proot 겹층 없이 가장 견고 |
| `helena-proot` (glibc) | proot Ubuntu | **작업실 셸** — 실제 원격 조작용 |

- `helena-android`가 온라인 = **폰 자체는 살아있음** (방전 아님).
- `helena-proot`가 온라인 = **작업실 셸 접속 가능**.
- 둘 다 죽음 = 폰 방전 or 데몬 크래시 → 긴급.

> ⚠️ **이 2노드 분리는 수혜자(누나 S21) 측에만 적용.** 간병인(박씨) 기기는 단일 노드로 충분.
> 이 구분이 ACL 단방향(`tag:helena` 보호측 / `autogroup:member` 접속측)의 근거다.

```
[박씨 기기 5대]  ──(ACL 단방향: 들어감만 허용)──▶  [누나 S21]
  autogroup:member                                        ├─ helena-android (Termux, 41642)
  (태그 없음, 계정 소유)                                   └─ helena-proot   (proot,  41641)
                                                          둘 다 tag:helena
  [누나 S21]  ──✗ (아웃바운드 차단)──▶  [박씨 기기]
```

---

## 3. 왜 안 됐었나 — 원인 4개 (이력 압축)

1. **배터리 최적화(Doze)** 가 Termux를 죽임 → "제한 없음"으로 해결 ✅
2. **proot 권한 0개**(CapEff=0) → 기본 TUN 모드 불가 → `--tun=userspace-networking` 필수 ✅
3. **노드 해제(deauthorized)** → auth key로 재승인 ✅
4. **계정 불일치** — proot이 Google(`REDACTED`)에, 박씨 기기가 GitHub(`REDACTED@`)에 갈라짐 → **GitHub 망으로 통일** ✅

---

## 4. 보안 모델 — ACL 단방향

**목적:** 누나 폰은 "들어오는 접속만 받고, 밖으로 나가는 접속은 전부 차단". 유출·역이동 방지.

적용된 ACL (최신 `grants` + `ssh` 스키마):

```json
{
  "tagOwners": { "tag:helena": ["autogroup:admin"] },
  "grants": [
    { "src": ["autogroup:member"], "dst": ["*"], "ip": ["*"] }
  ],
  "ssh": [
    { "action": "check",  "src": ["autogroup:member"], "dst": ["autogroup:self"], "users": ["autogroup:nonroot", "root"] },
    { "action": "accept", "src": ["autogroup:member"], "dst": ["tag:helena"],      "users": ["autogroup:nonroot", "root"] }
  ]
}
```

| 규칙 | 의미 |
|------|------|
| `grants: member → *` | 박씨 기기는 전부 접근 가능 (**절대 안 잠김**) |
| `ssh: member → tag:helena` | 박씨 → S21 SSH 허용 |
| (helena는 src에 없음) | `tag:helena` 노드는 아웃바운드 전부 차단 = 단방향 |

**검증:** `helena-proot`의 netmap에 `helena-android`가 안 보임(tag↔tag 차단) + 박씨 기기로의 `tailscale ssh`가 timeout(패킷 드랍) = 단방향 시행 확인.

> ⚠️ `tailscale ping`은 disco 프로토콜이라 ACL을 우회해서 "pong"이 나온다 — 정상. 실제 차단은 데이터 평면(SSH timeout)으로 확인해야 한다.

---

## 5. 핵심 기술 사실 (절대 잊지 말 것)

- **proot은 권한 0개** → `--tun=userspace-networking` **필수** (v1.102.2 실측 동작).
- **userspace 모드는 `tailscale0` 없음** → 직접 IP(`ping`/`ssh IP`) 불가, `tailscale ssh`/`tailscale serve`로만 접속.
- **재부팅엔 인증키 불필요** — 저장된 노드키가 자동 재접속 (실측 검증). 인증키는 노드 해제 시에만 안전장치.
- **Termux bionic 바이너리는 proot에서 exec 가능** — `tailscale` CLI 공유.

---

## 6. 구성 파일 지도

| 파일 | 역할 |
|------|------|
| `care/care-daemon.sh` | 아웃바운드 보고 스크립트 — 배터리·온도·GPS·움직임 → 텔레그램 (크론 미등록, 현재 수동) |
| `care/care.conf` | 아웃바운드 임계값 (배터리 15%, 온도 45°C 등) |
| `care/start-tailscale-boot.sh` | 부팅 시 노드 2개 자동 기동 (Termux:Boot → `~/.termux/boot/`) |
| `care/tailscale-check.sh` | **on-demand 상태 체크** (상주 없음, `--telegram` 선택) |
| `.secrets.env` | `TAILSCALE_AUTH_KEY`/`TAILSCALE_API_KEY` (gitignore, **커밋 금지**) |

---

## 7. 키 관리 — 만료 리마인더

| 키 | 만료 | 처리 |
|----|------|------|
| auth key `k51Jyn…` | **2026-11-11** (90일) | **수동 갱신 필요** — 리마인더 대상 |
| API key `knHqNem…` | **2026-11-11** (90일) | **수동 갱신 필요** — 리마인더 대상 |
| 노드 키 | 2027-02 (6개월) | tailscaled가 자동 갱신 — 조치 불필요 |

- 키는 `.secrets.env`(gitignore)에만 저장. **GitHub 커밋 금지.**
- 갱신은 관리콘솔(Settings → Keys)에서. 만료 전 새 키 발급 → `.secrets.env` 갱신.

---

## 8. 운영 — 원할 때 상태 체크

상주 워치독 없음 (RAM 상주 기피). 대신 on-demand:

```bash
bash care/tailscale-check.sh            # 상태 확인 (8항목)
bash care/tailscale-check.sh --telegram # + 텔레그램 보고
bash phone-health.sh                    # 기존 하드웨어 헬스체크
```

체크 8항목: proot/Termux tailscaled 생존 · backend Running · 온라인 · 태그 · SSH 광고 · 박씨 기기 가시성 · helena-android tailnet 등록.

결과: `_notebook/health/tailscale-*.json`(이력) + `tailscale-latest.json`(최신, 대시보드용 고정 경로).

---

## 9. 남은 일 / 리스크

- [ ] **재부팅 후 Phantom killer 값 유지 확인** — `getprop persist.sys.fflag.override.settings_enable_monitor_phantom_procs`가 재부팅 후에도 `false`인지.
- [ ] **auth/API 키 갱신** — 2026-11-11 전에 (수동).
- [ ] (선택) 대시보드 — `tailscale-latest.json`을 읽는 정적 페이지 (원하면).
- 리스크: 삼성이 극단 메모리 압박 시 여전히 앱을 죽일 수 있음 → 주기적으로 `tailscale-check.sh` 돌려 확인.

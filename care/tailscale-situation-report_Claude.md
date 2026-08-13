# 📡 Tailscale 진단 — 지금 뭐가 문제인가

> 2026-08-13 · 한 장 요약 · 작성 `_Claude`

## 결론 (한 줄)

박씨가 S21에 SSH로 못 들어오는 이유는 단 하나 —
**박씨 기기 5개(GitHub 망)와 S21 proot(Google 망)가 서로 다른 tailnet에 있어서 서로 안 보인다.**

## 지금 현황 (계정 지도)

한 폰(S21)에 tailscale 클라이언트가 **2개** 있고, 서로 다른 망에 붙어 있다.

| 장치 | 로그인 계정 | 망 | 상태 |
|------|-------------|-----|------|
| S21 proot | `REDACTED` (누나 Google) | Google 망 | ✅ 온라인 · SSH · owner |
| S21 Termux | `REDACTED@github` (박씨 GitHub) | GitHub 망 | ❌ 기기 0개 · 데몬 정지 |
| **박씨 기기 5개** | `REDACTED@github` (박씨 GitHub) | GitHub 망 | ✅ 있음 |

→ **박씨 기기 5개가 있는 GitHub 망에 S21이 없고, S21이 있는 Google 망에 박씨가 없다.**

## 왜 이렇게 됐나 (삽질 이력 압축)

1. 배터리 최적화 → 데몬 죽음 ✅ 해결
2. proot 권한 0 → TUN 불가 → `--tun=userspace-networking` ✅ 해결
3. 노드 해제(deauthorized) ✅ 해결
4. **계정 불일치** — 누나를 GitHub이 아니라 Google(`REDACTED`)로 로그인함
5. → **GitHub 망(박씨) vs Google 망(S21)으로 갈라짐** ← 지금 여기

## 뭐가 문제인가 (3줄)

- 박씨 기기 5개가 있는 **GitHub 망**에 S21이 없다.
- S21이 있는 **Google 망**에 박씨 기기가 없다.
- 서로 다른 tailnet = SSH 연결 불가. **"안 잡힘"의 진짜 정체.**

## 해결 — 결정 1개만 하면 됨

| 선택 | 방법 | 장점 | 단점 |
|------|------|------|------|
| **A. GitHub 망 통일** | S21을 `REDACTED@github`에 등록 | 박씨 5기기 이미 있음 → 바로 SSH | 계정 = 박씨 명의 |
| B. Google 망 통일 | 박씨 5기기를 누나 Google 망으로 | 누나 명의 | 5기기 이전 필요 |

**추천 A** — 돌봄은 "절대 안 깨질 것"이 1순위. 박씨 기기가 이미 있는 곳에 S21을 붙이는 게 제일 빠름.

## 결정 후 남은 일

1. 키 2개 회수 (평문 노출) — 관리콘솔에서 수동
2. Termux:Boot 자동시작
3. ACL 단방향 (박씨 → 누나 S21만)

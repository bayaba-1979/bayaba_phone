# 📡 Tailscale 돌봄 데몬 — 상황 보고 (2026-08-13)

## 결론 한 줄
돌봄 데몬의 원격 접속 채널(Tailscale)이 **계정 불일치**로 안 잡히고 있었다.
안드로이드 앱은 Google, proot은 GitHub에 붙어 서로 다른 망(tailnet)에 있었음.

## 원인 4가지 (진단 완료)
1. ✅ 배터리 최적화 → 데몬 살해 (해결: "제한 없음" 변경)
2. ✅ proot 권한 0개 → TUN 불가 (해결책: `--tun=userspace-networking`)
3. ⚠️ 노드 해제 → 재인증 필요
4. 🔴 **계정 불일치** — Android=Google / proot=GitHub → 서로 다른 tailnet

## 두 계정 정리
| | 안드로이드 앱 | proot |
|---|---|---|
| 로그인 | Google `REDACTED` | GitHub `REDACTED@github` |
| 상태 | 접속 중 | Logged out |

## 지금 할 일 (1개)
**proot을 Google 계정으로 재로그인** → 같은 tailnet 진입
```bash
tailscale up   # 로그인 URL → Google로 로그인
# 영구화: tailscale up --auth-key tskey-... --ssh
```

## 실행 계획
1. proot → Google 재로그인 (대기)
2. `--ssh` 켜고 tailnet 노드 확인
3. 재사용 인증키 → 부팅 자동화 (OAuth 반복 제거)
4. 안드로이드 자동시작 체크리스트 + 하트비트 워치독

## 참고
- 백서: `care/tailscale-care-whitepaper_Claude.md`
- 진단 상세: `care/tailscale-care-daemon_Claude.md`

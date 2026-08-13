# Tailscale 돌봄·케어 솔루션 리서치 — 카테고리 & 오픈 이슈

> **리서치 일시:** 2026-08-12  
> **출처:** Tailscale 공식 블로그, Hacker News, XDA Developers, Reddit, Lawrence Systems  
> **목적:** Tailscale 기반 돌봄·케어 커뮤니티 패턴을 수집하고, 헬레나 케어 시스템과의 접점 및 확장 방향을 정리

---

## 솔루션 카테고리

### 🩺 A. 원격 진단 및 수리 (Remote Diagnostics & Fix)

**커뮤니티 패턴:** 부모님/가족 기기 문제 발생 → Tailscale SSH/VNC 접속 → 원격 수리

| 사례 | 출처 | 헬레나 적용 |
|------|------|------------|
| 81세 어머니 PC 원격 지원 (SSH + screen share) | HN | ✅ S21 SSH 진단 — 이미 보유 |
| RustDesk + Tailscale 원격 데스크톱 | YouTube 튜토리얼 | ⚠️ GUI 필요할 때 검토 |
| "Mail a Node" — 라즈베리파이 사전설정 택배 배송 | Tailscale 공식 블로그 | ❌ 해당 없음 (이미 S21에 설치) |

**헬레나 오픈 이슈:**
- [ ] S21 SSH 진단 원라이너 (`care-ssh.sh`) — 한 줄로 S21 상태 확인 + 로그 덤프
- [ ] WSL에서 S21 care-daemon 원격 재시작 커맨드


### 📊 B. 건강 모니터링 및 알림 (Health Monitoring & Alerts)

**커뮤니티 패턴:** 연결된 기기의 상태를 주기적으로 확인, 이상 시 알림

| 사례 | 출처 | 헬레나 적용 |
|------|------|------------|
| 치매 가족 connected device 모니터링 | Reddit | ✅ care-daemon.sh — 이미 보유 |
| 배터리·네트워크·디스크 health check | 일반 패턴 | ✅ phone-health.sh — 이미 보유 |
| Telegram 봇 알림 연동 | 커뮤니티 | ✅ tg.sh — 이미 보유 |

**헬레나 오픈 이슈:**
- [ ] Tailscale heartbeat 모니터링 — S21이 tailnet에서 사라지면 Telegram 긴급 알림
- [ ] care-daemon에 "원격 진단 모드" 추가 — WSL이 주기적으로 S21 health pull
- [ ] S25(리모컨) 대시보드 — Telegram 봇으로 `/health` → S21 상태 즉시 응답


### 🗣️ C. 음성·커뮤니케이션 (Voice & Communication)

**커뮤니티 패턴:** 파일 공유, 미디어 스트리밍, 메시징

| 사례 | 출처 | 헬레나 적용 |
|------|------|------------|
| Taildrop — AirDrop급 파일 공유 | Tailscale 공식 | ⚠️ 모델 전송 대안으로 검토 |
| Jellyfin/Plex 가족 미디어 서버 | XDA | ❌ 해당 없음 |
| 가족 사진 백업 자동화 | 일반 패턴 | ⚠️ 음성 파일 백업으로 대체 |

**헬레나 오픈 이슈:**
- [ ] `synth_voice()` — S25 → WSL 원격 더빙 명령 → S21 자동 전송
- [ ] Taildrop으로 S21↔WSL 파일 전송 벤치마크 (vs scp vs curl)
- [ ] 누나 폰에서 음성 메시지 → WSL에서 텍스트 변환 → Boss에게 Telegram


### 🔒 D. 보안 및 접근 제어 (Security & Access Control)

**커뮤니티 패턴:** 가족 구성원별 ACL, 기기별 접근 제한

| 사례 | 출처 | 헬레나 적용 |
|------|------|------------|
| Single account for trusted family | HN | ✅ Boss 계정 통일 — 완료 |
| ACL로 기기 간 접근 제한 | Tailscale docs | ⚠️ 설정 필요 |
| Exit node로 안전한 트래픽 라우팅 | Tailscale 공식 | ⚠️ WSL exit node 설정 필요 |

**헬레나 오픈 이슈:**
- [ ] ACL 정책 수립: S21은 WSL·S25만 접근 가능, 외부 노드와 통신 차단
- [ ] WSL exit node 설정 — S21의 모든 외부 트래픽을 WSL 경유로 보호
- [ ] S21 Tailscale 연결 끊김 시 Fallback: WiFi Direct 또는 Bluetooth 파일 전송


### 🏗️ E. 인프라 및 확장 (Infrastructure & Scaling)

**커뮤니티 패턴:** 자체 호스팅, 멀티 디바이스 오케스트레이션

| 사례 | 출처 | 헬레나 적용 |
|------|------|------------|
| Headscale (self-hosted Tailscale) | GitHub | 🔮 장기 — Tailscale SaaS 의존성 제거 |
| Subnet routing | Tailscale docs | ⚠️ 추후 검토 |
| GitHub Actions fallback | 커뮤니티 | ⚠️ WSL 다운 시 cold standby |

**헬레나 오픈 이슈:**
- [ ] Tailscale 완전 장애 시 대체 통신 경로 설계 (WiFi Direct? Bluetooth?)
- [ ] GitHub Actions를 cold standby로 — WSL 꺼졌을 때 기본 진단·알림만 유지
- [ ] S21 → 태블릿 → WSL 멀티홉 라우팅 가능성 검토


### 🤖 F. AI 에이전트 통합 (헬레나 고유 카테고리)

**커뮤니티에 없는, 우리가 개척 중인 영역.**

| 컴포넌트 | 상태 | 비고 |
|----------|------|------|
| ParksyTTS (GPT-SoVITS) | ✅ 보유 | WSL에서만 실행 가능, CPU 471s |
| Edge TTS + RVC 파이프 | 🔄 구축 중 | WSL에서 RVC 변환 → S21 전송 |
| care-daemon.sh | ✅ 운영 중 | 15분 주기 health check |
| phone-health.sh | ✅ 운영 중 | 등급 A/B/C 진단 |
| Telegram 봇 (5종) | ✅ 운영 중 | 감지 레이어 |
| `synth_voice()` 원격 호출 | 🔜 예정 | S25 → WSL → S21 |

---

## 카테고리별 성숙도 요약

```
Category        Community    Helena     Gap
─────────────────────────────────────────────
A. 원격 진단     ████████    ████░░    SSH 원라이너, 재시작 커맨드
B. 건강 모니터링 ██████░░    ██████░    Heartbeat 모니터링
C. 음성·커뮤     ████░░░░    ██░░░░    synth_voice, Taildrop 벤치
D. 보안·접근     ████████    ██░░░░    ACL, Exit node
E. 인프라·확장   ██████░░    ██░░░░    Fallback, 멀티홉
F. AI 에이전트    (없음)      ████░░    우리가 선구자
```

---

## 우선순위 로드맵

### 즉시 (이번 주)
1. [ ] WSL Tailscale IP 확인 → S21 ↔ WSL 연결 완료
2. [ ] RVC 모델 파일 전송 (parksy_rvc.pth, parksy_rvc.index)

### 단기 (이번 달)
3. [ ] `care-ssh.sh` 원라이너 — S21 상태 원격 진단
4. [ ] Tailscale heartbeat 모니터링 → Telegram 알림
5. [ ] `synth_voice()` S25 → WSL → S21 파이프라인 실증

### 중기 (다음 달)
6. [ ] ACL 정책 적용 — S21 접근 제한
7. [ ] WSL exit node 설정
8. [ ] Taildrop 전송 속도 벤치마크

### 장기
9. [ ] GitHub Actions cold standby — WSL 장애 시 기본 알림 유지
10. [ ] Headscale 검토 — 자체 호스팅으로 SaaS 의존성 제거

---

_마지막 갱신: 2026-08-12 · 리서치: Claude Code · 검증: Boss_

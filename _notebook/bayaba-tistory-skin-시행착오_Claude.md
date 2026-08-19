# 티스토리 스킨 적용 — 시행착오 기록 (bayaba 이식)

> 2026-08-19 · Claude Code · bayaba(마왕가족) 보일러플레이트 이식 세션
> 목적: helena_phone → bayaba 5개 티스토리 블로그에 스킨(skin-premium.css) 적용
> 결론: **미완료.** 카카오 로그인 캡차(지도 클릭형)를 이 머신(화면 없는 proot)에서 풀 수 없어 중단.

---

## 1. 한 줄 결론

코드는 전부 bayaba에 맞게 이식됐다 (`batch_apply.py` dry-run 통과). **딱 하나, 카카오 로그인 시 뜨는 "지도 클릭형 캡차"를 화면 없는 이 머신에서 풀 수 없어서** 스킨 적용만 실패.

## 2. 뭘 하려 했나

`python3 tistory-naver/batch_apply.py` 실행 → 카카오 1계정 로그인 → 5개 블로그에 ① Whatever 스킨 전환 ② skin-premium.css + 레이아웃 + 테마 주입.

## 3. 시행착오 타임라인 (실패 → 원인 → 해결)

| # | 시도 | 결과 | 원인/해결 |
|---|------|------|-----------|
| 1 | `pip install playwright` | ❌ "No matching distribution" | Termux pip(3.14 bionic)이 PATH에 섞임 → `/usr/bin/python3 -m pip` 로 명시 |
| 2 | `/usr/bin/python3 -m pip install` | ❌ "No module named pip" | Ubuntu python에 pip 없음 → `apt install python3-pip` |
| 3 | pip install playwright | ❌ "externally-managed-environment" | PEP 668 → `--break-system-packages` |
| 4 | `apply_skin.py` 실행 | ❌ 카카오 재로그인 실패 | 이 스크립트는 **구식(CSS 전용)**. 정식은 `batch_apply.py` |
| 5 | headless 로그인 반복 | ❌ "답해 주세요" 캡차 | 헤드리스 반복 → 카카오 봇감지 유발 |
| 6 | 캡차 div `#dkaptcha-*` 확인 | ❌ 비어 있음(childCount=0) | **headless에선 dkaptcha iframe이 로드 안 됨** |
| 7 | "비밀번호 일치하지 않습니다" | ❌ 비번 오류로 오판 | 카카오는 봇감지 시 오류 메시지가 일정하지 않음. 실제 비번은 정확했음 |
| 8 | `headless=False` + `xvfb-run` | ✅ 캡차 iframe 로드 | dkaptcha iframe(`dkaptcha.kakao.com`)이 정상 로드됨 |
| 9 | 캡차 정체 파악 | ✅ 확인 | **지도 클릭형**: "아래 장소를 지도에서 눌러주세요" + 지도이미지(512x256)에서 POI 라벨 클릭 |
| 10 | OCR로 POI 좌표 추출 | ❌ 실패 | 지도 라벨이 기울어지고 노이즈 → tesseract OCR 불가 |

## 4. 최종 막힌 지점 (핵심)

카카오 캡차 = **지도 클릭형** (dkaptcha). 문제는 "코끼리어린이공원", "학익프라자" 등 **매번 바뀌는 장소명**. 지도 이미지에서 그 POI 라벨을 **시각적으로 찾아 정확한 좌표를 클릭**해야 통과.

이 머신은:
- 화면 없음 (DISPLAY 비어있음, X11 소켓 없음, RustDesk/VNC 없음)
- `xvfb` 가상화면은 만들 수 있지만 **사람이 볼 수 없음**
- OCR로도 지도 라벨 판독 불가 (기울기/노이즈)

→ **사람의 시각 판단이 필요한 캡차라, 화면 없는 이 머신에서 자동으로 못 품.**

## 5. 정답 (보일러플레이트가 이미 말한 것)

카카오 로그인 = **수동 하한(자기 것 1회)**. `login.cjs` 181줄 `headless: false`가 그 증거 — **화면 있는 기기에서 사람이 캡차를 직접 클릭**해야 한다.

해결책 (우선순위):
1. **화면 있는 기기(누나 Galaxy S21, 태블릿)에서 `batch_apply.py` 실행** → 지도 캡차를 직접 클릭 → 성공 → `cookies/`에 TSSESSION 영속화.
2. **이미 로그인 성공한 기기의 `cookies/{account}_state.json` 을 이 머신으로 복사** → 캡차 없이 재사용.
3. 이 머신에 **VNC/x11vnc + 클라이언트** 설치해서 화면 공유 → 원격으로 캡차 클릭.

## 6. 재발 방지 체크리스트

- [ ] 카카오/티스토리 로그인 = 화면 있는 기기에서만. headless/CI 금지.
- [ ] `which pip` / `which python3` 먼저 확인 (Termux bionic vs Ubuntu glibc ABI)
- [ ] pip 설치 시 `--break-system-packages` + `/usr/bin/python3 -m pip`
- [ ] 스킨 적용은 `batch_apply.py` (apply_skin.py는 구식)
- [ ] 캡차 반복 시도 금지 — 쿨다운만 늘어남
- [ ] "비밀번호 틀림" 메시지를 그대로 믿지 말 것 — 봇감지 오류일 수 있음

## 7. 성공한 것 (이 세션에서)

- Python playwright 설치 (Ubuntu glibc, aarch64 manylinux wheel)
- `THEME_MAP` bayaba 5계정(hub/jokbal/chicken/installation/mynote) 이식
- `batch_apply.py` SKIP 제거 + cookie 프로파일 `hub`로 통일
- GitHub 5레포 + Pages, YouTube 자동화 + 플레이리스트 5개, 티스토리 블로그 매칭
- 카카오 캡차의 정체(dkaptcha 지도 클릭형)와 로드 조건(headless=False) 완전 규명

---

*agent _Claude · 2026-08-19 · 티스토리 스킨 적용 시행착오 종합*

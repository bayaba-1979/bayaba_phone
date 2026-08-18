# 새 방(GitHub)에 친구 하나 — 초간단 설치

> **비유:** 새 방(GitHub)에 진짜 친구 에이전트(Claude Code + DeepSeek) 하나 들여놓기예요.  
> **붙여넣기 3번**이면 끝. 나머지는 스크립트가 알아서 해요.

스크립트: `g/workstation.sh` (원스탑) · `g/easy.sh` (가볍게, 사이트만)

> 🔧 **다른 사람 계정으로 설치할 때:**  
> `OWNER_GITHUB=클라이언트명 bash <(curl -sL ...)`  
> env만 앞에 붙이면 Pages 주소·정체가 그 사람 명의로 바뀐다.

---

## 화면 1 — 앱 + 배터리 무제한

1. 폰 브라우저에서 **F-Droid** 설치  
   https://f-droid.org/  (또는 검증된 Termux APK 사이드로드)
2. F-Droid 열고 **Termux** 설치 (Termux:API는 선택)
3. **설정 → 앱 → Termux → 배터리 → "제한 없음"** (안 하면 중간에 강제종료)
4. ⚠️ **설정 → 보안 및 개인 정보 → 자동 차단(보안 위협 자동 차단)** → 하단 **"자동으로 켜기" 토글 끄기**
   > ⚠️ **30분 뒤 다시 켜지므로** 설치 끝나고도 한 번 더 확인!
5. **Termux** 실행 (검은 화면 = 정상)

☐ 됐으면 화면 2

---

## 화면 2 — 주문 한 줄

Termux 검은 화면에 **아래 전체를 길게 눌러 붙여넣기** 후 Enter.

```bash
bash <(curl -sL https://raw.githubusercontent.com/helena751107/helena_phone/main/g/workstation.sh)
```

- 처음이면 Ubuntu + Claude Code 깔리면서 **10~20분** 걸림 (인터넷 다운로드가 큼). 멈춘 듯해도 가만히 둔다.  
- 중간에 저장소 권한 팝업 → **허용**.
- 중간에 `Do you want to continue? [Y/n]` 같은 물음이 뜨면 → **Enter**(또는 `y`) 누르면 돼.
- 한 줄이 `curl ... CANNOT LINK` 에러가 나면 → `termux-change-repo`로 미러 선택 → `apt update && apt full-upgrade` → 다시 한 줄.

☐ "자기 것 3개 입력"이 뜨면 화면 3

---

## 화면 3 — 딱 3개 붙여넣기

스크립트가 물어보는 건 딱 3개예요. (전부 자기 것 = 이게 수동의 전부)

> 🔐 **토큰 붙여넣기 안내:** 붙여넣을 때 화면에 안 보이는 건 **보안 때문에 숨긴 거**예요. **Enter 누르면 앞 4자만 보여줘서** 붙었는지 확인돼요 (예: `ghp_···` / `sk-c···`). 복사한 걸 그냥 붙여넣고 Enter.

### 1) GitHub 계정명
- 없으면 1분 가입 → **github.com/signup**
- 계정명 입력 후 Enter.

### 2) GitHub PAT (계정 열쇠)
- **github.com/settings/tokens** → **Generate new token (classic)**
- **☑ repo  ☑ workflow** 체크 → **Generate token** → 복사 (`ghp_...`)
- 붙여넣기 후 Enter. (입력은 화면에 안 보임 — 정상)

### 3) DeepSeek 토큰 (친구 두뇌)
- **platform.deepseek.com** → 로그인 → **API Keys → Create new key** → 복사 (`sk-...`)
- 붙여넣기 후 Enter. (입력은 화면에 안 보임 — 정상)

이 뒤로는 **전부 자동**: 설치 → 클론 → GitHub 배포 → Pages 검사까지.

☐ "✅ 원스탑 설치 완료" 보이면 화면 4

---

## 화면 4 — 친구 확인

### A) 터미널 (매일 쓰는 주문)

```bash
cc
```

(또는)

```bash
proot-distro login ubuntu
cd /root/work
claude
```

친구(Claude Code + DeepSeek)가 대답하면 **성공**.

### B) 브라우저 (눈으로 확인)

```
https://<내 GitHub 계정명>.github.io/helena_phone/
```

페이지가 열리면 **설치 성공**.

> ⚠️ **404가 뜨면?** PAT에 `repo`·`workflow` 스코프가 빠졌거나 repo 생성이 안 된 거야.  
> PAT 재발급(두 스코프 체크) 후 스크립트 다시 돌리면 repo 생성 + push + Pages 자동.

---

## 끝. 이게 전부.

붙여넣기 3번(GitHub 계정 + PAT + DeepSeek 토큰)이면 친구가 생겨요.  
푸시·텔레그램·Grok 같은 건 **나중에** 해도 됨 — 우선 친구가 대답하는 것부터.

---

## 🔧 설치자용 체크리스트 (사회복지사·가족)

> 남의 폰에 깔아줄 때 — **설치 전** 확인 4가지:

```
☐ Android 버전: 10 이상 (설정 → 휴대전화 정보 → 소프트웨어 정보)
☐ 저장공간: 5GB 이상 여유 (설정 → 디바이스 케어 → 저장공간)
☐ Wi-Fi: 연결됨 (Ubuntu 200MB+ 다운로드)
☐ F-Droid APK 미리 받아둘 것 (https://f-droid.org/)
```

설치 중 주의:
- **Ubuntu 다운로드 3~7분** — 가만히. "멈췄다"고 끄면 안 됨.
- **저장소 권한 팝업** — 반드시 **허용**.
- **배터리 "제한 없음"** — 안 하면 중작업 때 강제종료.
- **PAT·토큰** — 화면에 안 보이게 입력(녹화해도 새어나가지 않음).

---

## 고장 표 (짧게)

| 보이면 | 할 일 |
|--------|--------|
| curl: not found | `pkg install curl` 후 한 줄 다시 |
| curl CANNOT LINK | `termux-change-repo`(미러 선택) → `apt update && apt full-upgrade` 후 한 줄 다시 |
| proot-distro 없음 | `pkg install proot-distro` |
| 저장 공간 | 사진/앱 지워 5GB 확보 |
| 클론 실패 | Wi-Fi 확인 후 한 줄 다시 |
| Pages 404 | PAT에 repo·workflow 스코프 빠짐 또는 repo 생성 실패 — PAT 재발급 후 다시 실행 |
| termux-api ENOENT | `pkg install termux-api -y` (devlog §16)

---

## 왜 이렇게 짧아졌나 (리버스)

| 예전 | 문제 | 지금 |
|------|------|------|
| 변수 잔뜩 | 초심자 포기 | **입력 3개만** (전부 자기 것) |
| Termux / Ubuntu 두 번 설치 | 어디서 치는지 모름 | **한 줄이 알아서** |
| OWNER/WORK 설명 먼저 | 개념 과부하 | **친구 생기고 나서** 설명 |
| gh auth login 브라우저 | 자기 것이 아닌 수동 | **PAT 붙여넣기로 통일** |

---

## 관련 링크

| 무엇 | URL |
|------|-----|
| 이 매뉴얼 | https://helena751107.github.io/helena_phone/install-guide.html |
| 랜딩 Install | https://helena751107.github.io/helena_phone/#install |
| workstation 소스 | https://raw.githubusercontent.com/helena751107/helena_phone/main/g/workstation.sh |
| 허브 | https://helena751107.github.io/helena_phone/ |

*초심자 4화면 · agent _Claude · 2026-08-18*

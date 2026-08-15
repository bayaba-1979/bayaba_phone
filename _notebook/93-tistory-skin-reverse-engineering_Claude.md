# 🔬 티스토리 스킨 적용 — 리버스 엔지니어링 완전 해부

> 2026-08-15 · Claude Code (출판부) 정리 · Boss 지시: "히스토리 스킨 어떻게 적용하는지, 리버스 엔지니어링부터 전부 기록"  
> 대상: 갤럭시 S21 컨셉 블랙 스킨을 5개 티스토리 블로그에 일괄 적용하는 방법  
> 코드: `tistory-naver/` (`apply_layout.py` · `batch_apply.py` · `switch_skin.py` · `skin-premium.css` · `post.py`)

---

## 1. 결론부터 — 스킨은 "숨겨진 관리 API"로 찍어낸다

티스토리는 스킨을 고치는 **공식 REST API가 없다** (Open API는 2024년 2월 종료). 하지만 관리자 화면(스킨 편집기)의 **네트워크 요청을 관찰**하면, 브라우저가 실제로 호출하는 내부 API가 그대로 드러난다.

**핵심 3줄:**

| API | 메서드 | 역할 |
|-----|--------|------|
| `/manage/design/skin/html.json` | `GET` | 현재 스킨의 **HTML + CSS 전체**를 JSON으로 받음 |
| `/manage/design/skin/html.json` | `POST` | `{html, css, isPreview:false}` 로 **HTML+CSS 저장** |
| `/manage/design/skin/set.json` | `POST` | `{name:"pg_Whatever"}` 로 **스킨 종류 전환** |

즉, **"스킨 편집기의 저장 버튼" = `POST html.json`** 이고, **"스킨 선택기" = `POST set.json`** 이다. 로그인 세션 쿠키(`TSSESSION`)만 있으면 Playwright로 이걸 직접 때리면 된다.

> 쉽게 말하면: 티스토리 관리 화면의 "저장" 버튼 뒤에 숨은 주소를 찾아내서, 로봇이 그 주소로 직접 편지를 보내는 거야. 화면을 클릭할 필요 없이.

---

## 2. 리버스 엔지니어링 연대기 — 어떻게 찾아냈나

### 2.1 스킨 관리 API (`html.json` / `set.json`)

**관찰 방법:** 티스토리 관리 → 꾸미기 → 스킨 편집 화면에서 DevTools Network 탭을 열고 저장 버튼을 누른다. 실제로 오가는 XHR/fetch 요청 두 개가 잡힌다.

**GET 응답 구조** (예: galaxys21):
```json
{
  "html": "<!DOCTYPE html>... 전체 스킨 HTML ...",
  "css": "/* ... */ 전체 스킨 CSS ...",
  "files": [ "style.css", ... ],
  "skinname": "customize/8935375"
}
```

- `html` = 스킨 전체 HTML (티스토리 치환자 `[##_..._##]` 포함)
- `css` = 스킨 전체 CSS
- `skinname` = 현재 적용된 스킨 ID (galaxys21은 `customize/8935375`, 나머지는 `pg_Whatever`)

**POST 저장** (`html.json`): `data={html, css, isPreview:false}` → 성공 시 `200` + `/preview/skin?skin=...` 리다이렉트.

**스킨 전환** (`set.json`): `multipart={name:"pg_Whatever"}` → `200`.

**CSS 서빙 URL (캐시 무력화):** 저장하면 CSS가 다음 주소로 서빙된다.
```
https://tistory1.daumcdn.net/tistory/<skinId>/skin/style.css?_version_=<epoch>
```
`_version_` 이 epoch 타임스탬프라 **저장할 때마다 갱신 → CDN 캐시가 자동 무효화**된다. (curl로 검증 가능)

### 2.2 카카오 로그인 — "Enter는 실패한다"

**관찰:** 티스토리 로그인은 카카오 계정으로만 가능. `https://www.tistory.com/auth/login` → `a.btn_login.link_kakao_id` 클릭 → `accounts.kakao.com/login` 으로 이동.

**함정 3개:**
1. **폼이 JS SPA라 렌더 ~15-22초** (느린 폰 네트워크). `fill()`을 일찍 호출하면 빈 페이지 race로 크래시. → `#loginId--1`/`#password--2` 렌더를 폴링(최대 60s)한 뒤 채운다.
2. **`fill()` 대신 `evaluate()`로 채운다.** Playwright `fill()`이 직렬화 버그로 "Object is not JSON serializable" 크래시. 네이티브 setter + input/change 이벤트로 채움.
3. **제출은 `press("Enter")`가 아니라 submit 버튼 클릭.** Enter는 `prompt=select_account` 계정선택 화면에 막혀 실패. `button[type='submit']` 클릭 + 이후 "계속"/"동의하고 계속" 버튼 처리해야 성공.

```python
await page.locator("button[type='submit'], button.submit, .btn_g").first.click(timeout=3000)
```

**성공 판정:** URL에 `tistory.com` 포함 + `login`/`accounts.kakao` 미포함.

**⚠️ CAPTCHA:** 헤드리스 브라우저로 단시간 반복 로그인하면 카카오 봇감지 CAPTCHA("안전한 서비스 이용을 위해...")가 뜬다. **쿨다운 필요(~15-30분)** 또는 사람 수동 로그인. 하루 첫 시도는 보통 성공.

### 2.3 세션 쿠키 (`TSSESSION`) — 재실행하면 사라진다

**관찰:** 로그인 후 `TSSESSION` 쿠키가 생기는데, 이게 **세션 쿠키(`expires=-1`)** 라 Playwright `launch_persistent_context` 프로파일 디렉토리에 **영속되지 않는다**. → 매번 재실행 시 재로그인 → CAPTCHA 유발.

**해결:** 
1. 로그인 성공 후 `ctx.storage_state(path="galaxys21_state.json")` 로 저장.
2. 재실행 시 `ctx.add_cookies()`로 복원하되, `expires=-1` 인 쿠키는 `now + 7일` 로 보정해서 영속화.

```python
if c.get("expires", -1) == -1:
    c["expires"] = now + 86400 * 7
```

`batch_apply.py` · `apply_layout.py` · `post.py` 모두 이 패턴을 쓴다.

### 2.4 댓글 설정 — "마스터 끄기 토글은 없다"

**관찰:** `GET/PUT /manage/setting/comments.json` 의 설정 구조:
- `selected.allowGuestComment = "0"` → 비허용/deny
- `selected.commentWritePermission = "0"` → 로그인한 사용자만

**핵심 발견:** 티스토리는 **"아무도 댓글 못 씀" 마스터 토글이 없다.** 옵션이 `로그인한 사용자만(0)` / `비로그인도(1)` 둘뿐. → **댓글 완전 차단의 실효 수단은 CSS 숨김** `[data-tistory-react-app="Comment"] {display:none}`.

**개별 글 댓글 (발행 레이어):** 댓글 설정은 체크박스가 아니라 **TinyMCE select-menu(드롭다운)**. `button.select_btn`(텍스트 "댓글 허용") 클릭 → `.mce-menu-item:has(.mce-text:text-is('댓글 비허용'))` 클릭. `post.py _disable_comments()`에 반영 — 매 업로드 강제 적용.

### 2.5 발행 레이어 — textarea 동기화 ("빵꾸"의 근본 원인)

**관찰:** 티스토리 에디터는 실제로 **`textarea#editor-tistory` 값을 제출**한다. `tinymce.setContent()`는 내부 상태만 바꾸고 textarea는 비워둠 → 제출하면 본문이 빈 "빵꾸" 발생.

**해결:** `setContent()` 후 **`tinymce.activeEditor.save()`** 로 textarea에 강제 동기화. + 본문 길이 검증(`_verify_body`)으로 빵꾸 방지 QA 게이트.

```javascript
tinymce.activeEditor.setContent(html);
tinymce.activeEditor.save();   // ← 이게 핵심. textarea 동기화
```

---

## 3. 스킨 아키텍처 — 뭘 얹었나

### 3.1 베이스 = Whatever 스킨 + 프리미엄 다크 오버레이

- **베이스:** 티스토리 `pg_Whatever` 스킨 (구조는 그대로).
- **오버레이:** `skin-premium.css` (710줄) — 배경 `#08090a`, 표면 `#0f1115`, 본문 `#f7f8f8`, 액센트 틸/골드. 글래스 헤더·카드·사이드바·코드블록 전부 다크로.

### 3.2 Galaxy S21 시그니처 — 고정 오버레이 장식

전부 `position:fixed` + `pointer-events:none` (클릭 안 막음), z-index 9980~9992:

| id | 위치 | 움직임 |
|----|------|--------|
| `#s21-bezel` | 화면 전체 inset 14px 테두리 | `s21-breathe` 글로우 호흡 |
| `#s21-camera` | 우상단(동쪽) 컨투어컷 모듈 | 렌즈3+플래시, `s21-spin`/`s21-flash` |
| `#s21-punch` | 상단 중앙 펀치홀 | 정적 |
| `#s21-particles` | 전체 `inset:0` | `s21-nebula` 성운 + `<i>`별 + `<b>`유성 |
| `#s21-home` | 하단 중앙 제스처 필 | `s21-breathe` |
| `#s21-mic` | 하단 필 우측 삼성 STT 마이크 | `s21-micpulse` |
| `#category-nav` | 좌측 스티키 카테고리 패널 | 줌컨트롤 내장 |

### 3.3 마커 기반 멱등 주입 (핵심 설계)

스킨 HTML/CSS에 반복 적용해도 안 꼬이게, **마커로 감싼 블록을 교체**한다.

```
HTML 마커: <!-- HELENA-LAYOUT-START --> ... <!-- HELENA-LAYOUT-END -->
CSS  마커: /* HELENA-ORBITAL-SKIN-START */ ... /* HELENA-ORBITAL-SKIN-END */
```

`replace_block()` 함수: 마커가 이미 있으면 **그 사이만 교체**, 없으면 append. → 몇 번을 돌려도 같은 결과(멱등).

HTML 주입 위치: `<section class="container">` 바로 뒤.

---

## 4. 테마 시스템 — 블로그별 색 + 스타필드 (2026-08-15 신규)

일괄 적용의 단점 = **모든 블로그가 똑같아 보인다**. 이를 **두 변수(색 + 스타필드)** 로 보강.

### 4.1 색 → CSS 커스텀 프로퍼티(`:root` 토큰)

`skin-premium.css` 맨 위 `:root` 에 기본값(틸/골드)을 두고, 모든 색 규칙이 `var()`를 참조한다:

```css
:root {
  --s21-accent: #2dd4bf;        /* 주 액센트 */
  --s21-accent-rgb: 45, 212, 191;  /* rgba() 알파용 RGB 트리플릿 */
  --s21-accent2: #f0b429;       /* 보조(골드) */
  --s21-nebula-a/b/c: ...;      /* 성운 3색 */
  --s21-star1/2/3: ...;         /* 별 3색 */
  --s21-meteor: ...;            /* 유성색 */
  --s21-meteor-ang/dx/dy: ...;  /* 유성 방향·거리 */
}
```

**트릭:** `rgba(45,212,191,0.08)` 같은 알파 색은 `rgba(var(--s21-accent-rgb), 0.08)` 로 바꾼다. hex는 알파를 못 담으니 **RGB 트리플릿을 변수로** 분리한 것.

### 4.2 블로그별 override — HTML의 `<style id="s21-theme">`

`apply_layout.py` 가 블로그 테마에 맞춰 `:root` 를 **덮어쓰는 `<style>` 태그**를 HTML에 같이 주입한다. (body에 들어가 head의 CSS보다 늦게 로드 → 동일 specificity에서 **나중 선언이 이김**)

```html
<style id="s21-theme">
:root {
  --s21-accent:#e9d9a8;
  --s21-accent-rgb:233, 217, 168;
  ...
}
</style>
```

### 4.3 THEME_MAP — 5개 블로그 정체성

| 계정 id | 블로그 | 정체성 | 액센트 | 성운 | 별 | 유성 |
|---------|--------|--------|--------|------|----|----|
| `galaxys21` | galaxys21-pwuser | 개발·도구(원본) | 틸 `#2dd4bf` + 골드 | 틸-퍼플 은하수 | 18 | 3 (대각) |
| `faith` | helana-christianity | 신앙=영혼 | 아이보리골드 `#e9d9a8` | 금빛 확산 | 24 (느림) | 3 (수직 빛기둥) |
| `piano` | helena-piano | 연주=표현 | 딥블루 `#6b8cff` | 블루-바이올렛 | 18 | 3 (수평) |
| `metalcare` | helena-metalcare | 멘탈케어=마음 | 세이지 `#8fd6b3` | 세이지-소프트블루 | 12 (매우 느림) | 2 (은은) |
| `mynote` | mynote11605 | 노트·기록 | 앰버 `#e8a35a` | 웜그레이-세피아 | 18 | 3 (펜스트로크) |

### 4.4 스타필드 → 개수·속도·방향 (결정적 생성)

별/유성 개수·속도·방향은 블로그별로 다르다. `_starfield(theme)`가 `random.Random(seed)` 로 **결정적으로** 생성 (같은 seed → 같은 좌표, 재적용해도 동일 결과):

```python
def _starfield(theme):
    rng = random.Random(theme["seed"])     # 고정 seed → 결정적
    stars = []
    for _ in range(theme["stars"]):        # 별 개수 (12/18/24)
        x, y = rng.uniform(4,96), rng.uniform(4,96)
        s = rng.choice([2,2,3,3,4,5])      # 별 크기
        d = rng.uniform(3.0,5.2) * theme["pace"]  # 반짝임 속도(pace=느림 배수)
        stars.append(f'<i style="--x:{x}%;--y:{y}%;--s:{s}px;--d:{d}s;...">')
    ...
```

유성 방향은 `--s21-meteor-ang/dx/dy` 로: faith=수직(`-90deg`), piano=수평(`0deg`), mynote=짧은 펜(`-45deg`, 짧은 거리), metalcare=은은(짧은 거리+느림).

---

## 5. 코드 자산 — 뭘 돌리면 되나

| 파일 | 역할 | 실행 |
|------|------|------|
| `apply_layout.py` | 단일 블로그 HTML+CSS 주입 (메인 galaxys21용) | `python3 apply_layout.py --account galaxys21` |
| `batch_apply.py` | 4개 블로그 스킨전환+주입 일괄 | `python3 batch_apply.py` |
| `switch_skin.py` / `apply_skin.py` | 스킨 전환 / CSS 전용(구식) | 보조 |
| `skin-premium.css` | 다크 스킨 + S21 시그니처 + 테마 토큰 | (주입되는 CSS 본체) |
| `post.py` | 글 발행 (댓글 비허용 강제) | `python3 post.py` |
| `accounts.json.template` | 계정 양식 (secret 제외 — 실제 secret은 gitignored `accounts.json`) | 참고 |

**secret 주의:** `accounts.json`(계정 이메일·비밀번호)과 `cookies/` 디렉토리는 **gitignore 대상 — 절대 커밋 금지**. `accounts.json.template` 이 양식 참고용으로만 존재.

---

## 6. 재현 레시피 — 다른 사람 가르칠 때 (step-by-step)

> 새 티스토리 블로그에 이 스킨을 얹는 절차.

1. **계정 준비:** `accounts.json.template` → `accounts.json` 복사 후 계정 id/blog/이메일/비밀번호 채움.
2. **로그인 1회:** `batch_apply.py` 또는 `apply_layout.py` 최초 실행 → 카카오 로그인 → `galaxys21_state.json` 자동 저장 (TSSESSION 영속화).
3. **스킨 전환:** `POST /manage/design/skin/set.json {name:"pg_Whatever"}`.
4. **CSS+HTML 주입:** `apply_layout.py --account <id>` → `GET html.json` → 마커 블록 교체 → `POST html.json {html, css}`.
5. **테마 커스터마이즈:** `apply_layout.py` 의 `THEME_MAP` 에 블로그 계정 id + 색/스타필드 파라미터 추가 → 재실행.
6. **검증:** `POST` 응답 `200` + `GET` 재조회로 `html_marker=True`/`css_marker=True` 확인. 렌더는 `curl` 로 `<style id="s21-theme">` 와 `--s21-accent` 확인.

**재적용 흐름 (테마 변경 시):**
```bash
python3 apply_layout.py --account galaxys21   # 메인
python3 batch_apply.py                         # 나머지 4개
```

---

## 7. 함정 모음 (재삽질 금지)

| 함정 | 증상 | 해결 |
|------|------|------|
| Enter로 로그인 제출 | 계정선택 화면에 막힘 | submit 버튼 클릭 |
| `fill()` 이른 호출 | "Object not JSON serializable" 크래시 | 폼 렌더 폴링 + `evaluate()` 채움 |
| TSSESSION 유실 | 재실행마다 재로그인(CAPTCHA) | state.json 복원 + expires 보정 |
| 헤드리스 반복 로그인 | CAPTCHA | 쿨다운 15-30분 |
| `setContent`만 호출 | 본문 빵꾸 | `editor.save()` 동기화 + 길이 검증 |
| `.thum:empty` | 썸네일 안 사라짐 | `.thum {display:none!important}` |
| 테이블 가로 넘침 | 모바일 짤림 | `overflow-wrap:anywhere` + `overflow-x:auto` |
| `networkidle` 타임아웃 | 느린 폰 네트워크 | `domcontentloaded` + sleep |

---

## 8. 관련 문서

```
코드
├── tistory-naver/apply_layout.py     → 주입 + 테마 생성 (본문 4장)
├── tistory-naver/batch_apply.py      → 일괄 적용 + 로그인
├── tistory-naver/skin-premium.css    → 다크 스킨 + S21 시그니처 + :root 토큰
└── tistory-naver/post.py             → 발행 (댓글 비허용 강제)

수첩
├── 75-translation-logic-management_Claude.md  → 출판부 규칙
├── tistory-master-guide_Claude.md             → 5채널 전략·Paste Pipeline
└── 99-devlog.md                                → 전체 타임라인

메모리
├── tistory-skin-switch          → Whatever 스킨 전환
├── tistory-orbital-skin         → 다크 스킨 API 주입
├── tistory-s21-signature-design → S21 시그니처
└── tistory-comments-disabled    → 댓글 금지
```

---

*agent _Claude · 2026-08-15 · 리버스 엔지니어링 연대기 + 스킨 아키텍처 + 테마 시스템 종합*

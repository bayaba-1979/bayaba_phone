# tistory-naver — 티스토리 스킨 자동 적용 + 포스팅 도구

갤럭시 S21 컨셉 **블랙 다크 스킨**을 5개 티스토리 블로그에 자동 적용하고, 글을 발행하는 Playwright 도구 모음.

> 📚 전체 리버스 엔지니어링 해부(스킨 관리 API를 어떻게 찾았는지, 테마 시스템 설계)는
> **`_notebook/93-tistory-skin-reverse-engineering_Claude.md`** 참고.

---

## 핵심: 티스토리 스킨은 "숨겨진 관리 API"로 찍어낸다

공식 API는 없지만, 관리자 화면의 네트워크 요청을 관찰하면 내부 API가 드러난다.

| API | 메서드 | 역할 |
|-----|--------|------|
| `/manage/design/skin/html.json` | `GET` | 스킨 HTML+CSS 전체 조회 |
| `/manage/design/skin/html.json` | `POST` | `{html, css, isPreview:false}` 저장 |
| `/manage/design/skin/set.json` | `POST` | `{name:"pg_Whatever"}` 스킨 전환 |

로그인 세션 쿠키(`TSSESSION`)만 있으면 Playwright로 직접 호출 가능.

---

## 스크립트

| 파일 | 역할 | 실행 |
|------|------|------|
| `apply_layout.py` | 단일 블로그 HTML+CSS 주입 (메인 galaxys21) | `python3 apply_layout.py --account galaxys21` |
| `batch_apply.py` | 4개 블로그 스킨전환+주입 일괄 | `python3 batch_apply.py` |
| `switch_skin.py` | 스킨 전환 전용 | `python3 switch_skin.py` |
| `skin-premium.css` | 다크 스킨 + S21 시그니처 + `:root` 테마 토큰 | (주입되는 CSS 본체) |
| `post.py` | 글 발행 (댓글 비허용 강제) | `python3 post.py` |

### 블로그별 테마 (색 + 스타필드)

`apply_layout.py` 의 `THEME_MAP`(계정 id 키)으로 관리. CSS는 공유, 색·별·유성은 블로그마다 다름.

| id | 블로그 | 액센트 | 별 | 유성 |
|----|--------|--------|----|----|
| galaxys21 | galaxys21-pwuser | 틸 `#2dd4bf` + 골드 | 18 | 3 |
| faith | helana-christianity | 아이보리골드 `#e9d9a8` | 24 | 3 |
| piano | helena-piano | 딥블루 `#6b8cff` | 18 | 3 |
| metalcare | helena-metalcare | 세이지 `#8fd6b3` | 12 | 2 |
| mynote | mynote11605 | 앰버 `#e8a35a` | 18 | 3 |

---

## 재적용 (테마 변경 시)

```bash
python3 apply_layout.py --account galaxys21   # 메인
python3 batch_apply.py                         # 나머지 4개
```

---

## 🔒 secret 위생 (중요)

- `accounts.json` (계정 이메일·비밀번호) 과 `cookies/` 디렉토리는 **gitignore 대상 — 절대 커밋 금지**.
- `accounts.json.template` 이 양식 참고용 (secret 제외).

---

## 함정 요약

| 함정 | 해결 |
|------|------|
| Enter로 로그인 제출 실패 | submit 버튼 클릭 |
| `fill()` 이른 호출 크래시 | 폼 렌더 폴링 + `evaluate()` 채움 |
| TSSESSION 재실행 시 유실 | state.json 복원 + expires 보정 |
| 헤드리스 반복 로그인 CAPTCHA | 쿨다운 15-30분 |
| `setContent`만 호출 → 본문 빵꾸 | `editor.save()` 동기화 + 길이 검증 |

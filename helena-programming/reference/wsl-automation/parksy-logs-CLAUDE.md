# Tistory Publishing Pipeline — AI 에이전트 지침

이 문서는 AI 에이전트(Claude, DeepSeek 등)가 사용자의 명령을 받아
티스토리 블로그에 단행본을 자동 발행하기 위한 절차를 정의한다.

---

## 🚀 핵심 워크플로우

사용자가 아래처럼 말하면 → 에이전트가 전부 처리:

```
"철학자박씨에 '존재와 시간' 단행본 올려줘. 내용은..."
"기능인박씨 OJT 매뉴얼 3장 발행해"
"blogger-parksy에 영문판 업로드"
```

## 📋 에이전트 실행 절차

### Step 0: 블로그 목록 확인
```bash
python3 generator.py --list
```

### Step 1: 콘텐츠 생성
- 사용자의 말을 듣고 단행본급 콘텐츠를 작성
- 마크다운 형식으로 저장: `drafts/{blog_name}_{title}.md`

### Step 2: 변환 (generator.py 사용 — 권장)
```bash
cd publishing
python3 generator.py \
  --blog "철학자박씨" \
  --title "존재와 시간" \
  --input drafts/철학자박씨_존재와시간.md \
  --series "서양철학 OJT 시리즈" \
  --tags 철학 하이데거 존재론
```

자연어 명령도 가능:
```bash
python3 generator.py --say "철학자박씨에 존재와 시간 올려줘" --input drafts/존재와시간.md
```

### Step 3: 발행
```bash
# generator.py 생성 후 자동 발행 (--publish 플래그)
python3 generator.py \
  --blog 철학자박씨 \
  --title "존재와 시간" \
  --input draft.md \
  --publish

# 또는 별도 실행
python3 publisher.py --post posts/철학자박씨_존재와시간.json
python3 publisher.py --blog 철학자박씨
```

### Step 4: 발행 결과 확인
```bash
cat output/publish_*.log | tail -5
```

### ⚡ 에이전트 한 줄 명령 예시
```bash
# 말만 하면 끝:
python3 generator.py --blog 철학자박씨 --title "제목" --input draft.md --publish

# 블로그 목록:
python3 generator.py --list
```

---

## 🔗 계정·블로그 매핑 (사용자별 accounts.json 기준)

| 블로그명 | 슬러그 | 계정 |
|---------|-------|------|
| 블로거박씨 | polyglot14 | my_account |
| 철학자박씨 | dtslib | my_account |
| ... | ... | ... |

---

## 📂 디렉토리 구조

```
publishing/
├── accounts.json        ← 계정 정보 (1번만 설정)
├── cookies/             ← 로그인 세션 (login.py로 생성)
├── drafts/              ← 에이전트가 생성한 마크다운 원고
│   └── 철학자박씨_존재와시간.md
├── posts/               ← 변환된 JSON 포스트 (publisher가 읽음)
│   └── 철학자박씨_존재와시간.json
├── converter.py         ← 마크다운 → 단행본 HTML 변환
├── publisher.py         ← Playwright 자동 발행
├── login.py             ← 세션 로그인
├── install.sh           ← 최초 설치
├── template/
│   └── post.json        ← 포스트 템플릿
└── examples/
    └── sample-post.md   ← 샘플
```

---

## ⚡ 핵심 명령어

```bash
# 최초 1회: 설치
bash install.sh

# 최초 1회: 로그인 (크롬 창 뜸)
python3 login.py

# 매번: 변환 + 발행
python3 converter.py -i draft.md -b "블로그명" --slug "slug" --title "제목"
python3 publisher.py --blog "블로그명"

# 전체 발행 (posts/ 디렉토리 전부)
python3 publisher.py
```

---

## ⚠️ 주의사항
- `accounts.json`에 실제 계정 정보 입력 필수
- 로그인은 `headless=False` (크롬 창 직접 뜸, 봇탐지 우회)
- 한 번 로그인하면 세션 저장 → 다음부터 재사용
- 변환기 converter.py는 경량 마크다운 파서 내장 (복잡한 MD는 직접 HTML로)

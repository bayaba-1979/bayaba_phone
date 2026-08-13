# Tistory HTML 모드 — 기술 한도 레퍼런스

> **버전:** v1.0 · 2026-08-09
> **범위:** 티스토리 **글쓰기 HTML 모드** (스킨 편집 아님)
> **핵심:** 티스토리 글쓰기 HTML 모드는 **XSS 방지 필터**다. JS 실행만 막는다. CSS·SVG는 거의 다 통과.

---

## 구분: 스킨 편집 vs 글쓰기 HTML 모드

| 항목 | 스킨 편집 (`skin.html`) | 글쓰기 HTML 모드 |
|------|------------------------|-------------------|
| `<script>` | ✅ 가능 | ❌ 전부 제거 |
| `<style>` | ✅ 가능 | ✅ 가능 (글 본문 안에서도) |
| 이벤트 핸들러 | ✅ 가능 | ❌ `on*` 속성 제거 |
| 외부 JS 로딩 | ✅ 가능 | ❌ 불가 |
| SVG 인라인 | ✅ 가능 | ✅ 가능 |
| CSS 애니메이션 | ✅ 가능 | ✅ 가능 |
| `data-*` 속성 | ✅ 가능 | ✅ 가능 |
| `<iframe>` | ✅ 가능 | ⚠️ 제한적 (일부 남음) |
| HTML5 시맨틱 | ✅ 가능 | ✅ 가능 |

> **원칙:** 티스토리 글쓰기 HTML 모드의 필터는 **JS 실행을 막는 것**이 유일한 목적. CSS 표현·SVG 그래픽·HTML 구조는 건드리지 않는다.

---

## ✅ 지원 — 안심하고 쓸 수 있는 것

### HTML 요소
```html
<!-- 시맨틱 -->
<article> <section> <header> <footer> <nav> <main> <aside>

<!-- 아코디언 (JS 없이 작동) -->
<details><summary>제목</summary>내용</details>

<!-- 미디어 -->
<figure><figcaption>캡션</figcaption></figure>
<img src="https://..." alt="..." loading="lazy">
<picture><source><img></picture>
<audio controls src="...">  <!-- 제한적, MP3 권장 -->
<video controls width="100%">  <!-- 제한적, MP4 권장 -->

<!-- 표 -->
<table><thead><tbody><tfoot><caption>

<!-- 텍스트 -->
<mark> <time> <abbr title="..."> <code> <pre> <kbd> <samp>
<blockquote cite="..."> <cite>

<!-- 링크 -->
<a href="https://..." target="_blank" rel="noopener">  <!-- target 가능 -->
```

### CSS (전부 가능)
```css
/* 레이아웃 */
display: flex; display: grid; gap; position: sticky;

/* 애니메이션 */
@keyframes slide-in { ... }
animation: slide-in 0.3s ease-out;
transition: all 0.2s;

/* 변수 */
:root { --color: #333; }
color: var(--color);

/* 계산 */
width: calc(100% - 2rem);
counter-reset: turn-counter;

/* 미디어 쿼리 */
@media (max-width: 480px) { ... }
@media (prefers-color-scheme: dark) { ... }

/* 폰트 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR...');
/* ↑ @import는 될 확률 높지만, <link>보다 불안정하면 @font-face 직접 사용 */
```

### CSS 선택자 (전부 가능)
```css
:hover :focus :active :visited      /* 사용자 인터랙션 */
:target                              /* URL 해시로 요소 선택 — CSS 네비게이션 가능 */
:checked                             /* 체크박스 토글 — CSS 상태 머신 */
:nth-child() :first-child :last-child
:not()                               /* 2024+ :has()도 브라우저만 지원하면 됨 */
::before ::after                     /* 가상 요소 */
::marker                             /* 리스트 마커 */
```

### SVG (인라인 전부 가능)
```html
<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <!-- 모든 SVG 요소 가능 -->
  <circle> <rect> <path> <line> <polyline> <polygon>
  <text> <tspan> <textPath>
  <g> <defs> <use> <symbol>
  <linearGradient> <radialGradient> <pattern> <clipPath> <mask>
  <filter> <!-- SVG 필터(드롭섀도우 등) -->

  <!-- SVG에 CSS 애니메이션 적용 가능 -->
  <style>circle:hover { fill: red; }</style>

  <!-- SMIL 애니메이션도 동작 가능성 있음 (테스트 필요) -->
  <animate> <animateTransform>
</svg>
```

### CSS-only 인터랙티브 패턴
1. **아코디언:** `<details><summary>` + `[open]` 애니메이션
2. **탭/필터:** 숨은 `<input type="radio">` + `:checked` + 인접 형제 선택자
3. **모달/라이트박스:** `:target` + 고정 포지션
4. **툴팁:** `[title]` 속성 + `::after` + `content: attr(title)`
5. **프로그레스 바:** `@keyframes` + `animation-fill-mode: forwards`
6. **카운터:** `counter-reset` + `counter-increment` + `content: counter()`
7. **체크박스 토글 메뉴:** `<input type="checkbox">` + `<label>` + CSS 선택자

---

## ❌ 불가 — 시도해도 제거됨

### JavaScript 관련 (전부 막힘)
```html
<!-- 이 모든 게 제거됨 -->
<script>...</script>
<script src="..."></script>
<button onclick="...">       <!-- on* 속성 제거 -->
<body onload="...">
<img onerror="...">
<a href="javascript:...">    <!-- javascript: URL 차단 -->
<svg><script>...</script></svg>  <!-- SVG 안의 script도 제거 -->
```

### 이벤트 핸들러 속성 (전부 제거)
```
onclick ondblclick onmousedown onmouseup onmouseover onmousemove onmouseout
onkeydown onkeypress onkeyup onchange oninput onfocus onblur onsubmit onreset
onload onunload onerror onscroll onresize onselect oncontextmenu ontouchstart
ontouchmove ontouchend onwheel oncopy oncut onpaste ondrag ondragstart ondrop
```

> **중요:** 이벤트 핸들러 속성은 완전히 제거되지만, **`<style>` 태그와 `data-*` 속성은 보존**된다. `data-*`는 HTML5 표준 속성이라 XSS 위협으로 분류되지 않음.

---

## ⚠️ 회색 지대 — 환경 따라 다름 (테스트 필요)

| 항목 | 확률 | 비고 |
|------|------|------|
| `<iframe>` | 중간 | 티스토리 정책 따라 차단 가능성. 차단되면 일반 텍스트로 대체. |
| `<embed>`, `<object>` | 낮음 | 보안상 차단 가능성 높음 |
| `<link rel="stylesheet">` (body 내) | 중간 | body 안 `<link>`는 HTML 스펙 위반이지만 티스토리가 허용할 수도 |
| CSS `@import` | 높음 | 대부분 통과. 실패 시 `<style>` + 구글 폰트 `@font-face` 직접 사용 |
| CSS `url()` 외부 이미지 | 높음 | 배경 이미지 등엔 보통 통과 |
| `<canvas>` | 낮음 | JS 없으면 무의미. 필터가 제거할 가능성 |
| `contenteditable` | 낮음 | JS 없이 무의미하지만 보안 필터가 제거할 가능성 |
| `<form>` + `<input>` | 높음 (요소) / 낮음 (동작) | 요소는 남지만 JS 없으니 제출 안 됨 |
| SVG `<animate>` | 중간 | SMIL 애니메이션. 브라우저가 지원해도 티스토리가 막을 가능성. |
| CSS `:has()` | 브라우저 의존 | 2023년 말부터 크롬 지원. 구형 안드로이드 WebView에선 불발. 티스토리 필터는 무관. |
| `<template>`, `<slot>` | 중간 | Web Components. HTML 요소는 남을 수 있으나 JS 없이 무의미 |
| CSS `@property` | 브라우저 의존 | Houdini API. 크롬 85+ |
| `<meta>` 태그 | 낮음 | `<head>` 영역이 아닌 body에서 제거 가능성 |
| 코멘트 `<!-- -->` | 높음 | HTML 주석은 남음. 단, IE 조건부 주석은 제거 가능 |

---

## 🧪 확실하게 테스트하는 법

이 체크리스트를 HTML 모드로 글 발행 후, **실제 발행된 페이지**에서 확인:

```html
<!-- 테스트 1: <style> 생존 확인 -->
<style>.style-test{color:red!important}</style>
<p class="style-test">이 텍스트가 빨간색이면 &lt;style&gt; 통과</p>

<!-- 테스트 2: <details> 작동 확인 -->
<details><summary>클릭</summary>보이면 통과</details>

<!-- 테스트 3: :target 작동 확인 -->
<style>#target-test:target{background:yellow}</style>
<a href="#target-test">클릭</a> <p id="target-test">노란색이면 통과</p>

<!-- 테스트 4: SVG 생존 확인 -->
<svg width="50" height="50"><circle cx="25" cy="25" r="20" fill="blue"/></svg>

<!-- 테스트 5: data-* 속성 생존 확인 -->
<p data-test="hello">브라우저 개발자 도구로 data-test 속성 확인</p>

<!-- 테스트 6: @import 생존 확인 -->
<style>@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap'); .font-test{font-family:'Noto Sans KR'}</style>

<!-- 테스트 7: iframe 생존 확인 -->
<iframe src="https://example.com" width="100" height="50"></iframe>
```

> 발행 후 DevTools(`F12`)로 확인. 제거된 요소는 소스에 흔적도 없이 사라진다.

---

## 🎯 실전 전략: JS 없는 풀인터랙티브 페이지

### 패턴 1 — 아코디언 대화록
```
<details> 단위로 각 대화 턴. CSS로 화자별 색상 구분.
열릴 때 transition/애니메이션으로 부드럽게.
```

### 패턴 2 — 탭 필터
```
숨은 radio input + label 버튼 + :checked ~ .list 필터링.
전체/Boss/Grok/결정만 보기 등.
```

### 패턴 3 — SVG 사고 지도
```
inline SVG로 결정 트리·타임라인·네트워크 그래프.
CSS :hover로 노드 강조. data-*로 메타데이터.
```

### 패턴 4 — CSS 그래프
```
flex/grid + height 커스텀 프로퍼티로 바 차트.
@keyframes로 로드 시 성장 애니메이션.
```

### 패턴 5 — 타임라인
```
border-left 줄기 + ::before 원 마커 + position: relative.
결정 지점은 색상·크기 강조.
```

### 패턴 6 — 카드 그리드
```
Fact/Feel/Gap/Fix/Next 각각 색상 태그 + grid 레이아웃.
:hover 시 translateY(-2px)로 살짝 뜨는 느낌.
```

---

## 📦 결론: 티스토리 HTML 모드 최대치

| 계층 | 가능 여부 | 핵심 |
|------|-----------|------|
| **HTML5 구조** | ✅ 전부 | 시맨틱·아코디언·표·미디어 전부 |
| **CSS 표현** | ✅ 전부 | Grid·Flexbox·애니메이션·변수·미디어쿼리 |
| **SVG** | ✅ 인라인 전부 | `<svg>` + 모든 벡터 요소 + CSS 호버 |
| **CSS 상태** | ✅ 전부 | `:target`, `:checked`, `:hover`, `:focus` |
| **CSS 가상요소** | ✅ 전부 | `::before`, `::after`, `::marker` |
| **JS 인터랙션** | ❌ 전부 불가 | `<script>`, `on*`, `javascript:` 전부 제거 |
| **외부 리소스** | ⚠️ 대부분 | 이미지·폰트·오디오 URL은 통과, iframe은 의심 |

> **최대치 = JS 없이 CSS+SVG+HTML5만으로 구현할 수 있는 모든 인터랙션.**
> 2024년 기준, 이건 꽤 많은 것을 포함한다. `<details>`, `:target`, `:checked`, SVG CSS animation, `@keyframes`, Grid, Flexbox — 이 조합이면 인포그래픽·대시보드·인터랙티브 기사 수준의 페이지를 JS 없이도 만들 수 있다.

---

## 📚 참고: 티스토리 스킨 편집을 쓸 수 있다면

글쓰기가 아니라 **스킨 편집**(`skin.html`)에 접근할 수 있으면 JS 제한이 전부 풀린다.
D3.js, Chart.js, Mermaid, Vis.js 같은 라이브러리도 `<script src="...">`로 로딩 가능.

하지만 스킨 편집은 **블로그 전체에 적용**되므로, 글 하나만 JS 넣는 건 어렵다.
글 단위로 JS를 허용하는 플러그인/치환자도 있으나, 티스토리 정책 변경에 취약.

> **권장:** JS가 꼭 필요한 고급 인터랙티브 페이지는 GitHub Pages로 만들고, 티스토리는 "티저(teaser) + 링크"로 연결하는 하이브리드 전략.

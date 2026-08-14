# YouTube 채널 아키텍처

## 채널 구성 (2채널 · 2026-08-14 축소)

| YouTube 채널 | 이름 | 흡수하는 티스토리 | 콘텐츠 |
|-------------|------|------------------|--------|
| `@helena_phone` | **도구 (인프라)** | `galaxys21-pwuser` · `mynote11605` | S21 폰 셋업/코딩 + 기술 튜토리얼 |
| `@HelenaPark-e7c` | **돌봄 (누나)** | `helana-christianity` · `helena-piano` · `helena-metalcare` | 신앙·피아노·멘탈케어 (플레이리스트 3개) |

## 채널 구조

- **2채널 체계 (2026-08-14):** 콜드 스타트(꾸준한 업로드 빈도) 때문에 5채널 → 2채널로 축소
- `@helena_phone` = 인프라(도구) · `@HelenaPark-e7c` = 돌봄(누나)
- 누나 콘텐츠 3종(신앙·피아노·멘탈케어)은 채널이 아닌 **플레이리스트**로 분리
- 매핑: 1:1:1 → **5:5:2** (GitHub 5 : 티스토리 5 : YouTube 2)
- 네이버 블로그(관저탑)는 모든 채널의 교차 홍보 게이트웨이

## 채널 (2개)

```
https://www.youtube.com/@helena_phone     → 도구(인프라)
https://www.youtube.com/@HelenaPark-e7c   → 돌봄(누나)
```

## 구축 상태

| 단계 | 상태 |
|------|------|
| GCP 프로젝트 생성 | 📌 준비 완료 (gcloud CLI 설치됨) |
| YouTube Data API v3 활성화 | 📌 준비 완료 |
| OAuth 동의 화면 | ⏳ 수동 필요 (console.cloud.google.com) |
| TV 클라이언트 ID 생성 | ⏳ 수동 필요 |
| Device code 인증 | 📌 자동화 준비 |
| 업로드 스크립트 | ⏳ 미작성 |
| 쿼터 보호(playlistItems) | 📌 설계 반영 예정 |

## 수동 작업 (폰 브라우저)

```md
1. console.cloud.google.com → 새 프로젝트 "S21 YouTube"
2. OAuth 동의 화면 → 외부 → 앱이름 "S21 Phone" → 테스트 사용자 추가
3. 사용자 인증 정보 → OAuth 클라이언트 ID → "TV 및 제한된 입력 장치"
4. 클라이언트 ID + 시크릿 복사
```

## 쿼터 참고

| 작업 | 유닛 | 비고 |
|------|------|------|
| 업로드 (videos.insert) | 1,600 | 하루 약 6개 가능 |
| 메타데이터 수정 | 50 | |
| 목록 조회 (search.list) | 100 | ❌ 사용 금지 |
| playlistItems.list | 1 | ✅ 이걸로 대체 |
| 채널 정보 | 1 | |

**절대 `search.list`를 루프에 넣지 말 것. playlistItems.list (1유닛) 사용.**

---

## 현재 상태 (2026-07-25)

| 항목 | 값 |
|------|-----|
| Phase 1 채널 | @helena_phone ✅ (UC_IPajoyj6_IO8wt9JwVCAQ) |
| OAuth | TV Device Flow ✅ |
| API | Data v3 ✅ · Analytics ✅ · Reporting ⚠️ |
| 플레이리스트 | 5개 카테고리 (디바이스·AI·퍼블리싱·오피스·노트) |
| 업로더 | scripts/yt_upload.py (256줄) |
| 동영상 | 0개 (첫 업로드 대기) |

**Phase 2~5 (브랜드 채널 생성):** ~~8~11월 매월 25일~~ → **폐기 (2026-08-14)** — 2채널 체계로 전환, 브랜드 채널 생성 중단.

# JinjuHub 프론트엔드 고도화 인수인계 (2026-11-05)

> 이 문서만 읽고 바로 작업을 시작할 수 있도록 썼습니다.
> 이전 작업자(Claude Code)는 여기서 작업을 종료했고, 프론트엔드 고도화는 agy 새 세션이 이어서 맡습니다.

## 1. 현재 상태 한눈에

### 저장소
- 경로: `C:\Users\SSAFY\Desktop\JinjuHub`
- GitHub: https://github.com/cannedJean/jinju-hub

### 브랜치
- `feat/jinjuhub-mvp` = `31c431e`
  - push 완료, 배포 브랜치입니다.
  - 이 브랜치에 push하면 Render(백엔드)와 Netlify(프론트)가 **프로덕션에 자동 배포**됩니다.
- `main` = `3f4845b`
  - 초기 부트스트랩만 들어 있습니다.
  - feat → main 병합은 **소유자 동의가 필요하고 아직 하지 않았습니다.**

### 라이브 주소
- 프론트: https://jinju-hub.netlify.app
- 백엔드: https://jinjuhub-api.onrender.com
  - `/api/health` 기준 `data_version` = `20261105T115734+0900`

### 테스트 현황 (feat @31c431e)

| 영역 | 결과 |
|---|---|
| backend | 227 passed (+1 xfail) |
| pipeline | 311 passed (+1 skip) |
| frontend vitest | 239 passed |
| 로컬 fixture e2e | 18/18 |

### 지금까지 끝낸 일
- 계획서의 전 태스크
- 브랜치 전체 코드리뷰 후 수정 4그룹(채팅 검색 재설계, 파이프라인, 프론트, 게시판/운영)
- agy 교차 검증: Teamwork 정적 검증과 라이브 브라우저 UX 점검
  - 지적 사항은 코드·데이터·스크린샷과 대조해 판정을 마쳤습니다(4장 참고).

### 사양과 계획 문서
- 사양: `docs/superpowers/specs/2026-11-04-jinjuhub-design.md`
  - 마지막의 "구현 중 변경 사항" 절까지 구속력이 있습니다.
- 계획: `docs/superpowers/plans/2026-11-04-jinjuhub.md`
- 운영 문서: `DEPLOYMENT.md`, `DATA.md`, `docs/DEMO_RUNBOOK.md`

## 2. 반드시 지킬 규칙 (위반 시 실제 비용·데이터 피해)

1. **Claude API 키는 소유자의 제한된 유료 키입니다.**
   - 라이브 `https://jinjuhub-api.onrender.com/api/chat`에 요청을 보내지 마세요. 스크립트, curl, Playwright, 브라우저 어느 방법도 안 됩니다.
   - 라이브 사이트에서 챗봇 패널의 **추천 질문 칩 4개**와 **전송 버튼**을 누르지 마세요. 누르는 순간 키가 쓰입니다.
   - 패널을 열고 닫는 것은 괜찮습니다.
   - 채팅 동작은 로컬 테스트(가짜 클라이언트)로만 검증합니다.
2. **게시판은 프로덕션 DB(Neon)에 바로 씁니다.** 라이브 사이트에서 글 작성·수정·삭제를 제출하지 마세요.
3. **비밀값 규칙**
   - `backend/.env`, `pipeline/.env`, `frontend/.env.local`을 읽거나 출력하지 마세요.
   - 테스트도 .env를 읽지 않습니다.
   - 비밀값은 절대 커밋하지 마세요.
4. **배포와 병합**
   - `feat/jinjuhub-mvp` push는 곧 프로덕션 배포입니다.
   - 작업은 새 브랜치에서 하고, push와 병합은 소유자 확인 후에 합니다.
5. **사양상 제약**
   - 반응형은 **데스크톱 우선**(mobile-first 아님)입니다.
   - 유등(저장·점등) 상태는 **브라우저 localStorage에만** 둡니다(키 `jinjuhub.lanterns.v1`, 버전 있음).
   - 지도 타일은 OSM입니다(출처 표기 유지).
   - 공공누리 3유형 이미지는 **잘라내지 않습니다**(`object-fit: contain` 유지).
6. **TDD 원칙**
   - 기능·버그 수정마다 먼저 실패하는 테스트(vitest)를 쓰고, 그다음 수정합니다.
   - 끝나면 vitest 전체와 로컬 e2e를 통과시킵니다.

## 3. 프론트엔드 구조와 명령

### 스택
Vue 3, Vite, Pinia, Tailwind, Leaflet + markercluster, axios

### 주요 위치 (`frontend/src`)
- `views/`
  - HomeView, ExploreView(지도·바텀시트), PlaceDetailView, LanternsView(내 유등·배지), FestivalsView, BoardListView, PostDetailView, PostFormView, DataSourcesView
- `components/`
  - layout/: AppHeader, AppTabBar
  - explore/: BottomSheet, CategoryChips 등
  - place/: PlaceCard, InfoTable, ImageGallery 등
  - lanterns/: SavedList, BadgeShelf, CelebrationToast, LanternMap 등
  - festival/: FestivalCard, FestivalTimeline 등
  - map/: MapCanvas
  - 단일 파일: ChatWidget.vue, WeatherWidget.vue
- `stores/`: lanterns.js(유등·시연 모드·배지), collection.js, festivals.js, chat.js, markers.js, meta.js, postAuth.js
- `api/client.js`: 콜드스타트 대응
  - 첫 요청은 타임아웃을 길게 잡고 자동 재시도를 한 번 합니다.
  - 이때 WakingBanner가 뜹니다.
- 기타: `utils/`, `composables/`(useBasePoint 등), `data/`(chatSuggestions 등), `styles/`(tokens.css 디자인 토큰)

### 명령 (`frontend/` 폴더에서)
- 단위 테스트: `npm run test` (= `vitest run`)
- 로컬 e2e: `npx playwright test`
  - 시작 전에 `E2E_PYTHON=C:\Users\SSAFY\Desktop\JinjuHub\backend\.venv\Scripts\python.exe`를 설정하세요.
  - 백엔드는 fixture DB로, 프론트는 Vite dev 서버로 자동으로 뜹니다. 라이브 사이트는 건드리지 않습니다.
  - **`BASE_URL`과 `LIVE_URL`은 설정하지 마세요.** 설정하면 라이브를 대상으로 돕니다.
- 개발 서버: `npm run dev`
  - API 주소는 `VITE_API_BASE_URL`(/api 없이)로 지정합니다.
  - 로컬 백엔드를 띄울 때 실제 키는 넣지 마세요. 채팅은 키가 없으면 결정적 fallback으로 답합니다.

## 4. 프론트엔드 고도화 백로그 (검증 완료 항목만)

### 근거 자료
- 라이브 UX 점검 보고서와 스크린샷:
  - `C:\Users\SSAFY\Desktop\agy_tasks\jinjuhub-ux-live\UX_LIVE_REPORT.md`
  - `C:\Users\SSAFY\Desktop\agy_tasks\jinjuhub-ux-live\ux_shots\`
- Teamwork 정적 검증 보고서: `C:\Users\SSAFY\Desktop\agy_tasks\jinjuhub-verify\VERIFICATION_REPORT.md`
- 항목별 판정 근거(JSON):
  - `.superpowers/sdd/2026-11-04-jinjuhub/ux-live-findings-verified.json`
  - `.superpowers/sdd/2026-11-04-jinjuhub/agy-findings-verified.json`
  - `.superpowers`는 git-ignored입니다.

### 4-1. 우선 처리 (검증됨)

| # | 문제 | 원인과 위치 | 수정 방향 | 규모 |
|---|---|---|---|---|
| F1 | "Powered by Netlify" 배지가 데스크톱 챗봇 버튼·전송 버튼과 모바일 탭바의 `축제`·`더보기`를 가림. 모든 방문자에게 보임 | Netlify 무료 플랜 신규 프로젝트에서 엣지가 배지를 주입함 | **1차는 소유자가 Netlify에서 끄는 것**: Project configuration → General → Powered by Netlify badge, 재배포 불필요. 끈 뒤 시크릿 창에서 확인. 대안 (b): 데스크톱 런처·패널을 `md:bottom-20` 이상으로 올림. 모바일 탭바는 오프셋으로는 해결되지 않음 | S |
| F2 | `내 유등` 카드에 사진·주소·진주8경 배지가 없고, 삭제 컨트롤이 두 개(◇와 `빼기`)이며 정렬이 어긋남 | `stores/lanterns.js` snapshot()이 id·title·category·tags·lat·lng만 저장함. `components/lanterns/SavedList.vue` asPlace()가 다시 줄임. `views/LanternsView.vue`의 공유 목록 경로도 동일 | snapshot에 hero_image·summary·addr·jinju8_rank·is_collection(`?? null`) 추가, SavedList와 공유 목록에서 그대로 전달, 기존 저장분은 상세 조회 때 보강(backfill), 삭제 컨트롤을 하나로 정리. localStorage 버전 호환(마이그레이션) 테스트 필수 | S |
| F3 | 시연 모드에서 숙소 '현재 위치'를 누르면 '가상 내 위치' 툴팁 2개가 겹침 | `composables/useBasePoint.js` 라벨이 같음. `MapCanvas`가 같은 지점이어도 두 마커를 모두 그림 | 라벨을 `내 숙소 (가상 위치)`로 구분, 같은 지점이면 툴팁 하나만 표시 | S |
| F4 | 축제 카드에 '일정 미정 일정 미정'이 중복 표기됨 | `components/festival/FestivalCard.vue`가 상태 칩과 기간을 모두 표시함 | 기간이 status_label과 다를 때만 기간 표시 | S |
| F5 | 키보드 '본문 바로가기'(skip link)가 없음 | 레이아웃 | App 최상단에 skip link 추가, 포커스 이동 테스트 | S |
| F6 | 모바일 홈 날씨 카드가 지역명과 활동 추천을 숨겨 빈약함. 홈에서 날씨 요청이 중복됨 | `components/WeatherWidget.vue:94-98` 클래스가 compact가 아닐 때도 잘라냄. 위젯 인스턴스마다 따로 fetch함 | 잘라내기는 compact일 때만 적용, 날씨 요청을 스토어나 in-flight 공유로 중복 제거 | S |
| F7 | 모바일 레이어 겹침: 바텀시트(half/full)가 챗봇 버튼을 덮고, `더보기` 메뉴는 챗봇 버튼 아래에 깔림 | `components/ChatWidget.vue`(z-[100]), `explore/BottomSheet.vue`(z 500), `layout/AppTabBar.vue`(z-[59]/[61]) | z-index 체계 일원화(토큰화). 시트가 펼쳐지거나 더보기가 열리면 챗봇 버튼을 숨기거나 위치를 조정 | M |

### 4-2. 개선 과제 (정적·라이브 보고서 공통, 우선순위 순)

| # | 과제 | 위치 | 비고 |
|---|---|---|---|
| U1 | 모바일 하단 탭바에 `홈` 탭 추가 | `layout/AppTabBar.vue` | 탭 5개로 늘어나므로 터치 영역 유지 |
| U2 | 명도 대비 보정. `--text-faint: #94a3b8`(흰 배경 2.56:1)를 4.5:1 이상으로, 검색 placeholder 포함 | `styles/tokens.css` | WCAG AA |
| U3 | 모바일 헤더에 검색 진입 버튼(🔍) 추가 → `/explore` 검색창으로 포커스 | `layout/AppHeader.vue` | |
| U4 | 모바일 최소 터치 영역 44×44px. 담기 버튼(36px), 필터 칩(34px), 작은 버튼(28px) | `place/PlaceCard.vue`, `explore/CategoryChips.vue`, `Pagination.vue` | 시각 크기는 두고 히트 영역만 확장해도 됨 |
| U5 | 축제 카드의 연계 장소를 '행사 장소 1' 대신 실제 장소명으로 | `festival/FestivalCard.vue` | API가 venue 이름을 주는지 먼저 확인 |
| U6 | 탐색 화면에서 담기 해제 시 실행 취소(Undo) 스낵바 | `views/ExploreView.vue` | LanternsView의 Undo 패턴 재사용 |
| U7 | 축제 타임라인 모바일 가로 스크롤(12개월 그리드가 압축되어 잘림) | `festival/FestivalTimeline.vue` | |
| U8 | Pretendard 웹폰트 로드, 폼 필드에 `id`/`name` 부여 | `index.html`, 폼 컴포넌트 | 라이브 콘솔 경고 |
| U9 | 홈 진주8경 카드에 hero_image 썸네일 표시, 배지 진열장에 배지별 아이콘 | `views/HomeView.vue`, `lanterns/BadgeShelf.vue` | 이미지는 잘라내지 말 것 |
| U10 | 첫 점등 토스트 문구에 배지 획득을 명시: '첫 유등을 밝혔어요! · 배지 「첫 등불」 획득' | `lanterns/CelebrationToast.vue` | 모달 복원은 하지 않음. e2e·단위 테스트 문구 함께 수정 |
| U11 | 문체(해요체·하십시오체) 통일, 카테고리 용어·색 통일('관광지' 대 '명소') | `PlaceDetailView`, `DataSourcesView`, `utils/constants.js`, `utils/format.js` | 저우선 |
| U12 | 데이터 출처 페이지에 소스 상태 `skipped` 라벨 추가 | `views/DataSourcesView.vue`, `utils/constants.js`(sourceLabel) | 백엔드에 새 상태값이 생김 |

### 4-3. 하지 말 것 (검증 결과 틀린 지적)
- **D-02 "Safe Area 겹침"을 단독으로 고치지 마세요.**
  - `viewport-fit=cover`가 없으면 iOS는 홈 인디케이터 위까지만 화면을 씁니다. 지금은 결함이 아닙니다.
  - 엣지 투 엣지가 필요해지면 `viewport-fit=cover`, `env(safe-area-inset-bottom)` 패딩, 의존 오프셋(챗봇 `bottom-[72px]`, 바텀시트 등)을 한 번에 바꿔야 합니다.
- **'첫 등불' 배지 모달을 복원하지 마세요.** 첫 점등 때 토스트로 축하하는 것은 의도한 설계입니다(런북 8단계).
- 레이트리밋 키(`backend/app/core/ratelimit.py`)와 로그 마스킹은 건드리지 마세요. 라이브 검증으로 정상 확인했고, Teamwork가 제안한 수정은 오히려 취약점을 만듭니다.

### 4-4. 프론트 범위 밖 (참고: 파이프라인 + DB 재생성 필요)
- **촉석루·의암 중복 POI**
  - 진주8경 항목(tourinfo 621/622)이 일반 항목(504/292)과 `force_split`되어 있습니다(`pipeline/curation`).
  - 그 결과 상세 페이지에서 자기 자신의 중복이 '0m 추천'으로 뜹니다.
- **'밤의 남강' 배지 진행도 0/2**
  - night_view 태그가 중복 중 큐레이션되지 않은 쪽에 붙어 있습니다.
  - `pipeline/curation/tags.yaml`에서 ID로 고정해야 합니다.
- **소개 요약문 절단**
  - '2026년 4. 24.' 같은 숫자 뒤 마침표에서 문장이 끊깁니다.
  - `pipeline/jinju_pipeline/merge.py`의 `_summary` 정규식 문제입니다.
- 위 세 가지는 파이프라인 수정 후 `python -m jinju_pipeline run --from-raw`로 **오프라인** 재생성해야 합니다. 네트워크·키는 필요 없고, ID 집합이 변하지 않았는지 반드시 확인합니다.
  - 프론트 작업과 섞지 말고 별도 브랜치에서 하세요.

## 5. 남은 소유자 결정 사항
- Netlify 배지 끄기(F1)
- feat → main 병합 동의, 배포 브랜치를 main으로 전환할지 여부
- collection30 초안(`pipeline/curation/collection30.yaml`, `status: draft`) 확인
- GitHub secret `DATA_GO_KR_KEY` 등록(주간 data-refresh 워크플로용)
- (참고) agy 스킬 변경분은 `C:\Users\SSAFY\Desktop\claude-skills`의 `feat/agy-delegate-browser-allowlist` 브랜치에 있고 push하지 않았습니다.

## 6. agy 브라우저 사용 시 주의
- 라이브 사이트를 브라우저로 확인하려면 다음 규칙을 따르세요.
  - 소유자의 일상 Chrome은 원격 디버깅을 **끈 상태**로 두세요. 켜져 있으면 agy가 로그인된 그 Chrome을 조작할 수 있습니다.
  - 확인할 때는 일회용 프로필의 별도 Chrome을 쓰세요.
  - 챗봇 칩·전송, 게시판 제출은 누르지 마세요.
- 비용·데이터 위험 없이 마음껏 클릭하려면 **로컬 dev 서버와 로컬 fixture 백엔드**를 쓰세요.
  - 로컬에서는 채팅이 키 없이 fallback으로 답하고, 게시판은 로컬 SQLite에 씁니다.

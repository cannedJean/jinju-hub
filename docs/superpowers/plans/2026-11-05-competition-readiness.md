# JinjuHub 경진대회 대비 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `feat/frontend-polish` 브랜치의 리뷰 지적(R-01 ~ R-19)을 고쳐, 시연 화면과 제출 문서에 거짓·과장 문구가 없고 "완료"로 보고된 기능이 실제로 동작하는 상태로 만든다.

**Architecture:** 변경은 `frontend/`와 `docs/`에 한정한다. 랜딩의 숫자는 하드코딩하지 않고 `/api/data/report` 응답에서 읽는다. 레이어 순서는 Tailwind `zIndex` 한 곳에서 정의한다.

**Tech Stack:** Vue 3, Vite, Pinia, Tailwind, Leaflet, vitest, Playwright(로컬 fixture).

**Spec:**
- 리뷰 결과(지적별 근거와 수정 방향): `docs/reviews/2026-11-05-frontend-polish-review.md`
- 인수인계 문서(규칙, 백로그 원문): `docs/handoff/2026-11-05-frontend-handoff.md`, `docs/handoff/2026-11-05-competition-handoff.md`
- 디자인 사양: `docs/superpowers/specs/2026-11-04-jinjuhub-design.md`
- 대회 포스터: `docs/competition/2026-bigdata-contest-poster.png`

## Global Constraints

- 작업 브랜치는 `feat/frontend-polish`. `feat/jinjuhub-mvp`와 `main`에는 push·병합하지 않는다(둘 다 프로덕션 배포로 이어진다).
- 라이브 `https://jinjuhub-api.onrender.com/api/chat`에 요청을 보내지 않는다. 라이브 사이트에서 챗봇 추천 칩·전송 버튼, 게시판 제출을 누르지 않는다.
- `.env` 계열 파일을 읽거나 출력하거나 커밋하지 않는다.
- 백엔드·파이프라인 코드는 바꾸지 않는다. 필요해 보이면 보고서에 적는다.
- 사용자에게 보이는 문구에는 코드·데이터·출처로 확인되는 사실만 쓴다. 금지어: `1호`, `최초`, `혼잡`, 측정하지 않은 수치. `빅데이터`는 소유자 결정으로 제목에 유지한다(2026-11-05).
- 데스크톱 우선 반응형. 유등 상태는 localStorage 키 `jinjuhub.lanterns.v1`에만 저장하고 최상위 `version: 1`을 유지한다.
- 공공 이미지는 자르지 않는다(`object-contain`). OSM 출처 표기를 유지한다.
- 하지 말 것: Safe Area 단독 수정, 첫 등불 배지 모달 복원, 레이트리밋·로그 마스킹 수정.
- 태스크마다 실패하는 테스트를 먼저 쓴다. 클래스 이름이나 소스 문자열만 확인하는 테스트는 쓰지 않는다.
- 테스트 명령(`frontend/`에서): `npx vitest run`, 로컬 e2e는 `npx playwright test`(`BASE_URL`·`LIVE_URL` 미설정).
- 커밋은 태스크별로, Conventional Commits, 메시지에 R 번호를 넣는다.

## Review Focus

1. `/api/data/report`가 실패하거나 느릴 때(Render 콜드스타트 약 50초): 랜딩은 숫자 없는 문구를 보여야 하고 깨진 숫자나 `undefined`가 보이면 안 된다. → Task 1
2. 이 변경 전에 저장된 유등(사진·주소 필드 없음)과 밝힌 유등: 불러올 때 사라지면 안 되고, 상세 조회 후 사진이 채워져야 한다. → Task 3
3. 모바일 390px에서 바텀시트를 펼친 상태로 `더보기`를 열 때: 메뉴 3개가 모두 보이고 눌려야 한다. → Task 4
4. 대표 이미지가 없는 장소·이미지 로딩 실패: 카드는 대체 표시를 보여야 하고 재요청을 반복하면 안 된다. → Task 3, Task 8
5. 폰트 CDN이 막힌 발표장 네트워크: 화면은 시스템 폰트로 정상 표시돼야 한다. → Task 6

---

### Task 1: 랜딩 문구를 사실로 교정하고 숫자를 API에서 읽기 (R-01, R-02, R-03)

**Files:**
- Create: `frontend/src/stores/dataReport.js`
- Modify: `frontend/src/views/HomeView.vue:66-101`, `frontend/index.html`
- Test: `frontend/src/views/__tests__/HomeView.spec.js`, `frontend/src/stores/__tests__/dataReport.spec.js`

**Interfaces:**
- Produces: `useDataReportStore()` — state `data`(report 또는 `null`), getters `finalCount: number|null`, `cleanedCount: number|null`, `sourceCount: number|null`, action `load(): Promise<void>`(한 번만 요청, 실패는 삼키고 `data`는 `null` 유지). `fetchReport()`는 `src/api/places.js:36`에 있다.

- [ ] **Step 1: 실패하는 테스트 작성**

`dataReport.spec.js`:
```js
test('getters read the report', async () => {
  fetchReport.mockResolvedValue({ final_count: 1250, cleaned_count: 1356, sources: new Array(7).fill({}) })
  const s = useDataReportStore(); await s.load()
  expect([s.finalCount, s.cleanedCount, s.sourceCount]).toEqual([1250, 1356, 7])
})
test('a failed load leaves nulls and does not throw', async () => {
  fetchReport.mockRejectedValue(new Error('x'))
  const s = useDataReportStore(); await s.load()
  expect(s.finalCount).toBeNull()
})
test('load requests once', async () => { /* 두 번 호출 → fetchReport 1회 */ })
```
`HomeView.spec.js`에서 문구 정확 일치 단언 2개(부제, 칩 목록)를 지우고 다음으로 바꾼다:
```js
test('hero shows counts from the report', async () => {
  // report: final_count 1250, sources 7
  expect(hero.text()).toContain('1,250곳')
  expect(chips).toHaveLength(4)
  expect(chips[0].text()).toBe('📊 공공데이터 7종 → 1,250곳 통합·정제')
})
test('hero has no number when the report fails', async () => {
  expect(hero.text()).not.toMatch(/\d{3,}/)
  expect(chips[0].text()).toBe('📊 공공데이터 통합·정제')
})
test('hero never makes unverifiable claims', () => {
  expect(hero.text()).not.toMatch(/1호|최초|혼잡/)
})
test('first chip links to the data page', () => { /* to === '/about/data' */ })
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/views/__tests__/HomeView.spec.js src/stores/__tests__/dataReport.spec.js` → FAIL.

- [ ] **Step 3: 구현**

`HomeView.vue` 문구(정확히 이대로):
- H1(현재 문구 유지): `빅데이터와 AI로 밝히는 진주의 밤 · 머무르고 싶은 여행`
- 부제(숫자 있음): `진주시·한국관광공사 공공데이터로 정리한 {n}곳과 실시간 날씨를 반영한 추천. 낮의 촉석루부터 밤의 유등까지 나만의 체류형 여정을 만들어 보세요.`
- 부제(숫자 없음): `진주시·한국관광공사 공공데이터와 실시간 날씨를 반영한 추천. 낮의 촉석루부터 밤의 유등까지 나만의 체류형 여정을 만들어 보세요.`
- 칩 1(`router-link` → `/about/data`): `📊 공공데이터 {s}종 → {n}곳 통합·정제`, 실패 시 `📊 공공데이터 통합·정제`
- 칩 2: `🌙 문체부 선정 야간관광 특화도시 (2023)`
- 칩 3: `🤖 공공데이터 근거로 답하는 AI 여행 비서`
- 칩 4: `🏮 유등 모으기로 즐기는 진주 여행`
- `{n}`은 `finalCount.toLocaleString('ko-KR')`.

`index.html`(정적이므로 숫자 없음):
- title, og:title, twitter:title(현재 문구 유지): `JinjuHub | 빅데이터와 AI로 만나는 진주 관광`
- description 3곳: `진주시와 한국관광공사 공공데이터를 통합·정제해 지도, 날씨, AI 여행 비서로 안내하는 진주 여행. 낮의 촉석루부터 밤의 유등까지.`

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS. `e2e/live-smoke.spec.js`가 기대하는 홈 제목을 현재 H1에 맞춘다.

- [ ] **Step 5: 커밋** — `fix(home): replace unverifiable hero claims with report-backed copy (R-01 R-02 R-03)`

---

### Task 2: 문제 → 데이터 → 해결 스트립과 야경 필터 칩 (R-07, R-08)

**Files:**
- Create: `frontend/src/components/home/StoryStrip.vue`
- Modify: `frontend/src/views/HomeView.vue`(히어로 바로 아래에 삽입), `frontend/src/components/explore/CategoryChips.vue`
- Test: `frontend/src/components/home/__tests__/StoryStrip.spec.js`, `frontend/src/components/explore/__tests__/CategoryChips.spec.js`

**Interfaces:**
- Consumes: `useDataReportStore()`(Task 1).

- [ ] **Step 1: 실패하는 테스트 작성**
```js
// StoryStrip
test('data column shows report numbers and links to the data page', () => {
  expect(col('data').text()).toContain('공공데이터 7종 · 1,356건 → 1,250곳')
  expect(link('data').props('to')).toBe('/about/data')
})
test('data column hides numbers when the report is missing', () => {
  expect(col('data').text()).not.toMatch(/\d/)
})
test('solution links are deep links', () => {
  expect(solutionLinks()).toEqual(['/explore?tags=indoor', '/explore?tags=night_view', '/lanterns', '/festivals'])
})
// CategoryChips
test('night chip toggles the night_view tag', async () => {
  await chip('🌙 야경 명소').trigger('click')
  expect(emitted or query tags).toContain('night_view')
})
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/components/home src/components/explore/__tests__/CategoryChips.spec.js` → FAIL.

- [ ] **Step 3: 구현**
- `StoryStrip.vue`는 3칸(`data-test="story-problem|story-data|story-solution"`)이다.
  - 문제 칸 제목 `현장 문제`, 본문(숫자 없이): `진주 여행 정보는 여러 공공 사이트에 흩어져 있고, 지도·날씨·밤 시간대에 맞춰 고르기 어렵습니다.`
  - 데이터 칸 제목 `데이터`, 본문: `공공데이터 {s}종 · {cleaned}건 → {n}곳`(없으면 `공공데이터를 통합·정제했습니다`), 링크 `수집·정제 과정 보기` → `/about/data`
  - 해결 칸 제목 `해결`, 링크 4개: `비 오는 날 실내` → `/explore?tags=indoor`, `야경 명소` → `/explore?tags=night_view`, `내 유등` → `/lanterns`, `축제 일정` → `/festivals`
- `CategoryChips.vue`: 기존 `비 오면 실내` 칩과 같은 방식(`toggleTag`)으로 `🌙 야경 명소` 칩을 추가한다(`night_view`).

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS.

- [ ] **Step 5: 커밋** — `feat(home): problem-data-solution strip and night-view filter chip (R-07 R-08)`

---

### Task 3: 내 유등 카드 완성 — 기존 저장분 보강, 공유 목록, 밝힌 곳 표시 (R-10, R-11, R-12)

**Files:**
- Modify: `frontend/src/stores/lanterns.js`(`snapshot`, `verify`), `frontend/src/views/PlaceDetailView.vue`(`load`), `frontend/src/views/LanternsView.vue:54-101`, `frontend/src/components/lanterns/SavedList.vue:66`
- Test: `frontend/src/views/__tests__/LanternsView.spec.js`, `frontend/src/stores/__tests__/lanterns.spec.js`; `frontend/src/test/unit/LanternsF2.spec.js`의 동어반복 테스트 2개(삭제 버튼, 마이그레이션)는 지운다.

**Interfaces:**
- Produces: 저장 항목에 `metaV: 2` 필드. `lanterns.verify(detail)`는 상세 응답의 `hero_image, summary, addr, jinju8_rank, is_collection`을 항목에 반영하고 `metaV: 2`를 기록한다. `litAt, litOn, litMethod, savedAt`은 건드리지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**
```js
test('an item saved before this change gets its photo after the list loads', async () => {
  localStorage.setItem('jinjuhub.lanterns.v1', JSON.stringify({ version: 1, items: { 'jh-a': { id: 'jh-a', title: '촉석루', category: 'sight', tags: [], lat: 1, lng: 2, savedAt: '2026-10-01T00:00:00+09:00', litAt: '2026-10-02T00:00:00+09:00' } }, earnedBadges: {} }))
  fetchPlace.mockResolvedValue({ id: 'jh-a', hero_image: 'https://x/a.jpg', addr: '진주시', summary: 's', jinju8_rank: 1, is_collection: true })
  const w = await mountLanterns()
  expect(w.find('img').attributes('src')).toBe('https://x/a.jpg')
  expect(store.items['jh-a'].litAt).toBe('2026-10-02T00:00:00+09:00')
  expect(store.items['jh-a'].metaV).toBe(2)
})
test('an item without an image is fetched once, not on every mount', async () => { /* hero_image null → 두 번째 마운트에서 fetchPlace 0회 */ })
test('shared list shows photos and import keeps them', async () => { /* ?share= → img 렌더, import 후 items[id].hero_image 존재 */ })
test('a lit row says 밝힌 곳', async () => { expect(row.text()).toContain('밝힌 곳') })
test('opening a place detail backfills its saved lantern', async () => { /* PlaceDetailView.load 후 metaV === 2 */ })
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/views/__tests__/LanternsView.spec.js src/stores/__tests__/lanterns.spec.js` → FAIL.

- [ ] **Step 3: 구현**
- `snapshot()`과 `verify()`가 `metaV: 2`를 기록한다.
- `LanternsView.vue`의 기존 확인 루프(`verify(list)`)에서 `metaV !== 2`인 항목도 `fetchPlace` 대상에 넣고, 받은 상세를 `lanterns.verify(detail)`에 넘긴다.
- `PlaceDetailView.load()`에서 `place.value = data` 뒤에 `lanterns.verify(data)`를 호출한다.
- `loadShared()`의 map에 `hero_image, summary, addr, jinju8_rank, is_collection`을 추가한다(전체 상세를 넘기지 않는다).
- `SavedList.vue`: `it.litAt`이 있으면 `<span class="saved-row__lit">◆ 밝힌 곳</span>`을 DOM에 렌더링한다. CSS로 숨긴 버튼에 의존하지 않는다.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS, 이어서 `npx vitest run` 전체 PASS.

- [ ] **Step 5: 커밋** — `fix(lanterns): wire snapshot backfill, shared list fields and lit marker (R-10 R-11 R-12)`

---

### Task 4: 모바일 레이어 순서 (R-13)

**Files:**
- Modify: `frontend/tailwind.config.js`(`theme.extend.zIndex`), `frontend/src/components/explore/BottomSheet.vue:156`, `frontend/src/components/layout/AppTabBar.vue`, `frontend/src/components/ChatWidget.vue`, `frontend/src/views/ExploreView.vue`
- Create: `frontend/src/composables/useLayers.js`
- Test: `frontend/src/composables/__tests__/useLayers.spec.js`, `frontend/e2e/responsive.spec.js`; `frontend/src/test/unit/LayerHierarchyF7.spec.js`는 삭제한다.

**Interfaces:**
- Produces: `useLayers()` — 모듈 수준 공유 상태 `sheetExpanded: Ref<boolean>`, `moreOpen: Ref<boolean>`, computed `chatBubbleHidden`(둘 중 하나라도 참이면 참).
- zIndex 이름과 값: `sheet: 40`, `tabbar: 60`, `chat: 100`, `overlay: 110`, `menu: 120`, `toast: 600`.

- [ ] **Step 1: 실패하는 테스트 작성**
```js
// useLayers.spec.js
test('chat bubble hides while the sheet is expanded or the more menu is open', () => {
  const l = useLayers(); l.sheetExpanded.value = true
  expect(l.chatBubbleHidden.value).toBe(true)
})
```
`e2e/responsive.spec.js`(mobile 프로젝트)에 추가:
```js
test('more menu is fully clickable over an expanded sheet', async ({ page }) => {
  // /explore → 시트 half → 더보기 탭 → '데이터 출처' 클릭 → URL이 /about/data
})
test('chat bubble is hidden while the sheet is expanded', async ({ page }) => {
  await expect(page.getByRole('button', { name: '챗봇 열기' })).toBeHidden()
})
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/composables/__tests__/useLayers.spec.js` → FAIL, `npx playwright test e2e/responsive.spec.js --project=mobile` → 새 테스트 FAIL.

- [ ] **Step 3: 구현** — zIndex 값을 Tailwind 설정으로 옮기고 각 컴포넌트가 이름(`z-sheet` 등)을 쓴다. 바텀시트는 `sheet`(40)로 내린다. ExploreView가 `sheetSnap !== 'collapsed'`를 `sheetExpanded`에, AppTabBar가 메뉴 열림을 `moreOpen`에 반영한다. ChatWidget은 `chatBubbleHidden`이면 닫힌 말풍선을 렌더링하지 않는다(열린 패널은 유지).

- [ ] **Step 4: 통과 확인** — 두 명령 모두 PASS, 기존 e2e 18개도 PASS.

- [ ] **Step 5: 커밋** — `fix(layout): single z-index scale, sheet below tab bar, chat bubble yields (R-13)`

---

### Task 5: 중복 `명소` 칩 제거와 축제 장소명 (R-14, R-15)

**Files:**
- Modify: `frontend/src/utils/format.js:3`, `frontend/src/composables/useExploreQuery.js:8`, `frontend/src/components/festival/FestivalCard.vue:16`, `frontend/src/views/FestivalsView.vue`
- Test: `frontend/src/test/unit/CategoryTerminologyU11.spec.js`, `frontend/src/test/unit/FestivalCardU5.spec.js`, `frontend/src/views/__tests__/FestivalsView.spec.js`(신규)

- [ ] **Step 1: 실패하는 테스트 작성**
```js
test('explore has one chip per backend place category', () => {
  expect(CATEGORY_CODES).toEqual(['sight', 'culture', 'food', 'stay', 'festival', 'shopping', 'leisure', 'course'])
  expect(new Set(CATEGORY_CODES.map(categoryLabel)).size).toBe(CATEGORY_CODES.length)
})
// FestivalCard: 실제 응답 형태({ venue_place_ids: [...] })만 사용
test('venue names come from loaded markers', () => { /* markers 로드됨 → '진주성' */ })
test('neutral label when markers are not loaded', () => { /* 여러 곳 → '행사 장소 1', 한 곳 → '행사 장소 보기' */ })
test('festivals view loads markers', () => { expect(markers.load).toHaveBeenCalled() })
```
(`CATEGORY_CODES`의 순서는 현재 `CATEGORY_LABELS`에서 `tour`를 뺀 순서를 그대로 쓴다. 위 배열과 다르면 현재 순서에 맞춘다.)

- [ ] **Step 2: 실패 확인** — `npx vitest run src/test/unit/CategoryTerminologyU11.spec.js src/test/unit/FestivalCardU5.spec.js src/views/__tests__/FestivalsView.spec.js` → FAIL.

- [ ] **Step 3: 구현** — `CATEGORY_LABELS`에서 `tour`를 지운다. `CATEGORY_CODES`를 명시적 배열로 정의한다. `placeTitle()`에서 존재하지 않는 필드(`place_titles`, `place_title`, `place`, `location`) 분기를 지우고 위 중립 문구로 대체한다. `FestivalsView`가 마운트 때 `useMarkersStore().load().catch(() => {})`를 호출한다. `CategoryTerminologyU11.spec.js`용으로만 만든 re-export 모듈(`frontend/src/constants.js`)은 삭제한다.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS.

- [ ] **Step 5: 커밋** — `fix(explore,festival): remove duplicate category chip, real venue names (R-14 R-15)`

---

### Task 6: 폰트 적용과 폼 필드 이름 (R-16)

**Files:**
- Modify: `frontend/package.json`(의존성 `pretendard` 추가), `frontend/src/main.js`, `frontend/index.html`(CDN 링크 삭제), `frontend/src/styles/tokens.css:61`, `frontend/tailwind.config.js:45`, `frontend/src/views/ExploreView.vue:395,623`, `frontend/src/components/demo/DemoSettings.vue:61,74`, `frontend/src/components/lanterns/ShareDialog.vue:55`
- Test: `frontend/src/test/unit/FormAccessibility.spec.js`

- [ ] **Step 1: 실패하는 테스트 작성**
```js
test('the font family the CSS asks for is the one the stylesheet defines', () => {
  const css = fs.readFileSync(require.resolve('pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css'), 'utf8')
  const family = css.match(/font-family:\s*['"]([^'"]+)['"]/)[1]
  expect(tokensCss).toContain(`'${family}'`)
})
test('index.html loads no font from a CDN', () => { expect(indexHtml).not.toMatch(/cdn\.jsdelivr\.net/) })
test('every select and input in Explore, DemoSettings and ShareDialog has id and name', () => { /* 마운트 후 요소별 확인 */ })
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/test/unit/FormAccessibility.spec.js` → FAIL.

- [ ] **Step 3: 구현** — `npm i pretendard`(이 태스크에서만 설치 허용). `main.js`에서 `import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css'`. 두 폰트 스택 맨 앞에 `'Pretendard Variable'`을 넣는다. 정렬 select의 id는 `explore-sort`, `sheet-sort`.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS, `npx vite build --outDir "$TEMP/jh-build"` 성공.

- [ ] **Step 5: 커밋** — `fix(a11y): self-host Pretendard under the right family name, name form fields (R-16)`

---

### Task 7: 모바일 헤더 검색 진입 버튼 (R-17)

**Files:**
- Modify: `frontend/src/components/layout/AppHeader.vue:58-69`, `frontend/src/views/ExploreView.vue`
- Test: `frontend/src/test/unit/HeaderSearchU3.spec.js`(다시 작성)

- [ ] **Step 1: 실패하는 테스트 작성**
```js
test('mobile header has a search button and no inline input', () => {
  expect(w.find('input[type="search"]').exists()).toBe(false)
  expect(w.findComponent('[aria-label="장소 검색"]').props('to')).toEqual({ name: 'explore', query: { focus: 'search' } })
})
test('desktop header keeps the inline search', () => { /* input 존재 */ })
test('explore focuses the sheet search when asked', async () => {
  // route.query.focus === 'search' → sheetSnap 'half', document.activeElement.id === 'sheet-search', query에서 focus 제거
})
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/test/unit/HeaderSearchU3.spec.js` → FAIL.

- [ ] **Step 3: 구현** — 인라인 폼에 `v-if="!isMobile"`을 되돌린다. 모바일 전용 44×44 `router-link`(🔍)를 추가한다. ExploreView는 `route.query.focus`를 watch해 이미 `/explore`에 있을 때도 동작하게 한다. U3 커밋이 뒤집은 헤더의 `ml-auto` 조건을 `31c431e` 상태로 되돌린다.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS.

- [ ] **Step 5: 커밋** — `fix(header): mobile search entry button instead of a squeezed input (R-17)`

---

### Task 8: 진주8경 이미지 요청 1회, OG 이미지 (R-18, R-19)

**Files:**
- Modify: `frontend/src/stores/collection.js`, `frontend/src/views/HomeView.vue:17-40`, `frontend/index.html`
- Create: `frontend/public/og-image.png`(1200×630), `frontend/scripts/make-og-image.mjs`
- Test: `frontend/src/test/unit/Jinju8BadgeU9.spec.js`(다시 작성), `frontend/src/views/__tests__/HomeView.spec.js`

**Interfaces:**
- Produces: `useCollectionStore().heroImages`(`{ [id]: string }`), action `loadHeroImages(): Promise<void>` — `fetchPlaces({ sort: 'collection', size: 8 })`를 세션당 한 번 호출하고 `jinju8_rank != null`인 항목만 담는다. 실패는 삼킨다.

- [ ] **Step 1: 실패하는 테스트 작성**
```js
test('home loads jinju8 images with one list request', async () => {
  // /collection 응답은 { rank, id, title }만 포함
  expect(fetchPlaces).toHaveBeenCalledTimes(1)
  expect(fetchPlace).not.toHaveBeenCalled()
  expect(card(1).find('img').attributes('src')).toBe('https://x/1.jpg')
})
test('a second visit to home makes no new request', async () => { /* 재마운트 → fetchPlaces 여전히 1회 */ })
test('a card without an image shows the fallback', () => { /* data-test="jinju8-fallback" */ })
test('og:image points to a file that exists', () => {
  const p = new URL(ogImage).pathname
  expect(fs.existsSync(path.join('public', p))).toBe(true)
})
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/test/unit/Jinju8BadgeU9.spec.js src/views/__tests__/HomeView.spec.js` → FAIL.

- [ ] **Step 3: 구현** — HomeView의 `watch(jinju8, …fetchPlace…)` 블록을 지우고 스토어의 `heroImages`를 읽는다. `make-og-image.mjs`는 Playwright로 로컬 dev 서버(fixture 백엔드)의 홈 히어로를 1200×630으로 찍어 `public/og-image.png`에 저장한다(실행: `node scripts/make-og-image.mjs`). `index.html`에 `og:image:width`(1200), `og:image:height`(630), `og:image:alt`(`JinjuHub 홈 화면`)를 추가한다.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS.

- [ ] **Step 5: 커밋** — `perf(home): one request for jinju8 images; add the og image asset (R-18 R-19)`

---

### Task 9: 작은 수정 묶음 (Minor)

**Files:**
- Modify: `frontend/src/components/lanterns/CelebrationToast.vue`, `frontend/src/components/festival/FestivalTimeline.vue`, `frontend/src/views/ExploreView.vue`(undo 시간), `frontend/src/views/DataSourcesView.vue`, `frontend/src/styles/tokens.css`, `.gitignore`
- Test: 각 항목의 기존 spec을 동작 확인으로 고친다.

- [ ] **Step 1: 실패하는 테스트 작성** — 항목별 한 개씩:
  - 첫 점등 토스트 문구가 정확히 `첫 유등을 밝혔어요! · 배지 「첫 등불」 획득`.
  - 모바일 타임라인이 처음에 이번 달 칸을 화면 안에 둔다(`scrollLeft` 또는 시작 인덱스가 현재 월).
  - 탐색 화면 undo 스낵바가 5000ms 뒤에 사라진다(가짜 타이머).
  - 데이터 출처 페이지에서 상태 `reused_previous`가 경고 색 클래스를 유지한다(`31c431e`와 동일).
  - 보조 글자색이 `#f8fafc`와 `#f1f5f9` 배경에서 대비 4.5:1 이상(계산식으로 단언).
- [ ] **Step 2: 실패 확인** — `npx vitest run` → 위 5개 FAIL.
- [ ] **Step 3: 구현** — 위 5개를 고친다. `bg-subtle` 위의 `text-muted`는 `--text-nav`(#475569)를 쓴다. `.gitignore`에 `.agents/`와 루트 `image.png`를 추가한다. 미커밋 파일 `frontend/src/test/unit/ChallengerM2Stress.spec.js`는 통과하는 동작 테스트만 남겨 커밋하거나 삭제한다.
- [ ] **Step 4: 통과 확인** — `npx vitest run` 전체 PASS, `npx playwright test` 전체 PASS.
- [ ] **Step 5: 커밋** — `fix(frontend): toast copy, timeline start, undo window, status colour, contrast (minors)`

---

### Task 10: 제출 문서의 사실 교정과 근거 자료 (R-04, R-05, R-06, R-09)

**Files:**
- Modify: `docs/handoff/2026-11-05-frontend-polish-report.md`, `docs/DEMO_RUNBOOK.md`
- Create: `docs/competition/evidence.md`

- [ ] **Step 1: 보고서 교정** — 다음을 고친다.
  - `제1호 야간관광 특화도시` → `2023년 선정 야간관광 특화도시(2022년 인천·통영에 이은 2차 선정)`
  - `[정량·정성 성과]` → `[기대효과(가설)]`, 수치 `2배`, `60%`, `80%`, `검색 실패율 제로`, `120만 명` 삭제
  - `진주시 인허가 OpenAPI(S1~S5)` → `진주시 관광 OpenAPI 5종(관광지·음식점·축제·문화재·숙박) + 한국관광공사 TourAPI 2종`
  - `결측률 0%` → `필드 보유율 공개(운영시간 99%, 전화 84%, 좌표 67%, 이미지 47%, 소개 43%), 진주 밖 좌표 0건`
  - 공식 사이트 비교표에서 확인되지 않은 행(로그인 필수, 포기율, AI 기능 전무, 5~6단계 뎁스)을 삭제하거나 `미확인`으로 표시
  - 테스트 수를 커밋 기준 실제 값으로 갱신
- [ ] **Step 2: `evidence.md` 작성** — 개요서·PPT에 쓸 수 있는 사실만 표로 정리한다. 열: 주장, 값, 출처(파일 경로 또는 URL), 확인일. 최소 포함 항목:
  - 데이터: 원천 7종, 1,356건 → 106쌍 병합 → 1,250곳(`backend/app/data/report.json`), 카테고리별 수, 필드 보유율
  - 야간관광 특화도시 선정 연도(https://www.korea.kr/news/policyNewsView.do?newsId=148923653)
  - 대회 정보(포스터)
  - `공식 사이트 대비 클릭 수` 표는 빈 칸으로 두고 측정 방법(같은 목표 3개에 도달하는 클릭 수를 양쪽에서 센다)을 적는다. 소유자가 직접 채운다.
  - 문제 크기 통계(체류시간, 방문객 수)는 `출처 확보 필요` 목록으로 둔다. 출처 없는 숫자는 적지 않는다.
- [ ] **Step 3: 런북 보강** — `DEMO_RUNBOOK.md`에 추가: 시연 10분 전 Render 깨우기, 챗봇 실제 질문 1회로 폴백 표시가 없는지 확인(소유자만 수행), '밤의 남강' 배지는 진주성과 남가람 별빛길로 시연(8경 촉석루 카드는 쓰지 않음).
- [ ] **Step 4: 확인** — `grep -n "1호\|결측률 0%\|인허가 OpenAPI\|검색 실패율" docs/handoff/2026-11-05-frontend-polish-report.md` → 결과 없음.
- [ ] **Step 5: 커밋** — `docs: correct unverifiable claims, add competition evidence sheet (R-04 R-05 R-06 R-09)`

---

## 이 계획에 없는 것 (별도 계획 필요)

- 파이프라인(촉석루·의암 중복 POI, `night_view` 태그 확대, 요약문 절단): 데이터 병합 실패 위험 때문에 **진행하지 않기로 소유자가 결정했다**(2026-11-05).
- 제출물 작성(신청서, 개요서, PPT): 홈페이지 완성 후 소유자가 별도로 진행한다.
- 병합: 이 계획이 끝나고 재리뷰를 통과한 뒤 소유자 확인을 받아 `main`에 병합한다.

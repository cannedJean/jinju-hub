# feat/frontend-polish 코드리뷰 결과 (2026-11-05)

- 대상: `31c431e..f9a3430` (agy 작업, 커밋 19개, `frontend/`만 변경)
- 방법: 6개 관점 리뷰 후 지적마다 반박 검증 1회. 확정 47건(관점 간 중복 포함), 반박 0건, Minor 35건.
- 실행 결과: vitest 커밋 기준 55개 파일 / 291개 통과(미커밋 파일 포함 시 56 / 309), 로컬 e2e 18/18 통과.
- 판정: **병합 불가.** 아래 R-01 ~ R-19를 고친 뒤 다시 리뷰한다. 수정 계획은 `docs/superpowers/plans/2026-11-05-competition-readiness.md`.

아래는 중복을 합친 주요 지적이다. `근거`와 `수정`은 검증자가 확인한 내용이다.

## R-01 [critical] 랜딩 칩 "대한민국 1호 야간관광 특화도시"는 사실이 아님 (진주는 2023년, 2차 선정)

- 위치: `frontend/src/views/HomeView.vue:80`
- 근거: 코드: `🌙 대한민국 1호 야간관광 특화도시` (HomeView.vue:80, 테스트가 문자열을 고정: HomeView.spec.js:65). 보고서도 반복: 2026-11-05-frontend-polish-report.md:38-39 "문체부·한국관광공사 지정 제1호 야간관광 특화도시", :171. 외부 사실: 문체부·한국관광공사는 2022년 "첫 번째 '야간관광 특화도시'로 '국제명소형'에 인천광역시, '성장지원형'에 경남 통영시를 선정" (https://www.smarttoday.co.kr/ko-kr/articles/24429). 2023년에 부산·대전(국제명소형), 강릉·전주·진주(성장지원형) 5곳 선정 (https://sateconomy.co.kr/news/view/1065576833104326, https://kpinews.kr/newsView/179555250762435 — 2023-02-28 진주 선정, 콘셉트 '리버나이트'). 정책브리핑 2024-01-31: "2023년 선정된 대전, 부산, 강릉, 전주, 진주를 포함해 모두 10곳" (https://m.korea.kr/news/policyNewsView.do?newsId=148925410).
- 수정: 제안된 수정 방향은 맞지만 칩 문구가 길어 모바일(13px, flex-wrap)에서 두 줄로 넘어갈 수 있으니 더 짧게 쓰는 편이 낫다.

1. `HomeView.vue:80`을 `🌙 2023 문체부 선정 야간관광 특화도시`로 바꾼다. 브랜드를 살리려면 `🌙 야간관광 특화도시 '리버나이트 진주'`도 가능하다.
2. `HomeView.spec.js:65`의 고정 문자열을 같은 문구로 바꾼다.
3. untracked 보고서 `docs/handoff/2026-11-05-frontend-polish-report.md`의 38-39행, 78행, 171행에서 '제1호/1호'를 "2023년 문체부·한국관광공사 야간관광 특화도시(성장지원형) 선정"으로 고치고 정책브리핑 출처를 붙인다. 커밋하거나 개요서·PPT로 옮기기 전에 해야 한다.
4. 발표 자료에서 '최초/1호/유일' 같은 서열 표현은 출처가 없으면 쓰지 않는다.

## R-02 [important] 서브헤드 "실시간 분석으로 혼잡은 피하고" — 혼잡·실시간 분석 기능이 제품에 전혀 없음

- 위치: `frontend/src/views/HomeView.vue:68`
- 근거: 코드: `1,250개 공공 데이터와 실시간 분석으로 혼잡은 피하고, 숨은 명소는 더 깊게.` 전체 저장소(frontend/src, backend/app, pipeline)에서 `혼잡|congest|crowd|실시간` 검색 결과는 이 문구와 그 테스트(HomeView.spec.js:53)뿐. DATA.md §1.2는 "KTO 빅데이터 방문자수 … API: 이번 범위 밖", "버스(실시간/정류장): 비목표"로 명시적으로 제외. 같은 사이트의 /about/data 는 정반대로 말함: DataSourcesView.vue:117-118 "서비스는 실행 중에 외부 API를 직접 호출하지 않고, 미리 만들어 둔 데이터만 사용합니다." 실시간인 것은 기상청 초단기예보 위젯 하나(weather_service.py:16, 캐시 있음)뿐.
- 수정: 제안된 교체 문구는 사실과 맞으므로 그대로 써도 된다(1,250곳과 소스 7종을 DB에서 확인했고, 날씨 연동과 숙소 기준 탐색도 실제 기능이다). 보완할 점은 다음과 같다.

1. "혼잡"과 "분석"을 빼고 실제 기능만 말한다. 예: `진주시·한국관광공사 공공데이터 7종을 정제·병합한 1,250곳을 지도 하나로. 지금 날씨와 내 숙소 위치에 맞춰, 낮의 촉석루부터 밤의 남강까지 체류형 여정을 만드세요.` 분산 서사를 유지하려면 "진주8경·유등 30선 큐레이션으로 숨은 명소까지"처럼 수단을 큐레이션으로 명시한다.
2. `frontend/src/views/__tests__/HomeView.spec.js:53`의 기대 문자열을 함께 고친다.
3. 같은 문구가 `docs/handoff/2026-11-05-frontend-polish-report.md:75`에 있다. 같은 보고서의 "체류시간 2배 연장 · 탐색 클릭 60% 단축" 같은 측정되지 않은 성과 수치와 함께 PPT·개요서로 옮겨지지 않게 정리한다.
4. "1,250"은 주간 파이프라인 갱신 때 바뀔 수 있는 하드코딩 값이다. `/api/meta`의 집계로 표시하거나 "1,200여 곳"처럼 쓴다. `HomeView.vue:74`의 칩과 `index.html`의 메타 설명 3곳도 같은 값을 쓴다.
5. 혼잡 분산을 실제로 주장하려면 한국관광 데이터랩의 진주시 방문자 집계를 정적 JSON으로 넣어 "방문 통계 기반"으로 표기한다. 이 경우 `DATA.md` §1.2의 범위 제외 문구와 `/about/data`의 출처 표도 갱신해야 한다. "실시간"이라는 표현은 쓰지 않는다.

## R-03 [important] "1,250+ 공공 빅데이터" — 단위·표현이 부정확하고 '빅데이터'로 방어 불가, 숫자는 3곳에 하드코딩

- 위치: `frontend/src/views/HomeView.vue:74`
- 근거: `📊 1,250+ 공공 빅데이터` (:74), `1,250개 공공 데이터` (:68), index.html:10/18/23 `진주시 1,250개 공공 데이터와 AI가 추천하는 맞춤형 야간관광`. 실제 데이터(backend/app/data/places.db 읽기 전용 조회, report.json): places 1,250행 = '장소' 수이지 데이터셋 수가 아님. 정확히 1,250이라 '+'는 틀림. 원천은 2개 기관 7개 엔드포인트(진주시 관광 OpenAPI 5종 190/267/9/589/94 + TourAPI 199/8) 합계 1,356건 → 106쌍 병합 → 1,250. 그중 좌표가 있어 지도에 찍히는 것은 838곳(67%), 대표 이미지 47%, 소개글 43%, 이미지·좌표·소개가 모두 있는 곳은 459곳. 1,250 중 578곳(46%)이 문화재 목록(culture). 숫자는 하드코딩인데 /api/meta 가 `categories: list[CategoryCount]`(schemas/places.py:86-91)를, /api/data/report 가 `final_count`를 이미 제공하며 DataSourcesView는 그 값을 표시한다. data-refresh 주간 워크플로(handoff §5)가 돌면 랜딩과 /about/data 숫자가 어긋난다.
- 수정: Keep the proposed direction, with four adjustments.

1. **Update the spec in the same change.** `frontend/src/views/__tests__/HomeView.spec.js:43-82` pins the chip, subtitle and meta strings, so vitest fails otherwise. Add cases for meta loaded (number shown) and meta failed (number-free fallback).
2. **Read the count from the meta store.** In HomeView, call `useMetaStore().load()` in `onMounted` and compute the total as the sum of `meta.data.categories[].count`. The store already swallows errors. Chip text: `공공데이터 7종 → {n}곳 통합·정제`, falling back to `공공데이터 7종 통합·정제`, as a `router-link` to `/about/data`.
3. **Fix the subtitle too.** Change `1,250개 공공 데이터` at `:68` to a unit-correct phrase such as `진주시·한국관광공사 공공데이터로 정리한 {n}곳`. Keep `index.html` number-free, since it is static.
4. **Soften the wording selectively.** Drop "맞춤형". Reword "AI가 추천하는" to "AI 여행 비서가 안내하는" instead of deleting it, because the Claude chat assistant does recommend places.

"빅데이터" also appears in the H1 (`:67`) and in the `<title>`, `og:title` and `twitter:title`. Decide those together with the chip, so the claim is not removed in one place and left in four others.

## R-04 [important] 보고서가 측정한 적 없는 '성과' 수치를 사실처럼 기재 — 개요서·PPT로 옮기면 허위 성과

- 위치: `docs/handoff/2026-11-05-frontend-polish-report.md:69`
- 근거: :69 `[정량·정성 성과] 체류시간 2배 연장 · 외곽 상권 분산 · 탐색 클릭 60% 단축`; :169 `인지 부하 80% 감소: 원하는 관광 정보에 최대 2회 터치 이내 즉각 도달`; :173 `검색 실패율 제로`; :163 `전수 조사하여 … 모든 평가 지표에서 공식 포털을 압도`. 저장소에는 사용자 테스트, 로그 분석, 클릭 수 계측 코드·자료가 없다. 유등 상태는 사양상 localStorage 전용(handoff §2-5)이라 체류시간·분산 효과를 서버에서 집계할 수단 자체가 없다. '검색 실패율 제로'는 코드와도 불일치: places_repo.py:143 trigram FTS는 토큰 3글자 이상일 때만 쓰고 그 외는 LIKE이며, 오타 교정 기능은 없다(보고서 :173은 공식 사이트의 '오타 시 0건'을 약점으로 들지만 JinjuHub도 동일).
- 수정: Keep the proposed fix (do not carry the numbers into the 개요서 or PPT; relabel or measure), with three sharpenings:

1. **Edit the report itself.** Change line 69's box label from `[정량·정성 성과]` back to `[기대효과(가설)]`, matching agy's own upstream wording, and delete "2배", "60%" and "80%" unless measured.
2. **Fix the search row at line 173.** Replace "검색 실패율 제로" with the accurate claim: substring search via trigram FTS for tokens of 3+ characters and LIKE below that, with no typo correction. Drop the typo comparison against the official site, or actually add a fuzzy fallback (rapidfuzz is already used in the ETL).
3. **Replace the click and depth claims with a reproducible count.** Count the clicks needed to reach the same three targets on tour.web and on JinjuHub, and record the paths in a table. This needs no user sample and can stand in for the 60% and 80% figures.

"체류시간 2배" cannot be measured before the 11/18 presentation and should appear only as a target KPI with a measurement plan.

## R-05 [important] 보고서 1.3절 데이터 엔지니어링 주장 중 "인허가 OpenAPI"와 "결측률 0%"는 거짓 — 자사 /about/data 화면과 모순

- 위치: `docs/handoff/2026-11-05-frontend-polish-report.md:53`
- 근거: :53 `한국관광공사 TourAPI + 진주시 인허가 OpenAPI(S1~S5)` — DATA.md §1.1의 S1~S5는 진주시 관광 OpenAPI(`/openapi/tour/tourinfo.do`, restaurant, festival, asset, lodging)이고, §1.2는 "data.go.kr 진주 파일데이터(음식점 인허가 대장 6,898건…): … 노이즈"로 인허가 데이터를 명시적으로 제외. :54 `결측률 0%` — report.json completeness: hero_image 0.4704, overview 0.428, phone 0.8432, hours 0.9928, coords 0.6704 (좌표 없는 장소 412곳, 음식 308곳 중 좌표 153곳·숙박 97곳 중 49곳). DataSourcesView.vue:197-215 '정보 보유율' 막대가 이 값을 그대로 화면에 표시한다. 0인 것은 `out_of_bbox_final`(진주 밖 좌표) 뿐. 참인 부분: rapidfuzz 병합(merge.py:13, fuzzy_name 31쌍), 좌표 x/y 역전 자동 판별(clean/coords.py:1), 비동기 병렬 수집(collect.py:67 asyncio.gather).
- 수정: 제안된 교정 문구는 대체로 타당하다. 지오코딩 근거도 DATA.md:67, :230에서 확인된다. 다음 네 가지를 보완한다.

1. **수치는 report.json 기준으로 쓴다.** `/about/data` 화면이 보여주는 값은 1,356건 → 106쌍 → 1,250곳이다. DATA.md:240-241은 1,358건/108쌍으로 조금 달라서, 그쪽을 인용하면 다시 화면과 어긋난다.
2. **:53 교정안:** `진주시 관광 OpenAPI 5종(S1~S5: 관광지·음식점·축제·문화재·숙박) + 한국관광공사 TourAPI 2종 비동기 병렬 수집`
3. **:54 교정안:** `rapidfuzz 중복 병합(106쌍), 좌표 x/y 역전 보정, 진주 밖 좌표 0건, 필드 보유율(운영시간 99%·전화 84%·좌표 67%·이미지 47%·소개 43%) 투명 공개 + 품질 게이트(coords_thresholds)로 회귀 차단`
4. **:176의 `결측 보정 지표`도 `필드 보유율 지표`로 고친다.** 실제로는 결측을 보정하지 않고 비워 둔다.

개요서나 발표 자료를 만들 때는 이 보고서 문구를 복사하지 말고 report.json과 DATA.md에서 직접 수치를 가져온다.

## R-06 [important] 보고서 5절의 공식 사이트(tour.web) 비교에 사실과 다른·확인되지 않은 주장이 다수

- 위치: `docs/handoff/2026-11-05-frontend-polish-report.md:173`
- 근거: :173 공식 사이트 `AI 질의응답 기능 전무` — 실제 tour.web 페이지에 챗봇 링크 `물어보세요!진주톡포유` (https://www.jinju.go.kr/ennabot/index.html)가 있음(WebFetch로 확인, AI 여부는 페이지에 명시 안 됨). :36/:169 `5~6단계 뎁스` — 확인된 메뉴는 대분류 6개, 대부분 3단계·일부 4단계. :172 `관리자가 등록한 정적 텍스트 글 목록뿐` — 페이지에 `여행맞춤검색`(누구와·언제 등 조건 필터) 패널과 `주변정보검색`(/here.web)이 존재. :174 `시청 공공 로그인 및 본인인증 필수`, `회원가입 포기율 극심` — 페이지에서 확인 불가(마이페이지·나의 여행스케줄 링크만 존재), 포기율은 출처 없음. :174 `개인정보 유출 우려 없는` — 챗봇 질문은 서버를 거쳐 외부 LLM으로 전송되고 게시판은 서버 DB에 저장되므로 과장. :177 `WCAG 2.1 AA 명도 대비(4.54:1) 준수` — 새 `--text-faint #64748b`는 흰 배경 4.76:1이지만 `--bg-subtle #f1f5f9`(tokens.css:40) 위에서는 4.34:1로 미달(직접 계산). :187 `랜딩 히어로에 감성적인 "남강의 밤" 비주얼` — HomeView 히어로(:66)는 단색 `bg-night-900` 섹션으로 이미지가 없음.
- 수정: Keep the proposed fix, with three corrections:
1. **Contrast**: state the pair precisely: "보조 텍스트 `#64748b`: 흰 카드 4.76:1, 페이지 배경 `#f8fafc` 4.55:1". Either drop the blanket "WCAG 2.1 AA 준수" or fix the real failing pair, `text-muted` on `bg-subtle` (4.34:1) at BoardListView.vue:134, DataSourcesView.vue:132, HomeView.vue:116, FestivalCard.vue:46 and PostDetailView.vue:250. Using `--text-nav #475569` on subtle backgrounds would pass. Extend ContrastU2.spec.js to cover `#f8fafc` and `#f1f5f9`.
2. **Privacy**: scope the wording to the 보관함: "보관함은 브라우저 localStorage에만 저장(서버 전송 없음)". Do not present it as a whole-service guarantee, since chat and the board go through the server.
3. **Chatbot row**: do not describe 진주톡포유 as "시나리오형" either, because its type is unverified. Write "공식 사이트: 챗봇 '진주톡포유' 링크 제공(방식 미확인)" until the owner has opened it and captured a screenshot.

Also replace "5~6단계" with "최대 4단계", remove "전수 조사" at :163, and either add a real 남강 야경 image to the hero or delete the "비주얼" claim at :187.

## R-07 [important] 헤드라인의 '야간관광' 축을 받치는 기능·데이터가 빈약 (night_view 4곳, UI 필터 없음, 야간 배지 미획득 버그 잔존)

- 위치: `frontend/src/views/HomeView.vue:67`
- 근거: H1 `빅데이터와 AI로 밝히는 진주의 밤`, 메타 `맞춤형 야간관광`, 보고서 :171 `night_view 야간 명소 특화 탐색 지원 … 야간관광 특화도시 정체성을 시각 및 기능적으로 완벽 구현`. 실제: places.db에서 night_view 태그는 4곳뿐(남가람 별빛길, 진주 촉석루, 진주성, 제5경 망진산 봉수대). `night_view`는 useExploreQuery.js:9의 URL 파라미터 화이트리스트에만 있고 .vue 어디에도 이를 켜는 UI가 없다(CategoryChips.vue는 `비 오면 실내`(indoor) 칩만 제공). '야간 지도'는 타일 색 반전 토글(MapCanvas.vue:48-50, map.css:17-18)로 야간 운영 정보와 무관. 인수인계 4-4는 '밤의 남강' 배지 진행도 0/2 버그가 파이프라인 측에 남아 있다고 기록.
- 수정: Keep (a) and (c) from the proposed fix, and narrow (b).

- **(a) Chip.** Add a `🌙 야경 명소` quick chip in `CategoryChips.vue` using the existing `toggleTag('night_view')` pattern. `night_view` is already in `TAG_CODES`, and the chat service and badge rules already consume the tag, so this is a few lines plus a spec.
- **(b) Badge.** Reword the bug as: the 촉석루 night_view tag lands on the non-curated duplicate (jh-515e2bff18) instead of `제1경 진주성 촉석루` (jh-ecd8569ad9). Pin the manual rules in `tags.yaml` by id, extend night_view to roughly 10–15 curated places, and regenerate offline on a separate pipeline branch, checking the id set is unchanged. Until then the badge is demonstrable by lighting 진주성 and 남가람 별빛길; put that in `DEMO_RUNBOOK.md` and avoid the 8경 촉석루 card for the night badge.
- **(c) Report wording.** Replace `night_view 야간 명소 특화 탐색 지원 / 완벽 구현` with the features that exist: night map tile toggle, night-aware chatbot recommendation, `밤의 남강` badge, and the night chip once (a) ships.
- **Fallback.** If (a) and (b) do not land before submission, demote night tourism from the H1 and meta to an application scenario.

## R-08 [minor] 랜딩이 대회 주제의 '문제 → 데이터 → 해결' 서사를 전달하지 못함 (R1은 문구 교체에 그침)

- 위치: `frontend/src/views/HomeView.vue:66`
- 근거: 히어로(:66-101)는 H1·서브문구·비링크 `<span>` 칩 4개·'지도에서 탐색' 버튼뿐이고, 그 아래는 축제 배너·날씨·유등 진행도·진주8경(:103-185). 어떤 현안을 왜 푸는지(문제), 근거 통계, 데이터 파이프라인으로 가는 진입점이 랜딩에 없다. /about/data 링크는 푸터(AppFooter.vue:16)와 헤더 '더보기' 메뉴(AppHeader.vue:35, AppTabBar.vue:14)에만 있다. 테스트(HomeView.spec.js:37-70)는 문자열 일치만 검사해 '주제 정렬'을 증명하지 않는다(9개 통과 확인).
- 수정: 히어로 아래 3칸 스트립 방향은 유지하되 다음처럼 조정합니다.

1. **문제 칸**: 출처 URL과 기준 연도를 붙일 수 있는 통계만 넣습니다(한국관광 데이터랩, 진주시 통계 등). 확보하지 못하면 숫자 없이 서술형 문제 정의만 둡니다. 완료 보고서의 '120만 명', '체류시간 2배', '클릭 60% 단축'은 출처가 없으므로 랜딩에 옮기지 않습니다.
2. **데이터 칸**: `fetchReport()`의 `sources.length`, `cleaned_count`, `final_count`를 바인딩해 '공공데이터 7종 · 1,356건 → 1,250곳'을 표시하고 `/about/data`로 링크합니다. 로딩·실패 시에는 숫자를 숨깁니다. 히어로와 `index.html`에 하드코딩된 '1,250'도 같은 값으로 맞춥니다.
3. **해결 칸**: 이미 URL로 재현되는 것만 딥링크합니다 — `/explore?tags=indoor`, `/explore?tags=night_view`, `/lanterns`, `/festivals`. 숙소 반경은 `/explore` 진입으로 연결합니다. AI 비서는 `ChatWidget`의 `isOpen`을 공유 상태로 올린 뒤 '열기'까지만 연결하고, 자동 전송은 넣지 않습니다(유료 키 보호).
4. **테스트**: 문자열 일치 대신 각 칸 링크의 `to` 값과, report 모킹 값이 화면에 반영되는지를 검사합니다.

우선순위는 발표 PPT의 서사 다음입니다. 데스크톱에서는 상단 메뉴 '데이터 출처'가 이미 한 번 클릭 거리이므로 시연 동선에서 바로 활용할 수 있습니다.

## R-09 [minor] "Claude AI 스마트 여행 비서" 칩 — 시연 중 폴백이 뜨면 화면이 스스로 'AI 답변을 만들 수 없다'고 표시

- 위치: `frontend/src/views/HomeView.vue:86`
- 근거: chat_service.py:1018-1059: 키 없음, 일일 한도(`chat_daily_limit` 기본 200, config.py:30) 초과, APIStatusError/타임아웃(20초), refusal, 빈 응답이면 모두 `fallback=True`의 결정적 답변("관련 장소: …, 운영시간과 일정은 방문 전 확인해 주세요.")을 돌려준다. 프론트는 ChatWidget.vue:157-161에서 `AI 답변을 만들 수 없어 검색 결과로 안내했어요.`를 표시. render.yaml:22와 DEPLOYMENT.md:23,43은 `ANTHROPIC_API_KEY`를 "마지막 챗봇 테스트 때 추가"로 적고 있어 운영 환경에 키가 실제로 설정됐는지는 이 리뷰에서 확인할 수 없다(규칙상 라이브 /api/chat 호출 금지). 검색부는 임베딩이 아닌 어휘·규칙 기반 랭킹(chat_service.py `_rank_places`)이다.
- 수정: Keep this as a low-cost copy and rehearsal item, not a code defect.

1. Softening the chip is optional, since it is truthful when the key is set. If it changes (for example "🤖 공공데이터 근거로 답하는 AI 여행 비서 (Claude)"), update `frontend/src/views/__tests__/HomeView.spec.js:66` in the same commit.
2. Extend the existing `docs/DEMO_RUNBOOK.md` instead of writing a new checklist: the owner confirms `ANTHROPIC_API_KEY` in the Render dashboard, sends one real question at T-10 and checks there is no fallback note, and remembers the daily budget is per process and capped at 200. Add a recorded clip or screenshot of a normal Claude answer to the slides.
3. Correct the scenario: a cold start shows the network-error banner, not the fallback note. The warm-up covers it.
4. Correct the retrieval description for Q&A: "질문을 규칙 기반으로 분석한 뒤, 장소 DB를 필드 가중치 × IDF 부분일치로 랭킹해 근거 문맥을 만들고 Claude가 그 문맥만으로 답한다. 벡터 임베딩은 쓰지 않는다." FTS5 trigram belongs to the Explore search only, not the chatbot.
5. Before the demo, try an off-topic question (for example "안녕") locally with the fake client to see whether the empty-context path shows the "AI 답변을 만들 수 없어" note. If it does, script the demo questions, or give that case a neutral note in a separate change.

## R-10 [important] F2 backfill is dead code: store.verify() has no caller, so lanterns saved before this change stay without photo/address/진주8경 badge

- 위치: `frontend/src/stores/lanterns.js:127`
- 근거: `grep -rn "verify(" src` finds only the definition (stores/lanterns.js:127), two spec files, and the unrelated local function `async function verify(list)` in LanternsView.vue:54 (tombstone check, which only uses the fetched detail for `canonical_id`). PlaceDetailView.vue and LanternsView.vue are not in `git diff --stat 31c431e..f9a3430`. Scratch test (in %TEMP%, seeded localStorage `jinjuhub.lanterns.v1` with a pre-F2 snapshot, marker alive, fetchPlace returning full detail, mounted LanternsView): `B verify() calls: 0 | img rendered: false | text has 진주8경: false | stored hero_image: undefined`. agy report line 96 claims "구버전 localStorage 데이터를 위한 verify() 자동 마이그레이션/backfill 함수 구현".
- 수정: The proposed fix is correct in substance: call `lanterns.verify(data)` in `PlaceDetailView.load()` after `place.value = data` (and in the canonical-redirect branch after `migrateId`), and backfill from `LanternsView`'s verify pass.

One refinement for the LanternsView part. Do not key the refetch on `hero_image`/`addr` being null or undefined. Many places have no image, and `verify()`'s first loop rewrites undefined to null, so those items would be refetched on every mount (`checked` is per component instance). Use a durable per-item marker instead:
- Set a field such as `metaV: 2` in `snapshot()` and in `verify()` when a detail has been applied.
- In `LanternsView.verify()`, extend `rest` to include items where `metaV !== 2` even if they are in the marker list.
- Pass the fetched detail to `lanterns.verify(p)`.

Keep the top-level `version: 1`, because `loadState` wipes the state on a version mismatch.

Add an integration test that seeds `jinjuhub.lanterns.v1` with a pre-F2 item, mounts `LanternsView` with `fetchPlace` mocked, and expects the image and 진주8경 badge after `flushPromises`, with `fetchPlace` not called again on a second mount. Add a second test that mounts `PlaceDetailView` and expects the stored snapshot to gain `hero_image`.

## R-11 [important] F2 shared-list path not touched: shared view and '내 목록에 가져오기' still strip the new fields

- 위치: `frontend/src/views/LanternsView.vue:101`
- 근거: Unchanged line: `.map((p) => ({ id: p.id, title: p.title, category: p.category, tags: p.tags, lat: p.lat, lng: p.lng }))`. Handoff F2: "views/LanternsView.vue의 공유 목록 경로도 동일 ... SavedList와 공유 목록에서 그대로 전달". Scratch test with fetchPlace returning hero_image/summary/addr/jinju8_rank: `C shared view | img rendered: false | text has 진주8경: false | has addr/summary: false`; after clicking import: `{"id":"jh-a",...,"hero_image":null,"summary":null,"addr":null,"jinju8_rank":null,"is_collection":null,...}`.
- 수정: The proposed fix is sound. The smallest version:

- In `loadShared()`, replace the narrowing map on line 101 with one that also carries `hero_image`, `summary`, `addr`, `jinju8_rank` and `is_collection`. Keep it an explicit pick rather than passing the whole `PlaceDetail`, so `overview`, `nearby`, `images` and `sources` do not end up in `sharedItems`.
- `importShared()` → `_put()` → `snapshot()` then stores full snapshots with no store change.
- Add a `?share=` test to `LanternsView.spec.js` asserting that the image and the '진주8경' badge render, and that `lanterns.items[id].hero_image` is non-null after import.

Optionally, wire the existing `verify()` backfill into `LanternsView`'s tombstone check (which already calls `fetchPlace`) or into `PlaceDetailView`. That would repair lanterns already imported with null metadata.

## R-12 [important] F2 'single remove control' hides the only lit (◆ 밝힌 곳) indicator in the 내 유등 list

- 위치: `frontend/src/components/lanterns/SavedList.vue:66`
- 근거: `:deep(.place-card__save) { display: none; }`. In PlaceCard.vue:103-114 that same button is the only element carrying lit state (`'is-lit': lit`, `◆`, aria-label `${title}: 밝힌 곳`). Scratch test on a lit saved item: `.is-lit elements: 1 ['place-card__icon place-card__save ... is-lit']` and `lit wording left once save button is hidden: false`.
- 수정: The proposed `:deep(.place-card__save:not(.is-lit)) { display: none; }` works: specificity (0,3,0) beats PlaceCard's `display:inline-flex`, and the lit button is already `disabled`, so it acts as a pure status indicator. It has two drawbacks:

- Lit rows regain a 44px icon stacked above the map button, which brings back some of the row-height misalignment F2 set out to remove.
- It cannot be regression-tested in vitest, because jsdom does not apply SFC scoped CSS.

A more robust fix is to render an explicit non-interactive marker in the DOM. Either:

- add a PlaceCard prop (e.g. `hideSave`) that replaces the toggle with `<span class="place-card__lit">◆ 밝힌 곳</span>` when `lit` is true, or
- add `<span v-if="it.litAt" class="saved-row__lit">◆ 밝힌 곳</span>` in `SavedList.vue`.

Then add a test that mounts SavedList with an item carrying `litAt` and asserts the text "밝힌 곳" is present outside `.place-card__save`.

## R-13 [important] F7 only raised two numbers: on mobile /explore the 더보기 menu is still covered, now by the bottom sheet (z 500)

- 위치: `frontend/src/components/layout/AppTabBar.vue:56`
- 근거: Whole F7 source change (`git show 7ecdf10`): backdrop `z-[59]` -> `z-[110]`, sheet `z-[61]` -> `z-[120]`. BottomSheet.vue:156 is still `z-index: 500` and sits in the root stacking context (ancestors `main.relative`, `.explore.relative`, `div.relative.flex-1` have no z-index; only `.jh-map` isolates, map.css:4-8). The UX live report confirms the same context: "바텀시트(z-index: 500)가 챗봇 플로팅 버튼(z-[100])을 완전히 덮어 가리는 현상". Menu is `fixed bottom-14 inset-x-0` (~156px tall, 3 items); collapsed sheet is 96px tall with the same bottom edge.
- 수정: The proposed fix is sound; three refinements.

1. **Smallest safe change:** lower `.bottom-sheet` z-index from 500 to a value below the tab bar and header (60), for example 40. It only has to beat the isolated `.jh-map` (z 0) and the `z-[3]` map overlays in ExploreView. The ExploreView toast (`z-[600]`, same root context) stays above it.
2. **Chat bubble follow-up:** once the sheet is below ChatWidget (100), the bubble will float over an expanded half or full sheet. Do the other half of the handoff's F7 ask and hide or move the bubble while the sheet is not collapsed or while 더보기 is open, for example via a shared `useLayers` state.
3. **Tests:** put the scale in one place (Tailwind `theme.extend.zIndex` or tokens.css custom properties) and replace the class-string assertions in LayerHierarchyF7.spec.js, which cannot detect occlusion. Add a mobile e2e step in responsive.spec.js that opens 더보기 on /explore and clicks 데이터 출처 and 시연 설정, with the sheet both collapsed and at half.

## R-14 [important] U11 regression: a second '명소' filter chip appears on Explore and returns 0 places

- 위치: `frontend/src/utils/format.js:3`
- 근거: a9351f3 added `tour: '명소',` to CATEGORY_LABELS. frontend/src/composables/useExploreQuery.js:8 has `export const CATEGORY_CODES = Object.keys(CATEGORY_LABELS)` and CategoryChips.vue:54 renders `v-for="code in CATEGORY_CODES"`. Verified with node: keys are now ['sight','tour','culture',...] and labels ['명소','명소','문화·역사',...]. 'tour' is a board-post category only (backend/app/schemas/board.py:7); places_repo.py:18 has no 'tour' place category and places_repo.py:164 just does `p.category IN (...)` with no validation. There is no `--cat-tour` token, so the chip dot is colourless, and it has no count.
- 수정: The proposed fix is right: remove `tour` from `CATEGORY_LABELS` in `frontend/src/utils/format.js`. The board label already lives in `POST_CATEGORIES` in `frontend/src/utils/constants.js`, which the same commit changed to '명소', so the U11 terminology goal is still met.

In `CategoryTerminologyU11.spec.js`, drop the `categoryLabel('tour')` and `CATEGORY_LABELS.tour` assertions and add a guard that `CATEGORY_CODES` equals the 8 backend place categories and that the labels are unique.

Optional hardening: define `CATEGORY_CODES` as an explicit array instead of `Object.keys(CATEGORY_LABELS)`, so adding a display label can never again create a filter chip.

Separate, pre-existing issue worth a follow-up: the `course` chip also returns 0 places against the bundled database.

## R-15 [important] U5 reported done, but venue names only appear if the visitor opened Explore or 내 유등 first; tests use API fields that do not exist

- 위치: `frontend/src/components/festival/FestivalCard.vue:16`
- 근거: placeTitle() reads `markersStore.byId?.get(id)`, then `festival.place_titles`, `place_title`, `place?.title`, `location`, else `venue_place_ids.length > 1 ? `행사 장소 ${index + 1}` : '진주시 일원'`. backend/app/schemas/festivals.py FestivalOut has none of place_titles/place_title/place/location (only venue_place_ids and addr). The markers store is loaded only in ExploreView.vue:177 and LanternsView.vue:60; FestivalsView.vue never loads it. Local DB: the only festival with venues is 진주남강유등축제 with 3 ids (진주성, 진주 촉석루, 남가람 별빛길). FestivalCardU5.spec.js passes by injecting `place_title: '진주성'` and `location: ...` into the fixture or by pre-filling the markers store.
- 수정: Minimal: in `FestivalsView.vue`, call `useMarkersStore().load().catch(() => {})` on mount. The card already re-renders through the `byId` getter, and all three current venue ids are in `/places/markers`.

In `placeTitle()`, remove the four non-existent field fallbacks and restore the neutral fallback: `행사 장소 ${i + 1}` for multi-venue, `행사 장소 보기` for single-venue. `진주시 일원` should not label a link to one specific place page.

Rewrite `FestivalCardU5.spec.js` against the real `FestivalOut` shape, covering three cases: markers loaded gives real titles; markers not loaded gives the neutral fallback; markers loaded after mount updates the label reactively. Add a `FestivalsView` test asserting that markers load is triggered.

Longer term, have the backend return venue titles (for example `venues: [{id, title}]` in `FestivalOut`), so the page does not need the roughly 1,250-marker payload just for three names.

## R-16 [important] U8 Pretendard is linked but never applied: the CDN stylesheet defines 'Pretendard Variable', the app asks for 'Pretendard'

- 위치: `frontend/index.html:32`
- 근거: index.html links `.../pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css`. Fetching that file: all 92 @font-face rules declare `font-family:'Pretendard Variable'`. The app's stacks are `font-family: 'Pretendard', 'Inter', ...` (src/styles/tokens.css:61) and `sans: ['Pretendard', 'Inter', ...]` (tailwind.config.js:45); 'Pretendard Variable' appears nowhere in src. The tests (FormAccessibility.spec.js:107-110, HomeView.spec.js:105) only check that index.html contains the string 'pretendard'. Separately, form fields still without id/name: the two sort `<select class="sort-select">` in ExploreView.vue:395 and :623, DemoSettings.vue:61 and :74, ShareDialog.vue:55.
- 수정: Take the finding's second option, not its first. The static stylesheet is 553,677 bytes against 53,513 for the variable one, so switching the link would make the render-blocking CSS about ten times larger.

1. Keep the current variable link and put the matching name first in both stacks:
   - `frontend/src/styles/tokens.css:61`: `font-family: 'Pretendard Variable', 'Pretendard', 'Inter', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;`
   - `frontend/tailwind.config.js:45`: the same order.
2. For a presentation PC on a filtered or offline campus network, self-hosting is more robust: `npm i pretendard` and import `pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css` in `main.js`, then drop the CDN link.
3. Add `id`/`name` to the remaining fields:
   - the two sort selects in `ExploreView.vue` (`:395`, `:623`), with distinct ids such as `explore-sort` and `sheet-sort` and `name="sort"`;
   - the `DemoSettings.vue` checkbox and date input;
   - the `ShareDialog.vue` input.
4. Replace the string-match tests with one that reads the linked CSS variant from `index.html` and asserts the first family in `tokens.css` and `tailwind.config.js` matches it (`variable` means `Pretendard Variable`).
5. Add a test that every `input`, `select` and `textarea` in the mounted Explore, DemoSettings and ShareDialog components has an `id` or `name`.
6. Correct the U8 row in the polish report: the font link landed in `f9cccf6`, and the warning is not yet removed.

## R-17 [important] Mobile header search is squeezed to roughly 60-120 px and duplicates the Explore search

- 위치: `frontend/src/components/layout/AppHeader.vue:67`
- 근거: AppHeader.vue:58-69 removes `v-if="!isMobile"` and shows the full input: `class="flex-1 max-w-[360px] min-w-0"` between a `shrink-0` logo and a `shrink-0` cluster (weather chip plus "◆ 0/30"). Estimated width budget at 360 px: 360 - 24 padding - 16 gaps - about 86 logo - about 141 cluster = about 93 px, minus 24 px input padding. In the weather error state ("날씨 오류 재시도", which the runbook says is normal without WEATHER_API_KEY) the cluster is about 176 px, leaving about 58 px. Input is `text-[13px]` with `py-1.5` (about 32 px tall). Backlog U3 asked for a 🔍 button that focuses the /explore search box.
- 수정: Implement U3 as the handoff specified.

- In `AppHeader.vue`, restore `v-if="!isMobile"` on the inline form.
- Add a mobile-only 44x44 `router-link` (🔍, `aria-label="장소 검색"`) to `{ name: 'explore', query: { focus: 'search' } }` in the right-hand cluster.
- In `ExploreView.vue`, when `route.query.focus === 'search'`, set `sheetSnap = 'half'` and focus `#sheet-search` on `nextTick`, then strip the `focus` param with `router.replace`. Handle the already-on-`/explore` case with a watch on the query.
- Replace `HeaderSearchU3.spec.js` with tests that assert the mobile button exists, the inline input is absent on mobile, and the focus behaviour works.
- Optionally raise `#sheet-search` to 16 px to stop the existing iOS focus zoom.

## R-18 [minor] Home fires 8 uncached place-detail requests on every visit; the test does not cover the production path

- 위치: `frontend/src/views/HomeView.vue:26`
- 근거: HomeView.vue:24-26 `if (!p.hero_image && !placeImages.value[p.id]) { fetchPlace(p.id)`. /api/collection items are `class Jinju8Item: rank, id, title` (backend/app/schemas/places.py), so `p.hero_image` is always undefined and all 8 detail calls always run. `placeImages` is a component-local ref, so they repeat on every Home mount; get_place sets no Cache-Control. Each response is a full PlaceDetail (overview, images, sources, nearby). Jinju8BadgeU9.spec.js:13 mocks `jinju8: [{..., hero_image: 'https://example.com/chokseoknu.jpg'}]`, a shape the API never returns, and never asserts the fetchPlace-sourced image.
- 수정: Use the finding's first option, as it needs no backend change: in the collection store (or a small cached helper), call `fetchPlaces({ sort: 'collection', size: 8 })` once, keep a module- or store-level `id -> hero_image` map, and have HomeView read from it. That makes one request per session instead of 8 per mount. Filter the result to items with `jinju8_rank != null` so the map stays correct if the ranked set ever changes.

Then rewrite the U9 spec so the mocked `/collection` payload contains only `{rank, id, title}`, assert that the image `src` comes from the secondary fetch, and assert the request count (one list call, no `fetchPlace`).

If a backend change is acceptable, adding `hero_image: str | None` to `Jinju8Item` and selecting it in `PlacesRepo.collection()` is cleaner still: zero extra requests, and the existing `p.hero_image` branch becomes the real path.

## R-19 [minor] og:image·twitter:image가 존재하지 않는 파일을 가리키며 SPA 폴백 때문에 HTML이 200으로 반환됨

- 위치: `frontend/index.html:19`
- 근거: index.html:19, 24 `https://jinju-hub.netlify.app/og-image.png`. `ls frontend/public` 결과는 `_redirects` 하나뿐. `_redirects`와 netlify.toml 모두 `/* /index.html 200`. 보고서 7-2는 '추가 권장'으로만 적고 R1은 완료 처리. 테스트는 메타 태그 문자열 존재만 확인한다.
- 수정: 제안된 수정 방향은 타당하다. 병합 전에 아래 둘 중 하나를 적용한다.

1. **에셋 추가(권장)**: 1200x630 PNG를 `frontend/public/og-image.png`로 넣는다. 수백 KB 이하로 유지하고, `og:image:width`, `og:image:height`, `og:image:alt`도 함께 넣는다.
2. **에셋 준비 전까지 태그 제거**: og:image와 twitter:image를 빼고 `twitter:card`를 `summary`로 낮춘다. 이 경우 `HomeView.spec.js:93`의 og:image 단언과 twitter:image 단언도 같이 고쳐야 테스트가 통과한다.

재발 방지로 테스트를 보강한다. og:image content의 경로를 파싱해 `frontend/public`에 해당 파일이 실제로 있는지 `fs.existsSync`로 확인하면, 문자열 존재만 보는 지금의 허점이 막힌다.

보고서의 R1 표기는 에셋이 들어가기 전까지 "메타 태그 구성 완료, og-image 에셋 미완"으로 고친다.

## Minor (35건, 제목만)

- [backlog-F] 더보기 backdrop now sits above the tab bar, header and demo banner (`frontend/src/components/layout/AppTabBar.vue:46`)
- [backlog-F] Report's test total depends on an uncommitted file (`frontend/src/test/unit/ChallengerM2Stress.spec.js:1`)
- [backlog-F] F5 test checks markup only; the handoff asked for a focus-movement test (`frontend/src/test/unit/App.spec.js:45`)
- [backlog-F] F3 tooltip suppression ignores the label and uses a different tolerance than useBasePoint (`frontend/src/components/map/MapCanvas.vue:205`)
- [backlog-F] F6: loading and error states of the home weather card are still truncated on mobile (`frontend/src/components/WeatherWidget.vue:65`)
- [backlog-U] U10 toast copy is not the copy the handoff specified: it does not name the badge and uses a term the UI does not have (`frontend/src/components/lanterns/CelebrationToast.vue:29`)
- [backlog-U] U11 is only partly done: no tone unification, no colour unification, plus an unused bridge module (`frontend/src/utils/constants.js:3`)
- [backlog-U] U2 token passes, but the test covers white only and the main search placeholders are still about 2.3:1 (`frontend/src/styles/tokens.css:36`)
- [backlog-U] U7 mobile timeline opens on January to June; today's marker and the October/November festivals are off-screen with no scroll cue (`frontend/src/components/festival/FestivalTimeline.vue:47`)
- [backlog-U] U9 Home fires 8 uncached place-detail requests per visit; the test relies on a hero_image field the collection API does not return (`frontend/src/views/HomeView.vue:21`)
- [backlog-U] U4 enlarges the controls on desktop too, and the tests only check class names (`frontend/src/components/explore/CategoryChips.vue:96`)
- [backlog-U] U12: 'reused_previous' silently changed from red to normal text, outside the item's scope (`frontend/src/views/DataSourcesView.vue:150`)
- [backlog-U] U3 commit flipped the header's ml-auto condition, changing the desktop layout (`frontend/src/components/layout/AppHeader.vue:83`)
- [backlog-U] U6 undo window is 4s, not the reported 5s or the LanternsView pattern, and the test does not go through the card UI (`frontend/src/views/ExploreView.vue:67`)
- [constraints] 홈 진주8경 카드가 마운트마다 상세 API를 8번 호출(N+1)하고 백엔드 필요 사항으로 보고하지 않음 (`frontend/src/views/HomeView.vue:26`)
- [constraints] 히어로·메타의 '1,250' 하드코딩 4곳과 '1,250+ 공공 빅데이터' 표현 (`frontend/src/views/HomeView.vue:74`)
- [constraints] 저장소 루트의 미추적 잔여물이 .gitignore에 없고 완료 보고서도 커밋되지 않음 (`.gitignore:1`)
- [constraints] 커밋 위생: 메시지와 내용이 어긋난 커밋 3건, 테스트 전용 죽은 모듈 1개 (`frontend/src/constants.js:1`)
- [constraints] U10 토스트 문구가 인수인계 지정 문구와 다르고 UI에 없는 용어 '보관함'을 사용 (`frontend/src/components/lanterns/CelebrationToast.vue:29`)
- [tests] live-smoke e2e still expects the old hero heading (`frontend/e2e/live-smoke.spec.js:37`)
- [tests] U10 test locks in copy that differs from the handoff wording and uses a term the UI does not have (`frontend/src/test/unit/CelebrationToastU10.spec.js:24`)
- [tests] U4, U7 and F5 tests check Tailwind class names on mounted DOM, not size, scrolling or focus (`frontend/src/test/unit/TouchTargetU4.spec.js:19`)
- [tests] U11 third test covers a re-export file created only so the test can import it (`frontend/src/test/unit/CategoryTerminologyU11.spec.js:21`)
- [tests] U6 undo test bypasses the UI and does not cover the timeout; report says 5 seconds, code uses 4 (`frontend/src/test/unit/ExploreUndoU6.spec.js:72`)
- [tests] OpenGraph test checks tag presence only; og:image points to a file that is not in the repo (`frontend/src/views/__tests__/HomeView.spec.js:93`)
- [competition] og:image / twitter:image 가 존재하지 않는 파일을 가리킴 (SPA 리다이렉트로 HTML이 200 응답) (`frontend/index.html:19`)
- [competition] R1 테스트가 거짓 문구를 정확 일치로 고정 — 사실 교정 시 테스트가 막고, 숫자 변경에도 취약 (`frontend/src/views/__tests__/HomeView.spec.js:64`)
- [ux-runtime] og:image and twitter:image point to a file that does not exist (`frontend/index.html:19`)
- [ux-runtime] Desktop header layout changed by an inverted ml-auto condition (`frontend/src/components/layout/AppHeader.vue:83`)
- [ux-runtime] 44 px touch targets were applied as visual size on every viewport (`frontend/src/components/explore/CategoryChips.vue:96`)
- [ux-runtime] Festival timeline on mobile opens on the empty half of the year (`frontend/src/components/festival/FestivalTimeline.vue:48`)
- [ux-runtime] Explore undo snackbar is 4 s, single-slot and hard to reach by keyboard (`frontend/src/views/ExploreView.vue:67`)
- [ux-runtime] U2 leaves search placeholders on light backgrounds at about 2.3:1 (`frontend/src/styles/tokens.css:36`)
- [ux-runtime] Jinju8 card image alt and fallback repeat the link text (`frontend/src/views/HomeView.vue:161`)
- [ux-runtime] Reported test totals include an uncommitted spec; new specs add router warnings (`docs/handoff/2026-11-05-frontend-polish-report.md:216`)

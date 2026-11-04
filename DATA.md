# DATA — JinjuHub 장소 데이터

JinjuHub의 장소 데이터는 `pipeline/`이 공공 API에서 모아 정제·병합·큐레이션한 뒤 SQLite 파일
`backend/app/data/places.db` 하나로 만든다. 백엔드는 실행 중에 외부 API를 부르지 않고 이 파일만 읽는다.
품질 리포트는 `backend/app/data/report.json`(백엔드 `/api/data/report`)과 `pipeline/data/work/<run_id>/report.md`에 남는다.

- 출처 문구(화면 표기): **"한국관광공사 TourAPI · 진주시 공공데이터"**, 지도 **"© OpenStreetMap contributors © CARTO"**
- 설계 근거: `docs/superpowers/specs/2026-11-04-jinjuhub-design.md` §3, §5

## 1. 데이터 소스

### 1.1 채택

| # | 소스 | 엔드포인트 | 인증 | 건수(2026-11-04 실행) | 역할 |
|---|---|---|---|---|---|
| S1 | 진주시 OpenAPI 관광지 | `https://www.jinju.go.kr/openapi/tour/tourinfo.do` | 없음 | 191 | **주 소스**: 개요·요금·운영시간·주차·좌표·이미지. 진주8경("제N경 …") 항목 포함 |
| S2 | 진주시 OpenAPI 음식점 | `…/openapi/tour/restaurant.do` | 없음 | 269 | 영업시간·휴무·메뉴/가격 (좌표 일부 누락) |
| S3 | 진주시 OpenAPI 축제 | `…/openapi/tour/festival.do` | 없음 | 9 | 시작/종료일, `undecided`(날짜 미정 문구) |
| S4 | 진주시 OpenAPI 문화재 | `…/openapi/tour/asset.do` | 없음 | 590 | 문화·역사 |
| S5 | 진주시 OpenAPI 숙박 | `…/openapi/tour/lodging.do` | 없음 | 94 | 숙박 |
| T1 | TourAPI KorService2 `areaBasedList2` | `https://apis.data.go.kr/B551011/KorService2` | 서비스키 | 199 (타입별 §1.1 표) | 보강: 커버리지·이미지·개요. 필터 `lDongRegnCd=48&lDongSignguCd=170`, contentTypeId 12/14/15/25/28/32/38/39 |
| T2 | TourAPI `detailCommon2`/`detailIntro2`/`detailImage2` | 동일 | 서비스키 | 199곳 상세 완료(`detail_pending` 0), 갤러리 27곳 | 상세(개요·운영시간·이미지 저작권 유형) |
| T3 | TourAPI `searchFestival2` | 동일 | 서비스키 | 8 | 축제 기간 교차검증 (`eventStartDate=올해0101`) |
| T4 | TourAPI `areaBasedSyncList2` | 동일 | 서비스키 | (증분 모드에서만) | 주간 증분 갱신·숨김(showflag=0) 반영 |
| C1 | 큐레이션(수작업) | `pipeline/curation/*.yaml` | — | 진주8경 8, 30선 30(초안), 배지 6 | 게이미피케이션·시연 품질 |

진주시 API 사실(2026-11-04 실측): `http://`는 `https://`로 302 리다이렉트, 페이지 파라미터 `page`(1부터)·`pageunit`(최대 10),
응답 키 total=`record_count`, items=`results`, `xposition`=위도·`yposition`=경도(뒤바뀌는 경우가 있어 값 범위로 판별).
같은 `idx`가 두 페이지에 중복으로 나오는 경우가 있다(병합 단계에서 하나로 합쳐짐).

**TourAPI 코드 검증(2026-11-04 실행, `verify-codes`)**: `signgu_ok: true` — `ldongCode2`(lDongRegnCd=48)에서
`lDongSignguCd=170` = **진주시** 확인, `config/region.yaml` 수정 없음. 타입별 `totalCount`(lDongRegnCd=48·lDongSignguCd=170):

| 12 관광지 | 14 문화시설 | 15 축제공연행사 | 25 여행코스 | 28 레포츠 | 32 숙박 | 38 쇼핑 | 39 음식점 | 합계 |
|---|---|---|---|---|---|---|---|---|
| 57 | 18 | 8 | 0 | 5 | 10 | 53 | 48 | 199 |

```powershell
cd pipeline
.venv\Scripts\python -m jinju_pipeline verify-codes   # "signgu_ok": true, 8개 타입별 count
.venv\Scripts\python -m jinju_pipeline run            # 쿼터로 detail_pending > 0 이면 다음 날 run 1회 더(상세 이어받기)
```

`DATA_GO_KR_KEY`가 없거나 빈 값(`DATA_GO_KR_KEY=`·공백)이면 파이프라인은 TourAPI 소스를 건너뛰고(경고 로그) 진주시 OpenAPI만으로
`places.db`를 만들며, `verify-codes`는 종료 코드 2와 함께 "설정 오류: DATA_GO_KR_KEY가 설정되지 않았습니다…"를 출력한다.
CLI는 httpx 요청 로그(INFO)를 끈다 — TourAPI 요청 URL에 `serviceKey`가 들어 있기 때문이다.

**TourAPI 실응답에서 확인한 사실(2026-11-04 녹화, `pipeline/tests/fixtures/tourapi/`)**

- 목록(`areaBasedList2`)의 `tel`은 관광지 57건 **전부 빈 값**이고, `detailCommon2`의 `tel`도 빈 경우가 있다(진주성).
  전화는 `detailIntro2`의 안내 번호(`infocenter`·`infocenterculture`·`infocenterfood`… / 축제 `sponsor1tel`)로 보완한다.
- 목록 `firstimage`는 57건 중 17건이 `http://` → `tong.visitkorea.or.kr`은 https로 올려 저장. 저작권 유형은 Type1·Type3 혼재.
- `homepage`는 `<a href>` 태그가 아니라 맨 URL로 오는 경우가 있다(둘 다 처리).
- `detailImage2`는 `numOfRows`를 주지 않으면 10건만 준다(진주성 totalCount 15). 이미지 10장이면 충분해 그대로 둔다.
- `areaBasedSyncList2`의 `modifiedtime`은 "이후"가 아니라 **접두 일치**다(`20261001` → 0건, `20261023` → 2건, `202610` → 41건).
  증분 모드는 직전 실행 월부터 이번 달까지 `YYYYMM`으로 한 번씩 조회하고 직전 실행일 이후 수정분만 쓴다. 숨김 항목(`showflag=0`)도 실제로 온다.
- 목록에 `areacode`/`sigungucode`가 채워져 오지만(구 코드) 쓰지 않는다. 필터는 `lDongRegnCd`/`lDongSignguCd`만.

### 1.2 검토 후 제외 (사유)

- 공영주차장·공중화장실·전통시장·버스(실시간/정류장): 비목표.
- data.go.kr 진주 파일데이터(음식점 인허가 대장 6,898건, 숙박정보): 좌표 없음·관광 큐레이션 아님 → 노이즈.
- Kakao/VWorld 지오코딩: 결과 저장 금지 약관 → 좌표 없는 항목은 지오코딩하지 않고 목록에만 노출.
- 진주시 관광 사이트 스크래핑: OpenAPI로 대체 가능, 트래픽 차단 징후·저작권 불명. (진주8경 목록 등은 수작업 큐레이션)
- KTO 빅데이터 방문자수·무장애·반려동물 API: 이번 범위 밖.

## 2. 파이프라인

`python -m jinju_pipeline run` = `collect → clean → merge → curate → report/gate → load`.
단계 산출물은 `pipeline/data/work/<run_id>/`(`clean.jsonl`, `merge.jsonl`, `merge_log.jsonl`, `report.json`, `report.md`)에,
원본 응답은 변형 없이 `pipeline/data/raw/<source>/<run_id>/page-NNN.json` + `manifest.json`(키 마스킹)에 남는다(둘 다 git 제외).
`run_id` = `YYYYMMDDTHHMMSS+0900`.

```
            ┌─ S1 tourinfo ─┐
            ├─ S2 restaurant┤
 collect ───┼─ S3 festival ─┼──(asyncio.gather, 소스별 동시성 제한)──► raw_store (원본 그대로)
 (병렬)     ├─ S4 heritage ─┤      진주시: 동시성 4 + 요청 간 0.25s / TourAPI: 상세 워커 5
            ├─ S5 lodging ──┤
            └─ T1→T2, T3 ───┘   (T2는 T1 결과를 큐로 받아 스트리밍 병렬 호출)
 clean  : RawRecord → CleanRecord (원본 값은 raw로 보존, 정제 값은 별도 필드)
 merge  : CleanRecord[] → Place[] (소스 간 동일 장소 병합, provenance·병합 근거 기록)
 curate : 진주8경·30선·태그·축제 장소·배지 해석
 report : 카운트·결측률·병합/드롭 사유·게이트 판정 → report.json/md
 load   : 게이트 통과 시에만 places.db.tmp → integrity_check → places.db 원자적 교체(os.replace)
```

- 한 소스가 실패해도 다른 소스는 계속한다. 실패한 소스는 직전 `places.db`의 `place_sources.raw_json`으로 대체하고
  `reused_previous`로 표시한다(연속 1회 경고, 2회 실패).
- 쿼터 원장 `pipeline/data/state/quota.json`: 로컬 일 900회(진주시 페이지 호출도 센다 — 전체 수집 1회 약 117회),
  GitHub 러너(`GITHUB_ACTIONS=true`)는 실행당 300회.
- 장소 ID는 직전 `places.db`를 읽어 승계한다(같은 source key가 속했던 가장 오래된 ID). 새 장소만 `jh-` + sha1(최초 source key)[:10].
  병합으로 사라진 ID는 `place_aliases`에 남고 직전 alias도 모두 이월된다. `id_order`는 직전 순번을 유지하고 새 ID를 뒤에 붙인다.

### CLI

| 명령 | 설명 |
|---|---|
| `run [--incremental] [--today YYYY-MM-DD] [--out PATH] [--until clean\|merge]` | 전체 실행. `--out`은 places.db를 쓸 경로(report.json은 같은 폴더) — 직전 스냅샷(ID 승계·alias 이월·80% 게이트)은 계속 `backend/app/data/places.db`에서 읽는다. `--until`은 해당 단계까지 실행 후 중단(게시 안 함) |
| `verify-codes` | TourAPI `ldongCode2`로 48/170이 "진주시"인지와 타입별 건수 확인 |
| `report --run-id <id>` | 지난 실행의 `report.md` 출력 |

종료 코드: **0** 게이트 통과 · **1** 게이트 실패(places.db·report.json 그대로, 리포트는 `work/<run_id>/`에만) ·
**2** 설정 오류(`ConfigError` — 키 미설정/거부, 잘못된 환경변수 값, places.db 잠김, 없는 run-id).

## 3. 정제 규칙 (clean/)

| 규칙 | 구현 |
|---|---|
| 좌표 | 문자열→float. **이름이 아니라 값 범위로 위경도 판별**(lat 33~39, lng 124~132; 진주시 API의 x/y 뒤바뀜 자동 교정). `config/region.yaml` 진주 bbox(lat 35.05~35.33, lng 127.93~128.30, 여유 0.02°) 밖이면: 주소에 "진주"가 있으면 좌표만 비우고 유지(`geo_status=out_of_region`, 지도 제외·목록 노출), 없으면 드롭(`out_of_region`). `0,0`/빈값은 `geo_status=missing` |
| 텍스트 | HTML 태그 제거(selectolax), 엔티티 디코드, `<br>`→개행, 연속 공백 정리, trim |
| 전화 | 첫 번호만 숫자 추출 후 `055-XXX-XXXX` 등 한국 형식으로 포맷(나머지는 raw에 보존). TourAPI는 `detailCommon2.tel` → 목록 `tel` → `detailIntro2` 안내 번호 순 |
| URL·이미지 | 화이트리스트 도메인 `http→https`, 진주시 `/CmsMultiFile/view.do` 상대경로 → 절대 URL |
| 운영시간/휴무/요금 | 원문 보존 + 줄바꿈 정규화. 구조화 파싱은 하지 않음(오해석 위험) |
| 카테고리 | 소스별 원 분류 → 통합 카테고리(아래 표). 진주시 관광지 중 분류명에 "문화·박물관·전시"가 있으면 culture |
| 축제 날짜 | `YYYYMMDD`/`YYYY-MM-DD`/`YYYY.MM.DD` → `start_date/end_date`, `date_year`. 진주시 `undecided` 문구가 있으면 `date_undecided=1`. 진행 상태는 백엔드가 요청 시점에 계산 |
| 이미지 저작권 | TourAPI `cpyrhtDivCd`(Type1/Type3, 없으면 Type3) 보존, 진주시 이미지는 `license=jinju_city_unverified` |
| 원본 보존 | 모든 레코드의 원 payload를 `place_sources.raw_json`에 보관(공공누리 3유형 "변경 금지" 대응·추적성) |

| 코드 | 라벨 | 매핑 |
|---|---|---|
| `sight` | 명소 | S1, TourAPI 12 |
| `culture` | 문화·역사 | S4, S1 중 문화·박물관·전시 분류, TourAPI 14 |
| `food` | 맛집 | S2, TourAPI 39 |
| `stay` | 숙박 | S5, TourAPI 32 |
| `festival` | 축제·행사 | S3, TourAPI 15 |
| `shopping` | 쇼핑 | TourAPI 38 |
| `leisure` | 레포츠 | TourAPI 28 |
| `course` | 여행코스 | TourAPI 25 (좌표 없을 수 있음) |

## 4. 병합 규칙 (merge.py)

1. **블로킹**: 같은 카테고리 그룹 안에서만 비교(sight↔culture는 교차 허용).
2. **이름 정규화**: NFKC, 괄호부·특수문자 제거, 접두 "경상남도/경남/진주"·접미 "본점" 제거, 소문자화.
3. **매칭 조건**(하나라도 충족):
   - 정규화 이름 동일 AND 거리 ≤ 300m (좌표가 없으면 정규화 이름 + 정규화 주소 동일)
   - rapidfuzz `token_set_ratio ≥ 90` AND 거리 ≤ 150m
   - 정규화 전화번호 동일 AND 거리 ≤ 500m — **단, 서로 다른 소스 사이에서만, 그리고 어느 한 소스가 그 번호를 서로 다른 레코드 3건 이상에 적은 경우(부서 대표번호)는 제외**.
     소스별·레코드 키별로 세므로, 한 장소가 진주시·TourAPI 관광지·TourAPI 축제에 모두 있거나 진주시 API 페이지에 중복으로 나와도 그 장소 번호는 병합 근거로 남는다.
   - `merge_overrides.yaml`의 `force_merge`/`force_split`이 최우선
   - 한 쌍이 여러 조건을 만족하면 가장 강한 근거로 기록한다(같은 이름 > 같은 전화 > 이름 유사).
4. **결합 순서(증거 강도 순, K4)**: `force_merge`를 먼저 적용한 뒤, 후보쌍 전부의 근거를 먼저 계산하고
   `same_name`/`same_name_addr` → `same_phone` → `fuzzy_name` 순으로 결합한다(같은 순위 안에서는 `(key_a, key_b)` 정렬).
   결합할 때마다 컴포넌트 단위로 거부 규칙을 검사한다:
   - `force_split`: 두 키가 같은 그룹이 되는 결합은 (어떤 경로든) 거부.
   - **암묵적 contentid 분리**: 결합 결과 컴포넌트가 같은 TourAPI 소스(`tourapi.area` 또는 `tourapi.festival`)의 서로 다른
     contentid를 둘 이상 갖게 되면 거부. 단 그 두 레코드끼리 같은 이름 근거(`same_name`/`same_name_addr`)가 있으면 허용
     (같은 contentid가 area·festival 두 소스에 있는 것은 충돌이 아니다). 진주시 소스는 이 규칙이 없다(사찰 + 소장 문화재처럼 여러 행이 한 장소).
   그래서 결과가 레코드 키 문자열 순서나 입력 순서에 따라 달라지지 않는다. 이전에는 `(i, j)` 키 순서의 탐욕적 결합이라
   `"jinju_city.tourinfo:1163" < "…:605"` 때문에 "진주성 우물"이 이름 유사로 TourAPI "진주성"을 먼저 가져가고, 진주시 "진주성"은
   force_split에 막혀 합쳐지지 못했다(강제 분리 1건으로 땜질). 레코드가 추가될 때 이미지·개요가 다른 장소로 옮겨가는 것도 이 순서 문제였다.
5. **필드 우선순위**: 운영시간·요금·주차·휴무·메뉴·전화·좌표·이름 → 진주시 우선. 진주시 안에서는 관광지(tourinfo) > 축제 > 음식점 > 숙박 > 문화재 순.
   이 순서는 이름만이 아니라 **카테고리·좌표·전화·운영시간·요금·주차·휴무·메뉴·주소·홈페이지**(첫 번째로 값이 있는 레코드)에도 똑같이 적용된다.
   그래서 관광지 목록과 문화재가 합쳐진 사찰(예: 청곡사)은 관광지 쪽 값을 따라 **sight**가 되고, 비어 있는 필드만 문화재 값으로 채워진다.
   개요는 진주시 값이 40자 이상이면 가장 긴 값, 아니면 TourAPI. 이미지는 합집합(중복 URL 제거). 축제 날짜는 진주시 > TourAPI 축제 > TourAPI 관광지.
6. **ID 안정성**: §2 참조.
7. 병합 근거는 `work/<run_id>/merge_log.jsonl`에 기록.

**첫 실데이터(2026-11-04)에서 바꾼 것**

- *전화 일치 제한*: 진주시 API는 장소 고유 번호 대신 **담당 부서 번호**를 적는 경우가 많다(예: 055-749-5312가 문화재·관광지 584건에,
  055-749-5355가 44건에). 스펙의 전화 규칙을 그대로 쓰면 반경 500m 사슬로 297쌍이 잘못 병합되어 1,151건이 831건이 됐다.
  같은 소스 안의 전화 일치와, 한 소스가 서로 다른 레코드 3건 이상에 적은 번호는 병합 근거에서 뺐다 → 병합 44쌍, 최종 1,107건.
- *이름 우선순위*: 사찰(관광지 목록)에 그 사찰 소장 문화재들이 병합될 때 문화재 이름이 장소 이름이 되던 문제 → 진주시 안에서 관광지 목록 우선.
- *강제 분리*(`pipeline/curation/merge_overrides.yaml`): `token_set_ratio`는 짧은 이름이 긴 이름에 포함되면 100이 되므로
  진주성↔진주성 우물, 진양호↔제8경 진양호 노을, 망진산↔제5경 망진산 봉수대를 분리했다.

**TourAPI 보강 첫 실행(2026-11-04)에서 바꾼 것**

- *같은 TourAPI 소스 안에서는 이름 유사(fuzzy) 매칭을 쓰지 않는다*: TourAPI는 쇼핑몰 안 브랜드 매장을 각각 콘텐츠로 올린다
  ("아디다스 롯데몰 진주점" ⊃ "롯데몰 진주점" → `token_set_ratio` 100). 그대로 두면 롯데몰 17건·갤러리아 3건이 한 장소로 묶이고
  제목·개요가 아무 매장 것이 됐다. contentid가 다르면 이미 다른 콘텐츠이므로 같은 소스 안 fuzzy는 근거에서 뺐다(같은 이름·전화·주소 규칙은 그대로, 진주시 소스는 변화 없음).
- *강제 분리 추가*: 진주성 우물↔진주성(TourAPI)(키 정렬 순서상 우물이 먼저 묶여 진주시 "진주성"이 TourAPI 진주성과 합쳐지지 못함),
  제1경 진주성 촉석루↔촉석루(TourAPI)(진주시 "진주 촉석루"를 거쳐 진주8경 항목이 사라지고 fallback이 쓰임),
  김시민호↔물빛나루쉼터(같은 선착장 전화 → 게이트 실패 원인: 30선 "김시민호" 미해석), 진주논개제↔국가유산 미디어아트 진주성(같은 주최 전화),
  미디어 파사드(물초울공원 중앙광장)↔물초울공원.
- *강제 병합 추가*: 진주 레일바이크(진주시 관광지 ↔ TourAPI 레포츠, 카테고리 그룹이 달라 비교 안 됨),
  진주정원박람회↔2026 진주 정원박람회(좌표·기간 동일, 이름 앞 연도 + 부서 대표번호라 자동 매칭 안 됨).
- 결과: 병합 108쌍(same_name 64, fuzzy_name 34, same_phone 7, force_merge 2, same_name_addr 1). TourAPI 199곳 중 56곳이 진주시 장소와 합쳐지고 143곳이 새로 추가됐다.
  남은 경계 사례(그대로 둠): 진주국제농식품박람회↔"2026 진주국제농식품박람회 농업체험관"(같은 행사), 청곡사 괘불탱(문화재)→청곡사(사찰에 이미 합쳐지던 문화재).

**증거 강도 순 결합(K4, 2026-11-04)에서 바꾼 것**

- 결합 순서·암묵적 contentid 분리(위 4번). 근거 순위에 맞춰 한 쌍의 기록 근거도 전화 > 이름 유사로 바꿨다.
- *오버라이드 재검증*: 직전 실행(run `20261104T125916+0900`)의 `clean.jsonl`로 항목을 하나씩(서로 대체 관계인 것은 함께) 빼고
  병합을 다시 돌려 그룹이 달라지는지 확인했다. **제거 1건**: 진주성 우물(1163)↔진주성(TourAPI 126833) — 진주시 "진주성"(605)과
  TourAPI 진주성이 같은 이름으로 먼저 묶이고 605↔1163 분리가 우물을 막는다. 나머지 9건(강제 병합 2, 강제 분리 7 — 제1경 촉석루 체인 포함)은
  빼면 그룹이 달라져 유지했고, 각 항목의 이유를 YAML 주석에 적었다. 진주논개제 분리 2건(area·festival)은 서로 대체 관계(둘 다 빼야 합쳐짐)지만
  축제 목록이 기간에 따라 빠질 수 있어 둘 다 둔다.
- 같은 `clean.jsonl`에서 새 규칙 + 새 오버라이드의 결과는 커밋본 places.db와 **그룹 1,250개가 모두 같고 ID도 모두 같다**(alias 증가 0).
  병합 쌍 수는 108 그대로이고 근거 분포만 same_name 67 · fuzzy_name 31 · same_phone 7 · force_merge 2 · same_name_addr 1로 바뀌었다
  (같은 그룹을 이루는 결합이 이름 일치 쌍으로 먼저 이뤄진 결과). 암묵적 contentid 분리는 현재 데이터에서 거부한 결합이 없다(갱신 대비 안전장치).

## 5. 품질 게이트 (report.py)

리포트 항목: 소스별 수집 건수/실패, 정제 후 건수, 드롭 사유, 병합 쌍 수와 조건별 분포, 카테고리별 건수·좌표 보유율,
필드 결측률(이미지·개요·전화·운영시간·좌표; 좌표는 course 제외), 축제 연도 분포, 상세 미완료(`detail_pending`), 쿼터 사용량, 실행 시간, `content_hash`.

게이트(하나라도 실패하면 places.db·report.json을 교체하지 않고 종료 코드 1):

- 최종 장소 수 ≥ 직전 버전의 80% (직전 없음: 최소 300)
- sight / food / festival 각 1건 이상
- **좌표 보유율: sight ≥ 0.85, culture ≥ 0.55, stay ≥ 0.40** (food·festival·course 등은 리포트에만)
- 진주 bbox 밖 좌표 0건(큐레이션 적용 후 다시 검사)
- 진주8경·30선·축제 장소 큐레이션 항목이 모두 장소로 해석될 것(`unresolved_curation == []`).
  태그 수작업 항목(`tags:`)의 미해석은 경고만
- 직전 데이터 재사용 연속 1회 경고, 2회 이상 실패

**임계값 조정 기록(스펙 §5.7 "첫 실제 실행에서 게이트가 실패하면 빌더가 임계값을 조정할 수 있되 근거를 기록")**:
스펙의 시작값은 sight·culture·stay 모두 0.85. 2026-11-04 첫 실행(진주시 API만, TourAPI 키 없음)의 좌표 보유율은
sight 0.98, culture 0.65, stay 0.48이었다. 문화재 목록에는 좌표 없는 묘·비석이, 숙박 목록에는 좌표 없는 모텔이 많고
지오코딩은 약관상 저장할 수 없다. culture 0.55, stay 0.40은 그 실행보다 약 10%p 낮은 **회귀 감시선**이다.
TourAPI 보강 실행(2026-11-04)에서 다시 봤다: sight 0.97, culture 0.65, stay 0.51 — 세 기준 모두 여유 있게 통과해 **임계값은 바꾸지 않았다**
(TourAPI 항목은 좌표가 거의 다 있지만 문화재·모텔 수가 압도적이라 culture/stay 비율은 거의 그대로다). 현재 기준값은 `report.md` 게이트 절과 `report.json`의 `coords_thresholds`에도 찍힌다.

## 6. 최신 실행 요약 (run_id `20261104T125916+0900`, TourAPI 보강, 게이트 PASS)

| 항목 | 값 |
|---|---|
| 수집 | 진주시 tourinfo 191 · restaurant 269 · festival 9 · heritage 590 · lodging 94, TourAPI area 199 · festival 8 (7개 소스 전부 ok) |
| 호출 | 실행 1회분 551회(진주시 117 + TourAPI 434: 목록 8·축제 1·상세 398·이미지 27), 30.9s. `detail_pending` **0** |
| 정제 후 | 1,358 (드롭 `out_of_region` 2) |
| 병합 | 108쌍 (same_name 64, fuzzy_name 34, same_phone 7, force_merge 2, same_name_addr 1) |
| 최종 | **1,250** — culture 578, food 308, sight 196, stay 97, shopping 53, festival 14, leisure 4 (course 0: TourAPI 25 타입 0건) |
| 출처 | 진주시만 1,051 · 진주시+TourAPI 56 · TourAPI만 143 |
| 좌표 보유율 | sight 0.97, culture 0.65, stay 0.51, food 0.50, festival·shopping·leisure 1.00 (전체 0.67) |
| 결측률(채움 비율) | 대표 이미지 **0.47**(직전 0.41), 개요 **0.43**(0.35), 전화 0.84(0.83), 운영시간 0.99 |
| 이미지 | 1,784장 — TourAPI Type1 94 · Type3 209, 진주시 1,481 |
| 축제 연도 | 2026: 10, 2024: 1, 미정: 3 |
| 큐레이션 | 진주8경 8곳 모두 진주시 "제N경" 항목(fallback 미사용), 30선 30곳(14곳에 TourAPI `source_keys` → 갤러리), 야경 태그 4곳, 미해석 0 |
| 배지 대상 수 | first_light 838, jinju8 8, food_explorer 308, history_walk 578, night_namgang 4, festival_guest 13 |
| alias | 0 (직전 커밋본 places.db의 ID 1,107개는 모두 승계) |
| FTS | trigram, `integrity_check` ok |

**실행 방법과 쿼터(2026-11-04)**: 로컬 원장 기준 이날 사용 803/900 — 진주시 단독 실행 2회(234) + `verify-codes` 9 + 픽스처 녹화·
`areaBasedSyncList2` 확인 9 + TourAPI 보강 **실제 실행 1회 537**(진주시 117 + TourAPI 420, 게이트 FAIL: 30선 "김시민호" 미해석 → §4 수정)
+ 30선 갤러리용 `detailImage2` 14. 같은 날 다시 돌린 실행(병합 규칙·큐레이션 수정 후)은 첫 실행의 응답을 그대로 재생하는 로컬 녹화 캐시
(키 미포함, 저장소 밖)로 돌려 TourAPI 호출을 아꼈다. 위 표는 직전 커밋본(진주시 단독) places.db에서 출발한 마지막 재생 실행이다.

**K4 증거 강도 순 병합 검증(2026-11-04, 오프라인, API 호출 0)**: 실데이터 재생성(`run --incremental`)은 **컨트롤러 결정으로 건너뛰었다**
— 이날 로컬 원장이 803/900이고 진주시 전체 재수집(117회, 무키지만 원장에 집계)만으로 일 한도를 넘기 때문이다(900 한도 유지).
대신 위 실행의 `clean.jsonl`을 새 병합 규칙 + 새 `merge_overrides.yaml`로 다시 병합하고 커밋본 places.db를 직전 스냅샷으로 썼다:
그룹 1,250개·장소 ID·alias가 커밋본과 **모두 같다**(ID 승계 1,250/1,250, 새 ID 0, alias 증가 0, 바뀐 그룹 0).
병합은 108쌍 그대로이고, 근거 분포만 same_name 67 · fuzzy_name 31 · same_phone 7 · force_merge 2 · same_name_addr 1로 바뀌었다(§4).
그래서 위 표와 places.db는 그대로 두었다. 백엔드 픽스처 DB도 다시 만들어 비교했는데 빌드 시각(`updated_at`·`fetched_at`) 말고는 같아서 커밋하지 않았다.
새 결합 순서는 다음 정기 갱신(D2 주간 `run --incremental`)에서 처음 실데이터로 돈다.

## 7. 큐레이션 (pipeline/curation/)

- `jinju8.yaml`: 진주8경(공식: 진주시 관광 누리집 > 진주8경, https://www.jinju.go.kr/02232/02244.web). 진주시 API의 "제N경" 항목을 잡는다.
  fallback(항목이 사라졌을 때만 쓰는 큐레이션 장소)의 좌표·개요는 같은 API 항목에서 옮겼고 원문에 없는 내용은 넣지 않는다.
- `collection30.yaml`: "진주 유등 30선" — **현재 `status: draft`, 사용자 확정 대기.** 진주8경 8 + 대표 명소·박물관 10 + 향토 맛집·먹거리 6 + 야경/체험 6.
  TourAPI 보강 후 TourAPI 항목이 1:1로 합쳐진 14곳(진주성·국립진주박물관·유등전시관·이성자미술관·실크박물관·청동기문화박물관·경상남도수목원·
  월아산 숲속의 진주·진주대첩 역사공원·청곡사·소망진산유등테마공원·음악분수·유등체험관·레일바이크)에 `source_keys: [tourapi.area:<contentid>]`를 넣었다 →
  이 항목은 상세가 캐시돼 있어도 한 번은 `detailImage2`(갤러리)를 받는다(`images_fetched`로 다음 실행부터 재호출 없음).
  1:1이 아닌 후보(진주중앙시장·논개시장 통합 항목, 하연옥 본점≠하대점, 의기사와 의암≠제2경)는 넣지 않았다.
  진주시 음식점 API에 향토 음식점이 적어 먹거리 묶음에 전통시장·음식 체험을 넣었다. TourAPI 수집 후 다시 고르는 것을 권한다.
  항목 수정 후 `run`을 다시 실행하면 된다(미해석 항목이 있으면 게이트가 실패해 기존 DB가 유지된다).
- `tags.yaml`: indoor(문화 카테고리·박물관류 이름), outdoor(명소·레포츠), local_food(냉면·비빔밥·장어·헛제사밥), night_view(수작업: 촉석루·진주성·남가람 별빛길·망진산 봉수대).
- `festival_programs.yaml`: 유등축제 → 진주성·진주 촉석루·남가람 별빛길(진주시 API에 "남강둔치"·"진주교" 항목이 없어 대체). 매처에 category를 지정해 축제 행·동명 음식점에 걸리지 않게 한다.
- `badges.yaml`: 배지 6종 규칙 → 파이프라인이 장소 ID 집합으로 풀어 `badges.rule_json`에 저장.
- `merge_overrides.yaml`: 병합 예외(§4).
- 테스트는 `pipeline/tests/fixtures/curation/`(운영본과 별개인 사본)을 쓰므로 운영 YAML을 고쳐도 테스트가 깨지지 않는다.

## 8. 라이선스 표기 원칙

- 화면 하단·상세 페이지에 "한국관광공사 TourAPI · 진주시 공공데이터" 출처를 표기한다.
- 이미지는 장소별로 `place_images.license`를 함께 표기한다: TourAPI `Type1`(공공누리 1유형: 출처표시), `Type3`(공공누리 3유형: 출처표시·변경금지),
  진주시 이미지는 `jinju_city_unverified`(진주시 공공데이터 — 이용 조건 미확인, 출처를 반드시 표기).
- 이미지는 자르거나 필터를 씌우지 않는다(`object-fit: contain`) — 3유형 "변경 금지" 대응.
- 텍스트는 정제(태그 제거·공백 정리)만 하고 원문은 `place_sources.raw_json`에 보존한다.

## 9. 운영 절차

### 로컬 실행

```powershell
cd pipeline
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m jinju_pipeline run            # 게이트 통과 시 backend/app/data/places.db, report.json 교체
.venv\Scripts\python -m jinju_pipeline run --incremental
.venv\Scripts\python -m pytest -v                     # 네트워크 없이 전체 테스트
```

로컬 백엔드가 places.db를 열고 있으면 교체가 실패한다(종료 코드 2, "places.db가 다른 프로세스…"). 백엔드를 멈추거나 `--out`으로 다른 경로에 쓴다.
`--out`을 써도 직전 스냅샷은 기존 `backend/app/data/places.db`에서 읽으므로 ID·alias·게이트 기준이 그대로 유지된다. 백엔드를 멈춘 뒤 새 파일로 바꿔 넣는다.

### 백엔드 테스트용 픽스처 DB

`backend/tests/fixtures/places_fixture.db`는 녹화 픽스처(`pipeline/tests/fixtures/jinju_city/*_p1.json` — 실제 1페이지 + 같은 API의 뒤 페이지에서 그대로 옮긴
진주성·진주 촉석루·국립진주박물관·남가람 별빛길·진주8경 "제N경" 8곳·하연옥 하대점·냉면 상호 1곳)로 오프라인 생성한다.

```powershell
cd pipeline
$env:BUILD_FIXTURE_OUT="..\backend\tests\fixtures\places_fixture.db"; .venv\Scripts\python -m pytest tests/test_build_fixture.py -v
```

내용 계약(`test_fixture_db_contract`): 냉면 포함 제목 ≥1, 촉석루·진주성 존재, 유등축제 2026-10-03~18, indoor 태그 ≥1, jinju8_rank 1~8, 배지 6, food ≥3, stay ≥1.

### 스케줄 갱신과 러너 차단 시 대체 절차

- `data-refresh.yml`(Task D2에서 추가 예정): 매주 월 03:00 KST(`0 18 * * 0` UTC) + 수동 실행 → `python -m jinju_pipeline run --incremental` → 게이트 → `content_hash`가 바뀌었을 때만 places.db·report.json 커밋.
- 증분 모드의 상태 원천은 **커밋된 직전 places.db**다(러너는 매번 깨끗함). TourAPI는 변경분만 상세 재호출, 진주시 API는 매번 전체 재수집.
- GitHub 러너(해외 IP)에서 jinju.go.kr이 막히면 진주시 소스는 직전 DB의 원본으로 대체되고 경고로 통과한다. **2회 연속이면 워크플로가 실패한다.**
  이때는 로컬에서 같은 명령을 실행해 커밋한다:

```powershell
git pull
cd pipeline; .venv\Scripts\python -m jinju_pipeline run --incremental; cd ..
git add backend/app/data/places.db backend/app/data/report.json
git commit -m "data: refresh places.db (local run)"; git push
```

  로컬 실행은 모든 소스가 `ok`이므로 `reused_streak`가 0으로 돌아간다.

### places.db를 VACUUM 하지 말 것

`places_fts`는 `content='places', content_rowid='rowid'`인 **external-content FTS5** 테이블이라 `places`의 rowid를 가리킨다.
`VACUUM`은 명시적 INTEGER PRIMARY KEY가 없는 테이블의 rowid를 다시 매길 수 있어 검색 색인이 엉뚱한 행을 가리키게 된다.
배포되는 places.db에는 `VACUUM`(및 rowid를 바꾸는 재작성)을 하지 않는다. 크기를 줄이거나 색인을 고치려면 파이프라인을 다시 실행해 새로 만든다
(쓰기 단계가 `INSERT INTO places_fts(places_fts) VALUES('rebuild')` 후 `integrity_check`까지 수행한다).

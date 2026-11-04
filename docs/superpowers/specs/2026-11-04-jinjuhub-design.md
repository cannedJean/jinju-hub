# JinjuHub — 진주시 공공 관광 웹사이트 프로젝트 계획서

> 이 파일은 두 부분으로 구성된다. **Part A = 설계 명세(spec)**, **Part B = 구현 계획(implementation plan)**. Task 0에서 각각 `JinjuHub/docs/superpowers/specs/2026-11-04-jinjuhub-design.md`와 `JinjuHub/docs/superpowers/plans/2026-11-04-jinjuhub.md`로 분리 저장·커밋한다.

# Part A — 설계 명세

> 대전 LocalHub(Vue 3 + FastAPI) 역공학 → 진주시판 재구축. 실데이터 수집·정제 파이프라인 + UX 중심 UI(지도 고도화 + 유등 게이미피케이션).
> 작성일 2026-11-04 · 기간 1~2주 · 용도: 교육 과제 제출·시연(배포 URL 필요)

---

## 0. Context — 왜 하는가

- **이전 작업(대전 LocalHub)**: TourAPI 4.0 목록 응답 1,365건을 손으로 받아 JSON 8개로 커밋한 MVP. 수집 코드가 없고, 상세 정보(개요·운영시간·요금·축제 기간)가 없으며 `tel`은 축제 외 전부 공백, 이미지 17.6% 누락, 주소 부분문자열로 도시 필터링(계룡로 오탐), 상세 페이지 없음, 지도는 현재 페이지 20개 마커만 표시. 사용자 평가: **가장 아쉬웠던 건 UI**.
- **이번 목표**: 진주시를 대상으로 ① 실제로 구할 수 있는 데이터를 조사·결정하고 ② **병렬 수집 → 원본 보존 → 정제 → 중복 병합 → 적재 → 품질 리포트** 파이프라인을 명령 하나로 재현 가능하게 만들고 ③ 그 데이터를 쓰는 **배포된** 진주시 공공 웹사이트를 완성한다.
- **대표 사용자 장면**: *남강유등축제를 보러 온 외지인이 숙소에서 내일 동선을 짜는 순간.* 사이트를 닫을 때 손에 **"갈 만한 곳 목록"** 이 남아 있으면 성공.
- **시연에서 꼭 보여줄 것**: **사이트 사용 흐름** — 외지인 입장에서 탐색(지도) → 상세 → "담기"(유등 띄우기) → 다음날 현장 도착 시 유등 밝히기 → 배지.

## 1. 목표 · 비목표 · 안티목표

**목표**
1. 진주 장소 데이터(명소·문화/역사·맛집·숙박·축제/행사·쇼핑·레포츠·코스)를 2개 이상 공공 소스에서 **병렬** 수집, 정제·병합해 단일 스키마로 제공.
2. 상세 정보(개요, 운영시간, 휴무, 요금, 주차, 전화, 홈페이지, 메뉴, 이미지, 축제 기간)가 있는 **장소 상세 페이지**.
3. **지도 중심 탐색**(클러스터링, 카테고리 레이어, "이 지역 재검색", 숙소 기준 반경/거리순) + **유등 게이미피케이션**(담기 ◇ → 현장 도착 시 밝히기 ◆, 컬렉션 진행도, 배지).
4. 데스크톱 우선 설계 + 태블릿/모바일 **반응형**.
5. 대전판 기능 이식·개선: 날씨(기상청), 챗봇(**Claude**로 교체), 익명 게시판(**원격 DB 저장**).
6. 배포 URL(Netlify + Render + Neon Postgres) + 주간 자동 데이터 갱신(GitHub Actions).

**비목표 (이번에 안 함)**
- 주차장·공중화장실·전통시장·버스 등 **실용 정보 레이어** (사용자 결정: "목록에만 집중").
- 로그인/회원/랭킹 — 담기·유등 상태는 **브라우저(localStorage)에만** 저장 (사용자 결정).
- 시간대별 자동 일정(동선) 생성, 길찾기/경로 안내.
- 다국어, 네이티브 앱/PWA 오프라인.
- 모바일 우선(mobile-first) 설계 (사용자 결정: 제외. 단 반응형은 지원).

**안티목표 (동작해도 실패로 보는 것)**
- 시연 중 외부 API 장애로 화면이 비는 것 → 장소 데이터는 런타임에 외부 API를 호출하지 않는다(빌드된 DB 사용).
- 출처·라이선스 표기 누락, 공공누리 3유형 이미지 변형(크롭·필터).
- 이미 끝난 축제를 "진행 중"처럼 보이게 하는 것(대전판의 날짜 없는 축제 문제 재발).
- 정제 과정에서 원본 값을 덮어써 추적 불가능해지는 것.
- 게시판 글이 재배포 때 사라지는 것(대전판 Render SQLite 휘발 문제).

## 2. 제약

| 항목 | 내용 |
|---|---|
| 기간 | 1~2주 (10 작업일 기준 일정, §11) |
| 배포 | 공개 URL 필수 |
| 키 | 공공데이터포털 서비스키, 기상청 API허브 authKey, Anthropic API 키 — 사용자가 새로 발급해 제공 |
| TourAPI 쿼터 | 개발계정 1,000 calls/day (운영계정 신청 시 증설) |
| 진주시 OpenAPI | 키 불필요, `pageunit` 최대 10, `xposition`=위도/`yposition`=경도 (뒤바뀜), HTTP |
| 지오코딩 | Kakao/VWorld는 **결과 DB 저장 금지** → 사용 안 함. 소스 제공 좌표만 사용 |
| 라이선스 | TourAPI 이용허락 제한 없음, 이미지 공공누리 1·3유형(3유형=변경 금지). 진주시 OpenAPI는 data.go.kr에 "이용허락범위 제한 없음"이나 사이트엔 공공누리 표시 없음 → 확인 필요(§12) |
| 지도 타일 | OSM 공식 타일 대량 사용 금지 정책 → CARTO 베이스맵 사용(무료, 출처 표기) |

## 3. 데이터 소스 결정

### 3.1 채택 (수집 대상)

| # | 소스 | 엔드포인트 | 인증 | 대상 | 역할 |
|---|---|---|---|---|---|
| S1 | 진주시 OpenAPI 관광지 | `http://www.jinju.go.kr/openapi/tour/tourinfo.do` | 없음 | 191건(2026-11-04 실측) | **주 소스**: 개요·요금·운영시간·주차·좌표·이미지 |
| S2 | 진주시 OpenAPI 음식점 | `.../openapi/tour/restaurant.do` | 없음 | 269건 | 주 소스: 영업시간·휴무·메뉴/가격 (좌표 일부 누락) |
| S3 | 진주시 OpenAPI 축제 | `.../openapi/tour/festival.do` | 없음 | 9건 | 주 소스: 시작/종료일, `undecided`, 주최, 요금 |
| S4 | 진주시 OpenAPI 문화재 | spec 06578 (엔드포인트명 착수일 확인) | 없음 | 미확인 | 문화·역사 카테고리 |
| S5 | 진주시 OpenAPI 숙박시설 | spec 06579 (엔드포인트명 착수일 확인) | 없음 | 미확인 | 숙박 |
| T1 | TourAPI KorService2 `areaBasedList2` | `https://apis.data.go.kr/B551011/KorService2` | 서비스키 | `lDongRegnCd=48&lDongSignguCd=170`, contentTypeId 12/14/15/25/28/32/38/39 | 보강: 커버리지·이미지·`overview` |
| T2 | TourAPI `detailCommon2` / `detailIntro2` / `detailImage2` | 동일 | 서비스키 | T1 결과 각 contentId | 상세(개요·운영시간·이미지 저작권유형) |
| T3 | TourAPI `searchFestival2` | 동일 | 서비스키 | `eventStartDate=올해0101`, 진주 필터 | 축제 기간 교차검증 |
| T4 | TourAPI `areaBasedSyncList2` | 동일 | 서비스키 | `modifiedtime`, `showflag` | 주간 증분 갱신·삭제 반영 |
| W1 | 기상청 API허브 초단기예보 | `https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtFcst` | authKey | 진주 격자 nx=81, ny=75(계산값, §5.4에서 코드로 검증) | 런타임 날씨 위젯 (대전판 로직 재사용) |
| C1 | 큐레이션(수작업) | `pipeline/curation/*.yaml` | — | 진주8경, 유등 30선, 배지 정의, 병합 오버라이드, 축제 프로그램 | 게이미피케이션·시연 품질 |

> **지역 코드 주의**: KorService2에서 `areaCode`/`sigunguCode`는 "삭제예정"이며 필터 시 항목의 35~58%만 반환되는 사례가 보고됨 → **`lDongRegnCd/lDongSignguCd`만 사용**. 48/170은 패턴상 추정이므로 파이프라인 `verify-codes` 명령이 `ldongCode2`로 첫 실행 시 확인한다.

### 3.2 검토 후 제외 (사유 기록 — 발표 자료용)
- 공영주차장·공중화장실·전통시장·버스(실시간/정류장): 비목표.
- data.go.kr 진주 파일데이터(음식점정보 6,898건 인허가 대장, 숙박정보): 좌표 없음·관광 큐레이션 아님 → 노이즈.
- Kakao/VWorld 지오코딩: 결과 저장 금지 약관.
- 진주시 관광 사이트 스크래핑: OpenAPI로 대체 가능, 트래픽 차단 징후·저작권 불명. (진주8경 목록 등은 수작업 큐레이션으로 대체)
- KTO 빅데이터 방문자수·무장애·반려동물 API: 이번 범위 밖 (§13 확장 후보).

## 4. 저장소 · 프로젝트 구조

- **새 저장소**: `C:\Users\SSAFY\Desktop\JinjuHub` (git init, GitHub 원격 신규). LocalHub는 건드리지 않음. LocalHub 코드를 **복사해 출발점**으로 쓰되 죽은 코드는 옮기지 않는다.

```
JinjuHub/
├─ README.md · DEPLOYMENT.md · DATA.md(데이터 출처·파이프라인 설명·라이선스)
├─ config/region.yaml            # 진주 단일 지역 설정(이름, 중심, bbox, 법정동코드, KMA 격자 원천좌표)
├─ .github/workflows/
│   ├─ ci.yml                    # pipeline/backend pytest, frontend vitest+build
│   └─ data-refresh.yml          # 주 1회 파이프라인 실행→품질게이트→places.db 커밋
├─ pipeline/                     # 독립 파이썬 패키지 (jinju_pipeline)
│   ├─ requirements.txt          # httpx, tenacity, pydantic, pyyaml, rapidfuzz, selectolax(HTML strip)
│   ├─ jinju_pipeline/
│   │   ├─ __main__.py           # CLI: run | collect | clean | merge | load | report | verify-codes
│   │   ├─ settings.py           # env: DATA_GO_KR_KEY, 동시성/재시도 설정, 경로
│   │   ├─ http.py               # AsyncClient 팩토리, 소스별 Semaphore·RateLimiter, tenacity 재시도
│   │   ├─ sources/
│   │   │   ├─ base.py           # Source 프로토콜: name, async collect(ctx) -> RawBatch
│   │   │   ├─ jinju_city.py     # S1~S5 (공통 페이징 로직 1개)
│   │   │   └─ tourapi.py        # T1~T4 (+쿼터 원장)
│   │   ├─ raw_store.py          # data/raw/<source>/<run_id>/page-NNN.json + manifest.json
│   │   ├─ models.py             # RawRecord, Place, Image, Festival, Provenance (pydantic)
│   │   ├─ clean/                # coords.py, text.py, phone.py, hours.py, category.py, festival.py, images.py
│   │   ├─ merge.py              # 블로킹·매칭·병합·필드 우선순위
│   │   ├─ curation.py           # yaml 로드·장소 ID 해석
│   │   ├─ load.py               # places.db 생성(SQLite + FTS5) — 원자적 교체
│   │   └─ report.py             # report.json + report.md, 품질 게이트
│   ├─ curation/                 # jinju8.yaml, collection30.yaml, badges.yaml, merge_overrides.yaml, festival_programs.yaml
│   ├─ data/                     # raw/ (gitignore), state/quota.json (gitignore)
│   └─ tests/                    # fixtures/(녹화 응답) + 단위·통합 테스트
├─ backend/                      # LocalHub localhub-backend 기반
│   ├─ app/data/places.db        # 파이프라인 산출물(커밋, 읽기 전용)
│   ├─ app/data/report.json      # 최신 품질 리포트(커밋)
│   ├─ alembic/                  # 게시판 스키마 마이그레이션
│   └─ tests/
└─ frontend/                     # LocalHub localhub-frontend 기반
```

## 5. 데이터 파이프라인 상세

### 5.1 실행 흐름
`python -m jinju_pipeline run` = `collect → clean → merge → load → report` (각 단계 단독 실행 가능, 단계 산출물은 `pipeline/data/work/<run_id>/`에 JSONL로 남겨 디버깅·발표에 활용).

```
            ┌─ S1 tourinfo ─┐
            ├─ S2 restaurant┤
 collect ───┼─ S3 festival ─┼──(asyncio.gather, 소스별 동시성 제한)──► raw_store (원본 그대로)
 (병렬)     ├─ S4 heritage ─┤
            ├─ S5 lodging ──┤
            └─ T1→T2, T3 ───┘   (T2는 T1 결과를 큐로 받아 스트리밍 병렬 호출)
 clean  : RawRecord → CleanRecord (원본 값 보존 + 정제 값 별도 필드)
 merge  : CleanRecord[] → Place[] (소스 간 동일 장소 병합, provenance 기록)
 load   : Place[] → places.db.tmp → 검증 → places.db 원자적 교체(os.replace)
 report : 카운트·결측률·병합/드롭 사유·게이트 판정 → report.json/md
```

### 5.2 병렬 수집 (사용자 요구: 여러 데이터 동시 수집)
- **구조**: 모든 Source를 `asyncio.gather(*(run_source(s) for s in sources), return_exceptions=True)`로 동시에 시작(`TaskGroup`은 하나 실패 시 나머지를 취소하므로 사용하지 않음). `run_source`는 소스별 예외를 `SourceResult(status="failed", error=...)`로 감싸 반환 → 다른 소스는 계속, 리포트에 실패로 기록 → §5.9 폴백 규칙으로 판단. (구현: CLI는 `run` 한 명령으로 전 단계를 수행하고 단계별 중간 산출물 `work/<run_id>/{clean,merge}.jsonl`을 남긴다 — 단계별 단독 실행은 `--until clean|merge` 옵션으로 해당 단계까지만 수행.)
- **소스 내부 병렬**:
  - 진주시 API: 1페이지 호출로 총건수 파악 → 나머지 페이지를 동시 요청. 동시성 `Semaphore(4)` + 최소 간격 250ms(트래픽 차단 징후 대응).
  - TourAPI: 8개 contentTypeId 목록을 동시 요청(`numOfRows`는 1000 시도 후 응답 실제 건수로 페이징 보정). 목록 결과가 나오는 대로 `asyncio.Queue`에 넣고 상세 워커 N=5개가 `detailCommon2`/`detailIntro2`를 호출(목록 완료를 기다리지 않는 파이프라인).
- **재시도**: tenacity, 지수 백오프(0.5s→8s, 최대 4회), 대상은 네트워크 오류·5xx·TourAPI 비정상 resultCode(쿼터 초과 코드는 재시도하지 않고 중단 신호).
- **쿼터 원장**: `data/state/quota.json`에 날짜별 호출 수 기록, 기본 한도 900/일(여유 100). 한도 도달 시 남은 상세 호출은 다음 실행으로 이월(재개 가능).
- **캐시/재개**: 상세 응답은 `contentid + modifiedtime` 키로 raw 캐시. 같은 modifiedtime이면 재호출하지 않음 → 2회차부터 호출량 급감.
- **호출량 추정**: TourAPI 목록 ~10~20회 + 상세 2회×N(진주 예상 수백 건). 첫 수집이 1일 쿼터를 넘으면 2일에 걸쳐 완료(일정 D2~D3에 반영). `detailImage2`는 "유등 30선"+대표 이미지 없는 항목에만 호출.
- **진행 로그**: 소스별 진행률(rich 없이 표준 logging, 구조화 JSON 라인).

### 5.3 원본 보존 (raw_store)
- 응답 바디를 **변형 없이** `data/raw/<source>/<run_id>/page-NNN.json`로 저장 + `manifest.json`(요청 파라미터에서 키 마스킹, 수집 시각, 건수, HTTP 상태, sha256).
- `run_id` = `YYYYMMDDTHHMMSS+0900`. raw는 git에 커밋하지 않고 GitHub Actions artifact(30일)로 보관.

### 5.4 정제 규칙 (clean/)

| 규칙 | 구현 |
|---|---|
| 좌표 | 문자열→float. **이름이 아니라 값 범위로 위경도 판별**(lat 33~39, lng 124~132; 진주시 API의 x/y 뒤바뀜 자동 교정). `config/region.yaml`의 진주 bbox(대략 lat 35.05~35.33, lng 127.93~128.30, 여유 0.02°) 밖이면: 주소에 "진주"가 있으면 **좌표만 null로 비우고 유지**(`geo_status=out_of_region` → 지도 제외·목록 노출), 주소에도 진주가 없으면 **드롭**(사유 `out_of_region`). `0,0`/빈값은 `geo_status=missing` → 지도 제외, 목록 노출 |
| 텍스트 | HTML 태그 제거(selectolax), `&amp;` 등 엔티티 디코드, `<br>`→개행, 연속 공백 정리, 앞뒤 trim |
| 전화 | 첫 번호만 숫자 추출 후 `055-XXX-XXXX` 등 한국 형식으로 포맷(나머지 번호는 raw/provenance에 보존) |
| URL·이미지 | `http://`→`https://` 가능 여부(도메인 화이트리스트: tong.visitkorea.or.kr 등) 적용, 진주시 `/CmsMultiFile/view.do` 상대경로 → 절대 URL |
| 운영시간/휴무/요금 | 원문 문자열 보존 + 표시용 정리(줄바꿈 정규화). 구조화 파싱은 하지 않음(오해석 위험) |
| 카테고리 | 소스별 원 분류 → 통합 카테고리(아래 표) |
| 축제 날짜 | `YYYYMMDD`/`YYYY-MM-DD`/`YYYY.MM.DD` 파싱 → `start_date/end_date`. 상태 계산은 **API 요청 시점**에 수행(§6) — 파이프라인은 `date_year`와 `undecided` 플래그만 저장 |
| 이미지 저작권 | TourAPI `cpyrhtDivCd`(Type1/Type3) 보존, 진주시 이미지는 `license=jinju_city_unverified` |
| 원본 보존 | 모든 정제 필드 옆에 `raw` 원값을 provenance에 보관(공공누리 3유형 "변경 금지" 대응·추적성) |

**통합 카테고리**

| 코드 | 라벨 | 매핑 |
|---|---|---|
| `sight` | 명소 | S1 일반/대표명소, TourAPI 12 |
| `culture` | 문화·역사 | S4 문화재, TourAPI 14 |
| `food` | 맛집 | S2, TourAPI 39 |
| `stay` | 숙박 | S5, TourAPI 32 |
| `festival` | 축제·행사 | S3, TourAPI 15 |
| `shopping` | 쇼핑 | TourAPI 38 |
| `leisure` | 레포츠 | TourAPI 28 |
| `course` | 여행코스 | TourAPI 25 (좌표 없을 수 있음 — 목록/상세만) |

### 5.5 중복 병합 (merge.py)
1. **블로킹**: 같은 카테고리 그룹 내(sight↔culture는 교차 허용 — 진주성 같은 곳이 양쪽에 존재).
2. **이름 정규화**: 공백·괄호부·특수문자 제거, 접두 "진주"/접미 "본점" 등 제거 규칙, 소문자화.
3. **매칭 조건**(하나라도 충족):
   - 정규화 이름 동일 AND 거리 ≤ 300m
   - rapidfuzz `token_set_ratio ≥ 90` AND 거리 ≤ 150m
   - 정규화 전화번호 동일 AND 거리 ≤ 500m
   - `merge_overrides.yaml`의 강제 병합(force_merge)/강제 분리(force_split)가 최우선
4. **필드 우선순위**: 운영시간·요금·주차·휴무·메뉴 → 진주시(S*) 우선 / `overview`·이미지 → 진주시 값이 비었거나 짧으면 TourAPI / 좌표 → 진주시 우선, 없으면 TourAPI / 이미지는 양쪽 합집합(중복 URL 제거, 라이선스 유형별 표기).
5. **ID (안정성)**: 파이프라인은 **직전 `backend/app/data/places.db`를 입력으로 읽는다**. 새 Place의 source_key 중 하나라도 직전 Place에 속했으면 **직전 ID를 그대로 승계**(가장 오래된 ID 우선), 직전에 없던 장소만 `"jh-" + sha1(최초 source_key)[:10]`로 신규 발급. 두 기존 Place가 하나로 병합되면 승계되지 못한 ID를 `place_aliases(old_id→new_id)`에 추가하고, 직전 DB의 alias 행도 전부 이월 → localStorage 담기 상태가 갱신 후에도 유지.
6. 병합 결과·근거(어떤 조건으로 매칭)를 `work/merge_log.jsonl`에 기록 → 리포트·발표용.

### 5.6 적재 스키마 (places.db, SQLite)
```sql
places(id TEXT PK, category TEXT, title TEXT, title_norm TEXT, summary TEXT, overview TEXT,
       addr TEXT, lat REAL, lng REAL, geo_status TEXT, phone TEXT, homepage TEXT,
       hours TEXT, closed_days TEXT, fee TEXT, parking TEXT, menu TEXT,
       start_date TEXT, end_date TEXT, date_undecided INTEGER, date_year INTEGER,
       hero_image TEXT, is_collection INTEGER, jinju8_rank INTEGER,
       tags TEXT,               -- JSON 배열: night_view, indoor, outdoor, festival_venue, local_food 등
       venue_place_ids TEXT,    -- 축제 행만: 점등 대상이 되는 장소 ID JSON 배열(festival_programs.yaml)
       updated_at TEXT)
place_images(place_id, url, source, license, sort)
place_sources(place_id, source, source_id, source_url, fetched_at, raw_json)   -- provenance
place_aliases(old_id, new_id)
badges(id, label, description, rule_json)                                   -- 큐레이션
places_fts USING fts5(title, addr, overview, content='places', tokenize='trigram')  -- 한글 부분검색
meta(key, value)  -- data_version(run_id), generated_at, source_counts, region
```
- `trigram` 토크나이저 미지원 SQLite면 `LIKE` 폴백(백엔드에서 감지).
- `lat/lng` 인덱스(범위 질의), `category` 인덱스.

### 5.7 품질 리포트 & 게이트 (report.py)
- **리포트 항목**: 소스별 수집 건수/실패, 정제 후 건수, 드롭 사유별 건수(out_of_region, missing_coords, invalid), 병합 쌍 수와 조건별 분포, 카테고리별 최종 건수, 필드 결측률(이미지·개요·전화·운영시간·좌표), 축제 연도 분포(stale 감지), 실행 시간, 쿼터 사용량.
- **게이트(실패 시 places.db 교체 안 함, CI 실패)**:
  - 최종 장소 수 ≥ 직전 버전의 80% (첫 실행은 절대 최소 300)
  - 카테고리 sight/food/festival 각각 ≥ 1
  - 좌표 보유율 ≥ 85% — **sight·culture·stay에만 적용**(food는 S2 좌표 누락이 알려져 있어 목록 전용 허용, 보유율은 리포트에만 표기; course 제외)
  - 첫 실제 실행에서 게이트가 실패하면 빌더가 임계값을 조정할 수 있되, 조정 값과 근거를 `report.md`와 `DATA.md`에 기록
  - 진주 bbox 밖 좌표 0건이 최종 테이블에 존재하지 않을 것
  - 컬렉션 30선·진주8경 큐레이션 항목이 전부 ID로 해석될 것
- 출력: `report.json`(백엔드가 `/api/data/report`로 제공), `report.md`(발표/README용).

### 5.8 큐레이션 (curation/)
- `jinju8.yaml`: 진주8경(제1경 진주성 촉석루, 제2경 남강 의암, 제3경 뒤벼리, 제4경 새벼리, 제5경 망진산 봉수대, 제6경 비봉루, 제7경 월아산 일출, 제8경 진양호 일몰 — **진주시 관광 사이트 '진주8경' 메뉴로 착수일 검증**). 각 항목은 `match: {title_contains, near: [lat,lng]}`로 장소 해석, 미존재 시 큐레이션 전용 장소로 생성(좌표·설명 수작업, 출처 링크).
- `collection30.yaml`: "진주 유등 30선" = 진주8경(8) + 대표 명소·박물관(국립진주박물관, 남강유등전시관, 경상남도수목원, 월아산 숲속의 진주 등 ~10) + 향토 맛집(진주냉면·진주비빔밥·장어 등 ~7) + 야경/체험(~5). **빌더가 첫 `places.db`를 보고 D3에 초안을 작성 → 사용자 검토 후 확정**(헤더 진행도 분모).
- `tags.yaml`: 장소 태그 규칙 — `indoor`(문화시설·박물관·전시관 카테고리 기본 + 수작업 추가), `outdoor`(명소·레포츠 기본), `night_view`(촉석루 야경·진주교·남강 둔치 등 수작업), `local_food`(냉면·비빔밥·장어 등 이름/메뉴 키워드). 비 오는 날 "실내 명소" 필터(§7.6)와 배지에 사용.
- `badges.yaml`: §7.5 배지 규칙(파이프라인이 규칙을 **장소 ID 집합으로 해석**해 `badges.rule_json`에 저장).
- `festival_programs.yaml`: 유등축제 등 주요 축제 프로그램/장소 요약 + **`venue_place_ids`**(예: 유등축제 → 진주성·촉석루·남강 둔치·진주교; 개천예술제 → 진주성 등)(연 1회 수작업, 출처 URL 포함).
- `merge_overrides.yaml`: 병합 예외.

### 5.9 스케줄 갱신 (data-refresh.yml)
- cron 매주 월 03:00 KST(`0 18 * * 0` UTC) + 수동 실행(`workflow_dispatch`).
- 단계: checkout → Python 3.12 → `pip install -r pipeline/requirements.txt` → `python -m jinju_pipeline run --incremental` → 게이트 → 변경 시 `backend/app/data/places.db`, `report.json` 커밋/푸시(봇 커밋, main 직접 푸시) → Render·Netlify 자동 배포. raw는 artifact 업로드.
- **증분 모드의 상태 원천 = 커밋된 직전 `places.db`** (러너는 매번 깨끗하므로 raw 캐시·quota.json에 의존하지 않음):
  - TourAPI: `areaBasedSyncList2(modifiedtime=직전 generated_at 날짜)`로 변경/숨김(showflag=0)된 contentId만 상세 재호출. 변경 없는 항목은 직전 DB의 `place_sources.raw_json`에서 RawRecord를 복원해 clean→merge에 그대로 투입.
  - 진주시 API: 키·쿼터 제약이 없으므로 매번 전체 재수집(합계 약 50~60회 호출).
  - 쿼터: 러너에서는 그 실행의 호출 수만 세고 상한 300회로 제한(개발용 로컬 실행과 같은 키를 쓰므로 여유 확보).
- **소스 도달 실패 폴백**: 어떤 소스가 실패(예: 해외 IP인 GitHub 러너에서 jinju.go.kr 차단)하면 그 소스의 레코드를 **직전 DB의 raw_json으로 대체**하고 리포트에 `source_status=reused_previous`로 표시 → 게이트는 경고로 통과. 2회 연속 재사용이면 워크플로를 실패시켜 알림. 러너에서 진주시 API가 계속 막히면 대안은 로컬에서 `python -m jinju_pipeline run` 후 커밋(같은 산출물, DATA.md에 절차 명시). D1에 GitHub 러너에서 jinju.go.kr 접속 가능 여부를 `workflow_dispatch` 1회로 확인.
- 시크릿: `DATA_GO_KR_KEY`.

## 6. 백엔드 설계 (FastAPI, `backend/`)

### 6.1 구성
- LocalHub `localhub-backend` 복사 후 정리. `/api` prefix 유지(평면 라우트).
- **DB 2개 분리**:
  - `places.db` — 읽기 전용 SQLite(`file:...?mode=ro&immutable=1`), 앱 시작 시 연결, 배포물에 포함.
  - 게시판 — `DATABASE_URL`(운영: **Neon Postgres 원격 저장**, `postgresql+psycopg://`; 로컬: SQLite 허용). SQLAlchemy 2 + **Alembic** 마이그레이션(`create_all` at import 제거).
- 설정: `config/region.yaml`을 읽는 `RegionConfig` + 환경변수(`pydantic-settings`).

### 6.2 API 계약

| Method | Path | 파라미터 | 응답 |
|---|---|---|---|
| GET | `/api/health` | — | `{status, data_version}` |
| GET | `/api/meta` | — | 지역(이름·중심·bbox), 카테고리별 count, data_version, generated_at, 출처/라이선스 문구 |
| GET | `/api/places` | `q`, `category`(복수), `tags`(복수, 예: indoor), `bbox=minLng,minLat,maxLng,maxLat`, `near=lat,lng`, `radius`(m, ≤20000), `sort=relevance\|distance\|name\|collection`, `page`, `size≤50` | `{items:[PlaceSummary+distance_m], total, page, size, totalPages}` |
| GET | `/api/places/markers` | `category`(선택) | `[{id, lat, lng, category, title, is_collection}]` 전체(경량, ETag/Cache-Control) |
| GET | `/api/places/{id}` | — | PlaceDetail(전 필드 + images + sources + nearby 6개(1km 내, 거리순)). 구 ID는 `place_aliases`로 301 대신 `canonical_id` 포함 응답 |
| GET | `/api/festivals` | `status=ongoing\|upcoming\|ended\|all`, `today=YYYY-MM-DD`(선택, **시연 모드 전용** 기준일 주입. `DEMO_DATE_OVERRIDE_ENABLED=true`일 때만 허용) | 상태 계산 포함 목록 + `venue_place_ids` |
| GET | `/api/collection` | — | 유등 30선 + 진주8경 + 배지 정의(각 배지: `id,label,description,required,eligible_place_ids[]`, 축제 배지는 `festival_windows:[{festival_id,start,end,venue_place_ids}]`) + 컬렉션 장소의 `{id,category,tags}` |
| GET | `/api/data/report` | — | 최신 report.json |
| GET | `/api/weather` | (진주 고정; 대전판의 `city` 파라미터는 제거) | 대전판과 동일 스키마 |
| POST | `/api/chat` | `{message≤500, history≤20}` | `{answer, sources:[{type:"place"\|"post", id, label}]}` (대전판 `"location"` → `"place"`로 변경, 프론트 `utils/chatSources.js` 동시 수정) |
| GET/POST/PUT/DELETE | `/api/posts...` | 대전판과 동일 | 대전판과 동일 + `updated_at` |
| GET | `/api/posts/{id}?count_view=false` | 수정 폼에서 조회수 증가 방지 | |

- **축제 상태**: 요청 시점 KST 기준 — `ongoing`(start≤오늘≤end), `upcoming`(오늘<start), `ended`(end<오늘, 같은 해), `stale`(date_year<올해 → "작년 일정·올해 미정"으로 표시), `undecided`. 2026-11-04 기준 진주국제농식품박람회(11-04~08)=ongoing, 유등축제(10-03~18)=ended → "2027년 일정 미정" 안내.
- **거리 계산**: bbox 사전필터 후 파이썬 haversine(데이터 규모 수천 건 이하라 충분).
- **검색**: FTS5 trigram(2글자 이하 질의는 LIKE), 제목 일치 가중치 > 주소 > 개요.

### 6.3 날씨
- `weather_service.py` 재사용(KMA API허브 초단기예보, base_time 로직, 10분 캐시). 변경: `CITY_GRIDS` 제거 → `region.yaml`의 중심 좌표를 **KMA LCC 격자 변환 함수**로 nx/ny 계산(단위테스트: 서울 종로 (60,127), 대전 (67,100) 일치 확인 → 진주 81/75 확인). 전역 Lock을 HTTP 호출 바깥으로 이동(단일 지역이라 영향 작지만 정리).

### 6.4 챗봇 (OpenAI → Claude)
- 의존성 `openai` 제거, `anthropic` 추가. `AsyncAnthropic().messages.create(...)`.
- 모델 `ANTHROPIC_MODEL=claude-opus-5-5`(기본값, env로 변경 가능), `output_config={"effort": "low"}`, `max_tokens=4096`, 30s 타임아웃. 서버측 refusal fallback(`betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`) 적용, `stop_reason=="refusal"` 처리.
- **검색 증강**: 질문 → 카테고리/의도 감지(대전판 `TYPE_KEYWORDS` 재사용·진주화) → places FTS 상위 6개 + (필요 시) 축제 상태 + (날씨어 포함 시) 진주 날씨 + (후기/게시글 언급 시) 게시글 3개 → 컨텍스트 블록으로 전달. 시스템 프롬프트: 제공된 컨텍스트 밖 사실 금지, 장소 언급 시 ID 표기 규칙.
- 응답 `sources`는 프론트에서 상세 링크 + "담기" 버튼으로 렌더.
- 키 미설정/장애 시 결정적 폴백 답변(대전판 로직 유지), 503/502 구분 유지.
- 구현 시 `claude-api` 스킬의 python README를 읽고 SDK 시그니처 확인.

### 6.5 게시판 (원격 저장)
- 스키마 동일(`board_posts`) + 비밀번호 **bcrypt 해시**(`bcrypt` 패키지). 대전판의 평문 저장·`!=` 비교(`posts.py:56,66`)를 `bcrypt.checkpw`로 교체. 카테고리: `tour|food|festival|free`.
- 운영 DB: **Neon Postgres 무료 플랜**(원격, 재배포와 무관하게 영속). 시연용 시드 스크립트 `python -m app.scripts.seed_posts`(진주 후기 8~10개).
- POST/PUT/DELETE·chat에 **레이트 리밋**(slowapi, IP당 분당 10회).

### 6.6 보안/운영
- CORS: Netlify 도메인만. 키는 SecretStr, 로그 마스킹. 요청 로깅(경로·지연·상태). 전역 예외 핸들러.

## 7. 프론트엔드 설계 (Vue 3 + Vite, `frontend/`)

### 7.1 기술
- 유지: Vue 3.5, Vite 6, Vue Router 4, Pinia 2, Tailwind 3.4, axios, Leaflet 1.9.
- 추가: `leaflet.markercluster@1.5.3`, `vitest` + `@vue/test-utils`, `@playwright/test`(e2e 시연 흐름).
- 정리: 대전판 중복/죽은 코드(utils/locations.js, utils/posts.js, formatters.js, 미사용 State* 컴포넌트, base.css, `.vite/deps`) 미이식. 상수는 `/api/meta`·`/api/collection`에서 받아 **하드코딩 제거**.

### 7.2 디자인 방향
- 테마 "남강의 밤과 유등": 주색 남색 밤하늘(#0f1b3d 계열) + 등불 주황/호박(#f59e0b~#fb923c) 포인트, 본문은 밝은 배경(가독성). 토큰은 `tokens.css` 단일 출처 → `tailwind.config.js`가 CSS 변수 참조(대전판 이중 정의 해소).
- 데스크톱 우선 레이아웃(사용자 결정), 반응형 브레이크포인트:
  - **≥1280px**: 좌측 목록 패널 420px + 지도 전체, 상세는 패널 내 슬라이드 또는 별도 페이지.
  - **768~1279px**: 접이식 좌측 패널(토글), 지도 우선.
  - **<768px**: 지도 + 하단 바텀시트(3단 스냅: 접힘/중간/전체) + 하단 탭바(탐색·내 유등·축제·더보기).
- 접근성: 키보드 내비, 마커에 aria-label, 대비 4.5:1, `prefers-reduced-motion` 시 유등 애니메이션 비활성.

### 7.3 라우트

| 경로 | 화면 | 핵심 |
|---|---|---|
| `/` | 홈 | 축제 상태 배너(진행 중/다가오는/종료+내년 안내), 오늘 진주 날씨, 진주8경 카드, 유등 30선 진행도, "지도에서 탐색" CTA |
| `/explore` | **지도 탐색**(메인) | §7.4. URL 쿼리 동기화(`q, cat, bbox, near, radius, sort`) |
| `/places/:id` | 장소 상세 | 갤러리(라이선스 표기, 크롭 금지: `object-fit: contain`), 개요, 정보표(시간·휴무·요금·주차·전화·홈페이지·메뉴), 미니맵, 주변 장소 6, 담기/밝히기 버튼, 출처 표기 |
| `/lanterns` | 내 유등 | 담은 목록(◇/◆), 유등 지도(내 장소만), 진행도, 배지 진열장, 목록 공유 링크 |
| `/festivals` | 축제 | 상태 탭, 기간 타임라인, 주요 프로그램(큐레이션) |
| `/boards`, `/boards/new`, `/boards/:id`, `/boards/:id/edit` | 게시판 | 대전판 이식 + 반응형 |
| `/about/data` | 데이터 출처 | 소스·라이선스·파이프라인 리포트(수집/병합/드롭 수치, 갱신 시각) |
| `*` | 404 | |

- 전역: 헤더(로고·검색·내비·날씨 칩·유등 진행 `◆ n/30`), 플로팅 챗봇 위젯, 푸터(출처·라이선스).

### 7.4 지도 고도화
- **마커**: `/api/places/markers` 1회 로드 → 클라이언트 클러스터링(markercluster, 카테고리 색 도넛 클러스터). 카테고리별 SVG `divIcon`. 담은 장소는 ◇ 유등 아이콘, 밝힌 장소는 ◆ 발광 유등 아이콘(CSS glow 애니메이션).
- **카테고리 칩**: 다중 선택 토글 → 레이어 on/off(목록과 동기).
- **이 지역 재검색**: 지도 이동 종료(`moveend`) 시 버튼 노출 → 현재 bbox로 `/api/places` 조회해 목록 갱신.
- **숙소 기준점**: "내 숙소 설정"(지도 클릭/검색 결과의 숙박 장소 선택/현재 위치) → localStorage 저장, 반경 원(500m/1km/3km/5km) 표시, `sort=distance`, 목록에 거리 표시.
- **목록↔지도 연동**: 목록 hover 시 마커 하이라이트, 마커 클릭 시 목록 스크롤·미리보기 카드.
- **타일**: CARTO Voyager(주간)/Dark Matter(유등 테마 다크 토글), 출처 "© OpenStreetMap contributors © CARTO" + "한국관광공사 TourAPI·진주시". 타일 URL은 env로 교체 가능.
- `maxBounds` = 진주 bbox + 여유, 최소 줌 11.
- 팝업은 `textContent` 기반 DOM 생성 유지(XSS 방지, 대전판 패턴 재사용).

### 7.5 유등 게이미피케이션 (localStorage 전용)
- **상태 저장**: `localStorage["jinjuhub.lanterns.v1"]` = `{version:1, items:{[placeId]:{savedAt, title, category, tags[], lat, lng, litAt?, litOn?(YYYY-MM-DD, 점등 기준일), litMethod?: "gps"|"demo"}}, base:{lat,lng,label}?, demo:{enabled:boolean, today?:"YYYY-MM-DD"}, earnedBadges:{[badgeId]: earnedAt}}`. 담을 때 title·category·tags·좌표를 스냅샷 저장(오프라인 표시·배지 판정용). 모든 접근 try/catch, 실패 시 메모리 폴백. 데이터 갱신으로 ID가 바뀌면 `/api/places/{id}`의 `canonical_id`로 자동 이관.
- **담기(◇)**: 어느 장소든 상세/목록/팝업/챗봇 출처에서 담기. "갈 만한 곳 목록" = 담은 목록.
- **밝히기(◆)**: 상세의 "도착했어요" → Geolocation API(HTTPS 필수, 배포 Netlify OK)로 현재 위치 → `distance − accuracy ≤ 150m`면 점등. 실패 시 거리 안내("촉석루까지 1.2km").
- **시연 모드**: `/?demo=1` 또는 더보기>설정 토글. 켜면 상단에 "시연 모드" 표시(정직성), 상세에 "도착 시뮬레이션" 버튼, 지도에 드래그 가능한 "가상 내 위치" 핀, **기준일 선택**(기본값 "오늘", 프리셋 "유등축제 기간 2026-10-10") → 프론트가 `/api/festivals?today=`로 전달해 축제 상태·홈 배너·축제 배지를 그 날짜 기준으로 시연. 시연 모드 점등은 `litMethod:"demo"`로 구분. (시연일이 박람회(11-04~08) 이후라 '진행 중' 축제가 없어도 흐름을 보여줄 수 있게 함)
- **진행도**: 헤더 `◆ 점등수 / 30`(유등 30선 기준) + 내 유등 페이지에 담음/점등 수.
- **배지(badges.yaml → `/api/collection`의 해석된 규칙)**: 첫 등불(아무 곳 1곳 점등), 진주8경(eligible=8경 ID, required 8, 진행 n/8), 맛 탐험가(eligible=food 전체 ID, required 3), 역사 산책(eligible=culture 전체, required 3), 밤의 남강(eligible=`night_view` 태그, required 2), 축제 손님(festival_windows 중 하나의 `venue_place_ids` 장소를 `litOn`이 그 축제 기간 안일 때 점등). 판정은 클라이언트 순수 함수 `evaluateBadges(state, collection)` — 입력은 저장 상태 + `/api/collection`만으로 충분, 단위테스트 대상.
- **연출**: 점등 시 유등이 떠오르는 애니메이션 + 토스트, 배지 획득 모달. `prefers-reduced-motion` 존중.
- **공유**: `/lanterns?share=<base64url(placeIds)>` 읽기 전용 보기 + "내 목록에 가져오기".

### 7.6 기타 이식
- 날씨 위젯: 진주 고정, 활동 추천(실내/실외) → 탐색 화면에 "비 오면 실내 명소" 빠른 필터(`/api/places?tags=indoor`) 연결. (`/api/places`에 `tags` 파라미터 포함)
- 챗봇 위젯: 30s 타임아웃·세션 히스토리 유지, 출처 칩 → 상세 링크/담기. 추천 질문 진주화("유등축제 끝났는데 지금 볼 만한 축제 있어?", "진주성 근처 냉면집").
- 게시판: 대전판 기능 + 비밀번호 모달 + 반응형 + 조회수 중복 방지.

## 8. 배포

| 대상 | 서비스 | 설정 |
|---|---|---|
| 프론트 | Netlify | base `frontend`, build `npm run build`, publish `dist`, SPA redirect, env `VITE_API_BASE_URL` |
| 백엔드 | Render Web Service(무료) | root `backend`, build `pip install -r requirements.txt && alembic upgrade head`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`, health `/api/health`, `PYTHON_VERSION=3.12.x` |
| 게시판 DB | Neon Postgres(무료) | `DATABASE_URL=postgresql+psycopg://...?sslmode=require` |
| 데이터 | GitHub Actions | data-refresh.yml → places.db 커밋 → Render auto-deploy |

- 백엔드 env: `DATABASE_URL`, `ALLOWED_ORIGINS`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `WEATHER_API_KEY`, `RATE_LIMIT`, `DEMO_DATE_OVERRIDE_ENABLED`(기본 true, 과제 시연용). 파이프라인 env(Actions secret): `DATA_GO_KR_KEY`.
- **계정 선행 조건(사용자 소유)**: GitHub 저장소(JinjuHub, 사용자 계정), Netlify·Render·Neon 계정 생성과 저장소 연결, 키 3종 등록은 사용자가 수행(D1·D10에 체크리스트 제공). 빌더는 설정값·런북을 준비하고 사용자가 대시보드에 입력. 데이터 갱신 봇은 main에 직접 푸시(과제 저장소라 브랜치 보호 없음 가정).
- Render 무료는 15분 유휴 시 슬립(콜드스타트 ~50초) → 시연 10분 전 `/api/health` 워밍(런북에 명시). 필요 시 UptimeRobot 핑(선택).
- `.env.example` 3종(pipeline/backend/frontend), 실제 키 커밋 금지.

## 9. LocalHub에서 재사용할 것 (경로는 `C:\Users\SSAFY\Desktop\LocalHub` 기준)

| 재사용 | 원본 | 변경 |
|---|---|---|
| 앱 골격·CORS·라우터 | `localhub-backend/app/main.py`, `app/api/v1/routes.py` | create_all 제거, places/meta/festivals/collection/report 라우터 추가 |
| 설정 | `app/core/config.py` | OPENAI_* → ANTHROPIC_*, region.yaml 로딩 |
| 게시판 | `app/models/board.py`, `app/schemas/board.py`, `app/services/board_service.py`, `endpoints/posts.py` | bcrypt, Alembic, `count_view` |
| 날씨 | `app/services/weather_service.py`(파싱·base_time·캐시), `schemas/weather.py`, `tests/test_weather_service.py` | 격자 변환 함수, 진주 |
| 챗봇 | `app/services/chat_service.py`(키워드 감지·폴백·소스 구조), `schemas/chatbot.py` | Anthropic SDK, FTS 검색 |
| 테스트 패턴 | `tests/test_api.py`(인메모리 DB CRUD/403), `tests/test_weather_service.py`(`httpx.MockTransport`) | 고정 count 의존 제거, 테스트용 places.db 픽스처, `test_chat_service.py`의 실DB 의존 제거 |
| 프론트 골격 | `src/api/client.js`, `stores/chat.js`, `stores/postAuth.js`, `components/ChatWidget.vue`, `WeatherWidget.vue`, `Pagination.vue`, `StateView.vue`, `ImagePlaceholder.vue`, 게시판 뷰 4종 | 진주화·반응형 |
| 지도 패턴 | `views/PlacesView.vue`(마커 아이콘 번들 수정, textContent 팝업, 한국 bbox 검증) | 클러스터·viewport·유등 마커로 재작성 |
| 정규화 | `utils/normalizers.js`(좌표 검증·https 변환) | 대부분 파이프라인으로 이동, 프론트는 표시용만 |
| 배포 | `DEPLOYMENT.md`, `netlify.toml`, `public/_redirects` | Neon·Alembic·Actions 추가 |

## 10. 테스트 · 검증

**파이프라인 (`pipeline/tests`, pytest)**
- 녹화 응답 픽스처(진주시 API 각 1~2페이지, TourAPI 목록/상세 샘플)로 `respx`/`httpx.MockTransport` 오프라인 테스트.
- 단위: 좌표 뒤바뀜 교정·bbox 판정, HTML/엔티티 정리, 전화 포맷, 축제 날짜 파싱, 카테고리 매핑, 이름 정규화, 병합 규칙(동일명/퍼지/전화/오버라이드), place_id 안정성, 쿼터 원장 이월, 게이트 판정.
- 병렬성: 소스 하나 실패 시 나머지 완료 + 리포트 실패 기록 테스트, 동시성 제한(semaphore) 준수 테스트.
- 통합: 픽스처 → `run` → places.db 생성 → 스키마·FTS 질의 검증.

**백엔드 (`backend/tests`)**
- 픽스처 places.db로 `/api/places`(q·category·bbox·near·sort·페이징), markers, 상세(nearby·alias), festivals 상태(고정 시각 주입), collection, report.
- 게시판 CRUD/403/bcrypt, `count_view`, 레이트 리밋.
- 날씨: 격자 변환(서울 60/127, 대전 67/100, 진주 81/75), 파싱(기존 테스트 이식).
- 챗봇: Anthropic 클라이언트 페이크로 컨텍스트 구성·sources·refusal·키 없음 폴백.

**프론트 (`frontend`)**
- vitest: lanterns 스토어(담기/점등/거리 판정/마이그레이션/스토리지 실패 폴백), `evaluateBadges`, 축제 상태 표시, 공유 링크 인코딩.
- Playwright e2e(시연 시나리오 그대로): 홈 → 탐색 → 칩 "맛집" → 지도 이동 후 재검색 → 숙소 설정·거리순 → 상세 → 담기 → 시연 모드 도착 → 점등 애니메이션 → 내 유등 배지 확인 / 데스크톱 1440·태블릿 1024·모바일 390 뷰포트 스크린샷.

**종단 검증 절차 (완료 기준)**
1. `cd pipeline && python -m jinju_pipeline verify-codes` → 48/170 확인, 카테고리별 totalCount 출력.
2. `python -m jinju_pipeline run` → 게이트 PASS, `report.md`에 소스별·병합·결측 수치.
3. `cd backend && pytest && uvicorn main:app` → `/docs`에서 places·festivals·weather·chat 수동 확인.
4. `cd frontend && npm run test && npm run build && npx playwright test`.
5. 배포 후 Netlify URL에서 e2e를 `BASE_URL` 지정해 재실행, 게시글 작성 → Render 재배포 → 글 유지 확인(원격 저장 검증).
6. GitHub Actions `data-refresh` 수동 실행 → 커밋·자동 배포·`/api/meta` data_version 변경 확인.

## 11. 일정 (10 작업일, 2주차 후반은 버퍼)

| 일차 | 작업 | 산출물 |
|---|---|---|
| D1 | JinjuHub 저장소 생성, LocalHub 선별 복사·정리, region.yaml, 키 발급 확인, `verify-codes`, 진주시 문화재/숙박 엔드포인트 확인, CI 골격, GitHub 러너→jinju.go.kr 접속 확인(`workflow_dispatch`), 계정 체크리스트 전달 | 빌드되는 빈 골격, 코드 검증 결과 |
| D2 | 파이프라인 collect(병렬·재시도·쿼터·raw_store) + 픽스처 테스트 | raw 스냅샷 1회차 |
| D3 | clean + merge + curation(tags·festival venue·8경) + load + report/게이트, **유등 30선 초안 → 사용자 확정 요청** | 첫 `places.db`, `report.md`, 30선 초안 |
| D4 | 백엔드 places/meta/markers/detail/festivals/collection/report API + FTS + 테스트 | API 문서 |
| D5 | 게시판 Postgres(Neon)+Alembic+bcrypt+레이트리밋, 날씨 진주화(격자 함수), 챗봇 Claude 교체 | 백엔드 완료 |
| D6 | 프론트 디자인 토큰·레이아웃(반응형 3단), 헤더/푸터, 홈 | |
| D7 | 탐색 지도(클러스터·칩·재검색·숙소 반경·목록 연동) | |
| D8 | 장소 상세, 축제, 데이터 출처 페이지 | |
| D9 | 유등 게이미피케이션(스토어·점등·시연 모드·배지·연출·공유), 챗봇/게시판 UI 이식 | |
| D10 | 배포(Neon·Render·Netlify), data-refresh 워크플로, e2e, 시연 리허설 스크립트, README/DEPLOYMENT/DATA.md | 배포 URL |
| D11~ | 버퍼: 버그·디자인 폴리싱·발표 자료(파이프라인 다이어그램, 리포트 수치) | |

- 구현 방식: superpowers:writing-plans로 태스크 단위 계획 → subagent-driven-development(파이프라인/백엔드/프론트 병렬 트랙) + TDD.

## 12. 리스크 · 확인 필요 사항

| 리스크 | 대응 |
|---|---|
| `lDongSignguCd=170` 추정값 | D1 `verify-codes`로 확인, 틀리면 region.yaml만 수정 |
| TourAPI 1,000/일 쿼터 | 상세 캐시·이월·900 한도, 필요시 운영계정 신청, 첫 수집 2일 분할 |
| 진주시 OpenAPI 이미지·텍스트 라이선스 불명확 | 스마트도시과(055-749-5116) 문의 또는 저작권정책 확인. 확인 전에는 출처 표기+원문 링크, 문제 시 TourAPI 이미지로 대체(필드 우선순위 스위치 1개) |
| 진주시 API 트래픽 제한/HTTP 전용 | 동시성 4·간격 250ms·재시도, 런타임 호출 없음 |
| 진주시 문화재/숙박 엔드포인트명 미확인 | D1 spec 페이지 확인, 없으면 TourAPI 14/32로 대체 |
| 축제 데이터 stale(논개제 등 2024 날짜) | `stale` 상태로 정직하게 표시, festival_programs 수작업 보완 |
| Render 콜드스타트 | 시연 전 워밍, 프론트 로딩 스켈레톤 |
| Geolocation은 HTTPS·권한 필요, 시연장은 진주가 아님 | 시연 모드(명시 표시) |
| KMA 격자 81/75 계산값 | 격자 변환 함수 테스트로 검증 |
| SQLite FTS5 trigram 미지원 런타임 | 시작 시 감지 → LIKE 폴백 |
| Neon 무료 자동 일시정지 | 첫 요청 지연 수백 ms 수준, 커넥션 `pool_pre_ping` |

## 13. 결정 기록 (사용자 결정 vs 내 판단)

**사용자 결정**
- 대상 사용자·장면: 유등축제 외지인, 숙소에서 내일 동선 고민 / 성공 = 갈 만한 곳 목록
- 실용 정보(주차·화장실·시장·버스) 제외, 목록에 집중
- 교육 과제 제출·시연, 시연 핵심 = 사이트 사용 흐름
- 대전판 아쉬움 = UI → 반응형 + 게이미피케이션/지도 고도화, 방향 **C(지도+유등 혼합)**
- 담기/유등 저장 = 브라우저만(로그인 없음)
- 키: 공공데이터포털·기상청 API허브·Anthropic 제공 / 1~2주 / 배포 URL 필요
- mobile-first 제외, 데이터 수집은 병렬, 게시판 원격 저장

**내 판단 (검토 요청)**
- 새 저장소 `Desktop\JinjuHub`(모노레포: pipeline/backend/frontend), LocalHub 미수정
- 진주시 OpenAPI 주 소스 + TourAPI 보강, 지오코딩 미사용
- 장소 데이터는 빌드 산출 SQLite를 배포물에 포함(런타임 외부 호출 0), 주간 GitHub Actions 갱신
- 게시판 원격 DB = Neon Postgres 무료
- 챗봇 모델 `claude-opus-5-5`(effort low, env 변경 가능)
- 지도 타일 CARTO, 클러스터 markercluster
- 점등 반경 150m(정확도 보정), 컬렉션 "유등 30선", 배지 6종, 시연 모드 표시
- 디자인 테마 "남강의 밤과 유등"(남색+등불 주황)

- 리뷰 반영: 증분 갱신의 상태 원천 = 커밋된 직전 places.db(raw 캐시 비의존), 소스 실패 시 직전 데이터 재사용(2회 연속이면 실패), 장소 ID는 직전 DB에서 승계, 시연 모드에 기준일 주입, 태그(indoor/night_view 등)·축제 장소 연결 추가, 좌표 게이트는 sight·culture·stay에만, 유등 30선은 빌더 초안→사용자 확정, bot은 main 직접 푸시

**빌더 재량**
- 컴포넌트 세부 분해, 애니메이션 구현 방식, 정확한 색값·간격, 로그 포맷, 병합 임계값 미세조정(리포트 근거로), 시드 게시글 문구.

## 14. 확장 후보 (이번 범위 밖)
KTO 방문자수 기반 "요즘 뜨는 곳", 무장애·반려동물 동반 필터, 영어 콘텐츠(EngService2), 실용 정보 레이어, 로그인·랭킹, PWA.

---

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
| T1 | TourAPI KorService2 `areaBasedList2` | `https://apis.data.go.kr/B551011/KorService2` | 서비스키 | **미수집(키 발급 전)** | 보강: 커버리지·이미지·개요. 필터 `lDongRegnCd=48&lDongSignguCd=170`, contentTypeId 12/14/15/25/28/32/38/39 |
| T2 | TourAPI `detailCommon2`/`detailIntro2`/`detailImage2` | 동일 | 서비스키 | 미수집 | 상세(개요·운영시간·이미지 저작권 유형) |
| T3 | TourAPI `searchFestival2` | 동일 | 서비스키 | 미수집 | 축제 기간 교차검증 (`eventStartDate=올해0101`) |
| T4 | TourAPI `areaBasedSyncList2` | 동일 | 서비스키 | 미수집 | 주간 증분 갱신·숨김(showflag=0) 반영 |
| C1 | 큐레이션(수작업) | `pipeline/curation/*.yaml` | — | 진주8경 8, 30선 30(초안), 배지 6 | 게이미피케이션·시연 품질 |

진주시 API 사실(2026-11-04 실측): `http://`는 `https://`로 302 리다이렉트, 페이지 파라미터 `page`(1부터)·`pageunit`(최대 10),
응답 키 total=`record_count`, items=`results`, `xposition`=위도·`yposition`=경도(뒤바뀌는 경우가 있어 값 범위로 판별).
같은 `idx`가 두 페이지에 중복으로 나오는 경우가 있다(병합 단계에서 하나로 합쳐짐).

**TourAPI 코드 검증·보강: 키 발급 후 실행 예정.** `DATA_GO_KR_KEY`가 없으면 파이프라인은 TourAPI 소스를 건너뛰고(경고 로그)
진주시 OpenAPI만으로 `places.db`를 만든다. 키를 받으면 `pipeline/.env`에 넣고 아래 순서로 실행해 결과를 이 절에 기록한다.

```powershell
cd pipeline
.venv\Scripts\python -m jinju_pipeline verify-codes   # 기대: "signgu_ok": true, 8개 타입별 count
.venv\Scripts\python -m jinju_pipeline run            # 쿼터로 detail_pending > 0 이면 다음 날 run 1회 더(상세 이어받기)
```

`verify-codes`는 키가 없으면 종료 코드 2와 함께 "설정 오류: DATA_GO_KR_KEY가 설정되지 않았습니다…"를 출력하고 끝난다.

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
| 전화 | 첫 번호만 숫자 추출 후 `055-XXX-XXXX` 등 한국 형식으로 포맷(나머지는 raw에 보존) |
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
4. **필드 우선순위**: 운영시간·요금·주차·휴무·메뉴·전화·좌표·이름 → 진주시 우선. 진주시 안에서는 관광지(tourinfo) > 축제 > 음식점 > 숙박 > 문화재 순.
   이 순서는 이름만이 아니라 **카테고리·좌표·전화·운영시간·요금·주차·휴무·메뉴·주소·홈페이지**(첫 번째로 값이 있는 레코드)에도 똑같이 적용된다.
   그래서 관광지 목록과 문화재가 합쳐진 사찰(예: 청곡사)은 관광지 쪽 값을 따라 **sight**가 되고, 비어 있는 필드만 문화재 값으로 채워진다.
   개요는 진주시 값이 40자 이상이면 가장 긴 값, 아니면 TourAPI. 이미지는 합집합(중복 URL 제거). 축제 날짜는 진주시 > TourAPI 축제 > TourAPI 관광지.
5. **ID 안정성**: §2 참조.
6. 병합 근거는 `work/<run_id>/merge_log.jsonl`에 기록.

**첫 실데이터(2026-11-04)에서 바꾼 것**

- *전화 일치 제한*: 진주시 API는 장소 고유 번호 대신 **담당 부서 번호**를 적는 경우가 많다(예: 055-749-5312가 문화재·관광지 584건에,
  055-749-5355가 44건에). 스펙의 전화 규칙을 그대로 쓰면 반경 500m 사슬로 297쌍이 잘못 병합되어 1,151건이 831건이 됐다.
  같은 소스 안의 전화 일치와, 한 소스가 서로 다른 레코드 3건 이상에 적은 번호는 병합 근거에서 뺐다 → 병합 44쌍, 최종 1,107건.
- *이름 우선순위*: 사찰(관광지 목록)에 그 사찰 소장 문화재들이 병합될 때 문화재 이름이 장소 이름이 되던 문제 → 진주시 안에서 관광지 목록 우선.
- *강제 분리*(`pipeline/curation/merge_overrides.yaml`): `token_set_ratio`는 짧은 이름이 긴 이름에 포함되면 100이 되므로
  진주성↔진주성 우물, 진양호↔제8경 진양호 노을, 망진산↔제5경 망진산 봉수대를 분리했다.

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
TourAPI 수집 후 값을 다시 본다. 현재 기준값은 `report.md` 게이트 절과 `report.json`의 `coords_thresholds`에도 찍힌다.

## 6. 최신 실행 요약 (run_id `20261104T122749+0900`, 게이트 PASS)

| 항목 | 값 |
|---|---|
| 수집 | tourinfo 191 · restaurant 269 · festival 9 · heritage 590 · lodging 94 (전부 ok, 호출 117회, 30.6s) |
| 정제 후 | 1,151 (드롭 `out_of_region` 2) |
| 병합 | 44쌍 (fuzzy_name 32, same_name 11, same_name_addr 1) |
| 최종 | **1,107** — culture 576, food 260, sight 169, stay 93, festival 9 |
| 좌표 보유율 | sight 0.98, culture 0.65, stay 0.48, food 0.40, festival 1.00 (전체 0.63) |
| 결측률(채움 비율) | 대표 이미지 0.41, 개요 0.35, 전화 0.83, 운영시간 0.99 |
| 축제 연도 | 2026: 5, 2024: 1, 미정: 3 |
| 큐레이션 | 진주8경 8곳 모두 진주시 "제N경" 항목으로 해석(fallback 미사용), 30선 30곳, 야경 태그 4곳, 미해석 0 |
| 배지 대상 수 | first_light 697, jinju8 8, food_explorer 260, history_walk 576, night_namgang 4, festival_guest 8 |
| FTS | trigram |

## 7. 큐레이션 (pipeline/curation/)

- `jinju8.yaml`: 진주8경(공식: 진주시 관광 누리집 > 진주8경, https://www.jinju.go.kr/02232/02244.web). 진주시 API의 "제N경" 항목을 잡는다.
  fallback(항목이 사라졌을 때만 쓰는 큐레이션 장소)의 좌표·개요는 같은 API 항목에서 옮겼고 원문에 없는 내용은 넣지 않는다.
- `collection30.yaml`: "진주 유등 30선" — **현재 `status: draft`, 사용자 확정 대기.** 진주8경 8 + 대표 명소·박물관 10 + 향토 맛집·먹거리 6 + 야경/체험 6.
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

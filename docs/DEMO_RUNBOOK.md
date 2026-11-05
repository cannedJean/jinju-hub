# 시연 런북

## 시연 전 (T-10분)
1. `https://jinjuhub-api.onrender.com/api/health`를 열어 200이 나올 때까지 기다린다 (무료 플랜 콜드스타트 약 50초).
2. `https://jinju-hub.netlify.app/?demo=1`을 열어 화면 맨 위 가로 전체 주황 배너 `시연 모드`(기준일을 바꾸면 `· 기준일 YYYY-MM-DD`)를 확인한다.
3. 브라우저 위치 권한은 "허용", 또는 시연 모드의 도착 시뮬레이션을 쓴다.
4. (선택) 읽기 전용 라이브 스모크로 주요 화면 확인: `cd frontend && LIVE_URL=https://jinju-hub.netlify.app npm run e2e:live` (쓰기 없음, desktop + mobile).
5. 챗봇 한 번 호출해 응답 확인 (`ANTHROPIC_API_KEY` 설정 후).

## 시연 대본 (e2e `demo-flow`와 동일한 순서)
1. 공유 링크 `/?demo=1`로 진입 -> 시연 모드.
2. 히어로 CTA -> 탐색 화면.
3. 카테고리 칩 `맛집`.
4. 지도를 드래그 -> "이 지역 재검색" -> 목록이 보이는 영역으로 한정.
5. `내 숙소`: 현재 위치(시연 모드에서는 지도의 `가상 내 위치` 핀, 기본 촉석루 — 실제 GPS가 아님) -> 반경(근처에 장소가 없으면 3~5km), 가까운 순.
6. 첫 카드에 숙소로부터의 거리 표시 확인.
7. 상세 -> `담기` -> 도착 시뮬레이션 (가상 위치 핀이 그 장소로 이동하고 곧바로 점등; 거리 제한 없음. 실제 GPS 모드만 150m 규칙 적용).
8. 첫 유등 토스트, 점등 상태, 헤더 진행도.
9. `내 유등`: `첫 등불` 배지.
10. 기준일 프리셋 `유등축제 기간`.
11. 축제 목록: 진주남강유등축제가 진행 중으로 표시.
(이후) 챗봇에 질문 -> 답변과 장소 출처 확인.

## 실패 대비
| 증상 | 대응 |
|---|---|
| 챗봇 키/호출 문제 | 결정적 폴백 답변(검색 결과 요약)이 나온다. 그대로 진행하고 "키 없이도 동작하는 폴백"이라고 설명 |
| 백엔드 무응답/다운 | 아래 로컬 실행 백업으로 전환 |
| 날씨 위젯 오류 | 503 오류 상태가 정상 폴백. 본 흐름에는 영향 없음 |
| 위치 권한 거부 | 시연 모드의 도착 시뮬레이션 사용 |

### 로컬 실행 백업
```bash
# 터미널 1: 백엔드 (SQLite 게시판)
cd backend && source .venv/Scripts/activate
# backend/.env의 Neon URL 대신 로컬 SQLite를 쓰도록 먼저 지정한다 (환경변수가 .env보다 우선).
export DATABASE_URL=sqlite:///./jinjuhub.db
alembic upgrade head                 # 게시판 테이블 생성 (멱등)
python -m app.scripts.seed_posts     # 시연용 게시글 (멱등)
uvicorn main:app --port 8000
# 터미널 2: 프론트
cd frontend && VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```
브라우저에서 `http://127.0.0.1:5173/?demo=1`.

- 장소 데이터: `PLACES_DB_PATH` 기본값은 `backend/app/data/places.db`(저장소에 커밋됨) — 따로 설정할 것 없음.
- 키 없이 실행하면: 챗봇은 `ANTHROPIC_API_KEY`가 없으면 결정적 폴백 답변(검색 결과 요약)을, 날씨 위젯은 `WEATHER_API_KEY`가 없으면 503 오류 상태를 보인다. 둘 다 본 시연 흐름에는 영향 없음.

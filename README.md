# JinjuHub — 진주시 공공 관광 웹사이트

진주시 공공데이터(진주시 OpenAPI · 한국관광공사 TourAPI)를 병렬 수집·정제·병합해 만든 장소 데이터 위에,
지도 중심 탐색과 "유등 밝히기" 게이미피케이션을 얹은 웹사이트입니다.

## 구조

```
JinjuHub/
├─ config/region.yaml   # 진주 지역 설정
├─ pipeline/            # 데이터 수집·정제 파이프라인 (Python)
├─ backend/             # FastAPI (places.db 읽기 전용 + 게시판 + 날씨 + Claude 챗봇)
├─ frontend/            # Vue 3 SPA (Leaflet 지도, 유등 게이미피케이션)
└─ docs/superpowers/    # 설계 명세와 구현 계획
```

## 배포

- 사이트: `TODO(controller): https://<site>.netlify.app` · API: `TODO(controller): https://<render-service>.onrender.com/api/health`
- 스크린샷(3장): `TODO(controller)` — 탐색 지도 / 상세 · 담기 / 내 유등
- 지도 타일은 OSM 기본이며 `VITE_TILE_URL` / `VITE_TILE_URL_DARK`로 덮어쓸 수 있다.

## 아키텍처

`pipeline`(진주시 OpenAPI · TourAPI 수집·정제·병합) -> `backend/app/data/places.db`(읽기 전용) -> `backend`(FastAPI: 장소·게시판·날씨·챗봇) -> `frontend`(Vue 3 SPA).
게시판만 DB(Neon Postgres, 로컬은 SQLite)에 저장한다.

## 로컬 실행

```bash
# 1) 데이터 파이프라인 (pipeline/.env 에 DATA_GO_KR_KEY)
cd pipeline && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt
python -m jinju_pipeline run

# 2) 백엔드 (backend/.env 는 .env.example 참고)
cd backend && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt
alembic upgrade head
PLACES_DB_PATH=./app/data/places.db DATABASE_URL=sqlite:///./jinjuhub.db uvicorn main:app --reload --port 8000

# 3) 프론트
cd frontend && npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 테스트

```bash
cd pipeline && python -m pytest        # 파이프라인
cd backend  && python -m pytest        # 백엔드
cd frontend && npm test                # vitest
cd frontend && npx playwright test     # e2e (BASE_URL 지정 시 배포본 대상)
```

## 문서

[설계 명세](docs/superpowers/specs/2026-11-04-jinjuhub-design.md) · [구현 계획](docs/superpowers/plans/2026-11-04-jinjuhub.md) · [DATA.md](DATA.md) · [DEPLOYMENT.md](DEPLOYMENT.md) · [시연 런북](docs/DEMO_RUNBOOK.md)

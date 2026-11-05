# DEPLOYMENT — Neon · Render · Netlify

구성: 프론트 Netlify(정적 SPA) → 백엔드 Render(FastAPI, 무료 웹 서비스) → DB Neon(Postgres).
장소 데이터는 `backend/app/data/places.db`(저장소에 커밋)를 백엔드가 읽기 전용으로 쓰고, 게시판만 Neon에 저장한다.

## 1. 배포 순서

**Render → Netlify → Render `ALLOWED_ORIGINS` 설정 → 재배포**

### 1.1 Neon (DB)
- 프로젝트 `jinju-hub` (`silent-queen-60966622`, Singapore). **Pooled** 연결 문자열을 `DATABASE_URL`로 쓴다 (`postgresql://...?sslmode=require`).
- 이 개발 PC는 5432 포트에 닿지 못해 로컬에서 마이그레이션을 못 돌린다. 테이블은 Render 빌드(`alembic upgrade head`)가 만든다.
- Neon **Data API**(`NEON_DATA_API_URL`, `backend/.env`)는 앱 런타임에서 쓰지 않는다. HTTPS REST이며 JWT가 필요하다.
  `board_posts`에 비밀번호 해시가 있으므로 **"Grant public schema access"는 끄고**, 노출 테이블을 두지 않는다. 앱은 Render에서 SQLAlchemy로만 접속한다.

### 1.2 Render (백엔드)
- Blueprint(`render.yaml`)로 Web Service `jinjuhub-api` 생성: 지역 Singapore, root `backend`, Python, plan free, health check `/api/health`.
- 브랜치: 지금은 `feat/jinjuhub-mvp`, **`main` 병합 후에는 `main`** (`render.yaml`의 `branch`와 대시보드 설정을 함께 바꾼다).
- 빌드: `pip install -r requirements.txt && alembic upgrade head && python -m app.scripts.seed_posts`
  (무료 플랜은 셸·preDeploy가 없다. 마이그레이션과 시드는 멱등이라 재배포마다 돌아도 안전하다.)
- 시작: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` (레이트리밋이 실제 클라이언트 IP를 쓰도록)
- 시크릿 입력(`sync: false`): `DATABASE_URL`, `WEATHER_API_KEY`, `ALLOWED_ORIGINS`(처음엔 비워 두거나 임시값). `ANTHROPIC_API_KEY`는 마지막 챗봇 테스트 때 추가.
- 확인: `https://<render-service>.onrender.com/api/health` 200.

### 1.3 Netlify (프론트)
- GitHub 저장소 `https://github.com/cannedJean/jinju-hub` 연결. **Base directory = `frontend`** (UI에서 설정; `frontend/netlify.toml`에는 build `npm run build`, publish `dist`, SPA redirect, `NODE_VERSION=20`).
- 환경변수 `VITE_API_BASE_URL=https://<render-service>.onrender.com` (**`/api` 제외**, 끝 슬래시 없음).
- 배포 브랜치는 Render와 동일(지금 `feat/jinjuhub-mvp`, 병합 후 `main`).

### 1.4 CORS 마무리
- Render `ALLOWED_ORIGINS`에 Netlify 주소(`https://<site>.netlify.app`, **끝 슬래시 없음**)를 넣고 재배포.
  - 최종 값: `TODO(controller): 사용자가 알려 준 Netlify URL`

## 2. 환경변수 표

| 위치 | 변수 | 값 / 비고 |
|---|---|---|
| Render | `PYTHON_VERSION` | `3.12.10` |
| Render | `DATABASE_URL` | Neon pooled URL (시크릿) |
| Render | `WEATHER_API_KEY` | 기상청 API허브 (시크릿) |
| Render | `ANTHROPIC_API_KEY` | 챗봇 최종 테스트 때 추가 (시크릿). 없으면 결정적 폴백 답변 |
| Render | `ANTHROPIC_MODEL` | `claude-opus-5-5` |
| Render | `ALLOWED_ORIGINS` | Netlify 주소, 끝 슬래시 없음 |
| Render | `RATE_LIMIT` | `10/minute` |
| Render | `DEMO_DATE_OVERRIDE_ENABLED` | `true` |
| Netlify | `VITE_API_BASE_URL` | Render 주소 (`/api` 제외) |
| Netlify | `VITE_TILE_URL` / `VITE_TILE_URL_DARK` | 선택. 지도 타일 URL 덮어쓰기. 기본은 OSM (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`); CARTO는 API 키가 필요해 제외 |
| GitHub Actions | `DATA_GO_KR_KEY` | data-refresh 워크플로 시크릿 |

실제 값은 각 플랫폼 대시보드와 로컬 `.env`(git 무시)에만 둔다. 저장소에는 넣지 않는다.

## 3. GitHub Actions
- `data-refresh`는 `schedule`이 **기본 브랜치에서만** 돈다. `main` 병합 전에는 Actions 탭에서 `workflow_dispatch`로 `feat/jinjuhub-mvp`를 선택해 실행한다.
- 시크릿 `DATA_GO_KR_KEY` 등록 필요 (Settings > Secrets and variables > Actions).

## 4. 배포 검증
- 라이브 e2e: `cd frontend && BASE_URL=https://<site>.netlify.app npx playwright test --project=desktop --project=mobile` (`BASE_URL`이 있으면 로컬 webServer를 띄우지 않는다).
  - 결과: `TODO(controller): 라이브 e2e 결과`
- 수동 확인: 게시글 작성 → Render "Manual Deploy"로 재배포 → 글 유지(원격 저장), 실기기에서 HTTPS 위치 권한 프롬프트, 챗봇 실답변(장소 출처 포함).

## 5. 콜드스타트 주의
Render 무료 플랜은 15분 무요청 시 잠들고 깨우는 데 **약 50초**가 걸린다. 시연 10분 전에 `/api/health`를 호출해 워밍한다 ([런북](docs/DEMO_RUNBOOK.md)).

## 6. 롤백
- 데이터 문제: 문제의 `places.db` 커밋을 `git revert` → 푸시하면 Render/Netlify가 자동 재배포.
- 코드 문제: Render 대시보드 Events에서 이전 배포로 Rollback, Netlify Deploys에서 이전 배포 "Publish deploy".
- 마이그레이션은 되돌리지 않는다(추가형만 사용).

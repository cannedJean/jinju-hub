# DEPLOYMENT — Neon · Render · Netlify

구성: 프론트 Netlify(정적 SPA) → 백엔드 Render(FastAPI, 무료 웹 서비스) → DB Neon(Postgres).
장소 데이터는 `backend/app/data/places.db`(저장소에 커밋)를 백엔드가 읽기 전용으로 쓰고, 게시판만 Neon에 저장한다.

## 1. 배포 순서

**Render → Netlify → Render `ALLOWED_ORIGINS` 설정 → 재배포**

### 1.1 Neon (DB)
- 프로젝트 `jinju-hub` (`silent-queen-60966622`, Singapore). **Pooled** 연결 문자열을 `DATABASE_URL`로 쓴다 (`postgresql://...?sslmode=require`).
- 이 개발 PC는 5432 포트에 닿지 못해 로컬에서 마이그레이션을 못 돌린다. 테이블은 Render 빌드(`alembic upgrade head`)가 만든다.
- Neon **Data API**와 **Neon Auth**는 앱이 쓰지 않아 2026-11-05에 비활성화/삭제했다. 앱은 Render에서 SQLAlchemy로만 접속한다.
  다시 켜려면 `board_posts`(비밀번호 해시)에 RLS를 걸고 공개 grant를 주지 않아야 한다.

### 1.2 Render (백엔드)
- Blueprint(`render.yaml`)로 Web Service `jinjuhub-api` 생성: 지역 Singapore, root `backend`, Python, plan free, health check `/api/health`.
- 브랜치: 지금은 `feat/jinjuhub-mvp`, **`main` 병합 후에는 `main`** (`render.yaml`의 `branch`와 대시보드 설정을 함께 바꾼다).
- 빌드: `pip install -r requirements.txt && alembic upgrade head && python -m app.scripts.seed_posts`
  (무료 플랜은 셸·preDeploy가 없다. 마이그레이션과 시드는 멱등이라 재배포마다 돌아도 안전하다.)
- 시작: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
  (레이트리밋 키는 uvicorn이 고른 IP가 아니라 `app/core/ratelimit.py`의 `client_ip`: Render 프록시가 붙이는 `True-Client-IP` → 없으면 `X-Forwarded-For`의 **마지막** 항목 → 소켓 주소. XFF 맨 앞 값은 클라이언트가 위조할 수 있어 쓰지 않는다. Render에서는 XFF의 마지막 hop이 Cloudflare 엣지 IP라서 `True-Client-IP`를 우선하며, 이 헤더는 Render 프록시가 덮어쓴다(2026-11-05 라이브 검증, §4).)
- 시크릿 입력(`sync: false`): `DATABASE_URL`, `WEATHER_API_KEY`, `ALLOWED_ORIGINS`(처음엔 비워 두거나 임시값). `ANTHROPIC_API_KEY`는 마지막 챗봇 테스트 때 추가.
- 확인: `https://jinjuhub-api.onrender.com/api/health` 200 (`{"status":"ok","data_version":...}`). 지역 Singapore. 게시판은 빌드의 alembic + 시드로 Neon에 시드 글 8개가 들어 있다.

### 1.3 Netlify (프론트)
- GitHub 저장소 `https://github.com/cannedJean/jinju-hub` 연결. **Base directory = `frontend`** (UI에서 설정; `frontend/netlify.toml`에는 build `npm run build`, publish `dist`, SPA redirect, `NODE_VERSION=20`).
- 환경변수 `VITE_API_BASE_URL=https://jinjuhub-api.onrender.com` (**`/api` 제외**, 끝 슬래시 없음).
- 배포 브랜치는 Render와 동일(지금 `feat/jinjuhub-mvp`, 병합 후 `main`).

### 1.4 CORS 마무리
- Render `ALLOWED_ORIGINS`에 Netlify 주소(`https://jinju-hub.netlify.app`, **끝 슬래시 없음**)를 넣고 재배포.
  - 최종 값: `https://jinju-hub.netlify.app` (CORS 검증 완료)

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
| Render | `CHAT_DAILY_LIMIT` | 선택. 기본 `200`. 프로세스 전체의 하루(KST) Claude 호출 상한. 넘으면 Claude를 부르지 않고 폴백 답변(`fallback: true`) |
| Render | `ANTHROPIC_TIMEOUT_SECONDS` | 선택. 기본 `20`. 프론트 챗 타임아웃(30초)에서 날씨 대기(3초)와 여유를 뺀 값보다 작게 둔다 |
| Render | `ANTHROPIC_MAX_TOKENS` | 선택. 기본 `1024`. 1024보다 크게 넣어도 1024로 제한된다 |
| Netlify | `VITE_API_BASE_URL` | Render 주소 (`/api` 제외) |
| Netlify | `VITE_TILE_URL` / `VITE_TILE_URL_DARK` | 선택. 지도 타일 URL 덮어쓰기. 기본은 OSM (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`); CARTO는 API 키가 필요해 제외 |
| GitHub Actions | `DATA_GO_KR_KEY` | data-refresh 워크플로 시크릿 |

실제 값은 각 플랫폼 대시보드와 로컬 `.env`(git 무시)에만 둔다. 저장소에는 넣지 않는다.

챗봇 비용·장애 동작: Claude 호출이 실패하거나 시간 초과되면, 또는 `CHAT_DAILY_LIMIT`에 도달하면 `/api/chat`은 502가 아니라 200과 결정적 폴백 답변(`fallback: true`)을 돌려준다. `ANTHROPIC_API_KEY`를 넣기 전에 Anthropic 콘솔에서 워크스페이스 지출 한도도 설정해 둔다.

## 3. GitHub Actions
- `data-refresh`는 `schedule`이 **기본 브랜치에서만** 돈다. `main` 병합 전에는 Actions 탭에서 `workflow_dispatch`로 `feat/jinjuhub-mvp`를 선택해 실행한다.
- 시크릿 `DATA_GO_KR_KEY` 등록 필요 (Settings > Secrets and variables > Actions).

## 4. 배포 검증
- 라이브 스모크(읽기 전용, 쓰기 없음): `cd frontend && LIVE_URL=https://jinju-hub.netlify.app npm run e2e:live` (desktop + mobile, 콜드스타트 대비로 `/api/health`를 먼저 워밍한다). 픽스처 e2e는 라이브에서 돌리지 않는다(글 작성 등 쓰기가 있음).
  - 결과: 2026-11-05 desktop + mobile 12/12 통과 (홈 히어로, 탐색 지도+카드, 장소 상세, 축제, 데이터 출처 리포트 카드 4개, 게시판 시드 글 목록)
- 레이트리밋 위조 방지 확인 (부작용 없음: 없는 글 삭제 시도라 404만 쌓인다). 헤더를 매번 바꿔도 11번째가 `429`여야 한다. 모두 `404`면 키가 위조 가능한 상태다. 각 루프 사이에 1분 이상 기다린다.
  ```bash
  API=https://jinjuhub-api.onrender.com
  for H in X-Forwarded-For True-Client-IP CF-Connecting-IP; do
    echo "$H:"
    for i in $(seq 1 11); do curl -s -o /dev/null -w "%{http_code} " -X DELETE $API/api/posts/987654321 -H "Content-Type: application/json" -H "$H: 203.0.113.$i" -d '{"password":"xxxx"}'; done; echo
  done
  ```
  라이브 결과 (2026-11-05):
  | 위조 헤더 | 결과 | 해석 |
  |---|---|---|
  | `X-Forwarded-For` | 404 ×10 → 429 | 위조 무효 (마지막 hop/True-Client-IP 사용) |
  | `True-Client-IP` | 404 ×10 → 429 | Render/Cloudflare가 값을 덮어쓴다 |
  | `CF-Connecting-IP` | 403 ×11 | Cloudflare 엣지가 앱에 닿기 전에 거부 |
  기대: 앞의 둘은 404 ×10 다음 429 (`RATE_LIMIT=10/minute`), 1분 뒤 다시 404.
- 수동 확인: 게시글 작성 → Render "Manual Deploy"로 재배포 → 글 유지(원격 저장), 실기기에서 HTTPS 위치 권한 프롬프트, 챗봇 실답변(장소 출처 포함).

## 5. 콜드스타트 주의
Render 무료 플랜은 15분 무요청 시 잠들고 깨우는 데 **약 50초**가 걸린다. 시연 10분 전에 `/api/health`를 호출해 워밍한다 ([런북](docs/DEMO_RUNBOOK.md)).

## 6. 롤백
- 데이터 문제: 문제의 `places.db` 커밋을 `git revert` → 푸시하면 Render/Netlify가 자동 재배포.
- 코드 문제: Render 대시보드 Events에서 이전 배포로 Rollback, Netlify Deploys에서 이전 배포 "Publish deploy".
- 마이그레이션은 되돌리지 않는다(추가형만 사용).

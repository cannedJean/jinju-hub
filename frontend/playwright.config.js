import { defineConfig } from '@playwright/test'

// Demo rehearsal e2e. Without BASE_URL, Playwright starts the backend (fixture places db + a throwaway
// SQLite board db) and the Vite dev server. Env goes through the `env` objects (Windows-safe, no
// inline VAR=x); real environment variables beat backend/.env in pydantic-settings.
const BASE_URL = process.env.BASE_URL
const PY = process.env.E2E_PYTHON ?? (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python')
// webServer starts before globalSetup, so the stale board db is removed here, before the migration.
// --no-access-log: the backend's secret-mask log filter clears record.args, which uvicorn's access
// formatter cannot format (a 'Logging error' traceback per request); app request logs still print.
const RESET_DB = `${PY} -c "import pathlib; pathlib.Path('e2e.db').unlink(missing_ok=True)"`

const servers = [
  {
    command: `${RESET_DB} && ${PY} -m alembic upgrade head && ${PY} -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log`,
    cwd: '../backend',
    url: 'http://127.0.0.1:8000/api/health',
    env: {
      PLACES_DB_PATH: 'tests/fixtures/places_fixture.db',
      DATABASE_URL: 'sqlite:///./e2e.db',
      RATE_LIMIT: '1000/minute',
      DEMO_DATE_OVERRIDE_ENABLED: 'true',
      // Blank (whitespace) secrets count as unset: chat uses its fallback answer, weather shows its error state.
      ANTHROPIC_API_KEY: ' ',
      WEATHER_API_KEY: ' ',
    },
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173',
    url: 'http://127.0.0.1:5173',
    env: { VITE_API_BASE_URL: 'http://127.0.0.1:8000' },
    timeout: 120_000,
  },
]

const browserUse = { permissions: ['geolocation'] }

export default defineConfig({
  testDir: './e2e',
  // The flows share one backend board db and run fast enough serially; keeps the demo steps readable.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL ?? 'http://127.0.0.1:5173',
    testIdAttribute: 'data-test',
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...browserUse, viewport: { width: 1440, height: 900 } } },
    { name: 'tablet', use: { ...browserUse, viewport: { width: 1024, height: 768 } } },
    { name: 'mobile', use: { ...browserUse, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: BASE_URL ? undefined : servers,
})

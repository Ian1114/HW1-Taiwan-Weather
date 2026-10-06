# CWA Taiwan Weather Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CWA seven-day Taiwan weather dashboard with a rubric-compliant Streamlit submission and a companion Vercel web application, sharing one Python data core.

**Architecture:** `src/weather_dashboard` owns configuration, CWA retrieval/parsing, normalized records, and SQLite persistence. Root `app.py` is the Streamlit presentation layer. The Vercel deployment uses a Vite/React frontend and a server-side Python function that imports the shared package; both UIs display chart, table, and GIS data. SQLite is required for Streamlit grading and is never represented as durable Vercel storage.

**Tech Stack:** Python, requests, pandas, python-dotenv, SQLite, Streamlit, streamlit-folium/Folium, Vercel Python Functions, Vite, React, TypeScript, Leaflet-compatible map library.

**Spec:** `docs/superpowers/specs/2026-10-02-cwa-weather-dashboard-design.md`

## Global Constraints

- CWA dataset is F-A0010-001 JSON; extract `MinT` and `MaxT` by element name for `北部地區`, `中部地區`, `南部地區`, `東北部地區`, `東部地區`, `東南部地區`.
- Normalized rows use `regionName`, `dataDate` as ISO `YYYY-MM-DD`, `mint`, and `maxt`; do not hard-code poster sample values.
- SQLite table is `TemperatureForecasts` with `id`, `regionName`, `dataDate`, `mint`, `maxt` and a unique (`regionName`, `dataDate`) key; SQL is parameterized.
- Streamlit must provide region selection, SQL-backed MinT/MaxT chart, matching table, refresh status, GIS map, attribution, and safe empty/error states.
- Vercel UI and API reuse the Python core; API keys remain server-side and runtime storage is treated as ephemeral.
- Local key source is `.env`/`CWA_API_KEY`; deployment sources are Streamlit secrets and Vercel server environment settings. Never commit secrets or generated databases.
- GIS popups show region, selected date, MinT, and MaxT; maps include a temperature legend and credit CWA and the basemap provider.
- HTTP requests use finite timeouts and errors must not reveal credentials.

## Review Focus

- CWA response has reordered or missing `weatherElement` entries: parser finds elements by name and skips incomplete region/date pairs with a safe diagnostic.
- Forecast value is absent, non-numeric, or uses an unavailable date: normalization rejects the invalid pair without crashing the whole application.
- API key is absent or the API returns HTTP/JSON errors: both UIs give setup/error guidance without exposing the key; Streamlit keeps showing stored rows.
- Refresh is repeated for the same region/date: SQLite updates rows without duplicates and date queries remain ordered.
- Selected map date has partial regional coverage or no records: map renders only available points and shows a clear empty state.

---

### Task 1: Shared configuration, CWA client, and parser

**Files:**
- Create: `src/weather_dashboard/__init__.py`
- Create: `src/weather_dashboard/config.py`
- Create: `src/weather_dashboard/cwa.py`
- Create: `src/weather_dashboard/models.py`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- `config.get_api_key() -> str | None` loads `.env` locally and reads Streamlit/Vercel server environment sources without exposing provider details elsewhere.
- `cwa.fetch_forecast(api_key: str, timeout: float = 20.0) -> dict` requests F-A0010-001, checks HTTP status, and returns decoded JSON or raises a sanitized domain error.
- `cwa.parse_forecast(payload: dict) -> list[ForecastRow]` matches the six required region names and `MinT`/`MaxT` by name, returning normalized rows.
- `models.ForecastRow` has `regionName: str`, `dataDate: str`, `mint: float`, and `maxt: float`.

- [ ] Create an installable `src`-layout package in `pyproject.toml`, shared Python dependencies in the root `requirements.txt`, `.env.example` placeholder, and ignore rules for `.env`, `.streamlit/secrets.toml`, databases, Python caches, and frontend build artifacts.
- [ ] Implement configuration lookup with local dotenv loading and deployment environment compatibility; missing key returns `None`.
- [ ] Implement finite-timeout CWA request and sanitized errors for network, status, and JSON failures.
- [ ] Implement structure-tolerant parser that pairs MinT/MaxT by forecast date, validates values, and returns normalized rows.
- [ ] Manually inspect a representative payload path and verify that the parser interface and all six region names match the design; do not use poster sample values as runtime data.

### Task 2: SQLite persistence and query layer

**Files:**
- Create: `src/weather_dashboard/database.py`

**Interfaces:**
- `database.init_db(db_path: str = "data/weather.db") -> None` creates `TemperatureForecasts` and its unique region/date constraint.
- `database.upsert_forecasts(rows: list[ForecastRow], db_path: str = "data/weather.db") -> int` parameterizes inserts and updates and returns affected row count.
- `database.get_regions(db_path: str = "data/weather.db") -> list[str]` returns sorted distinct region names.
- `database.get_forecasts(region_name: str, db_path: str = "data/weather.db") -> list[ForecastRow]` returns the selected region ordered by `dataDate`.
- `database.get_forecasts_for_date(data_date: str, db_path: str = "data/weather.db") -> list[ForecastRow]` returns available regions for a map date.

- [ ] Implement table creation and ensure the database directory is created when needed.
- [ ] Implement parameterized, idempotent upsert keyed by region/date.
- [ ] Implement distinct-region and ordered forecast queries, including date-wide map lookup.
- [ ] Manually verify schema columns, uniqueness behavior, and date ordering using a temporary local database.

### Task 3: Shared GIS presentation data

**Files:**
- Create: `src/weather_dashboard/regions.py`
- Create: `src/weather_dashboard/presentation.py`

**Interfaces:**
- `regions.REGION_COORDINATES: dict[str, tuple[float, float]]` maps each required region to a representative Taiwan coordinate.
- `presentation.temperature_color(value: float) -> str` maps temperatures to the design's blue/green/yellow/red bands.
- `presentation.build_map_rows(rows: list[ForecastRow], data_date: str) -> list[dict]` joins available forecast rows to coordinates and display colors.

- [ ] Define fixed representative coordinates for all six regions and document their approximate nature.
- [ ] Implement consistent temperature color bands and map row construction for available regions only.
- [ ] Manually inspect that all six regions resolve to coordinates and that temperatures on either side of each band boundary produce the intended color.

### Task 4: Streamlit rubric application

**Files:**
- Create: `app.py`
- Create: `.streamlit/config.toml`
- Modify: `requirements.txt`

**Interfaces:**
- `app.main() -> None` initializes the SQLite cache, provides refresh and region selection, queries the database, and renders status, metadata, chart, table, and map.
- Internal `refresh_forecast() -> tuple[int, str]` uses the shared key, fetch, parse, and database interfaces; returned status text is safe for display.

- [ ] Implement page title, CWA source/dataset/units/update metadata, and refresh feedback.
- [ ] On refresh, fetch and parse actual CWA JSON, upsert valid records, and retain prior database rows on failure.
- [ ] Add `st.selectbox`, SQL-backed MinT/MaxT line chart, and matching date/value table.
- [ ] Add date-selectable Folium map with colored markers, legend, popups, empty state, and attribution through `streamlit-folium`.
- [ ] Show clear setup and empty-database guidance when credentials or data are absent.
- [ ] Manually run the app with no key and with a populated local database to inspect the expected error/empty states and the chart/table/map flow.

### Task 5: Vercel Python API and web frontend

**Files:**
- Create: `api/index.py`
- Create: `vercel.json`
- Create: `package.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/api.ts`
- Create: `web/src/WeatherMap.tsx`
- Create: `web/src/styles.css`
- Create: `web/tsconfig.json`
- Create: `web/vite.config.ts`
- Modify: `.gitignore`

**Interfaces:**
- `api/index.py` exports a serverless ASGI application with `GET /api/forecast`; it reads `CWA_API_KEY` server-side, calls `fetch_forecast` and `parse_forecast`, and returns normalized rows plus source metadata.
- Frontend `fetchForecast(): Promise<ForecastResponse>` calls `/api/forecast`; response types match `ForecastRow[]` and contain no credential fields. Use Recharts for the line chart and React Leaflet for the map.
- React UI filters by region/date and renders chart, table, and GIS map from the same normalized record contract.

- [ ] Add a Vercel Python API entrypoint that imports the repository's shared package and safely returns normalized forecast JSON.
- [ ] Configure Vite/TypeScript and Vercel routing/build so the React frontend and `/api/forecast` endpoint are served from one project, with the root Python package importable by the function.
- [ ] Build region/date controls, MinT/MaxT chart and table, and an interactive Taiwan map with matching markers, legend, popups, and attribution.
- [ ] Add loading, API error, missing configuration, and partial-data states; keep the key exclusively in the Python server environment.
- [ ] Manually run a local frontend/API development flow with a configured key and inspect the browser network responses to confirm no key is returned to the client.

### Task 6: Setup, GitHub, and deployment documentation

**Files:**
- Create: `README.md`
- Create: `.streamlit/secrets.toml.example`
- Create: `vercel-env.example`

- [ ] Document Python and Node setup, local `.env`, dependency installation, Streamlit launch, and optional Vercel local development.
- [ ] Document GitHub repository setup and safe push workflow, explicitly excluding real keys and generated SQLite data.
- [ ] Document Streamlit Community Cloud secrets and entrypoint configuration plus Vercel project/root/build/environment settings.
- [ ] Document CWA and basemap attribution, refreshable-cache behavior, and the distinction between the rubric submission and Vercel companion.
- [ ] Review README commands and paths against the actual repository layout and deployment configuration.

### Task 7: Rubric coverage review and delivery polish

**Files:**
- Modify: `README.md`
- Modify: `app.py` and/or `web/src/App.tsx` only for gaps found in review.

- [ ] Walk through the poster rubric in order: API 20%, JSON 20%, SQLite 20%, Streamlit 40%, then optional GIS.
- [ ] Confirm both deployment guides explain their secret sources and that `.gitignore` excludes every local secret/database artifact.
- [ ] Confirm failure and partial-data states from Review Focus are addressed in the corresponding UI/core behavior.
- [ ] Summarize deliverables and deployment limitations in README without claiming durable serverless storage.

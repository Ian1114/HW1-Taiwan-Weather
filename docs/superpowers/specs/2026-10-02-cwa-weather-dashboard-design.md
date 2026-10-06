# CWA Taiwan Weather Dashboard Design Spec

**Date:** 2026-10-02  
**Status:** User-approved; implementation prepared, deployment pending  
**Course:** HW10 / Taiwan Weather Forecast

## Goal

Deliver a rubric-compliant Streamlit application and a companion Vercel application for Taiwan's CWA seven-day forecast. Both applications use the same Python configuration, retrieval, parsing, and normalization core. The Streamlit application is the course submission and must satisfy all required rubric items; both applications include an interactive GIS map.

## Source of requirements

The teacher's HW10 poster is authoritative for the graded requirements:

| Rubric section | Weight | Required result |
| --- | ---: | --- |
| CWA API retrieval | 20% | Use CWA Open Data JSON product F-A0010-001 and retrieve seven-day forecast data for six regions. |
| JSON analysis | 20% | Find location and weather-element records; extract daily `MinT` and `MaxT`. |
| SQLite storage | 20% | Create `TemperatureForecasts` and save normalized forecast rows. |
| Streamlit web app | 40% | Provide a region selector, SQL-backed results, minimum/maximum line chart, and data table. |
| Taiwan map | Optional | Show regional temperature values on an interactive Folium map. |

The poster's sample dates and temperatures are illustrative. Runtime results must come from CWA.

## Architecture and data flow

One GitHub repository contains a shared Python package, the graded Streamlit application, and a Vercel application.

1. **Shared Python core:** reads configuration, retrieves F-A0010-001 JSON, validates the response, parses the six regions, and normalizes date/minimum/maximum rows. Both applications use these same functions so their weather values and error handling agree.
2. **SQLite persistence:** the Streamlit application creates and queries `TemperatureForecasts` using parameterized SQL and an idempotent region/date key. The Vercel edition uses the shared retrieval/parser and may cache data only within the limits of its runtime; it must not claim durable SQLite storage.
3. **Streamlit application:** provides refresh, region selection, a SQL-backed chart and table, and Folium GIS visualization. This is the version submitted for the teacher's rubric.
4. **Vercel application:** provides a web frontend and server-side Python API using the shared core, with region/date selection and the same GIS weather view. The CWA key remains server-side in Vercel environment settings. Vercel deployment is a companion deliverable and does not replace the Streamlit submission.

Data flow for Streamlit: CWA JSON -> shared parser -> normalized rows -> SQLite -> selected-region SQL query -> chart, table, and map.

Data flow for Vercel: browser -> server-side Python API -> shared parser -> normalized forecast -> frontend chart, table, and map. The browser never receives the CWA key.

## CWA data and normalization

- Dataset: CWA Open Data F-A0010-001 seven-day forecast JSON.
- Required forecast regions: `北部地區`, `中部地區`, `南部地區`, `東北部地區`, `東部地區`, `東南部地區`.
- Required weather elements: `MinT` and `MaxT`.
- Each normalized record has `regionName`, `dataDate` (ISO `YYYY-MM-DD`), `mint`, and `maxt`.
- Parse the actual response structure and find weather elements by name. Do not depend on list ordering or poster sample data.
- Refresh obtains current data. Existing Streamlit database rows remain viewable if CWA is unavailable, with a readable failure message and the last successful refresh time.

## SQLite schema

The Streamlit database creates `TemperatureForecasts`:

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Row identifier. |
| `regionName` | `TEXT NOT NULL` | One of the six forecast region names. |
| `dataDate` | `TEXT NOT NULL` | Forecast date in ISO `YYYY-MM-DD` form. |
| `mint` | `REAL NOT NULL` | Daily minimum temperature in Celsius. |
| `maxt` | `REAL NOT NULL` | Daily maximum temperature in Celsius. |

Add a unique constraint on (`regionName`, `dataDate`) so refreshes update rather than duplicate records. Use parameterized SQL. Provide queries for distinct regions and a selected region's rows ordered by date.

## Streamlit application

- Identify the app as a CWA seven-day Taiwan weather forecast.
- A refresh control reports loading, success, or failure.
- A `st.selectbox` selects a region.
- Display separate `MinT` and `MaxT` chart series, the matching date/value table, and an interactive Folium map with temperature-colored markers, a legend, and date/min/max popups.
- Show source, dataset ID, Celsius units, map attribution, and last successful update time.
- Missing credentials, empty database, malformed data, and failed refreshes produce readable guidance; no traceback or secret is shown to users.

## Vercel application

- Deploy a companion web frontend and server-side Python API from the same GitHub repository.
- Reuse the shared Python configuration, CWA request, parser, and normalized data contract. Keep Vercel-specific request/response and frontend code separate from the Streamlit UI.
- Provide region/date selection and a temperature chart, table, and interactive Taiwan GIS map with source attribution.
- Read `CWA_API_KEY` only in the server-side runtime environment. Do not expose it to browser code, client-prefixed build variables, URLs, logs, or responses.
- Treat any local database/cache in serverless execution as temporary and rebuildable. Durable multi-user persistence is out of scope.

## GIS and attribution

Use Folium for the Streamlit map and a browser-compatible map library for Vercel. Show forecast region values for a selected date using fixed regional coordinates, temperature-based marker colors, a readable legend, and popups containing region, date, MinT, and MaxT. Credit CWA as the data source and credit the selected public basemap/data provider in both interfaces and the README. Do not copy reference sites' layouts, text, code, or visual assets.

## Environment and credentials

- Local development reads `CWA_API_KEY` from `.env` via `python-dotenv` or an equivalent loader.
- Commit `.env.example` with a placeholder only. Ignore `.env`, `.streamlit/secrets.toml`, generated `*.db`, and local deployment secrets.
- Streamlit Community Cloud reads the key from app secrets; Vercel reads it from server-side project environment variables. A shared config helper resolves supported sources without exposing provider-specific secret handling to the parser.
- Never place the key in source code, UI, URL, database, screenshots, or logs. Missing credentials produce clear setup instructions.
- Any API key previously pasted in chat is considered compromised and must not be reused; configure a rotated key only in local or deployment secrets.

## GitHub and deployment

- Keep source, dependency declarations, README, and `.env.example` in GitHub. Never commit credentials or generated databases.
- Document deployment of the Streamlit entrypoint from GitHub to Streamlit Community Cloud and the companion frontend/API to Vercel.
- The Streamlit SQLite database is a refreshable cache, not a durable archive. The app detects a missing or empty database and lets the user rebuild it from CWA. Historical durability across restarts is out of scope.
- Vercel deployment complements and does not replace the Streamlit rubric submission.

## Error handling and quality

- Use a finite HTTP timeout. Handle network errors, non-success status codes, invalid JSON, missing regions/elements/dates, and invalid temperatures without exposing the key.
- Use parameterized SQL and the unique region/date key.
- Separate retrieval, parsing, persistence, and presentation into focused modules.
- On Streamlit refresh failure, show the most recent valid stored forecast and explain the failure.
- Pin deployment-compatible dependencies and document local setup, secrets, GitHub workflow, and both deployment paths in `README.md`.

## Out of scope

- AirBox air-quality readings, accounts, notifications, user-generated content, unrelated APIs, and durable historical storage.
- Recreating supplied reference websites' branding, source code, wording, or visual assets.
- Production-grade multi-user database behavior.

## Acceptance criteria

1. With a configured key, the shared core retrieves F-A0010-001 JSON and safely reports request/configuration errors.
2. Parsing matches weather elements by name and produces valid `regionName`, `dataDate`, `mint`, and `maxt` records for available dates across the six regions.
3. Streamlit creates `TemperatureForecasts`, stores rows idempotently, and supports region/date queries.
4. The Streamlit app provides region selection, SQL-backed MinT/MaxT chart and matching table, refresh status, and safe empty/error states.
5. Both applications show the optional interactive GIS enhancement with six regional values, date-specific popups, readable temperature legend, and source attribution.
6. Local `.env`, Streamlit secrets, and Vercel secrets are documented and excluded from Git; the API key is never exposed client-side.
7. README documents GitHub setup, local `.env`, Streamlit Community Cloud deployment, and Vercel deployment.
8. A missing Streamlit SQLite file can be recreated by refreshing CWA; neither app claims durable history from ephemeral storage.

## Superpowers workflow

After user approval of this updated design document, create and review a task-by-task implementation plan under `docs/superpowers/plans/`. The user then reviews the plan and selects native or subagent-driven execution before implementation begins.

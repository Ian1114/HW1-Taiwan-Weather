# CWA Taiwan Weather Dashboard — Design Spec

**Date:** 2026-10-02  
**Status:** Draft for user review  
**Course:** HW10 / Taiwan Weather Forecast

## Goal

Build a Python and Streamlit web app that retrieves the Central Weather Administration (CWA) seven-day forecast, extracts daily minimum and maximum temperatures for Taiwan's six forecast regions, stores the normalized results in SQLite, and lets a viewer select a region to inspect a temperature chart and table. The implementation must prioritize the teacher's assignment rubric. An interactive GIS map is an optional enhancement.

## Source of requirements

The teacher's HW10 poster is the authoritative rubric:

| Rubric section | Weight | Required result |
| --- | ---: | --- |
| CWA API retrieval | 20% | Use the CWA Open Data JSON product F-A0010-001 and retrieve seven-day forecast data for the six regions. |
| JSON analysis | 20% | Find the location and weather-element records and extract each date's `MinT` and `MaxT` values. |
| SQLite storage | 20% | Create a `TemperatureForecasts` table and save normalized temperature rows. |
| Streamlit web app | 40% | Provide a region selector, SQL-backed forecast results, a minimum/maximum line chart, and a data table. |
| Taiwan map | Optional | Show the regional temperature values on an interactive Folium map. |

The poster's examples are illustrative values and dates, not hard-coded expected forecast data. Use the actual CWA response at runtime.

## Design

### Architecture and data flow

The project is a single Python repository with three clear responsibilities:

1. **CWA retrieval and parsing:** a Python data module uses `requests` to call F-A0010-001, checks the HTTP response, parses the JSON locations, and maps each region/date to `mint` and `maxt` values. Pandas is used to normalize, inspect, and prepare the rows.
2. **SQLite persistence and queries:** a database module creates `TemperatureForecasts`, writes rows idempotently, and exposes focused read functions for distinct regions and a selected region's forecast rows.
3. **Streamlit dashboard:** `app.py` presents the refresh action, selected-region forecast, chart, and table. It calls the data and database modules rather than embedding API, SQL, and UI logic in one file.

Data flow: CWA JSON → parsed and normalized Python records → SQLite → SQL query for selected region → Streamlit chart and table.

### CWA data and normalization

- Dataset: CWA Open Data F-A0010-001, seven-day forecast JSON, as identified in the teacher's poster.
- Regions: 北部地區、中部地區、南部地區、東北部地區、東部地區、東南部地區.
- Weather elements: `MinT` and `MaxT`.
- Each normalized record contains `regionName`, `dataDate`, `mint`, and `maxt`.
- The parser must use the actual response's field structure and match weather elements by their names; it must not depend on record ordering or the sample dates printed in the poster.
- A refresh button retrieves and stores the latest response. The app reports its last successful refresh time. If the CWA service is unavailable, existing database rows remain viewable and the app shows a readable error.

### SQLite schema

Create a `TemperatureForecasts` table with these fields:

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Row identifier, following the teacher's example. |
| `regionName` | `TEXT NOT NULL` | One of the six CWA forecast region names. |
| `dataDate` | `TEXT NOT NULL` | Forecast date in ISO `YYYY-MM-DD` form. |
| `mint` | `REAL NOT NULL` | Daily minimum temperature in Celsius. |
| `maxt` | `REAL NOT NULL` | Daily maximum temperature in Celsius. |

Add a unique constraint on (`regionName`, `dataDate`) so refreshing the same forecast updates rows rather than creating duplicates. Use parameterized SQL. The app must be able to query distinct region names and forecast rows for a chosen region ordered by date.

### Streamlit user experience

- Title and short description identify the app as a CWA seven-day Taiwan forecast.
- A refresh control retrieves current CWA data and shows loading, success, or failure status.
- A `st.selectbox` lets the user choose one of the six regions.
- For the selected region, show a line chart with separate `MinT` and `MaxT` series over the available forecast dates.
- Show the corresponding dates and temperature values in a table.
- Display the source name, dataset identifier, units, and last successful update time.
- If no API key is configured or no rows are available, show setup guidance or an empty-state message rather than a traceback.

### Optional GIS enhancement

After the four required rubric sections work, add an interactive Folium map using `streamlit-folium`. Show the six forecast regions with a temperature-based marker color, legend, and a popup containing the selected date and that region's minimum/maximum values. Use an openly licensed or public map/data source, credit it in the interface and README, and do not copy the reference websites' layout, text, code, or visual assets. The map remains optional and must not delay completion of the 60% API/JSON/SQLite work or the 40% Streamlit dashboard.

The supplied Taiwan weather-map reference is useful for ideas such as map layers, readable markers, controls, and source attribution. The AirBox reference is useful for ideas such as map-based discovery, filters, legends, and showing recent values. AirBox is an air-quality monitoring service; its readings and content are outside this weather assignment.

## Environment and credential handling

- Local development reads `CWA_API_KEY` from a `.env` file using `python-dotenv` or an equivalent environment loader.
- Commit `.env.example` with a placeholder only; ignore `.env`, `.streamlit/secrets.toml`, and generated `*.db` files in `.gitignore`.
- The deployed Streamlit app reads `CWA_API_KEY` from Streamlit Community Cloud's app secrets. Keep a single configuration helper so the API module does not know whether a value came from local `.env` or deployment secrets.
- Never put the key in source code, the UI, a URL, a database row, screenshots, or logs. Missing credentials must produce a clear setup message.
- The API key previously pasted in chat must not be reused; the user should rotate it and provide the replacement only through the local secret configuration or deployment settings.

## GitHub and online deployment

- Keep source code, dependency declarations, README, and `.env.example` in a GitHub repository; never commit credentials or the generated SQLite database.
- Deploy the Streamlit entrypoint from that repository to Streamlit Community Cloud, which connects to GitHub and deploys an app from a selected repository, branch, and entrypoint file.
- The assignment's SQLite database is a refreshable cache of public forecast data, not the authoritative long-term archive. Community Cloud does not guarantee persistence of local generated files, so the app must detect an empty/missing database and allow the forecast to be fetched again. Historical durability across restarts is out of scope.
- Vercel is not part of the course-first implementation. The teacher's rubric requires Streamlit; a Vercel-specific alternative would need a separate architecture and should be considered only after the rubric-compliant app is complete.

## Error handling and quality requirements

- Set a finite HTTP timeout; handle request failures, non-success status codes, invalid JSON, missing regions/elements/dates, and invalid temperature values without exposing the API key.
- Use parameterized SQL and a unique region/date key to prevent duplicate forecast rows.
- Keep data retrieval, parsing, persistence, and presentation in separate modules with clear names and short functions.
- Show the most recent valid stored forecast when a refresh fails; explain the problem without hiding it.
- Pin dependencies in a deployment-compatible `requirements.txt` and document local setup and deployment steps in `README.md`.

## Out of scope

- Recreating the reference sites' design, source code, wording, or branding.
- AirBox air-quality data, accounts, notifications, user-generated content, and unrelated APIs.
- Persistent historical storage or a production-grade multi-user database.
- Vercel deployment in the course-priority phase.

## Acceptance criteria

1. The app can retrieve F-A0010-001 JSON using a configured key and reports API failures safely.
2. The parser returns normalized `regionName`, `dataDate`, `mint`, and `maxt` rows for available dates and the six required forecast regions.
3. SQLite creates `TemperatureForecasts`, stores rows, prevents duplicate region/date records after repeated refreshes, and supports region/date queries.
4. The Streamlit app has a working region selector and presents the selected region's minimum/maximum chart and matching table.
5. Local `.env` secrets and deployed app secrets are excluded from Git, and the README explains both configuration paths.
6. On Community Cloud, an absent/cleared SQLite file can be rebuilt by refreshing the public CWA forecast.
7. The optional map is only accepted after criteria 1–6 are satisfied.

## Superpowers workflow

This document is the reviewed design/spec stage. After the user approves this file, create a separate, task-by-task implementation plan under `docs/superpowers/plans/`. Review that plan before implementation begins. This follows Superpowers' design → written spec → user spec review → implementation plan → user plan review and execution-choice sequence.

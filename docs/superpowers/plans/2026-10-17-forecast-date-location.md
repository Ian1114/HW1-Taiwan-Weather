# Forecast Date and Location Fix Plan

> **For agentic workers:** Implement inline using the already approved native execution approach.

**Goal:** Make the map date selector reflect valid township forecast dates, include today in the seven-day forecast, show an accurate forecast high on map markers, refine chart legend sizing, and use the requested HTML5 location options.

**Architecture:** Keep the existing React data flow and browser Geolocation API. Derive available dates from town forecast rows and fall back to the current regional forecast date only while township data is unavailable. Keep chart/table data scoped to all selected-region rows.

**Tech Stack:** React, TypeScript, Recharts, Leaflet, HTML5 Geolocation API.

**Spec:** Approved in-chat design and user corrections on 2026-10-17.

## Global Constraints

- Keep the regional chart and data table on the complete seven-day forecast.
- The town map markers and their temperature details must follow the selected valid date.
- Recharts legend marks and labels are 12 pixels; do not resize the chart SVG itself.
- Geolocation options: `enableHighAccuracy: true`, `timeout: 5000`, `maximumAge: 0`.

## Review Focus

- Regional and township forecast dates may not align; use township dates for the map selector.
- Keep the displayed regional table independent of the map date selection.
- Preserve browser permission prompts and existing location error messaging.
- CWA may replace today's 06:00 period with a 12:00 period; use the available periods and retain today.
- Map marker values identify the selected date's forecast high, not a live station reading.

### Task 1: Align forecast date selection and map rows

**Files:** Modify `web/src/App.tsx`, `web/src/WeatherMap.tsx`.

- [x] Derive the shared date selector options from township forecast rows when loaded.
- [x] Pass the selected township date into the map and filter marker values/popups by that date.
- [x] Keep regional chart and table mapped from the first seven rows for the selected region.

### Task 2: Refine chart legend and location timeout

**Files:** Modify `web/src/App.tsx`, `web/src/styles.css`, `web/src/location.ts`.

- [x] Set only the two temperature legend symbols to 12×12 and their text to 12 pixels.
- [x] Set browser geolocation timeout to 5000 ms while preserving high accuracy and no cache.

### Task 3: Verify

- [x] Run the frontend production build and inspect the diff for unrelated changes.

### Task 4: Restore the current forecast date

**Files:** Modify `src/weather_dashboard/cwa.py`, `src/weather_dashboard/towns.py`, `web/src/WeatherMap.tsx`, `README.md`; add `tests/test_forecast_today.py`.

- [x] Prove both parsers drop a current date with 12:00 and 18:00 periods.
- [x] Aggregate today's available periods and retain full 06:00/18:00 future dates.
- [x] Show the selected date's forecast high in map markers and label it clearly.
- [x] Confirm the live CWA response yields 2026-10-17 through 2026-10-23.

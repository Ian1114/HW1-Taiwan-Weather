"""Vercel ASGI endpoint backed by the shared weather package."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from weather_dashboard.config import get_api_key
from weather_dashboard.towns import COUNTY_DATASETS, get_town_forecast
from weather_dashboard.conditions import get_conditions, SOURCES
from weather_dashboard.cwa import (
    CWAError,
    DATASET_ID,
    SOURCE_NOTE,
    fetch_forecast,
    forecast_coverage_warnings,
    parse_forecast,
)

app = FastAPI(title="台灣天氣預報資料服務", docs_url=None, redoc_url=None)


def _forecast_response(response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    api_key = get_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="伺服器尚未設定氣象署 API 金鑰。",
        )
    try:
        rows = parse_forecast(fetch_forecast(api_key))
    except CWAError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="氣象署預報載入失敗，請稍後重試。") from exc

    return {
        "source": "中央氣象署開放資料",
        "datasetId": DATASET_ID,
        "unit": "°C",
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "warnings": [SOURCE_NOTE, *forecast_coverage_warnings(rows)],
        "rows": [row.to_dict() for row in rows],
    }


@app.get("/")
def root(response: Response) -> dict[str, Any]:
    return _forecast_response(response)


@app.get("/forecast")
def forecast(response: Response) -> dict[str, Any]:
    return _forecast_response(response)


@app.get("/api/forecast")
def forecast_with_prefix(response: Response) -> dict[str, Any]:
    return _forecast_response(response)


@app.get("/api/index/forecast")
def forecast_vercel_rewrite(response: Response) -> dict[str, Any]:
    return _forecast_response(response)


@app.get("/api/counties")
@app.get("/api/index/counties")
@app.get("/counties")
def counties():
    return {"counties": list(COUNTY_DATASETS)}


@app.get("/api/towns")
@app.get("/api/index/towns")
@app.get("/towns")
def towns(response: Response, county: str = "臺中市"):
    response.headers["Cache-Control"] = "no-store"
    if county not in COUNTY_DATASETS:
        raise HTTPException(status_code=400, detail="請選擇有效的縣市。")
    key = get_api_key()
    if not key:
        raise HTTPException(status_code=503, detail="尚未設定氣象署 API 金鑰。")
    try:
        return get_town_forecast(key, county)
    except CWAError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except Exception:
        raise HTTPException(status_code=502, detail="鄉鎮市區預報載入失敗，請稍後重試。") from None


@app.get("/api/conditions")
@app.get("/api/index/conditions")
@app.get("/conditions")
def conditions(response: Response, kind: str = "rain", county: str = "臺中市"):
    response.headers["Cache-Control"] = "no-store"
    if kind not in SOURCES or county not in COUNTY_DATASETS:
        raise HTTPException(status_code=400, detail="不支援的資訊類型或縣市。")
    try:
        return get_conditions(kind, county)
    except Exception:
        raise HTTPException(status_code=502, detail="資料載入失敗，請稍後重試。") from None


@app.get("/{path:path}")
def forecast_route_fallback(path: str, response: Response) -> dict[str, Any]:
    return _forecast_response(response)

"""CWA weekly forecast retrieval and regional response normalization."""

from __future__ import annotations

import math
import ssl
from datetime import date, datetime
from typing import Any

import requests
import truststore

from .models import ForecastRow

DATASET_ID = "F-D0047-091"
SOURCE_NOTE = (
    "資料來源 F-D0047-091：六區數值由所屬縣市預報彙整，"
    "最低溫取最小值、最高溫取最大值；非氣象署官方六區預報。"
)
API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{DATASET_ID}"
REQUEST_TIMEOUT = 20.0
REGION_NAMES = (
    "\u5317\u90e8\u5730\u5340",
    "\u4e2d\u90e8\u5730\u5340",
    "\u5357\u90e8\u5730\u5340",
    "\u6771\u5317\u90e8\u5730\u5340",
    "\u6771\u90e8\u5730\u5340",
    "\u6771\u5357\u90e8\u5730\u5340",
)


class CWAError(RuntimeError):
    """A safe, user-displayable CWA service or response error."""


class _SystemTrustAdapter(requests.adapters.HTTPAdapter):
    """Use native certificate validation without modifying global SSL state."""

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        host, pool = super().build_connection_pool_key_attributes(request, verify, cert)
        if verify is True:
            pool["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return host, pool


def fetch_forecast(api_key: str, timeout: float = REQUEST_TIMEOUT, *, dataset_id: str = DATASET_ID) -> dict[str, Any]:
    """Fetch the CWA dataset without including credentials in errors."""
    try:
        with requests.Session() as session:
            session.mount("https://opendata.cwa.gov.tw/", _SystemTrustAdapter())
            response = session.get(
                f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}",
                headers={"Authorization": api_key},
                timeout=timeout,
            )
        response.raise_for_status()
    except requests.exceptions.SSLError:
        raise CWAError("氣象署 HTTPS 憑證驗證失敗，請檢查系統憑證設定。") from None
    except requests.Timeout as exc:
        raise CWAError("氣象署連線逾時，請稍後重試。") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise CWAError(f"氣象署回應錯誤（HTTP {status}），請稍後重試。") from exc
    except requests.RequestException as exc:
        raise CWAError("無法連接氣象署服務，請稍後重試。") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise CWAError("氣象署回傳資料格式無效。") from exc
    if not isinstance(payload, dict):
        raise CWAError("氣象署回傳資料結構不符預期。")
    if str(payload.get("success", "true")).lower() == "false":
        raise CWAError("氣象署未提供所要求的預報資料。")
    return payload


def _forecast_date(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _temperature(element: dict[str, Any], day: str) -> float | None:
    times = element.get("time", [])
    if not isinstance(times, list):
        return None
    for item in times:
        if not isinstance(item, dict) or _forecast_date(item.get("startTime")) != day:
            continue
        values = item.get("elementValue", [])
        raw: object = None
        if isinstance(values, list) and values and isinstance(values[0], dict):
            raw = values[0].get("value")
        elif isinstance(item.get("parameter"), dict):
            raw = item["parameter"].get("parameterName")
        try:
            parsed = float(raw)
        except (TypeError, ValueError):
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def parse_forecast(payload: dict[str, Any]) -> list[ForecastRow]:
    """Normalize available region/day MinT and MaxT values by element name."""
    records = payload.get("records")
    if not isinstance(records, dict):
        raise CWAError("氣象署預報缺少地區資料。")

    if "Locations" in records:
        return _parse_county_weekly(records)

    location_blocks = records.get("locations")
    if isinstance(location_blocks, list):
        locations: list[Any] = []
        for block in location_blocks:
            if not isinstance(block, dict):
                continue
            nested = block.get("location")
            if isinstance(nested, list):
                locations.extend(nested)
            elif "weatherElement" in block:
                locations.append(block)
    else:
        locations = []
    legacy_locations = records.get("location")
    if not locations and isinstance(legacy_locations, list):
        locations = legacy_locations
    if not locations:
        raise CWAError("氣象署預報的地區資料格式不符預期。")

    rows: list[ForecastRow] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        region = location.get("locationName")
        if region not in REGION_NAMES:
            continue
        weather = location.get("weatherElement", [])
        if not isinstance(weather, list):
            continue
        by_name = {
            element.get("elementName"): element
            for element in weather
            if isinstance(element, dict) and isinstance(element.get("elementName"), str)
        }
        mint_element = by_name.get("MinT")
        maxt_element = by_name.get("MaxT")
        if not mint_element or not maxt_element:
            continue

        date_keys: set[str] = set()
        for element in (mint_element, maxt_element):
            for item in element.get("time", []) if isinstance(element.get("time"), list) else []:
                if isinstance(item, dict):
                    day = _forecast_date(item.get("startTime"))
                    if day:
                        date_keys.add(day)
        for day in sorted(date_keys):
            mint = _temperature(mint_element, day)
            maxt = _temperature(maxt_element, day)
            if mint is None or maxt is None or mint > maxt:
                continue
            rows.append(ForecastRow(regionName=region, dataDate=day, mint=mint, maxt=maxt))

    if not rows:
        raise CWAError("氣象署未提供完整的每日高低溫預報。")
    return sorted(rows, key=lambda row: (REGION_NAMES.index(row.regionName), row.dataDate))


REGION_COUNTIES = {
    REGION_NAMES[0]: ("基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣"),
    REGION_NAMES[1]: ("苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"),
    REGION_NAMES[2]: ("嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"),
    REGION_NAMES[3]: ("宜蘭縣",),
    REGION_NAMES[4]: ("花蓮縣",),
    REGION_NAMES[5]: ("臺東縣",),
}


def _parse_county_weekly(records: dict[str, Any]) -> list[ForecastRow]:
    """Aggregate complete 06:00/18:00 forecast days; never invent missing values."""
    samples: dict[tuple[str, str, str], dict[int, float]] = {}
    for block in records.get("Locations", []):
        for location in block.get("Location", []):
            county = location.get("LocationName", "").replace("台", "臺")
            for element in location.get("WeatherElement", []):
                field = {"最低溫度": "MinTemperature", "最高溫度": "MaxTemperature"}.get(element.get("ElementName"))
                if not field:
                    continue
                for item in element.get("Time", []):
                    try:
                        start = datetime.fromisoformat(item["StartTime"])
                        value = float(item["ElementValue"][0][field])
                    except (KeyError, ValueError, TypeError, IndexError):
                        continue
                    if math.isfinite(value) and start.hour in (6, 18):
                        samples.setdefault((county, start.date().isoformat(), field), {})[start.hour] = value
    dates = sorted({key[1] for key in samples})
    rows = []
    for day in dates:
        daily = []
        for region, counties in REGION_COUNTIES.items():
            lows, highs = [], []
            for county in counties:
                low = samples.get((county, day, "MinTemperature"), {})
                high = samples.get((county, day, "MaxTemperature"), {})
                if set(low) != {6, 18} or set(high) != {6, 18}:
                    break
                lows.extend(low.values())
                highs.extend(high.values())
            else:
                if min(lows) <= max(highs):
                    daily.append(ForecastRow(regionName=region, dataDate=day, mint=min(lows), maxt=max(highs)))
        if len(daily) == len(REGION_NAMES):
            rows.extend(daily)
        if len(rows) == 42:
            break
    if not rows:
        raise CWAError("氣象署未提供完整的區域預報日期。")
    return sorted(rows, key=lambda row: (REGION_NAMES.index(row.regionName), row.dataDate))


def forecast_coverage_warnings(rows: list[ForecastRow]) -> list[str]:
    """Describe omitted regions or incomplete daily data without exposing secrets."""
    dates_by_region = {
        region: {row.dataDate for row in rows if row.regionName == region}
        for region in REGION_NAMES
    }
    missing_regions = [region for region, dates in dates_by_region.items() if not dates]
    all_dates = set().union(*dates_by_region.values()) if rows else set()
    partial_regions = [
        region
        for region, dates in dates_by_region.items()
        if dates and dates != all_dates
    ]
    warnings: list[str] = []
    if len(all_dates) < 7:
        warnings.append(f"目前僅有 {len(all_dates)} 天完整預報，未滿七天。")
    if missing_regions:
        warnings.append(f"預報缺少以下區域：{', '.join(missing_regions)}.")
    if partial_regions:
        warnings.append(
            "以下區域的預報日期不完整：" + ", ".join(partial_regions) + "."
        )
    return warnings

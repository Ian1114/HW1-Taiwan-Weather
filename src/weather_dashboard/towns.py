"""County-scoped CWA township forecasts, shared by both interfaces."""

import math
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from .cwa import CWAError, fetch_forecast

COUNTY_DATASETS = dict(zip(
    ("宜蘭縣", "桃園市", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣",
     "屏東縣", "臺東縣", "花蓮縣", "澎湖縣", "基隆市", "新竹市", "嘉義市", "臺北市",
     "高雄市", "新北市", "臺中市", "臺南市", "連江縣", "金門縣"),
    (f"F-D0047-{number:03}" for number in range(3, 88, 4)),
))
_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = Lock()


def parse_towns(payload: dict, county: str) -> list[dict]:
    """Use actual township coordinates and today's remaining forecast periods."""
    blocks = payload.get("records", {}).get("Locations", [])
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    rows = []
    for block in blocks:
        if block.get("LocationsName", "").replace("台", "臺") != county:
            continue
        for town in block.get("Location", []):
            try:
                lat, lon = float(town["Latitude"]), float(town["Longitude"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            samples = {}
            for element in town.get("WeatherElement", []):
                field = {"最低溫度": "MinTemperature", "最高溫度": "MaxTemperature"}.get(element.get("ElementName"))
                if not field:
                    continue
                for item in element.get("Time", []):
                    try:
                        start = datetime.fromisoformat(item["StartTime"])
                        value = float(item["ElementValue"][0][field])
                    except (KeyError, TypeError, ValueError, IndexError):
                        continue
                    if math.isfinite(value):
                        samples.setdefault(start.date().isoformat(), {}).setdefault(field, {})[start.hour] = value
            complete = 0
            for day, values in sorted(samples.items()):
                if day < today:
                    continue
                low, high = values.get("MinTemperature", {}), values.get("MaxTemperature", {})
                hours = set(low) & set(high)
                if not hours or (day != today and not {6, 18}.issubset(hours)):
                    continue
                if day != today:
                    hours = {6, 18}
                mint, maxt = min(low[hour] for hour in hours), max(high[hour] for hour in hours)
                if mint > maxt:
                    continue
                rows.append({"county": county, "townName": town["LocationName"],
                             "latitude": lat, "longitude": lon, "dataDate": day,
                             "mint": mint, "maxt": maxt})
                complete += 1
                if complete == 7:
                    break
    if not rows:
        raise CWAError("此縣市目前沒有完整的鄉鎮市區預報，請稍後再試。")
    return rows


def get_town_forecast(api_key: str, county: str) -> dict:
    if county not in COUNTY_DATASETS:
        raise ValueError("請選擇有效的縣市。")
    with _cache_lock:
        cached = _cache.get(county)
        if cached and monotonic() - cached[0] < 600:
            return cached[1]
    dataset = COUNTY_DATASETS[county]
    payload = fetch_forecast(api_key, dataset_id=dataset)
    rows = parse_towns(payload, county)
    result = {"county": county, "datasetId": dataset, "rows": rows,
              "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with _cache_lock:
        _cache[county] = (monotonic(), result)
    return result

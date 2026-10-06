"""Latest observations and marine forecasts; never replace missing values with zero."""
import math
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import requests

from .config import get_api_key, get_secret
from .cwa import CWAError, _SystemTrustAdapter, fetch_forecast
from .towns import COUNTY_DATASETS

SOURCES = {
    "rain": ("O-A0002-001", "即時降雨量"),
    "wind": ("O-A0001-001", "即時風向與風速"),
    "typhoon": ("W-C0034-001", "颱風警報資訊"),
    "air": ("aqx_p_432", "空氣品質"),
    "marine": ("F-A0012-001", "漁業氣象・海面預報"),
}
_cache = {}
_lock = Lock()


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) and parsed >= 0 else None
    except (ValueError, TypeError):
        return None


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else None
    except ValueError:
        return None


def wind_direction(value, speed):
    degree = number(value)
    if speed == 0:
        return "靜風"
    if degree == 990:
        return "風向不定"
    if degree is None or degree > 360:
        return "缺測"
    names = ("北", "北北東", "東北", "東北東", "東", "東南東", "東南", "南南東", "南", "南南西", "西南", "西南西", "西", "西北西", "西北", "北北西")
    return names[int((degree + 11.25) / 22.5) % 16] + "風"


def parse_stations(payload, kind, county):
    rows = []
    for station in payload.get("records", {}).get("Station", []):
        geo = station.get("GeoInfo", {})
        if geo.get("CountyName", "").replace("台", "臺") != county:
            continue
        observed = station.get("ObsTime", {}).get("DateTime")
        dt = instant(observed)
        row = {"station": station.get("StationName"), "town": geo.get("TownName"), "observedAt": observed,
               "freshness": "超過兩小時" if dt and (datetime.now(timezone.utc)-dt).total_seconds() > 7200 else "依觀測時間"}
        if kind == "rain":
            values = station.get("RainfallElement", {})
            for name, key in (("rain10m", "Past10Min"), ("rain1h", "Past1hr"), ("rain24h", "Past24hr")):
                row[name] = number(values.get(key, {}).get("Precipitation"))
        else:
            values = station.get("WeatherElement", {})
            row["speed"] = number(values.get("WindSpeed"))
            row["direction"] = wind_direction(values.get("WindDirection"), row["speed"])
            degrees = number(values.get("WindDirection"))
            row["degrees"] = degrees if degrees is not None and degrees <= 360 else None
        rows.append(row)
    return rows


def parse_typhoon(payload):
    rows = []
    now = datetime.now(timezone.utc)
    infos = payload.get("records", {}).get("info", [])
    if isinstance(infos, dict):
        infos = [infos]
    for info in infos:
        if info.get("language") not in (None, "zh-TW"):
            continue
        end = instant(info.get("expires"))
        begin = instant(info.get("effective"))
        headline = info.get("headline", "颱風警報")
        active = bool(begin and end and begin <= now < end and "解除" not in headline and info.get("urgency") != "Past")
        description = info.get("description", {})
        sections = description.get("section", []) if isinstance(description, dict) else []
        rows.append({"headline": headline, "state": "有效警報" if active else "歷史／已解除／非有效時段",
                     "publishedAt": info.get("effective"), "expiresAt": info.get("expires"),
                     "description": "\n".join(f"{part.get('title', '')}：{part.get('value', '')}" for part in sections) if sections else str(description)})
    return rows


def parse_marine(payload):
    dataset = payload.get("cwaopendata", {}).get("Dataset", {})
    issued = dataset.get("DatasetInfo", {}).get("IssueTime")
    rows = []
    for location in dataset.get("Locations", {}).get("Location", []):
        periods = {}
        for element in location.get("WeatherElement", []):
            for item in element.get("Time", []):
                start, end = item.get("StartTime"), item.get("EndTime")
                if not start or not end:
                    continue
                row = periods.setdefault((start, end), {"sea": location.get("LocationName"), "start": start, "end": end, "issuedAt": issued})
                values = item.get("ElementValue", {})
                if isinstance(values, list):
                    values = values[0] if values else {}
                for source, target in (("Weather", "weather"), ("WindDirectionDescription", "direction"), ("BeaufortScaleDescription", "wind"), ("WaveHeightDescription", "wave"), ("WaveTypeDescription", "seaState")):
                    if source in values:
                        row[target] = values[source]
        rows.extend(periods.values())
    return rows


def parse_air(payload, county):
    return [{"station": r.get("sitename"), "aqi": number(r.get("aqi")), "quality": r.get("status"),
             "pm25": number(r.get("pm2.5")), "pm10": number(r.get("pm10")), "observedAt": r.get("publishtime") or r.get("datacreationdate")}
            for r in payload.get("records", []) if r.get("county", "").replace("台", "臺") == county]


def _download(kind):
    dataset = SOURCES[kind][0]
    key = get_secret("MOENV_API_KEY") if kind == "air" else get_api_key()
    if not key:
        raise CWAError("尚未設定環境部 API 金鑰。" if kind == "air" else "尚未設定氣象署 API 金鑰。")
    if kind not in ("air", "marine"):
        return fetch_forecast(key, dataset_id=dataset)
    try:
        with requests.Session() as session:
            domain = "https://data.moenv.gov.tw/" if kind == "air" else "https://opendata.cwa.gov.tw/"
            session.mount(domain, _SystemTrustAdapter())
            url = domain + ("api/v2/aqx_p_432" if kind == "air" else "fileapi/v1/opendataapi/F-A0012-001")
            params = {"api_key": key, "format": "json", "limit": 1000} if kind == "air" else {"Authorization": key, "format": "JSON"}
            response = session.get(url, params=params, timeout=20)
            if not response.ok:
                raise CWAError(f"官方服務回應錯誤（HTTP {response.status_code}），請稍後重試。")
            payload = response.json()
            if kind == "air" and isinstance(payload, list):
                payload = {"records": payload}
            if not isinstance(payload, dict):
                raise CWAError("官方資料格式不符預期。")
            if kind == "air" and not isinstance(payload.get("records"), list):
                raise CWAError("環境部未提供有效資料，請確認 API 金鑰與服務狀態。")
            return payload
    except (requests.RequestException, ValueError):
        # Query-string credentials must never appear in client errors or traces.
        raise CWAError("官方資料連線或格式發生問題，請稍後重試。") from None


def get_conditions(kind, county="臺中市"):
    if kind not in SOURCES or county not in COUNTY_DATASETS:
        raise ValueError("不支援的資訊類型或縣市。")
    dataset, title = SOURCES[kind]
    base = {"title": title, "datasetId": dataset, "source": "環境部" if kind == "air" else "中央氣象署", "county": county,
            "status": "ok", "rows": [], "fetchedAt": None, "note": ""}
    if kind == "air" and not get_secret("MOENV_API_KEY"):
        return {**base, "status": "unconfigured", "note": "尚未設定環境部金鑰。請申請後在本機 .env 加入 MOENV_API_KEY；部署時加入伺服器環境變數。"}
    try:
        with _lock:
            cached = _cache.get(kind)
        if cached and monotonic() - cached[0] < 300:
            _, payload, fetched = cached
        else:
            payload = _download(kind)
            fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with _lock:
                _cache[kind] = (monotonic(), payload, fetched)
        rows = parse_stations(payload, kind, county) if kind in ("rain", "wind") else parse_air(payload, county) if kind == "air" else parse_typhoon(payload) if kind == "typhoon" else parse_marine(payload)
        notes = {"rain": "最新測站累積雨量，單位為毫米；不是降雨機率。缺測與特殊代碼顯示為缺測，不當作零雨量。",
                 "wind": "風向代表風的來向；風速單位為公尺／秒，角度由正北順時針計算。",
                 "typhoon": "顯示官方最近一則警報資料及有效時段；歷史或已解除警報不代表目前存在有效警報。警報資訊也不代表全部海上颱風。",
                 "air": "空氣品質指標與測站污染物濃度；資料時間以環境部發布時間為準。",
                 "marine": "漁業氣象採用海面預報，請依海域及預報時段查看浪高、浪況與風級；不是出海安全判定。"}
        return {**base, "rows": rows, "fetchedAt": fetched, "status": "ok" if rows else "empty", "note": notes[kind]}
    except CWAError as exc:
        return {**base, "status": "error", "note": str(exc)}

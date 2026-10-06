"""Rubric-compliant CWA weather dashboard using Streamlit and SQLite."""

from __future__ import annotations

import html
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from weather_dashboard.config import get_api_key
from weather_dashboard.conditions import SOURCES, get_conditions
from weather_dashboard.cwa import (
    CWAError,
    DATASET_ID,
    SOURCE_NOTE,
    fetch_forecast,
    forecast_coverage_warnings,
    parse_forecast,
)
from weather_dashboard.database import (
    DEFAULT_DB_PATH,
    get_forecasts,
    get_last_successful_refresh,
    get_regions,
    init_db,
    set_last_successful_refresh,
    upsert_forecasts,
)
from weather_dashboard.towns import COUNTY_DATASETS, get_town_forecast

st.set_page_config(page_title="台灣天氣預報", page_icon="⛅", layout="wide")


def _refresh() -> tuple[str, str]:
    api_key = get_api_key()
    if not api_key:
        return "error", "尚未設定氣象署 API 金鑰，請在本機 .env 或部署機密設定中填入。"
    try:
        rows = parse_forecast(fetch_forecast(api_key))
        saved = upsert_forecasts(rows)
        refreshed_at = set_last_successful_refresh()
        warnings = forecast_coverage_warnings(rows)
        message = f"已更新 {saved} 筆預報，時間：{refreshed_at}（世界協調時間）。"
        if warnings:
            return "warning", message + " " + " ".join(warnings)
        return "success", message
    except CWAError as exc:
        return "error", str(exc)
    except Exception:
        return "error", "更新失敗，仍可查看先前儲存的預報資料。"


def _render_map(rows, selected_date: str) -> None:
    points = [row for row in rows if row["dataDate"] == selected_date]
    if not points:
        st.info("所選日期目前沒有預報資料。")
        return

    weather_map = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7,
        tiles=None,
        scrollWheelZoom=True,
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© 開放街圖貢獻者", name="街道地圖",
    ).add_to(weather_map)
    weather_map.fit_bounds([[p["latitude"], p["longitude"]] for p in points], max_zoom=12)
    for point in points:
        region = html.escape(str(point["county"]) + "・" + str(point["townName"]))
        middle = (point["mint"] + point["maxt"]) / 2
        color = "#1976d2" if middle < 20 else "#16a765" if middle < 25 else "#f4cf24" if middle <= 30 else "#e85935"
        forecast_date = html.escape(str(point["dataDate"]))
        popup_html = (
            f"<b>{region}</b><br>預報日期：{forecast_date}<br>"
            f"最低溫：{float(point['mint']):g} °C<br>最高溫：{float(point['maxt']):g} °C"
        )
        folium.CircleMarker(
            location=[float(point["latitude"]), float(point["longitude"])],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=2,
            tooltip=region,
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(weather_map)

    legend = """
    <div style="position:fixed;bottom:28px;left:28px;z-index:9999;background:white;
        padding:10px 12px;border:1px solid #9aa6b2;border-radius:6px;font-size:13px">
      <b>高低溫中間值</b><br>
      <span style="color:#1976d2">●</span> &lt; 20 °C<br>
      <span style="color:#16a765">●</span> 20–25 °C<br>
      <span style="color:#f4cf24">●</span> 25–30 °C<br>
      <span style="color:#e85935">●</span> &gt; 30 °C
    </div>
    """
    weather_map.get_root().html.add_child(folium.Element(legend))
    st_folium(weather_map, use_container_width=True, height=800, key="taiwan-weather-map")
    st.caption("天氣資料：中央氣象署。地圖：© 開放街圖貢獻者。")


def main() -> None:
    init_db(DEFAULT_DB_PATH)
    st.title("台灣天氣預報")
    st.info(SOURCE_NOTE)
    st.caption(
        "串接中央氣象署最新一週預報，查看區域氣溫與鄉鎮市區天氣。"
    )

    with st.expander("即時降雨・颱風・風向・空氣品質・漁業氣象", expanded=False):
        kind = st.selectbox("選擇資訊類型", list(SOURCES), format_func=lambda value: SOURCES[value][1])
        names = list(COUNTY_DATASETS)
        county = st.selectbox("觀測縣市", names, index=names.index("臺中市"), disabled=kind in ("marine", "typhoon"))
        try:
            conditions = get_conditions(kind, county)
            st.info(conditions["note"])
            if conditions["status"] == "unconfigured":
                st.link_button("環境部金鑰申請說明", "https://data.moenv.gov.tw/paradigm")
            labels = {"station":"測站", "town":"鄉鎮市區", "observedAt":"觀測／發布時間", "freshness":"資料時效",
                      "rain10m":"近十分鐘雨量（毫米）", "rain1h":"近一小時雨量（毫米）", "rain24h":"近二十四小時雨量（毫米）",
                      "speed":"風速（公尺／秒）", "direction":"風向", "degrees":"方位角（度）", "aqi":"空氣品質指標",
                      "quality":"品質等級", "pm25":"細懸浮微粒（微克／立方公尺）", "pm10":"懸浮微粒（微克／立方公尺）",
                      "headline":"警報標題", "state":"有效狀態", "publishedAt":"發布時間", "expiresAt":"有效至", "description":"警報全文",
                      "sea":"海域", "start":"預報起始", "end":"預報結束", "issuedAt":"發布時間", "weather":"天氣", "wind":"風級", "wave":"浪高", "seaState":"浪況"}
            rows = conditions["rows"]
            if kind == "marine" and rows:
                sea = st.selectbox("選擇海域", sorted({row["sea"] for row in rows}))
                rows = [row for row in rows if row["sea"] == sea]
            if rows:
                st.dataframe(pd.DataFrame(rows).rename(columns=labels), use_container_width=True, hide_index=True)
            st.caption(f"來源：{conditions['source']}・{conditions['datasetId']}・取得時間：{conditions['fetchedAt'] or '尚未取得'}；伺服器快取最長五分鐘。")
        except Exception:
            st.error("此項資料目前無法取得，其他預報仍可使用。")

    action_col, status_col = st.columns([1, 3])
    with action_col:
        refresh_clicked = st.button("更新氣象署預報", type="primary", use_container_width=True)
    if refresh_clicked:
        with st.spinner("正在取得氣象署最新預報…"):
            st.session_state["refresh_message"] = _refresh()
    if message := st.session_state.get("refresh_message"):
        kind, text = message
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        else:
            st.error(text)

    last_update = get_last_successful_refresh()
    with status_col:
        st.caption(f"資料來源：中央氣象署・資料集：{DATASET_ID}・單位：°C")
        st.caption(f"上次更新時間（世界協調時間）：{last_update or '尚未更新'}")

    regions = get_regions()
    if not regions:
        if not get_api_key():
            st.info("請先在本機 .env 或部署機密設定中加入 CWA_API_KEY，再更新資料。")
        else:
            st.info("尚未儲存預報，請按「更新氣象署預報」取得資料。")
        st.caption("六區數值由縣市預報彙整。")
        return

    selected_region = st.selectbox("選擇預報區域", regions)
    region_rows = get_forecasts(selected_region)
    if not region_rows:
        st.info("此區域目前沒有預報資料。")
        return

    chart_col, table_col = st.columns([3, 2], gap="large")
    with chart_col:
        st.subheader(f"一週氣溫預報・{selected_region}")
        chart_data = pd.DataFrame(
            {
                "日期": [row.dataDate for row in region_rows],
                "最低溫（°C）": [row.mint for row in region_rows],
                "最高溫（°C）": [row.maxt for row in region_rows],
            }
        ).set_index("日期")
        st.line_chart(chart_data, height=360)
    with table_col:
        st.subheader("每日預報明細")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "日期": row.dataDate,
                        "最低溫（°C）": row.mint,
                        "最高溫（°C）": row.maxt,
                    }
                    for row in region_rows
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("鄉鎮市區氣溫地圖")
    map_dates = sorted({row.dataDate for region in regions for row in get_forecasts(region)})
    selected_date = st.selectbox(
        "地圖預報日期",
        map_dates,
        index=0,
        format_func=lambda value: date.fromisoformat(value).strftime("%Y-%m-%d"),
    )
    county_names = list(COUNTY_DATASETS)
    county = st.selectbox("選擇地圖縣市", county_names, index=county_names.index("臺中市"))
    st.caption("滑鼠滾輪縮放・拖曳移動・點選標記查看氣溫")
    api_key = get_api_key()
    if api_key:
        try:
            with st.spinner("正在載入鄉鎮市區預報…"):
                town_data = get_town_forecast(api_key, county)
            town_names = sorted({row["townName"] for row in town_data["rows"]})
            town = st.selectbox("定位鄉鎮市區", ["全部鄉鎮市區", *town_names])
            town_rows = [row for row in town_data["rows"] if town == "全部鄉鎮市區" or row["townName"] == town]
            _render_map(town_rows, selected_date)
            st.caption(f"鄉鎮資料集：{town_data['datasetId']}；資料取得時間：{town_data['fetchedAt']}（世界協調時間），快取最長十分鐘。")
        except CWAError as exc:
            st.error(str(exc))
        except Exception:
            st.error("鄉鎮預報載入失敗，請稍後再試。")
    else:
        st.info("請設定氣象署 API 金鑰，以載入鄉鎮預報。")
    st.caption("標記採用氣象署鄉鎮預報點座標；顯示日間與夜間預報高低溫，並非即時觀測值。")


if __name__ == "__main__":
    main()

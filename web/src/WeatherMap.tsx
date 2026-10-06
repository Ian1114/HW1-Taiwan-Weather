import { useEffect, useMemo, useRef, useState } from "react";
import { divIcon } from "leaflet";
import { AttributionControl, Circle, CircleMarker, MapContainer, Marker, Popup, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";
import RefreshButton from "./RefreshButton";
import { assessLocation, requestLocation } from "./location";
import type { UserLocation } from "./location";
import { fetchTownData } from "./api";
import type { TownForecast, TownResponse } from "./api";

function markerColor(value: number): string {
  if (value < 20) return "#1976d2";
  if (value < 25) return "#16a765";
  if (value <= 30) return "#d1a800";
  return "#e85935";
}

function MapFocus({ points, position }: { points: TownForecast[]; position: UserLocation | null }) {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  useEffect(() => {
    const translateClose = () => {
      const close = map.getContainer().querySelector(".leaflet-popup-close-button");
      close?.setAttribute("aria-label", "關閉氣溫資訊");
      close?.setAttribute("title", "關閉氣溫資訊");
    };
    map.on("popupopen", translateClose);
    return () => { map.off("popupopen", translateClose); };
  }, [map]);
  const locations = JSON.stringify(points.map((p) => [p.latitude, p.longitude]));
  useEffect(() => {
    const bounds: [number, number][] = JSON.parse(locations);
    if (position) {
      map.setView([position.latitude, position.longitude], 14);
    } else if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  }, [map, locations, position]);
  return null;
}

export default function WeatherMap({ selectedDate }: { selectedDate: string }) {
  const [position, setPosition] = useState<UserLocation | null>(null);
  const [unverifiedPosition, setUnverifiedPosition] = useState<UserLocation | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");
  const mounted = useRef(true);
  const locationRequest = useRef(0);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function locate() {
    const id = ++locationRequest.current;
    setLocating(true); setLocationError(""); setUnverifiedPosition(null); setPosition(null);
    try {
      const next = await requestLocation();
      if (!mounted.current || id !== locationRequest.current) return;
      const assessment = assessLocation(next, data?.rows ?? []);
      if (assessment.needsReview) {
        setUnverifiedPosition(next);
        setLocationError(`瀏覽器回報的位置不夠可靠：精度約 ${Math.round(next.accuracy)} 公尺，距離所選 ${county} 的預報地點最近約 ${Math.round(assessment.nearestKm)} 公里。地圖已暫停跳轉。請在上方選擇實際鄉鎮市區，或檢查電腦與瀏覽器的位置設定。`);
      } else {
        setTown("");
        setPosition(next);
      }
    } catch (cause) {
      if (mounted.current && id === locationRequest.current) setLocationError(cause instanceof Error ? cause.message : "定位失敗，請重試。");
    } finally {
      if (mounted.current && id === locationRequest.current) setLocating(false);
    }
  }
  function clearLocationFocus() { locationRequest.current++; setPosition(null); setUnverifiedPosition(null); setLocating(false); setLocationError(""); }
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (!expanded) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setExpanded(false); };
    window.addEventListener("keydown", close);
    return () => { document.body.style.overflow = previous; window.removeEventListener("keydown", close); };
  }, [expanded]);
  const [counties, setCounties] = useState<string[]>([]);
  const [county, setCounty] = useState("臺中市");
  const [town, setTown] = useState("");
  const [data, setData] = useState<TownResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setData(null);
    Promise.all([
      fetchTownData<{ counties: string[] }>("/api/counties", controller.signal).then((catalog) => {
        if (!controller.signal.aborted) setCounties(catalog.counties);
        return catalog;
      }),
      fetchTownData<TownResponse>(`/api/towns?county=${encodeURIComponent(county)}`, controller.signal),
    ]).then(([catalog, forecast]) => {
      if (!controller.signal.aborted) {
        setCounties(catalog.counties);
        setData(forecast);
      }
    }).catch((cause) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "鄉鎮資料載入失敗。");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [county, retry]);

  const townNames = useMemo(() => [...new Set(data?.rows.map((row) => row.townName) ?? [])], [data]);
  const points = useMemo(() => (data?.rows ?? []).filter((row) => row.dataDate === selectedDate && (!town || row.townName === town)), [data, selectedDate, town]);

  return (
    <div className={expanded ? "town-map map-expanded" : "town-map"}>
      <div className="map-topbar">
        <div className="map-title-actions">
          <h2>各鄉鎮市區預報</h2>
          <button className="locate-button" type="button" onClick={() => void locate()} disabled={locating || loading || !data?.rows.length} aria-label={locating ? "定位中" : "定位當前位置"} title={locating ? "定位中" : "定位當前位置"}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16 10c0-2.21-1.79-4-4-4s-4 1.79-4 4 1.79 4 4 4 4-1.79 4-4m-6 0c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2"/><path fill="currentColor" d="M11.42 21.81c.17.12.38.19.58.19s.41-.06.58-.19c.3-.22 7.45-5.37 7.42-11.82 0-4.41-3.59-8-8-8s-8 3.59-8 8c-.03 6.44 7.12 11.6 7.42 11.82M12 4c3.31 0 6 2.69 6 6 .02 4.44-4.39 8.43-6 9.74-1.61-1.31-6.02-5.29-6-9.74 0-3.31 2.69-6 6-6"/></svg>
          </button>
        </div>
        <div className="town-controls">
          <label className="control"><span>選擇縣市</span>
            <select value={county} onChange={(event) => { clearLocationFocus(); setCounty(event.target.value); setTown(""); }}>
              {(counties.length ? counties : [county]).map((name) => <option key={name}>{name}</option>)}
            </select>
          </label>
          <label className="control"><span>定位鄉鎮市區</span>
            <select value={town} onChange={(event) => { clearLocationFocus(); setTown(event.target.value); }} disabled={loading || !data}>
              <option value="">全部鄉鎮市區</option>
              {townNames.map((name) => <option key={name}>{name}</option>)}
            </select>
          </label>
        </div>
        <div className="map-view-actions">
          <span className="map-date-pill">{selectedDate}</span>
          <button className="map-icon-button" type="button" aria-label={expanded ? "關閉全螢幕地圖" : "全螢幕檢視地圖"} title={expanded ? "關閉全螢幕地圖" : "全螢幕檢視地圖"} aria-pressed={expanded} onClick={() => setExpanded(value => !value)}><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M10 3H3v7h2V5h5zM10 19H5v-5H3v7h7zM21 14h-2v5h-5v2h7zM21 3h-7v2h5v5h2z" /></svg></button>
        </div>
      </div>
      {locationError && <div className="town-status location-alert" role="alert">{locationError}{unverifiedPosition && <button type="button" onClick={() => { setTown(""); setPosition(unverifiedPosition); setUnverifiedPosition(null); setLocationError(""); }}>仍顯示裝置回報的位置</button>}</div>}
      {position && <p className="town-status" role="status">已標示瀏覽器回報位置（{position.latitude.toFixed(5)}、{position.longitude.toFixed(5)}），精度約 {Math.round(position.accuracy)} 公尺。</p>}
      {loading && <p className="town-status" role="status">正在載入{county}鄉鎮預報…</p>}
      {error && <div className="town-status" role="alert">{error} <RefreshButton onClick={() => setRetry((value) => value + 1)} label="重新載入鄉鎮預報" /></div>}
      {!loading && !error && !points.length && <p className="town-status" role="status">{selectedDate} 暫無完整的鄉鎮預報，請選擇其他日期。</p>}
      <div className="map-scroll"><div className="map-frame">
        <MapContainer center={[23.75, 120.95]} zoom={7} scrollWheelZoom zoomControl={false} attributionControl={false}>
          <ZoomControl zoomInTitle="放大地圖" zoomOutTitle="縮小地圖" />
          <AttributionControl prefix={false} />
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">開放街圖貢獻者</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <MapFocus points={points} position={position} />
          {position && <>
            <Circle center={[position.latitude, position.longitude]} radius={position.accuracy} pathOptions={{color:"#2563eb",weight:1,fillOpacity:0.08}} interactive={false} />
            <CircleMarker center={[position.latitude, position.longitude]} radius={10} pathOptions={{color:"white",weight:3,fillColor:"#2563eb",fillOpacity:1}}>
              <Tooltip permanent direction="top">裝置回報位置</Tooltip><Popup>瀏覽器回報位置<br/>定位精度約 {Math.round(position.accuracy)} 公尺</Popup>
            </CircleMarker>
          </>}
          {points.map((row) => {
            const middleTemperature = Math.round((row.mint + row.maxt) / 2);
            const color = markerColor(middleTemperature);
            const icon = divIcon({
              className: "temperature-marker-wrapper",
              html: `<span class="temperature-marker" style="--marker-color:${color};--marker-text:${middleTemperature >= 25 && middleTemperature <= 30 ? "#183247" : "#ffffff"}">${middleTemperature}°</span>`,
              iconSize: [34, 24],
              iconAnchor: [17, 12],
            });
            return (
              <Marker key={`${row.county}-${row.townName}-${row.dataDate}`} position={[row.latitude, row.longitude]} icon={icon}>
                <Tooltip direction="top">{row.townName}：{row.mint}～{row.maxt} °C</Tooltip>
                <Popup><strong>{row.county}・{row.townName}</strong><br />預報日期：{row.dataDate}<br />最低溫：{row.mint} °C<br />最高溫：{row.maxt} °C</Popup>
              </Marker>
            );
          })}
        </MapContainer>
        <div className="map-legend">
          <strong>高低溫中間值</strong>
          <span><i className="dot blue" /> 低於 20 °C</span>
          <span><i className="dot green" /> 20～未滿 25 °C</span>
          <span><i className="dot yellow" /> 25～30 °C</span>
          <span><i className="dot red" /> 高於 30 °C</span>
        </div>
      </div></div>
      <div className="town-metadata">
        {data && <>
          <p>{county}：顯示 {points.length} 個鄉鎮市區／共 {townNames.length} 個。資料集：{data.datasetId}。</p>
          <p>取得時間：{new Date(data.fetchedAt).toLocaleString("zh-TW", { timeZone: "Asia/Taipei" })}（快取最長 10 分鐘）。</p>
        </>}
        <p>顯示日間及夜間預報的最低與最高溫；夜間時段延續至翌日清晨。</p>
        <p>這是預報資料，並非即時測站觀測值。</p>
      </div>
    </div>
  );
}

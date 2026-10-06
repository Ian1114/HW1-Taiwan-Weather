import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchForecast } from "./api";
import type { ForecastResponse } from "./api";
import WeatherMap from "./WeatherMap";
import ConditionsPanel from "./ConditionsPanel";
import RefreshButton from "./RefreshButton";

export default function App() {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [selectedRegion, setSelectedRegion] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const next = await fetchForecast();
      setForecast(next);
      const regions = [...new Set(next.rows.map((row) => row.regionName))];
      const dates = [...new Set(next.rows.map((row) => row.dataDate))].sort();
      setSelectedRegion((current) => regions.includes(current) ? current : regions[0] ?? "");
      setSelectedDate((current) => dates.includes(current) ? current : dates[0] ?? "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "天氣預報載入失敗，請稍後重試。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const regions = useMemo(
    () => [...new Set(forecast?.rows.map((row) => row.regionName) ?? [])],
    [forecast],
  );
  const dates = useMemo(
    () => [...new Set(forecast?.rows.map((row) => row.dataDate) ?? [])].sort(),
    [forecast],
  );
  const regionRows = useMemo(
    () => (forecast?.rows ?? []).filter((row) => row.regionName === selectedRegion),
    [forecast, selectedRegion],
  );
  const summary = useMemo(() => {
    if (!regionRows.length) return null;
    return {
      low: Math.min(...regionRows.map((row) => row.mint)),
      high: Math.max(...regionRows.map((row) => row.maxt)),
      days: regionRows.length,
    };
  }, [regionRows]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="臺灣天氣預報首頁">
          <span className="brand-mark">☼</span>
          <span>臺灣天氣預報</span>
        </a>
        <span className="topbar-meta">中央氣象署開放資料 <i /> 最新預報</span>
      </header>

      <main id="top" className="dashboard">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot" /> 臺灣・未來七天天氣</div>
            <h1>HW1: CWA 天氣預報網站</h1>
          </div>
          <div className="hero-side">
            <span className="hero-icon">☀</span>
          </div>
        </section>

        <section className="toolbar" aria-label="預報篩選">
          <label className="control">
            <span>預報區域</span>
            <select value={selectedRegion} onChange={(event) => setSelectedRegion(event.target.value)} disabled={!regions.length}>
              {regions.length ? regions.map((region) => <option key={region}>{region}</option>) : <option>等待資料載入</option>}
            </select>
          </label>
          <label className="control date-control">
            <span>地圖預報日期</span>
            <select value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} disabled={!dates.length}>
              {dates.length ? dates.map((value) => <option key={value} value={value}>{value}</option>) : <option>—</option>}
            </select>
          </label>
          <RefreshButton onClick={() => void refresh()} loading={loading} label="更新預報" />
          <span className="unit-note">氣溫 <b>°C</b></span>
        </section>

        {error && (
          <div className="notice error-notice" role="alert">
            <span className="notice-symbol">!</span>
            <div><strong>無法取得預報</strong><span>{error}</span></div>
            <RefreshButton onClick={() => void refresh()} loading={loading} label="重新嘗試" />
          </div>
        )}
        {loading && !forecast && <div className="notice loading-notice">正在連接中央氣象署開放資料…</div>}
        {forecast?.warnings?.map((warning) => (
          <div className="notice error-notice" role="status" key={warning}>
            <span className="notice-symbol">!</span>
            <div><strong>資料說明</strong><span>{warning}</span></div>
          </div>
        ))}
        {!loading && !error && forecast && !forecast.rows.length && (
          <div className="notice">目前沒有完整的區域預報，請稍後重新整理。</div>
        )}

        {forecast && forecast.rows.length > 0 && (
          <>
            <section className="summary-grid" aria-label="預報摘要">
              <article className="summary-card summary-main">
                <span className="summary-label">目前區域</span>
                <strong>{selectedRegion}</strong>
                <span className="summary-caption">{summary?.days ?? 0} 天預報</span>
              </article>
              <article className="summary-card">
                <span className="summary-label">一週最低溫</span>
                <strong>{summary?.low ?? "—"}<small>°C</small></strong>
                <span className="summary-caption">目前預報期間的氣溫極值</span>
              </article>
              <article className="summary-card">
                <span className="summary-label">一週最高溫</span>
                <strong>{summary?.high ?? "—"}<small>°C</small></strong>
                <span className="summary-caption">目前預報期間的氣溫極值</span>
              </article>
              <article className="summary-card update-card">
                <span className="summary-label">資料取得時間</span>
                <strong>{new Date(forecast.fetchedAt).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Taipei" })}</strong>
                <span className="summary-caption">{new Date(forecast.fetchedAt).toLocaleDateString("zh-TW", { timeZone: "Asia/Taipei" })}</span>
              </article>
            </section>

            <section className="content-grid">
              <article className="panel chart-panel">
                <div className="panel-heading">
                  <div><span className="section-kicker">氣溫趨勢</span><h2>一週高低溫預報</h2></div>
                  <span className="region-chip">{selectedRegion}</span>
                </div>
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={regionRows} margin={{ top: 12, right: 14, left: -14, bottom: 4 }}>
                      <CartesianGrid stroke="#e9eff3" vertical={false} />
                      <XAxis dataKey="dataDate" tickLine={false} axisLine={false} tick={{ fill: "#72818e", fontSize: 11 }} />
                      <YAxis tickLine={false} axisLine={false} tick={{ fill: "#72818e", fontSize: 11 }} unit="°" domain={["dataMin - 4", "dataMax + 4"]} />
                      <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e3ebef", boxShadow: "0 8px 30px #0a253314" }} />
                      <Legend iconType="circle" />
                      <Line type="monotone" dataKey="maxt" name="最高溫" stroke="#e56f50" strokeWidth={3} dot={{ r: 3, fill: "#e56f50" }} activeDot={{ r: 5 }} />
                      <Line type="monotone" dataKey="mint" name="最低溫" stroke="#2d86a4" strokeWidth={3} dot={{ r: 3, fill: "#2d86a4" }} activeDot={{ r: 5 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="chart-footnote"><span>每日預報氣溫</span><span>資料來源・ {forecast.datasetId}</span></div>
              </article>

              <article className="panel table-panel">
                <div className="panel-heading">
                  <div><span className="section-kicker">每日明細</span><h2>預報資料表</h2></div>
                  <span className="table-count">{regionRows.length} 天</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead><tr><th>日期</th><th>最低溫</th><th>最高溫</th></tr></thead>
                    <tbody>
                      {regionRows.map((row) => (
                        <tr key={`${row.regionName}-${row.dataDate}`}>
                          <td>{row.dataDate}</td><td><span className="temp-value min-value">{row.mint}°</span></td><td><span className="temp-value max-value">{row.maxt}°</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="table-footer">溫度單位：攝氏度（°C）</div>
              </article>
            </section>

            <section className="panel map-panel">
              <WeatherMap selectedDate={selectedDate} />
            </section>
          </>
        )}

        <ConditionsPanel />

        <footer className="footer">
          <span>臺灣天氣預報 <i /> 開放資料應用</span>
          <span>資料來源：中央氣象署・ {forecast?.datasetId ?? "—"}</span>
          <span className="profile-note">製作者：Ian.Li｜男｜中興大學 資訊工程學系｜學號 5115056026｜w115056026@mail.nchu.edu.tw</span>
        </footer>
      </main>
    </div>
  );
}

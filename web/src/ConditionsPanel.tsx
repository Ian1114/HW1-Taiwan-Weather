import { useEffect, useMemo, useState } from "react";
import { fetchTownData } from "./api";
import RefreshButton from "./RefreshButton";
import EmtAssessment from "./EmtAssessment";

type Kind = "rain" | "typhoon" | "wind" | "air" | "marine" | "emt";
type Row = Record<string, string | number | null>;
interface Conditions { kind: Kind; title: string; source: string; county: string; datasetId: string; status: string; note: string; fetchedAt: string | null; rows: Row[] }
const tabs: { kind: Kind; title: string; subtitle: string; icon: string }[] = [
  {kind:"rain",title:"即時降雨量",subtitle:"最新測站累積雨量",icon:"☂"},
  {kind:"typhoon",title:"颱風資訊",subtitle:"警報與有效時段",icon:"◎"},
  {kind:"wind",title:"風向與風速",subtitle:"最新地面觀測",icon:"➶"},
  {kind:"air",title:"空氣品質",subtitle:"空氣品質指標與懸浮微粒",icon:"◌"},
  {kind:"marine",title:"漁業氣象",subtitle:"海面風浪預報",icon:"≈"},
  {kind:"emt",title:"EMT 緊急救護與防救災應變評估",subtitle:"警報、雨量、風速與空氣品質",icon:"✚"},
];
const columns: Record<Kind, [string,string][]> = {
  rain: [["station","測站"],["town","鄉鎮市區"],["rain10m","近十分鐘（毫米）"],["rain1h","近一小時（毫米）"],["rain24h","近二十四小時（毫米）"],["observedAt","觀測時間"],["freshness","時效"]],
  wind: [["station","測站"],["town","鄉鎮市區"],["direction","風向"],["degrees","方位角（度）"],["speed","風速（公尺／秒）"],["observedAt","觀測時間"],["freshness","時效"]],
  air: [["station","測站"],["aqi","空氣品質指標"],["quality","品質等級"],["pm25","細懸浮微粒（微克／立方公尺）"],["pm10","懸浮微粒（微克／立方公尺）"],["observedAt","發布時間"]],
  marine: [["sea","海域"],["start","預報起始"],["end","預報結束"],["weather","天氣"],["direction","風向"],["wind","風級"],["wave","浪高"],["seaState","浪況"],["issuedAt","發布時間"]],
  typhoon: [],
  emt: [],
};
const timeKeys = new Set(["observedAt","start","end","issuedAt","publishedAt","expiresAt"]);
function display(value: string | number | null | undefined, key = ""): string {
  if (value === null || value === undefined || value === "") return "缺測／未提供";
  if (timeKeys.has(key)) {
    const raw = String(value).replace(/\//g, "-");
    // The environmental API publishes local Taiwan time without an offset.
    const date = new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(raw) ? raw : raw.replace(" ", "T") + "+08:00");
    if (!Number.isNaN(date.valueOf())) return date.toLocaleString("zh-TW", {timeZone:"Asia/Taipei",hour12:false});
  }
  return String(value);
}

export default function ConditionsPanel() {
  const [kind,setKind] = useState<Kind>("rain");
  const [county,setCounty] = useState("臺中市");
  const [counties,setCounties] = useState<string[]>([]);
  const [sea,setSea] = useState("");
  const [result,setData] = useState<Conditions|null>(null);
  const data = result?.kind === kind && result.county === county ? result : null;
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  const [refresh,setRefresh] = useState(0);
  useEffect(() => {
    if (kind === "emt") return;
    const controller = new AbortController();
    fetchTownData<{counties:string[]}>("/api/counties",controller.signal).then(result=>setCounties(result.counties)).catch(()=>{});
    const interval = window.setInterval(()=>setRefresh(value=>value+1),300000);
    return ()=>{controller.abort();window.clearInterval(interval);};
  },[]);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);setLoading(true);setError("");
    fetchTownData<Conditions>(`/api/conditions?kind=${kind}&county=${encodeURIComponent(county)}`,controller.signal)
      .then(result=>{if(!controller.signal.aborted)setData({...result,kind});})
      .catch(cause=>{if(!controller.signal.aborted)setError(cause instanceof Error?cause.message:"資料載入失敗。");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[kind,county,refresh]);
  const seas = useMemo(()=>[...new Set((data?.rows ?? []).map(row=>String(row.sea ?? "")).filter(Boolean))],[data]);
  const rows = (data?.rows ?? []).filter(row=>kind!=="marine" || !sea || row.sea===sea);
  const sourceUrl = kind==="air" ? "https://data.moenv.gov.tw/dataset/detail/AQX_P_432" : kind==="typhoon" ? "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_WARN.html" : `https://opendata.cwa.gov.tw/dataset/${kind==="marine"?"forecast":"observation"}/${data?.datasetId ?? ""}`;
  return <section className="panel conditions-panel" aria-label="天氣環境與救災資訊">
    <div className="panel-heading"><div><h2>更多天氣與環境資訊</h2></div><span className="region-chip">每五分鐘自動更新</span></div>
    <div className="conditions-tabs" role="group" aria-label="選擇資訊類型">
      {tabs.map(tab=><button key={tab.kind} aria-pressed={kind===tab.kind} className={kind===tab.kind?"condition-tab selected":"condition-tab"} onClick={()=>{setKind(tab.kind);setSea("");}}><span className="condition-icon" aria-hidden="true">{tab.icon}</span><strong>{tab.title}</strong><small>{tab.subtitle}</small></button>)}
    </div>
    {kind === "emt" ? <EmtAssessment county={county} counties={counties} onCountyChange={setCounty} /> : <>
    <div className="condition-toolbar">
      {!["typhoon","marine"].includes(kind) && <label className="control"><span>觀測縣市</span><select value={county} onChange={event=>setCounty(event.target.value)}>{(counties.length?counties:[county]).map(name=><option key={name}>{name}</option>)}</select></label>}
      {kind==="marine" && <label className="control"><span>預報海域</span><select value={sea} onChange={event=>setSea(event.target.value)}><option value="">全部海域</option>{seas.map(name=><option key={name}>{name}</option>)}</select></label>}
      {kind === "typhoon" ? <div className="typhoon-refresh-row"><strong>颱風最新資訊</strong><RefreshButton loading={loading} onClick={()=>setRefresh(value=>value+1)} label="重新取得颱風資訊" /></div> : <>
        <RefreshButton loading={loading} onClick={()=>setRefresh(value=>value+1)} />
        <span className="town-help">觀測與警報顯示最新資料，不隨一週預報日期切換。</span>
      </>}
    </div>
    {loading && <p role="status" className="condition-note">正在取得官方資料…</p>}
    {error && <p role="alert" className="condition-note">{error}</p>}
    {data && <>
      <p className="condition-note" role={data.status==="error"?"alert":"status"}>{data.note}</p>
      {data.status==="unconfigured" && <a className="source-link" href="https://data.moenv.gov.tw/paradigm" target="_blank" rel="noreferrer">前往環境部申請金鑰與查看設定說明 ↗</a>}
      {data.status==="empty" && <p>官方目前未提供此範圍資料，請稍後重試。</p>}
      {kind==="typhoon" ? <div className="typhoon-list">{rows.map((row,index)=><article key={index} className="typhoon-card"><span className={row.state==="有效警報"?"warning-tag":"history-tag"}>{display(row.state)}</span><h3>{display(row.headline)}</h3><p>發布：{display(row.publishedAt,"publishedAt")}<br/>有效至：{display(row.expiresAt,"expiresAt")}</p><details><summary>查看官方警報全文</summary><p className="warning-description">{display(row.description)}</p></details></article>)}</div>
      : rows.length>0 && <div className="conditions-table"><table><thead><tr>{columns[kind].map(([key,label])=><th key={key}>{label}</th>)}</tr></thead><tbody>{rows.map((row,index)=><tr key={index}>{columns[kind].map(([key])=><td key={key}>{display(row[key],key)}</td>)}</tr>)}</tbody></table></div>}
      <div className="conditions-source"><span>{data.source}・{data.datasetId}{data.fetchedAt?`・取得時間：${display(data.fetchedAt,"observedAt")}（臺灣時間）`:""}・伺服器快取最長五分鐘</span><a href={sourceUrl} target="_blank" rel="noreferrer">官方來源 ↗</a></div>
    </>}
    </>}
  </section>;
}

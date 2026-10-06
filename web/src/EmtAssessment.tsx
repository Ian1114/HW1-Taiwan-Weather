import { useEffect, useMemo, useState } from "react";
import { fetchTownData } from "./api";
import RefreshButton from "./RefreshButton";

type Source = "rain" | "wind" | "air" | "typhoon";
type Observation = {
  station?: string | null;
  observedAt?: string | null;
  publishtime?: string | null;
  freshness?: string | null;
  rain1h?: number | null;
  speed?: number | null;
  direction?: string | null;
  aqi?: number | null;
  quality?: string | null;
  headline?: string | null;
  state?: string | null;
};
type SourceData = { status: string; rows: Observation[]; fetchedAt: string | null; datasetId: string; note: string };

const sources: Source[] = ["typhoon", "rain", "wind", "air"];
const sourceLinks: Record<Source, string> = {
  typhoon: "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_WARN.html",
  rain: "https://opendata.cwa.gov.tw/dataset/observation/O-A0002-001",
  wind: "https://opendata.cwa.gov.tw/dataset/observation/O-A0001-001",
  air: "https://data.moenv.gov.tw/dataset/detail/AQX_P_432",
};

function highest(rows: Observation[], key: "rain1h" | "speed" | "aqi"): Observation | undefined {
  return rows.filter(row => typeof row[key] === "number" && Number.isFinite(row[key]))
    .sort((first, second) => (second[key] ?? 0) - (first[key] ?? 0))[0];
}

function timeLabel(value: string | null | undefined): string {
  if (!value) return "時間未提供";
  const normalized = value.replace(/\//g, "-").replace(" ", "T");
  const dated = new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(normalized) ? normalized : `${normalized}+08:00`);
  return Number.isNaN(dated.valueOf()) ? value : dated.toLocaleString("zh-TW", { timeZone: "Asia/Taipei", hour12: false });
}

export default function EmtAssessment({ county, counties, onCountyChange }: {
  county: string;
  counties: string[];
  onCountyChange: (value: string) => void;
}) {
  const [data, setData] = useState<Partial<Record<Source, SourceData>>>({});
  const [failures, setFailures] = useState<Partial<Record<Source, string>>>({});
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setRefresh(value => value + 1), 300000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData({});
    setFailures({});
    Promise.allSettled(sources.map(source => fetchTownData<SourceData>(
      `/api/conditions?kind=${source}&county=${encodeURIComponent(county)}`,
      controller.signal,
    ))).then(results => {
      if (controller.signal.aborted) return;
      const nextData: Partial<Record<Source, SourceData>> = {};
      const nextFailures: Partial<Record<Source, string>> = {};
      results.forEach((result, index) => {
        const source = sources[index];
        if (result.status === "fulfilled") nextData[source] = result.value;
        else nextFailures[source] = result.reason instanceof Error ? result.reason.message : "資料暫時無法取得";
      });
      setData(nextData);
      setFailures(nextFailures);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [county, refresh]);

  const rain = useMemo(() => highest((data.rain?.rows ?? []).filter(row => row.observedAt && row.freshness !== "超過兩小時"), "rain1h"), [data.rain]);
  const wind = useMemo(() => highest((data.wind?.rows ?? []).filter(row => row.observedAt && row.freshness !== "超過兩小時"), "speed"), [data.wind]);
  const air = useMemo(() => highest(data.air?.rows ?? [], "aqi"), [data.air]);
  const activeWarning = data.typhoon?.rows.find(row => row.state === "有效警報");
  const rainReachesHeavyDefinition = rain?.rain1h !== null && rain?.rain1h !== undefined && rain.rain1h >= 40;

  const cards: { source: Source; title: string; value: string; detail: string; observed: string | null | undefined }[] = [
    {
      source: "typhoon", title: "颱風警報",
      value: activeWarning ? "有效警報" : "未列出有效警報",
      detail: activeWarning?.headline ?? "請查看官方警報涵蓋範圍及有效時間。",
      observed: data.typhoon?.fetchedAt,
    },
    {
      source: "rain", title: "近一小時雨量最高測站",
      value: rain ? `${rain.rain1h} 毫米` : "無近期有效觀測",
      detail: rain ? `${rain.station ?? "未標示測站"}${rainReachesHeavyDefinition ? "・達氣象署大雨雨量定義" : ""}` : "測站資料缺少、過期或暫不可用。",
      observed: rain?.observedAt,
    },
    {
      source: "wind", title: "近期最大測站風速",
      value: wind ? `${wind.speed} 公尺／秒` : "無近期有效觀測",
      detail: wind ? `${wind.station ?? "未標示測站"}・${wind.direction ?? "風向未提供"}` : "測站資料缺少、過期或暫不可用。",
      observed: wind?.observedAt,
    },
    {
      source: "air", title: "空氣品質最高測站 AQI",
      value: air ? String(air.aqi) : "無有效資料",
      detail: air ? `${air.station ?? "未標示測站"}・${air.quality ?? "等級未提供"}` : "測站資料缺少或暫不可用。",
      observed: air?.observedAt,
    },
  ];

  return <div className="emt-assessment">
    <div className="condition-toolbar">
      <label className="control"><span>評估縣市</span><select value={county} onChange={event => onCountyChange(event.target.value)}>{(counties.length ? counties : [county]).map(name => <option key={name}>{name}</option>)}</select></label>
      <RefreshButton loading={loading} onClick={() => setRefresh(value => value + 1)} label="重新取得應變評估資料" />
      <span className="town-help">整合最新環境觀測與警報，不隨一週預報日期切換。</span>
    </div>
    {loading && <p className="condition-note" role="status">正在整理官方環境資料…</p>}
    <div className="emt-grid">
      {cards.map(card => {
        const source = data[card.source];
        const unavailable = Boolean(failures[card.source]) || source?.status === "error" || source?.status === "unconfigured" || !source;
        return <article className="emt-card" key={card.source}>
          <span className="emt-card-label">{card.title}</span>
          <strong>{unavailable ? "資料暫不可用" : card.value}</strong>
          <p>{unavailable ? (failures[card.source] ?? source?.note ?? "請稍後重新取得。") : card.detail}</p>
          <small>{unavailable ? "無可用時間" : `觀測／取得：${timeLabel(card.observed ?? source?.fetchedAt)}`}</small>
          <a href={sourceLinks[card.source]} target="_blank" rel="noreferrer">官方資料 ↗</a>
        </article>;
      })}
    </div>
    <div className="emt-guidance">
      <strong>出勤前環境核對</strong>
      <p>{activeWarning ? "資料集列有有效颱風警報，請核對官方警報範圍、路線與現場指揮資訊。" : "請核對官方警報、道路通行與現場指揮資訊。"}</p>
      {rainReachesHeavyDefinition && <p>縣市內有測站近一小時雨量達 40 毫米；這符合氣象署的大雨雨量定義，並不表示本站已確認官方發布大雨特報。請查證現場積淹水及通行狀況。</p>}
      <p>此處呈現縣市測站與最近警報供環境評估；派遣、救護及現場安全仍依單位程序與現場指揮判斷。</p>
      <a href="https://www.cwa.gov.tw/Data/prevent/alert_color.pdf" target="_blank" rel="noreferrer">氣象署雨量分級說明 ↗</a>
    </div>
  </div>;
}

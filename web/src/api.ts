export interface ForecastRow {
  regionName: string;
  dataDate: string;
  mint: number;
  maxt: number;
}

export interface ForecastResponse {
  source: string;
  datasetId: string;
  unit: string;
  fetchedAt: string;
  warnings?: string[];
  rows: ForecastRow[];
}

export interface TownForecast {
  county: string;
  townName: string;
  latitude: number;
  longitude: number;
  dataDate: string;
  mint: number;
  maxt: number;
}

export interface TownResponse {
  county: string;
  datasetId: string;
  fetchedAt: string;
  rows: TownForecast[];
}

export async function fetchTownData<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "鄉鎮預報載入失敗，請稍後重試。");
  return payload as T;
}

export async function fetchForecast(): Promise<ForecastResponse> {
  const response = await fetch("/api/forecast", {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as {
    detail?: string;
  };
  if (!response.ok) {
    throw new Error(payload.detail || "天氣預報載入失敗，請稍後重試。");
  }
  return payload as ForecastResponse;
}

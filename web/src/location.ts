export interface UserLocation { latitude: number; longitude: number; accuracy: number }
export interface Coordinates { latitude: number; longitude: number }
type Provider = Pick<Geolocation, "getCurrentPosition">;

function distanceKm(first: Coordinates, second: Coordinates): number {
  const radians = Math.PI / 180;
  const latitudeGap = (second.latitude - first.latitude) * radians;
  const longitudeGap = (second.longitude - first.longitude) * radians;
  const arc = Math.sin(latitudeGap / 2) ** 2
    + Math.cos(first.latitude * radians) * Math.cos(second.latitude * radians) * Math.sin(longitudeGap / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(arc)));
}

/** Treat a desktop browser's location as an estimate until it matches the selected forecast area. */
export function assessLocation(position: UserLocation, forecastPoints: Coordinates[]): { nearestKm: number; needsReview: boolean } {
  const nearestKm = Math.min(...forecastPoints.map(point => distanceKm(position, point)));
  return { nearestKm, needsReview: position.accuracy > 3000 || nearestKm > 25 };
}

/** Called only by the location button; no automatic permission request. */
export function requestLocation(provider: Provider | undefined = typeof navigator === "undefined" ? undefined : navigator.geolocation): Promise<UserLocation> {
  return new Promise((resolve, reject) => {
    if (!provider) { reject(new Error("此瀏覽器不支援定位，請使用 HTTPS 或本機網址開啟。")); return; }
    provider.getCurrentPosition(position => {
      const { latitude, longitude, accuracy } = position.coords;
      if (![latitude, longitude, accuracy].every(Number.isFinite) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || accuracy < 0) {
        reject(new Error("定位資料無效，請重新定位。")); return;
      }
      resolve({ latitude, longitude, accuracy });
    }, error => {
      const message = error.code === 1 ? "定位權限未獲允許。可在瀏覽器的網站權限設定中允許位置存取後重試。"
        : error.code === 3 ? "定位逾時，請確認裝置定位服務已開啟後再試。"
        : "目前無法取得位置，請確認裝置定位服務已開啟。";
      reject(new Error(message));
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
  });
}

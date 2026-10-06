# Taiwan Weather Forecast

A CWA seven-day regional temperature dashboard built for the HW10 assignment. The Streamlit application is the rubric submission; the companion Vite/React application is deployed on Vercel. Both use the same Python CWA client and parser.

## What it does

- Retrieves CWA Open Data dataset **F-D0047-091** as JSON.
- Aggregates county minimum/maximum forecasts into six regions (see the source correction below).
- Stores the Streamlit forecast in SQLite table `TemperatureForecasts`, keyed uniquely by region and date.
- Displays a region selector, minimum/maximum chart, matching table, refresh status, and date-selectable Taiwan GIS map.
- Provides the same forecast chart, table, and GIS view in the Vercel companion application.

The interface uses Traditional Chinese and the heading `HW1: CWA 天氣預報網站`. The township map supports mouse-wheel zoom, dragging, county selection, and township selection. Points use the actual CWA forecast coordinates. Marker colors use the midpoint of forecast minimum and maximum (not an observed daily mean): blue below 20 °C, green 20–under 25 °C, yellow 25–30 °C, and red above 30 °C.

### 鄉鎮市區地圖

地圖依選定縣市載入 CWA 鄉鎮一週預報（F-D0047-003 至 F-D0047-087，每四號一組），支援全臺 22 縣市、368 個鄉鎮市區。縣市與資料集對應表在 `src/weather_dashboard/towns.py`。最低與最高溫取當日 06:00、18:00 起始預報時段的極值，夜間延續至次日清晨；缺少完整時段時不補造資料。選擇上方日期即可切換地圖日期，點選標記可查看高低溫。資料在伺服器快取最長 10 分鐘；切換縣市時會清除舊標記，載入失敗會提供重新載入按鈕。

API endpoints: `/api/counties` lists supported counties; `/api/towns?county=臺中市` returns the county's township forecasts. Invalid counties return HTTP 400. These routes are also configured for Vercel rewrites. Keys remain server-side.

## Requirements

### 即時觀測、警報與漁業氣象

新增資訊頁籤，支援縣市或海域篩選，透過 `/api/conditions?kind=rain&county=臺中市` 取得資料。`kind` 可使用 `rain`、`wind`、`typhoon`、`air`、`marine`。目前頁籤每五分鐘自動更新，伺服器快取最多五分鐘。頁面同時顯示資料取得時間及實際觀測／發布／預報時段。

| 資訊 | 官方資料集 | 顯示內容 |
| --- | --- | --- |
| 即時降雨 | O-A0002-001 | 測站近十分鐘、一小時、二十四小時累積雨量（毫米） |
| 風向 | O-A0001-001 | 中文風向、方位角、風速（公尺／秒） |
| 颱風警報 | W-C0034-001 | 最新警報全文、發布及到期時間、有效／歷史狀態 |
| 空氣品質 | aqx_p_432 | 指標、品質等級、細懸浮微粒與懸浮微粒濃度 |
| 漁業氣象 | F-A0012-001（檔案 API） | 海域天氣、風向、蒲福風級、浪高與浪況 |

降雨與風向為測站資料，空氣品質為環境部測站資料，均不隨七天預報日期切換。缺測值與負數特殊代碼不當作零；過期或已解除的颱風警報不標成有效警報。颱風警報資料不等於所有海上颱風追蹤。海面預報提供漁業氣象參考，不作出海安全判定。

「EMT 緊急救護與防救災應變評估」頁籤整合所選縣市的降雨、風速、空氣品質測站資料，以及全臺最近颱風警報；顯示各來源的時間與狀態。近一小時測站雨量達 40 毫米時，依氣象署大雨雨量定義提示查證，但不宣稱已發布大雨特報。此頁籤提供出勤前環境資訊，現場處置仍依單位程序與指揮判斷。

環境部金鑰需獨立設定 `MOENV_API_KEY`，與 `CWA_API_KEY` 一樣放在本機 `.env`、Streamlit Secrets 或 Vercel 伺服器環境變數。未設定時只有空氣品質頁籤提示設定需求，不會讓其他資料失效。[環境部 API 說明](https://data.moenv.gov.tw/paradigm)。兩把金鑰均不傳給前端或寫入版本控制。

一般地圖在寬螢幕下為 1142 × 800 像素；全螢幕檢視時地圖為 1300 × 1300 像素。小螢幕採自適應版面，全螢幕模式可在地圖容器內捲動，不讓整頁橫向溢出。可使用滑鼠滾輪、拖曳與放大／縮小控制，按 Esc 關閉全螢幕模式。

資料格式與警報時效的迴歸檢查：`python -m unittest discover -s tests -v`。

### Data source correction (2026-10-04)

Live requests to the assignment's `F-A0010-001` datastore and file API endpoints returned HTTP 404. The current implementation uses `F-D0047-091`, which returned HTTP 200 with the user's key. This is an explicit deviation from the poster's dataset requirement; confirm acceptance with the teacher before submission. Both applications display the actual source and aggregation notice.

Regional values are computed by this application, not official CWA six-region forecasts. North includes 基隆、臺北、新北、桃園、新竹市、新竹縣; central includes 苗栗、臺中、彰化、南投、雲林; south includes 嘉義市、嘉義縣、臺南、高雄、屏東; northeast is 宜蘭; east is 花蓮; southeast is 臺東. Offshore counties are excluded. For each forecast date, take the minimum of county `MinTemperature` and maximum of county `MaxTemperature` across the 06:00 and 18:00 forecast periods. Dates refer to period start dates (the evening period ends the following morning). Require both periods and all mapped counties, and use the first seven complete dates; do not fabricate missing data.

HTTPS uses a request-scoped `truststore` adapter to validate with native system certificates. This resolves the observed Python 3.14 `Missing Subject Key Identifier` certificate failure on Windows while retaining certificate and hostname verification. No `verify=False` or global SSL replacement is used. Streamlit users should refresh from CWA after upgrading to populate SQLite with the corrected source.

### Runtime

- Python 3.11 or later.
- Node.js 18 or later and npm for the Vercel frontend.
- A CWA Open Data API key.

## Local setup

1. Copy `.env.example` to `.env` and replace the placeholder with your CWA key. Never paste the key into source code or commit `.env`.
2. Create and activate a virtual environment, then install the Python package:

   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

3. Start the graded Streamlit app:

   ```powershell
   streamlit run app.py
   ```

4. Select **Refresh from CWA**. The SQLite cache is created at `data/weather.db` and can be rebuilt if removed.

## Vercel app local development

In one terminal, activate the same Python environment and start the API:

```powershell
uvicorn api.index:app --reload --port 8000
```

In another terminal, install JavaScript dependencies and start Vite:

```powershell
npm install
npm run dev -- --host 0.0.0.0
```

Vite proxies `/api` requests to the local Python API. The browser receives forecast data only; it never receives `CWA_API_KEY`.

## Secrets and environment files

- **Local:** `.env` contains `CWA_API_KEY=...`. `.env.example` is a placeholder template.
- **Streamlit Community Cloud:** configure `CWA_API_KEY` in the app's **Secrets** settings. `.streamlit/secrets.toml.example` shows the TOML format; do not commit the real `secrets.toml`.
- **Vercel:** add `CWA_API_KEY` as a server-side project environment variable for Preview and Production as needed. Do not use a `VITE_`-prefixed variable; Vite exposes those values to browser code.
- If an API key was previously pasted into chat or committed, rotate it at CWA and configure only the replacement in a secret store.

## GitHub workflow

Create a public GitHub repository for the course and push this project with source, `README.md`, dependency manifests, and placeholder examples. Before pushing, confirm `.env`, `.streamlit/secrets.toml`, generated `data/*.db`, `node_modules`, and build output are ignored by `.gitignore`. If you use a private repository, grant the deployment provider access.

After the first `npm install`, commit the generated `package-lock.json` so the frontend's transitive dependencies are locked as well as the direct versions pinned in `package.json`.

## Streamlit Community Cloud deployment

1. Push the repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository and select `app.py` as the entrypoint.
3. Add `CWA_API_KEY` under the app's Secrets settings.
4. Deploy, then use **Refresh from CWA** to populate the SQLite cache.

Community Cloud's local generated database is a rebuildable cache, not an archival store. If it is missing after a restart, refresh the CWA data again.

## Vercel deployment

1. Import the GitHub repository as a Vercel project with the repository root as the project root.
2. Keep the configured build command `npm run build` and output directory `web/dist` from `vercel.json`.
3. Add `CWA_API_KEY` and `MOENV_API_KEY` in Vercel Project Settings → Environment Variables for Production (and Preview if needed). Keep both values server-side; do not add a `VITE_` prefix. Deploy again after adding or changing them.
4. Visit the Vercel URL. The frontend calls the same-origin `/api/forecast` Python function.

The Vercel version fetches and normalizes live forecast data for each request. It does not provide durable SQLite history; serverless local files are not treated as persistent storage. Vercel currently lists its Python runtime as Beta; see [Vercel Python Functions](https://vercel.com/docs/functions/runtimes/python) and [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi) for current runtime details.

## Data and map attribution

- Weather data: Central Weather Administration (CWA) Open Data, dataset F-D0047-091; six-region aggregation by this application.
- Basemap: © OpenStreetMap contributors. See [OpenStreetMap copyright](https://www.openstreetmap.org/copyright).
- The six map markers represent forecast regions with approximate coordinates, not official station locations or boundaries.


### 地圖定位與更新按鈕

網頁地圖預設為 1142 × 800 像素，較窄螢幕縮小寬度；可全螢幕檢視。更多天氣與環境資訊置於地圖下方，資料重新取得按鈕統一採回轉箭頭圖示，保留中文提示及無障礙標籤。

點選 Boxicons 定位圖示才呼叫瀏覽器 Geolocation API；回報的精度超過 3 公里，或位置距所選縣市的鄉鎮預報點超過 25 公里時，地圖先不跳轉並提示使用者檢查定位或改用鄉鎮選單。使用者也可明確選擇顯示瀏覽器回報的位置。接受的座標以藍色標記與精度圓圈顯示，網站不將精確座標送至自家 API 或儲存到資料庫。權限詢問由瀏覽器管理，定位需 HTTPS 或 localhost；桌機定位仍取決於瀏覽器、作業系統與裝置來源的精度。

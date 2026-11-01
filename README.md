# 我的投資行事曆

把持股的財報、法說會、股東會、除息日，以及總經（FOMC、CPI、央行）、科技大會、政治、幣圈日程整理在同一個頁面。

| 檔案 | 內容 | 誰維護 |
|---|---|---|
| `data/holdings.json` | 持股清單（代號、名稱、市場、顏色） | 你 |
| `data/events_manual.json` | 人工整理的事件：央行、總經、政治、科技大會、幣圈、推估的財報日等 | 你（或請 Claude 定期重查） |
| `data/events_auto.json` | 程式自動抓的事件 | GitHub Actions，每天台灣時間 07:00、19:00 |
| `scripts/update.py` | 抓取程式 | — |
| `.github/workflows/update.yml` | 排程設定 | — |
| `index.html` | 網頁 | — |

網頁會把兩個事件檔合併；自動抓到的正式日期會蓋掉人工檔裡同一檔、同類型、日期相近的「推估」。

## 自動抓取的來源

| 來源 | 內容 | 涵蓋持股 |
|---|---|---|
| 證交所 OpenAPI 開休市日程 | 台股休市、封關、開紅盤 | — |
| 證交所 OpenAPI 股東會公告 | 股東常會／臨時會日期、停止過戶 | 2330、2886 |
| 證交所 OpenAPI 每日重大訊息 | 法說會、除息、股利、股東會相關公告（每天累積） | 2330、2886 |
| 證交所處置股公告 | 持股被列處置 | 2330、2886 |
| Nasdaq | 下次財報日、除息日 | GOOGL、AAPL、MSFT、NVDA、TSLA、BRK.B、MSTR |

港股（騰訊）、A 股、幣圈、央行與大會沒有穩定的公開資料，留在人工檔。

## 第一次架設

1. 建好 Public repo，把整個資料夾的內容上傳（含隱藏的 `.github` 資料夾）。
2. **Settings → Pages → Build and deployment**：Source 選 **Deploy from a branch**，Branch 選 `main`、`/ (root)`，Save。
3. **Settings → Actions → General → Workflow permissions**：確認是 **Read and write permissions**，Save。
4. **Actions** 頁籤 → 左邊「更新行事曆資料」→ **Run workflow**，手動跑第一次，綠色勾勾代表成功。
5. 網址：`https://你的帳號.github.io/investor-calendar/`

## 日常維護

### 新增或修改人工事件
在 GitHub 打開 `data/events_manual.json`，按鉛筆圖示編輯，存檔後一兩分鐘網頁就更新。欄位：

| 欄位 | 說明 | 範例 |
|---|---|---|
| `d` | 日期（必填） | `"2027-01-14"` |
| `e` | 結束日（多日活動才填） | `"2027-01-16"` 或 `null` |
| `c` | 類別：`tw` `hk` `cn` `us` `crypto` `macro` `tech` `politics` `holiday` | `"us"` |
| `sym` | 持股代號（持股事件才填） | `"NVDA"` 或 `null` |
| `t` | 標題（必填） | `"NVIDIA FY27 Q4 財報"` |
| `k` | 類型：`earnings` `dividend` `agm` `revenue` `holiday` `expiry`（用來和自動資料比對） | `"earnings"` |
| `tm` | 時間備註 | `"盤後（台北隔日 05:30）"` |
| `st` | `"o"` 官方已公告 / `"e"` 推估 | `"e"` |
| `u` | 來源連結 | `"https://..."` |
| `n` | 備註 | `"依往年推估"` |

### 新增或移除持股
編輯 `data/holdings.json`。`market` 填 `tw` 的會自動抓證交所資料，填 `us` 的會自動抓 Nasdaq 資料。

### 看自動更新有沒有成功
Actions 頁籤，紅色叉叉就點進去看訊息。某個來源失敗時，網頁最上方會顯示警告，並沿用上一次的資料，不會變空。來源網站改版時請 Claude 調整 `scripts/update.py`。

## 注意
- 篩選設定只存在你自己的瀏覽器。
- 內容僅供個人行程整理，不構成投資建議。

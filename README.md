# 我的投資行事曆

把自己持股的財報、法說會、股東會、除息日，以及總經（FOMC、CPI、央行）、科技大會、政治日程整理在同一個頁面。

- 持股清單：`data/holdings.json`
- 所有事件：`data/events.json`
- 網頁：`index.html`（純靜態，不需要任何伺服器）

## 第一次架設（全程在 GitHub 網頁上操作）

1. 登入 GitHub → 右上角 **+** → **New repository**，名稱例如 `investor-calendar`，選 **Public**，按 **Create repository**。
2. 在新 repo 頁面按 **uploading an existing file**，把 `index.html`、`README.md` 和整個 `data` 資料夾拖進去，按 **Commit changes**。
3. **Settings → Pages → Build and deployment**：Source 選 **Deploy from a branch**，Branch 選 `main`、資料夾 `/ (root)`，按 **Save**。
4. 等一兩分鐘，網址是 `https://你的帳號.github.io/investor-calendar/`。

## 日常維護

### 新增或修改事件
在 GitHub 上打開 `data/events.json`，按鉛筆圖示編輯，存檔後一兩分鐘網頁就會更新。

每一筆事件的欄位：

| 欄位 | 說明 | 範例 |
|---|---|---|
| `d` | 日期（必填） | `"2027-01-14"` |
| `e` | 結束日（多日活動才填） | `"2027-01-16"` 或 `null` |
| `c` | 類別：`tw` `hk` `cn` `us` `crypto` `macro` `tech` `politics` `holiday` | `"us"` |
| `sym` | 持股代號（持股事件才填，要和 `holdings.json` 一致） | `"NVDA"` 或 `null` |
| `t` | 標題（必填） | `"NVIDIA FY27 Q4 財報"` |
| `tm` | 時間備註 | `"美股盤後（台北隔日 05:20）"` |
| `st` | `"o"` 官方已公告 / `"e"` 推估 | `"e"` |
| `u` | 來源連結 | `"https://..."` |
| `n` | 備註 | `"依往年推估"` |
| `added` | 加入日期（最近 7 天會顯示「新」標籤） | `"2026-11-01"` |

### 新增或移除持股
編輯 `data/holdings.json`，每檔一行：`sym` 代號、`name` 名稱、`market` 市場、`color` 顏色。

### 推估日期轉正式
公司公告正式日期後，把那筆的 `st` 從 `"e"` 改成 `"o"`，日期改對，`added` 改成當天，網頁就會標「新」。

## 注意
- 篩選設定（勾了哪些持股、列表或月曆）只存在你自己的瀏覽器。
- 內容僅供個人行程整理，不構成投資建議。

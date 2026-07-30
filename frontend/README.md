# Emotion Spectrum Frontend

React 19 + TypeScript + Vite 即時介面。

## 開發

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

預設網址為 <http://localhost:5173>，後端需先在
<http://localhost:8000> 啟動。

## 驗證

```powershell
npm run lint
npm run build
```

## 資料規則

- Demo Mode 只輪播視覺狀態，不寫入 Dashboard 歷史。
- Live Mode 必須由使用者同意後才開啟攝影機。
- 影格縮成 JPEG 後透過 WebSocket 傳送，不寫入瀏覽器儲存空間。
- Dashboard 只使用 FastAPI 回傳值，沒有亂數或假資料。
- 工作階段歷史上限 1,200 筆。

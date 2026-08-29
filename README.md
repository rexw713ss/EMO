# Emotion Spectrum Engine

即時表情訊號視覺化系統，包含 TensorFlow／MediaPipe FastAPI 後端，以及
React + TypeScript + Vite 前端。瀏覽器透過 WebSocket 傳送壓縮 JPEG，後端回傳
八類模型信心度、四種視覺狀態、趨勢、人臉框與推論效能。

> 本專案分析的是影像中的可見表情訊號，不等同於人的真實情緒，也不能用於心理、
> 醫療、人格、招募或高風險決策。

## 必要模型檔

啟動後端前，repo 根目錄必須包含：

| 檔案 | 用途 | 版本管理 |
| --- | --- | --- |
| `emotion_model.keras` | 八類 TensorFlow 模型，約 44 MB | Git LFS |
| `class_names.npy` | 模型輸出的固定類別順序 | Git |
| `face_landmarker.task` | MediaPipe 人臉 landmarker | Git |

模型類別順序為：

```text
anger, contempt, disgust, fear, happy, neutral, sad, surprise
```

前端仍維持四種主要情緒，八類模型結果各自映射一次：

| 四種主要情緒 | API key | 八類模型來源 |
| --- | --- | --- |
| 平靜 | `calm` | `neutral` |
| 愉悅 | `pleasant` | `happy` |
| 緊張 | `alert` | `anger`、`fear`、`surprise` |
| 低落 | `low` | `sad`、`contempt`、`disgust` |

情緒球與主要趨勢顯示這四種結果；Dashboard 的八類信心度仍保留原始模型細節。

`*.keras` 已由 `.gitattributes` 設為 Git LFS。首次 clone 後請執行：

```powershell
git lfs install
git lfs pull
```

若團隊不希望使用 Git LFS，可改成 GitHub Release 下載流程，但不可同時把大型模型
直接提交為一般 Git blob。目前專案採 Git LFS。

## 1. 啟動 FastAPI

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```

驗證：

- 健康檢查：<http://127.0.0.1:8000/api/health>
- Swagger 文件：<http://127.0.0.1:8000/docs>
- WebSocket：`ws://127.0.0.1:8000/ws/emotion`

可複製根目錄的 `.env.example` 查看後端環境變數。Uvicorn 不會自動載入該檔；
可由 shell、程序管理器或部署平台設定。

## 2. 啟動 React

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

開啟 <http://127.0.0.1:5173>。前端 `.env` 預設連線：

```dotenv
VITE_API_HTTP_URL=http://localhost:8000
VITE_API_WS_URL=ws://localhost:8000/ws/emotion
```

修改 `.env` 後需重新啟動 Vite。部署於 HTTPS 時，WebSocket URL 也必須使用 `wss://`。

## 前端功能

- Demo Mode：`calm`、`pleasant`、`alert`、`low` 每四秒輪播，不產生 Dashboard 假資料
- Live Mode：經使用者同意後使用 `getUserMedia()`
- 隱藏 Canvas：縮放至最長邊 640 px、JPEG quality 0.72、約 4 FPS
- 背壓：上一張影格尚未回傳時不送下一張
- 自動重連：WebSocket 斷線後以退避時間重試
- 狀態：模型連線中／離線、無人臉、攝影機拒絕、分析暫停
- Live Mode 若持續 12 秒未偵測到人臉，情緒球自動切換成展示模式（輪播四種視覺
  狀態吸引目光），偵測到人臉立即恢復即時資料，不影響攝影機與 WebSocket 連線
- Dashboard 開啟期間由隱藏影格傳送器持續送出攝影機畫面，圖表與狀態即時更新
- 工作階段控制：暫停／繼續、清除、CSV 匯出、停止攝影機
- 安全模式、偏好減少動態支援與全螢幕
- Live Mode：先顯示五秒觀看引導，但持續偵測直到使用者主動停止
- SQLite：停止後經使用者勾選同意，保存代碼化使用者資訊與工作階段摘要

### 情緒球（觀眾端展示）

面向現場觀眾的投影畫面（設計上 1920×1080），刻意不顯示任何數字，只呈現一顆
隨視覺狀態變色、呼吸的球：

- 四種視覺狀態各有獨立的呼吸節奏與振幅（例如 `alert` 淺而快、`low` 淺而慢），
  而非只是調整速度
- 背景漸層、環境粒子光暈與橢圓軌道裝飾依狀態變色，靜態雜訊紋理與暈影增加層次
- 狀態切換時球體背景平滑跨接漸變

### Dashboard（後台監控台，僅供工作人員）

切分成「現況」與「模型評估」兩個分頁：

**現況**

- 主角狀態卡：呼吸小球＋目前狀態秒數／幀數／信心度；Demo Mode 下可點選狀態預覽
- 狀態脈動：主導狀態色帶＋四軌（平靜／愉悅／緊張／低落）獨立趨勢線，可切換
  90 秒／10 分鐘／1 小時範圍
- 八類模型輸出 → 四類展示狀態：分組長條圖，展開顯示各組原始八類分數
- 分佈摘要：今日／本週切換，各狀態次數、平均信心、平均持續時間與最常見轉換
- 門檻警示・狀態轉換：可調整秒數門檻，超過門檻顯示警示；狀態轉換紀錄由前端
  即時資料即時推導（非模型端的八類轉換紀錄）
- 歷史 session：瀏覽已儲存的過往工作階段摘要
- 底部 telemetry 列：推論延遲、伺服器耗時、FPS、已收影格、裝置、TTA 狀態

**模型評估**

- 固定測試集準確度／+TTA 準確度／樣本數／信賴區間
- 8×8 混淆矩陣、各類 P/R/F1、依側臉角度／背光／遮擋分組的表現
- 候選資料集比較（現場自採／AffectNet／RAF-DB／FER-2013）與下一步建議
- 資料來源為 `data/model_eval.json`；目前為工程測試估計值，`benchmark.py`
  之後可覆寫為正式基準測試結果

新增後端端點：`GET /api/analytics/distribution?range=today|week`、
`GET /api/model-eval`，欄位說明見 [API 文件](docs/API.md)。

### 推論效能

- 模型以 inference-only 模式載入，不還原訓練 optimizer。
- 固定 `tf.function` 動態 batch signature，避免一般模式與 TTA 重複 tracing。
- Accuracy Mode 將原圖與水平翻轉圖組成 batch，一次前向傳播後平均。
- CPU threads 可用 `EMOTION_TF_INTRA_OP_THREADS` 與
  `EMOTION_TF_INTER_OP_THREADS` 調整；目前預設值為本機實測的 `4 / 1`。
- XLA 在目前 Windows CPU 實測較慢，因此沒有啟用。

本機 CPU 基準（40 次暖機後推論）中，一般模式約 21 ms；Accuracy Mode 從原本
兩次呼叫約 41.38 ms，降至單一 batch 約 28.73 ms，改善約 30.6%。實際延遲仍會受
CPU、同時執行程式與臉部偵測時間影響。

前端記憶體中的歷史上限為 1,200 筆，避免長時間執行無限制增長。

## 資料與隱私

- 正式 React／FastAPI 路徑不會呼叫 `cv2.imwrite()`，也不建立人臉資料集。
- WebSocket 影格只存在瀏覽器、網路傳輸與後端程序記憶體中。
- 使用者主動儲存的工作階段只保存使用者編號、選填名稱／備註、時間、樣本數、
  四類主狀態與八類平均分數，且需使用者勾選同意。
- 另有 `visual_state_events` 資料表，會在**任何** Live Mode 連線中，於每次四類
  視覺狀態切換時自動記錄該區間的狀態、起訖時間與平均信心度（不含使用者編號、
  不含影像），供 Dashboard 的「分佈摘要」（今日／本週）查詢彙總，不需另外的
  使用者同意流程。詳見 [隱私文件](docs/PRIVACY.md)。
- Dashboard「清除紀錄」只清除目前瀏覽器工作階段與 WebSocket EMA／趨勢狀態；
  已保存資料需在儲存完成畫面按「刪除此筆」或呼叫資料庫刪除 API。
- `.env`、token、金鑰、使用者照片、錄影、匯出檔與虛擬環境均由 `.gitignore` 排除。
- 若曾經把 ngrok token 分享或提交，必須在 ngrok 控制台撤銷；repo 內無法替隊友確認
  外部帳號是否已完成撤銷。

完整說明見 [隱私文件](docs/PRIVACY.md)。

## 舊工具

`module1_camera.py` 已標示為 **LEGACY / OFFLINE**，只供本機 OpenCV 攝影機與人臉框
診斷，不屬於正式資料流、不儲存影格，也不宣稱個人化校正。介面用語已改為
「開始偵測」。

`legacy/第一版使用者介面.jsx` 保留 Module III 的初版畫面作為設計參考；正式前端
只使用 `frontend/` 內的 React + TypeScript 元件。

`demo.py`、`main.py`、`benchmark.py` 與 `train_optimized.py` 為模型展示、評估與訓練
工具。正式網頁不使用 Gradio、Streamlit、ngrok 或隨機假資料。

## 專案結構

```text
.
├── api_server.py
├── emotion_system.py
├── emotion_model.keras
├── class_names.npy
├── face_landmarker.task
├── data/
│   └── model_eval.json      # 模型評估頁資料來源，Git 追蹤（其餘 data/ 內容排除）
├── frontend/
│   └── src/
│       ├── components/
│       │   └── dashboard/   # Dashboard 專用元件（狀態卡、分佈摘要、session 切換…）
│       ├── hooks/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── LiveDisplay.tsx
│       │   └── ModelEvaluation.tsx
│       ├── services/
│       ├── types/
│       ├── App.tsx
│       └── main.tsx
├── docs/
│   ├── API.md
│   └── PRIVACY.md
└── legacy/
    └── 第一版使用者介面.jsx
```

API 欄位與 WebSocket 訊息見 [API 文件](docs/API.md)。

## 已驗證命令

```powershell
.\.venv\Scripts\python.exe -m py_compile api_server.py emotion_system.py module1_camera.py
cd frontend
npm run lint
npm run build
```

攝影機權限、真實人臉偵測和長時間記憶體測試需要在目標瀏覽器與實際硬體上完成。

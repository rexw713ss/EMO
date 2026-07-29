# Emotion Spectrum Engine

以 TensorFlow、FER 與 MediaPipe 建立的即時人臉情緒辨識系統。專案包含四階段桌面展示、FastAPI/WebSocket 後端、React 串接範例，以及 GPU 訓練與評估工具。

## 系統輸出

模型辨識八種情緒：

`anger`、`contempt`、`disgust`、`fear`、`happy`、`neutral`、`sad`、`surprise`

前端另將八類整理成四種視覺狀態：

| 視覺狀態 | 對應模型類別 |
| --- | --- |
| `calm` | `neutral` |
| `pleasant` | `happy` |
| `alert` | `anger`、`fear`、`surprise` |
| `low` | `sad`、`contempt`、`disgust` |

API 仍會回傳完整八類機率，前端可自行調整四種狀態的映射。

## 快速開始

需求：Python 3.11、攝影機；GPU 模式另需 Docker Desktop、NVIDIA GPU 與 NVIDIA Container Toolkit。

### Windows CPU

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt
```

啟動桌面展示：

```powershell
.\.venv\Scripts\python.exe main.py
```

啟動 React 可連接的 API：

```powershell
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Docker GPU

```powershell
$env:EMOTION_API_PORT="8001"
docker compose -f compose.gpu.yaml up --build -d
```

服務啟動後可使用：

- 健康檢查：`http://localhost:8001/api/health`
- API 文件：`http://localhost:8001/docs`
- WebSocket：`ws://localhost:8001/ws/emotion`

停止服務：

```powershell
docker compose -f compose.gpu.yaml down
```

更完整的 API 格式與 React 串接方式請見 [docs/API.md](docs/API.md)。

## React 串接

`frontend-example/` 提供可複製到 React/Vite 專案的 Hook 與相機元件：

- `useEmotionStream.ts`：擷取影像、限制傳送頻率、處理 WebSocket 結果
- `EmotionCamera.tsx`：相機畫面與情緒結果範例
- `.env.example`：WebSocket 網址設定

此目錄是整合範例，不是獨立 React 專案。將兩個 TypeScript 檔案複製到既有前端後，依 `.env.example` 設定網址即可。

## 模型與評估

目前正式展示使用 `emotion_model.keras`（EfficientNetV2B0 微調模型），最終系統再加入 EMA 滑動平均與情緒趨勢分析。EMA 改善連續影像穩定度，不會改變單張影像模型本身的 Accuracy。

相同抽樣測試集的快速評估結果：

| 模型 | Accuracy | Macro F1 | 用途 |
| --- | ---: | ---: | --- |
| 現有 FER 模型 | 34.38% | 詳見報告 | Baseline |
| 自訓模型 | 38.75% | 詳見報告 | 改良模型 |
| 自訓模型 + TTA | 40.00% | 39.65% | Accuracy Mode |
| 最終系統 | 38.75% | 詳見報告 | 實際展示與穩定化 |

這是 160 張平衡抽樣影像的工程快速測試，不應視為完整資料集的最終研究結論。歷史完整測試報告中的自訓模型 Accuracy 為 52.11%、Macro F1 為 49.93%，但早期訓練流程曾將 Test 當作驗證資料，因此本專案不以該數字宣稱相對提升。後續比較應以完全獨立且相同的測試集重跑所有模型。

評估產物位於 `reports/`。重跑快速評估需先自行準備資料集：

```text
archive (3)/
└─ archive (3)/
   ├─ Train/
   ├─ Test/
   └─ labels.csv
```

```powershell
.\.venv\Scripts\python.exe benchmark.py
.\.venv\Scripts\python.exe benchmark.py --tta
```

## 重新訓練

資料集與使用者照片不納入 Git，請依上方結構放置 FER 資料；自建照片可放在：

```text
custom_dataset/
├─ anger/
├─ contempt/
├─ disgust/
├─ fear/
├─ happy/
├─ neutral/
├─ sad/
└─ surprise/
```

GPU 訓練：

```powershell
docker compose -f compose.train.gpu.yaml build
docker compose -f compose.train.gpu.yaml run --rm emotion-train
```

訓練會輸出 `emotion_model_candidate.keras`，不會直接覆蓋正式模型。

## 專案結構

```text
.
├─ api_server.py              # FastAPI 與 WebSocket 後端
├─ emotion_system.py          # 四階段辨識引擎
├─ demo.py / main.py          # 桌面攝影機展示
├─ benchmark.py               # 同測試集模型評估
├─ train_optimized.py         # 改良模型訓練
├─ emotion_model.keras        # 正式情緒模型
├─ class_names.npy            # 八類標籤
├─ face_landmarker.task       # MediaPipe 人臉關鍵點模型
├─ frontend-example/          # React 串接範例
├─ docs/                      # API 與企劃文件
└─ reports/                   # 評估結果與圖表
```

## 隱私

API 預設只在記憶體中處理影像，不儲存使用者原始畫面。正式部署時仍應使用 HTTPS/WSS、限制允許的前端來源，並取得使用者同意。

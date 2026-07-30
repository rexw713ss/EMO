# Emotion Spectrum API

預設位址為 `http://localhost:8000`，WebSocket 位址為
`ws://localhost:8000/ws/emotion`。

## HTTP

### `GET /api/health`

模型載入完成後回傳：

```json
{
  "status": "ok",
  "model_ready": true,
  "device": "CPU",
  "tensorflow_version": "2.21.0",
  "warmup_ms": 1801.6,
  "uptime_seconds": 2.8,
  "accuracy_mode_default": false,
  "tf_intra_op_threads": 4,
  "tf_inter_op_threads": 1,
  "tta_batching": true
}
```

### `GET /api/config`

回傳八類模型名稱、視覺狀態映射、影格限制與 WebSocket path。

四類視覺狀態由八類模型聚合：

- `calm`（平靜）：`neutral`
- `pleasant`（愉悅）：`happy`
- `alert`（緊張）：`anger`、`fear`、`surprise`
- `low`（低落）：`sad`、`contempt`、`disgust`

### `POST /api/predict`

使用 multipart form-data 的 `file` 欄位上傳單張 JPEG／PNG。
`accuracy_mode=true` 可啟用 TTA；每次 HTTP 呼叫使用獨立 session，不保留跨影格趨勢。
即時串流請使用 WebSocket。

### `POST /api/sessions`

保存由使用者主動停止的工作階段。資料包含：

- `participant_code`：必填的代碼化使用者編號
- `display_name`、`note`：選填文字
- `started_at_ms`、`ended_at_ms`
- `sample_count`、`face_detected_samples`
- `dominant_visual_state`：四類主狀態或 `unknown`
- `average_scores`：八類模型的平均信心度

此 API 不接受也不保存影像。成功時回傳 201 與資料庫 record ID。

### `GET /api/sessions?limit=20`

列出最近保存的工作階段，`limit` 範圍為 1–100。

### `DELETE /api/sessions/{session_id}`

刪除指定資料庫紀錄。成功時回傳：

```json
{"deleted": true}
```

## WebSocket

連線成功後，伺服器先傳：

```json
{
  "type": "ready",
  "schema_version": "1.0",
  "device": "CPU",
  "accuracy_mode": false
}
```

Client 直接傳送 JPEG／PNG binary frame。Server 對每張已處理影格回傳：

```json
{
  "type": "emotion",
  "schema_version": "1.0",
  "timestamp_ms": 1785341180000,
  "face_detected": true,
  "emotion": {
    "label": "neutral",
    "confidence": 0.73,
    "raw_label": "neutral",
    "raw_confidence": 0.78,
    "scores": {},
    "smoothed_scores": {}
  },
  "visual_state": {
    "key": "calm",
    "label": "平靜",
    "confidence": 0.73,
    "scores": {}
  },
  "trend": {
    "dominant_emotion": "neutral",
    "duration_frames": 12,
    "stability": 0.83,
    "distribution": {},
    "recent_transitions": []
  },
  "bbox": {
    "x": 100,
    "y": 60,
    "width": 220,
    "height": 220
  },
  "frame": {
    "width": 640,
    "height": 480
  },
  "performance": {
    "inference_ms": 95.2,
    "server_ms": 100.8,
    "device": "CPU",
    "accuracy_mode": false
  }
}
```

`scores` 和 `smoothed_scores` 實際回應會包含八個模型類別。若未偵測到人臉：

- `face_detected` 為 `false`
- `emotion.label` 為 `unknown`
- `visual_state.key` 為 `unknown`
- `bbox` 為 `null`

### Client control messages

重設目前連線的 EMA、趨勢與轉換紀錄：

```json
{"type": "reset"}
```

切換 TTA accuracy mode：

```json
{"type": "config", "accuracy_mode": true}
```

Keep-alive：

```json
{"type": "ping"}
```

Server 可能回傳 `ready`、`emotion`、`error`、`reset`、`config` 或 `pong`。

## 背壓與限制

前端只會保留一張 in-flight frame。Server 回傳 `emotion` 或 `error` 後才會送下一張，
避免 WebSocket queue 隨時間累積。單張預設上限為 2.5 MB，最大邊會縮至 1,280 px。

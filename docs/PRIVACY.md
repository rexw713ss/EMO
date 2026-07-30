# 隱私、安全與使用限制

## 影像處理

正式網頁資料流如下：

```text
攝影機 → 瀏覽器 Video → 記憶體 Canvas JPEG → WebSocket
       → FastAPI 記憶體解碼 → MediaPipe / TensorFlow → JSON 結果
```

React 與 FastAPI 的正式路徑均未寫入原始影格。停止攝影機會停止所有
`MediaStreamTrack`；清除紀錄會移除瀏覽器工作階段資料，並重設該 WebSocket
session 的 EMA、趨勢與轉換紀錄。

CSV 只包含時間、類別、信心度和效能，不包含影像。CSV 由使用者主動點擊後在瀏覽器
產生並下載。

前五秒是觀看引導，偵測會持續進行，直到使用者主動按下「完成並停止偵測」。停止後
介面才會要求輸入代碼化編號；只有在使用者勾選同意並送出後，SQLite 才會保存：

- 使用者編號、選填顯示名稱與備註
- 工作階段起訖時間與樣本數
- 四類主要狀態與八類平均信心度

資料庫預設位於 `data/emotion_sessions.db`，由 `.gitignore` 排除。它是持久資料，
不會被 Dashboard 的「清除紀錄」刪除；使用者可在儲存完成畫面刪除該筆，或呼叫
`DELETE /api/sessions/{session_id}`。任何影像或臉部特徵點都不會寫入 SQLite。

## 攝影機同意

Live Mode 不會自動要求攝影機權限。使用者閱讀提示並點擊「同意並開啟攝影機」後，
程式才呼叫 `getUserMedia()`。拒絕權限時介面會顯示錯誤且不會啟動串流。

除了 localhost，瀏覽器通常要求 HTTPS 才允許攝影機。HTTPS 頁面也必須使用 WSS
連線後端。

## 模型限制

模型輸出是可見表情模式的統計預測，可能受到光線、遮擋、角度、攝影機品質、
膚色、年齡、文化差異和訓練資料偏差影響。它不能可靠推論：

- 一個人的內在感受、意圖、誠實程度或人格
- 心理健康或醫療狀態
- 工作能力、風險、犯罪傾向或其他高影響資格

不得把本系統用於醫療診斷、執法、教育評分、保險、信貸、招募或監控決策。

## Repository 安全

`.gitignore` 排除 `.env`、token、私鑰、虛擬環境、使用者影像、錄影與匯出資料。
提交前仍應執行秘密掃描，因為忽略規則無法撤回已提交的秘密。

若 ngrok token 曾經出現在任何共享檔案、截圖或 Git 歷史中，請由 token 擁有者登入
ngrok 控制台撤銷並建立新 token。僅從工作目錄刪除 token 並不足以讓舊 token 失效。

### 目前稽核結果

本機掃描確認目前工作目錄沒有常見 credential 簽章，但遠端分支
`origin/後端儀表板(module-IV)` 的歷史 commit `c9c1491` 中，舊
`untitled1.py` 曾包含 ngrok credential assignment。稽核未輸出該值，也不能從 Git
判斷 ngrok 控制台是否已撤銷。token 擁有者仍須在控制台確認撤銷；確認後再決定是否
重寫歷史或刪除舊遠端分支。歷史清理不能取代 token 撤銷。

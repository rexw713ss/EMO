# EMO
# 情緒光譜 Module 4
## 一、負責內容
本 branch 是我負責的 **模組四：儀表板與後台管理功能**。
主要功能是把其他模組傳來的情緒分析結果顯示在網頁上，讓使用者可以看到目前情緒、信心度、紀錄與報告。
---
## 二、使用技術

- 前端：React
- 後端：Python FastAPI
- 資料儲存：SQLite
- 報告格式：CSV
---
## 三、主要功能
1. 顯示目前情緒狀態
2. 顯示四種情緒的信心度
3. 記錄每次分析結果
4. 顯示情緒紀錄
5. 暫停或繼續分析
6. 切換展示模式
7. 匯出 CSV 報告
---
## 四、情緒代碼
本系統使用以下情緒代碼，方便和其他模組串接：
```js
CALM: {
  label: '平靜'
}

JOY: {
  label: '愉悅'
}

ANXIOUS: {
  label: '緊張'
}

DEPRESSED: {
  label: '低落'
}
---
backend/
後端程式，負責接收情緒資料、儲存紀錄、匯出報告。

frontend/
前端畫面，負責顯示 Dashboard。

README.md
專案說明文件。

SECURITY.md
安全注意事項。

.gitignore
避免上傳不必要或敏感檔案。

**執行方式
1. 啟動後端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
2. 啟動前端
cd frontend
npm install
npm run dev
3. 開啟網頁
http://127.0.0.1:5173

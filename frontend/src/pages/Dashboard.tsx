import { ConfidenceBars } from '../components/ConfidenceBars'
import { EmotionTrendChart } from '../components/EmotionTrendChart'
import type { EmotionResponse, HistoryPoint } from '../types/emotion'

interface DashboardProps {
  latest: EmotionResponse | null
  history: HistoryPoint[]
  paused: boolean
  sessionActive: boolean
  sessionElapsedSeconds: number
  onTogglePaused: () => void
  onFinishSession: () => void
  onClear: () => void
  onExport: () => void
}

export function Dashboard({
  latest,
  history,
  paused,
  sessionActive,
  sessionElapsedSeconds,
  onTogglePaused,
  onFinishSession,
  onClear,
  onExport,
}: DashboardProps) {
  const transitions = latest?.trend.recent_transitions ?? []
  const confidence = latest?.emotion.confidence ?? 0
  const sessionMinutes = Math.floor(sessionElapsedSeconds / 60)
  const sessionSeconds = String(sessionElapsedSeconds % 60).padStart(2, '0')

  return (
    <main className="dashboard-page">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">LIVE TELEMETRY</div>
          <h1>情緒訊號儀表板</h1>
          <p>所有圖表均來自目前 FastAPI 工作階段，清除或重新整理後不保留。</p>
          {sessionActive && (
            <div className="dashboard-live-status" aria-live="polite">
              <span />
              即時分析中 · {sessionMinutes}:{sessionSeconds} · WebSocket 真實資料
            </div>
          )}
        </div>
        <div className="dashboard-actions">
          {sessionActive ? (
            <button
              className="button secondary"
              type="button"
              onClick={onFinishSession}
            >
              完成並停止偵測
            </button>
          ) : (
            <button className="button secondary" type="button" onClick={onTogglePaused}>
              {paused ? '繼續分析' : '暫停分析'}
            </button>
          )}
          <button className="button ghost" type="button" onClick={onClear}>
            清除紀錄
          </button>
          <button
            className="button primary"
            type="button"
            onClick={onExport}
            disabled={history.length === 0}
          >
            匯出 CSV
          </button>
        </div>
      </div>

      <section className="metric-grid">
        <article className="metric-card primary-metric">
          <span>目前情緒</span>
          <strong>{latest?.face_detected ? latest.visual_state.label : '未知'}</strong>
          <small>
            {latest?.face_detected
              ? `模型類別：${latest.emotion.label}`
              : '等待即時資料'}
          </small>
        </article>
        <article className="metric-card">
          <span>信心度</span>
          <strong>{Math.round(confidence * 100)}%</strong>
          <small>EMA 平滑後結果</small>
        </article>
        <article className="metric-card">
          <span>狀態持續</span>
          <strong>{latest?.trend.duration_frames ?? 0}</strong>
          <small>frames</small>
        </article>
        <article className="metric-card">
          <span>推論延遲</span>
          <strong>{latest ? latest.performance.inference_ms.toFixed(0) : '—'}</strong>
          <small>ms · server {latest ? latest.performance.server_ms.toFixed(0) : '—'} ms</small>
        </article>
        <article className="metric-card">
          <span>推論裝置</span>
          <strong className="device-value">{latest?.performance.device ?? '—'}</strong>
          <small>CPU / GPU 由 FastAPI 回報</small>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel trend-panel">
          <div className="panel-title">
            <div>
              <span>TIME SERIES</span>
              <h2>情緒時間趨勢</h2>
            </div>
            <small>最近 {Math.min(history.length, 100)} 筆</small>
          </div>
          <EmotionTrendChart history={history} />
        </article>

        <article className="panel confidence-panel">
          <div className="panel-title">
            <div>
              <span>MODEL OUTPUT</span>
              <h2>八類信心度</h2>
            </div>
          </div>
          <ConfidenceBars scores={latest?.emotion.smoothed_scores ?? {}} />
        </article>

        <article className="panel transition-panel">
          <div className="panel-title">
            <div>
              <span>RECENT EVENTS</span>
              <h2>最近模型類別轉換</h2>
            </div>
          </div>
          {transitions.length === 0 ? (
            <p className="empty-state">尚無情緒轉換紀錄。</p>
          ) : (
            <ol className="transition-list">
              {[...transitions].reverse().map((transition) => (
                <li key={`${transition.timestamp_ms}-${transition.from}-${transition.to}`}>
                  <span>{new Date(transition.timestamp_ms).toLocaleTimeString()}</span>
                  <strong>
                    {transition.from} → {transition.to}
                  </strong>
                  <small>{transition.duration_frames} frames</small>
                </li>
              ))}
            </ol>
          )}
        </article>
      </section>
    </main>
  )
}

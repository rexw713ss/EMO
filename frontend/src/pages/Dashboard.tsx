import { useState } from 'react'
import { ConfidenceBars } from '../components/ConfidenceBars'
import { EmotionTrendChart } from '../components/EmotionTrendChart'
import { DistributionSummaryCard } from '../components/dashboard/DistributionSummaryCard'
import { HeroStateCard } from '../components/dashboard/HeroStateCard'
import { SessionSwitcher } from '../components/dashboard/SessionSwitcher'
import { TelemetryStrip } from '../components/dashboard/TelemetryStrip'
import { TransitionAlertPanel } from '../components/dashboard/TransitionAlertPanel'
import { ModelEvaluation } from './ModelEvaluation'
import { deriveCurrentStateRun } from '../services/visualStateTimeline'
import type { EmotionResponse, HistoryPoint, VisualStateKey } from '../types/emotion'

const THRESHOLD_STORAGE_KEY = 'emotion-spectrum:threshold-seconds'

interface DashboardProps {
  latest: EmotionResponse | null
  history: HistoryPoint[]
  mode: 'demo' | 'live'
  demoState: VisualStateKey
  liveState: VisualStateKey
  onSelectDemoState: (state: VisualStateKey) => void
  paused: boolean
  sessionActive: boolean
  sessionElapsedSeconds: number
  sessionsVersion: number
  attractMode: boolean
  attractCountdownSeconds: number | null
  onTogglePaused: () => void
  onFinishSession: () => void
  onClear: () => void
  onExport: () => void
}

function loadThreshold(): number {
  const raw = window.localStorage.getItem(THRESHOLD_STORAGE_KEY)
  const parsed = raw ? Number(raw) : NaN
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 30
}

export function Dashboard({
  latest,
  history,
  mode,
  demoState,
  liveState,
  onSelectDemoState,
  paused,
  sessionActive,
  sessionElapsedSeconds,
  sessionsVersion,
  attractMode,
  attractCountdownSeconds,
  onTogglePaused,
  onFinishSession,
  onClear,
  onExport,
}: DashboardProps) {
  const [tab, setTab] = useState<'current' | 'eval'>('current')
  const [thresholdSeconds, setThresholdSeconds] = useState(loadThreshold)

  const confidence = latest?.emotion.confidence ?? 0
  const sessionMinutes = Math.floor(sessionElapsedSeconds / 60)
  const sessionSeconds = String(sessionElapsedSeconds % 60).padStart(2, '0')

  const heroState = mode === 'demo' ? demoState : liveState
  const currentRun = deriveCurrentStateRun(history)
  const heroSubtitle = latest?.face_detected
    ? `${heroState} · ${latest.emotion.label}`
    : mode === 'demo'
      ? 'Demo Mode'
      : '等待即時資料'

  const changeThreshold = (seconds: number) => {
    setThresholdSeconds(seconds)
    window.localStorage.setItem(THRESHOLD_STORAGE_KEY, String(seconds))
  }

  return (
    <main className="dashboard-page">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">OPERATOR CONSOLE</div>
          <h1>情緒訊號儀表板</h1>
          <p>所有圖表均來自目前 FastAPI 工作階段，清除或重新整理後不保留。</p>
          {sessionActive && (
            <div className="dashboard-live-status" aria-live="polite">
              <span />
              即時分析中 · {sessionMinutes}:{sessionSeconds} · WebSocket 真實資料
            </div>
          )}
          {attractMode && (
            <div className="dashboard-live-status attract-status" aria-live="polite">
              <span />
              閒置中 · 展示模式自動輪播
            </div>
          )}
          {!attractMode && mode === 'live' && attractCountdownSeconds !== null && (
            <div className="idle-countdown">
              未偵測到人臉 · {attractCountdownSeconds}s 後進入展示模式
            </div>
          )}
        </div>
        <div className="dashboard-actions">
          <SessionSwitcher sessionActive={sessionActive} refreshKey={sessionsVersion} />
          {sessionActive ? (
            <button className="button secondary" type="button" onClick={onFinishSession}>
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

      <div className="dashboard-tabs">
        <button
          type="button"
          className={tab === 'current' ? 'active' : ''}
          onClick={() => setTab('current')}
        >
          現況
        </button>
        <button
          type="button"
          className={tab === 'eval' ? 'active' : ''}
          onClick={() => setTab('eval')}
        >
          模型評估
        </button>
      </div>

      {tab === 'eval' ? (
        <ModelEvaluation />
      ) : (
        <>
          <section className="operator-grid">
            <HeroStateCard
              state={heroState}
              subtitle={heroSubtitle}
              confidence={confidence}
              elapsedMs={currentRun?.elapsedMs ?? 0}
              frameCount={currentRun?.frameCount ?? 0}
              mode={mode}
              onSelectState={onSelectDemoState}
            />

            <article className="panel trend-panel">
              <div className="panel-title">
                <div>
                  <span>STATE PULSE</span>
                  <h2>狀態脈動</h2>
                </div>
                <small>最近 {Math.min(history.length, 200)} 筆</small>
              </div>
              <EmotionTrendChart history={history} />
            </article>

            <div className="operator-row-2">
              <article className="panel grouped-confidence-panel">
                <div className="panel-title">
                  <div>
                    <span>MODEL OUTPUT</span>
                    <h2>八類模型輸出 → 四類展示狀態</h2>
                  </div>
                </div>
                <ConfidenceBars scores={latest?.emotion.smoothed_scores ?? {}} />
              </article>

              <DistributionSummaryCard />

              <TransitionAlertPanel
                history={history}
                thresholdSeconds={thresholdSeconds}
                onChangeThreshold={changeThreshold}
              />
            </div>
          </section>

          <TelemetryStrip latest={latest} history={history} />
        </>
      )}
    </main>
  )
}

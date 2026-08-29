import {
  deriveCurrentStateRun,
  deriveVisualStateTransitions,
} from '../../services/visualStateTimeline'
import { VISUAL_STATES } from '../../services/visualStates'
import type { HistoryPoint } from '../../types/emotion'

interface TransitionAlertPanelProps {
  history: HistoryPoint[]
  thresholdSeconds: number
  onChangeThreshold: (seconds: number) => void
}

export function TransitionAlertPanel({
  history,
  thresholdSeconds,
  onChangeThreshold,
}: TransitionAlertPanelProps) {
  const currentRun = deriveCurrentStateRun(history)
  const transitions = deriveVisualStateTransitions(history, 8)
  const elapsedSeconds = currentRun ? Math.floor(currentRun.elapsedMs / 1000) : 0
  const alertActive =
    Boolean(currentRun) &&
    currentRun!.state !== 'unknown' &&
    elapsedSeconds >= thresholdSeconds

  return (
    <article className="panel alert-transition-panel">
      <div className="panel-title">
        <div>
          <span>THRESHOLD ALERT</span>
          <h2>門檻警示・狀態轉換</h2>
        </div>
        <label className="threshold-input">
          門檻
          <input
            type="number"
            min={5}
            max={300}
            value={thresholdSeconds}
            onChange={(event) => {
              const next = Number(event.target.value)
              if (Number.isFinite(next) && next > 0) onChangeThreshold(next)
            }}
          />
          秒
        </label>
      </div>

      {alertActive && currentRun && (
        <div className="threshold-alert-banner" role="alert">
          <strong>「{VISUAL_STATES[currentRun.state].label}」已持續 {elapsedSeconds} 秒</strong>
          <span>超過 {thresholdSeconds} 秒門檻</span>
        </div>
      )}

      {transitions.length === 0 ? (
        <p className="empty-state">尚無狀態轉換紀錄。</p>
      ) : (
        <ol className="transition-list">
          {transitions.map((transition) => (
            <li key={`${transition.startedAt}-${transition.endedAt}`}>
              <span>{new Date(transition.endedAt).toLocaleTimeString()}</span>
              <strong>
                {VISUAL_STATES[transition.from].label} → {VISUAL_STATES[transition.to].label}
              </strong>
              <small>
                {Math.round(transition.durationMs / 1000)}s ·{' '}
                {Math.round(transition.confidenceAtEnd * 100)}%
              </small>
            </li>
          ))}
        </ol>
      )}
    </article>
  )
}

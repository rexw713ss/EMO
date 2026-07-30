import { useEffect, useState, type FormEvent } from 'react'
import { VISUAL_STATES } from '../services/visualStates'
import type {
  SessionFlowPhase,
  StoredEmotionSession,
  UserSessionForm,
} from '../types/emotion'

interface LiveSessionFlowProps {
  phase: SessionFlowPhase
  secondsRemaining: number
  elapsedSeconds: number
  error: string | null
  savedSession: StoredEmotionSession | null
  deleteBusy: boolean
  onSubmit: (form: UserSessionForm) => void
  onFinish: () => void
  onNext: () => void
  onDelete: () => void
  onCancel: () => void
}

export function LiveSessionFlow({
  phase,
  secondsRemaining,
  elapsedSeconds,
  error,
  savedSession,
  deleteBusy,
  onSubmit,
  onFinish,
  onNext,
  onDelete,
  onCancel,
}: LiveSessionFlowProps) {
  const [participantCode, setParticipantCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [note, setNote] = useState('')
  const [consented, setConsented] = useState(false)

  useEffect(() => {
    if (phase !== 'countdown') return
    setParticipantCode('')
    setDisplayName('')
    setNote('')
    setConsented(false)
  }, [phase])

  if (phase === 'idle') return null

  if (phase === 'detecting') {
    const minutes = Math.floor(elapsedSeconds / 60)
    const seconds = String(elapsedSeconds % 60).padStart(2, '0')
    return (
      <aside className="continuous-detection-panel" aria-live="polite">
        <div className="continuous-status">
          <span className="recording-dot" />
          <div>
            <strong>持續偵測中</strong>
            <small>
              已偵測 {minutes}:{seconds} · 直到你按下完成才會停止
            </small>
          </div>
        </div>
        <button className="button primary" type="button" onClick={onFinish}>
          完成並停止偵測
        </button>
      </aside>
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!participantCode.trim() || !consented || phase === 'saving') return
    onSubmit({ participantCode, displayName, note })
  }

  return (
    <div className="session-flow-overlay" role="dialog" aria-modal="true">
      {phase === 'countdown' && (
        <section className="session-flow-card countdown-card">
          <div className="eyebrow">LIVE SESSION · DETECTING NOW</div>
          <div className="countdown-number" aria-live="polite">
            {secondsRemaining}
          </div>
          <h2>請看前方螢幕 5 秒鐘</h2>
          <p>
            系統已開始即時偵測。五秒引導結束後仍會持續，直到你主動按下停止。
          </p>
          <div className="detecting-pill">
            <span />
            偵測與八類信心度統計進行中
          </div>
          <button className="text-button" type="button" onClick={onCancel}>
            取消並停止攝影機
          </button>
        </section>
      )}

      {(phase === 'form' || phase === 'saving') && (
        <form className="session-flow-card user-form-card" onSubmit={submit}>
          <div className="eyebrow">DETECTION STOPPED</div>
          <h2>輸入使用者資訊</h2>
          <p>
            偵測已依你的操作停止。資料庫只保存以下資訊與本次摘要，不包含照片或影格。
          </p>

          <div className="user-form-grid">
            <label>
              <span>使用者編號 *</span>
              <input
                value={participantCode}
                onChange={(event) => setParticipantCode(event.target.value)}
                maxLength={64}
                autoComplete="off"
                placeholder="例如 P-001"
                required
              />
              <small>建議使用代碼，不要填身分證字號。</small>
            </label>
            <label>
              <span>顯示名稱（選填）</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                maxLength={100}
                autoComplete="off"
                placeholder="暱稱或識別名稱"
              />
            </label>
            <label className="full-field">
              <span>備註（選填）</span>
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                maxLength={500}
                rows={3}
                placeholder="本次測試備註"
              />
            </label>
          </div>

          <label className="database-consent">
            <input
              type="checkbox"
              checked={consented}
              onChange={(event) => setConsented(event.target.checked)}
            />
            <span>
              我同意將上述資訊與本次偵測摘要保存至本機資料庫；資料不包含人臉影像。
            </span>
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <div className="form-actions">
            <button className="button danger" type="button" onClick={onCancel}>
              取消
            </button>
            <button
              className="button primary"
              type="submit"
              disabled={!participantCode.trim() || !consented || phase === 'saving'}
            >
              {phase === 'saving' ? '儲存中…' : '同意並儲存摘要'}
            </button>
          </div>
        </form>
      )}

      {phase === 'saved' && savedSession && (
        <section className="session-flow-card saved-card">
          <div className="saved-check" aria-hidden="true">
            ✓
          </div>
          <div className="eyebrow">SESSION SAVED</div>
          <h2>已儲存至本機資料庫</h2>
          <dl className="saved-summary">
            <div>
              <dt>使用者編號</dt>
              <dd>{savedSession.participant_code}</dd>
            </div>
            <div>
              <dt>主要情緒</dt>
              <dd>{VISUAL_STATES[savedSession.dominant_visual_state].label}</dd>
            </div>
            <div>
              <dt>有效人臉樣本</dt>
              <dd>
                {savedSession.face_detected_samples} / {savedSession.sample_count}
              </dd>
            </div>
          </dl>
          <small className="record-id">Record · {savedSession.id}</small>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="form-actions">
            <button
              className="button danger"
              type="button"
              onClick={onDelete}
              disabled={deleteBusy}
            >
              {deleteBusy ? '刪除中…' : '刪除此筆'}
            </button>
            <button className="button primary" type="button" onClick={onNext}>
              開始下一筆
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

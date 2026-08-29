import { useEffect, useState } from 'react'
import { listEmotionSessions } from '../../services/sessionApi'
import { VISUAL_STATES } from '../../services/visualStates'
import type { StoredEmotionSession } from '../../types/emotion'

interface SessionSwitcherProps {
  sessionActive: boolean
  refreshKey: number
}

const POLL_MS = 10_000

export function SessionSwitcher({ sessionActive, refreshKey }: SessionSwitcherProps) {
  const [sessions, setSessions] = useState<StoredEmotionSession[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      listEmotionSessions(20)
        .then((result) => {
          if (!cancelled) setSessions(result.items)
        })
        .catch(() => {
          // Session history is a convenience panel; a failed poll just keeps stale data.
        })
    }
    load()
    const timer = window.setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [refreshKey])

  const selected = sessions.find((session) => session.id === selectedId) ?? null

  return (
    <div className="session-switcher">
      <button
        type="button"
        className={`session-switcher-toggle ${sessionActive ? 'live' : ''}`}
        onClick={() => setOpen((value) => !value)}
      >
        {sessionActive && <span className="session-live-dot" />}
        歷史 session ({sessions.length})
      </button>

      {open && (
        <div className="session-switcher-panel glass-panel">
          {sessions.length === 0 ? (
            <p className="empty-state">尚無已儲存的工作階段。</p>
          ) : (
            <ul className="session-switcher-list">
              {sessions.map((session) => (
                <li key={session.id}>
                  <button
                    type="button"
                    className={selectedId === session.id ? 'active' : ''}
                    onClick={() =>
                      setSelectedId((current) => (current === session.id ? null : session.id))
                    }
                  >
                    <span>{session.participant_code}</span>
                    <small>{new Date(session.created_at_ms).toLocaleString()}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {selected && (
            <div className="session-detail">
              <div className="panel-title">
                <div>
                  <span>SESSION DETAIL</span>
                  <h2>{selected.display_name || selected.participant_code}</h2>
                </div>
              </div>
              <p>
                主導狀態：
                <strong className={`state-text-${selected.dominant_visual_state}`}>
                  {VISUAL_STATES[selected.dominant_visual_state].label}
                </strong>
              </p>
              <p>
                樣本數：{selected.sample_count}（偵測到人臉 {selected.face_detected_samples}）
              </p>
              <p>
                時長：
                {Math.round((selected.ended_at_ms - selected.started_at_ms) / 1000)} 秒
              </p>
              {selected.note && <p>備註：{selected.note}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

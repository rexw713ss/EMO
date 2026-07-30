import type { CSSProperties } from 'react'
import { VISUAL_STATES } from '../services/visualStates'
import type { ConnectionStatus, VisualStateKey } from '../types/emotion'

interface EmotionOrbProps {
  state: VisualStateKey
  confidence?: number
  safeMode: boolean
  connectionStatus?: ConnectionStatus
  statusText?: string
}

export function EmotionOrb({
  state,
  confidence = 0,
  safeMode,
  connectionStatus,
  statusText,
}: EmotionOrbProps) {
  const config = VISUAL_STATES[state]
  const orbStyle = {
    '--orb-color': config.color,
    '--orb-glow': config.glow,
    '--pulse-duration': `${safeMode ? 6 : config.pulseSeconds}s`,
    '--orb-opacity': safeMode ? 0.62 : Math.max(0.72, confidence),
  } as CSSProperties

  return (
    <section
      className={`emotion-stage state-${state} ${safeMode ? 'safe-mode' : ''}`}
      style={{ background: config.background }}
      aria-live="polite"
    >
      <div className="orb-field" aria-hidden="true">
        <span className="orbit orbit-one" />
        <span className="orbit orbit-two" />
        <div className="emotion-orb" style={orbStyle}>
          <span className="orb-core" />
        </div>
      </div>

      <div className="emotion-caption">
        <div className="eyebrow">VISUAL STATE · {state}</div>
        <h1>{config.label}</h1>
        <p>{config.description}</p>
        <div className="caption-meta">
          <span>{statusText ?? '等待資料'}</span>
          {state !== 'unknown' && (
            <span>狀態信心度 {Math.round(confidence * 100)}%</span>
          )}
          {connectionStatus && (
            <span className={`connection-dot status-${connectionStatus}`}>
              {connectionStatus === 'connected' ? '模型已連線' : '模型未就緒'}
            </span>
          )}
        </div>
      </div>
    </section>
  )
}

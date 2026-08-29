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

const MOTE_COUNT = 8

export function EmotionOrb({
  state,
  confidence = 0,
  safeMode,
  connectionStatus,
  statusText,
}: EmotionOrbProps) {
  const config = VISUAL_STATES[state]
  const stageStyle = {
    background: config.background,
    '--orb-color': config.color,
    '--orb-glow': config.glow,
    '--pulse-duration': `${safeMode ? 6 : config.pulseSeconds}s`,
    '--orb-opacity': safeMode ? 0.62 : Math.max(0.72, confidence),
    '--breathe-min': safeMode ? 0.97 : config.breatheMin,
    '--breathe-max': safeMode ? 1.03 : config.breatheMax,
  } as CSSProperties

  return (
    <section
      className={`emotion-stage state-${state} ${safeMode ? 'safe-mode' : ''}`}
      style={stageStyle}
      aria-live="polite"
    >
      <div className="particle-field" aria-hidden="true">
        {Array.from({ length: MOTE_COUNT }).map((_, index) => (
          <span className="mote" key={index} />
        ))}
      </div>

      <div className="orb-field" aria-hidden="true">
        <span className="orbit orbit-one" />
        <span className="orbit orbit-two" />
        <div className="emotion-orb">
          <span className="orb-core" />
        </div>
      </div>

      <div className="emotion-caption">
        <div className="eyebrow">
          <span className="state-dot" aria-hidden="true" />
          VISUAL STATE · {state}
        </div>
        <h1>{config.label}</h1>
        <p>{config.description}</p>
        <div className="caption-meta">
          <span>{statusText ?? '等待資料'}</span>
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

import type { CSSProperties } from 'react'
import { VISUAL_STATES } from '../../services/visualStates'
import { VISUAL_STATE_ORDER } from '../../services/visualStateGroups'
import type { VisualStateKey } from '../../types/emotion'

interface HeroStateCardProps {
  state: VisualStateKey
  subtitle: string
  confidence: number
  elapsedMs: number
  frameCount: number
  mode: 'demo' | 'live'
  onSelectState?: (state: VisualStateKey) => void
}

export function HeroStateCard({
  state,
  subtitle,
  confidence,
  elapsedMs,
  frameCount,
  mode,
  onSelectState,
}: HeroStateCardProps) {
  const config = VISUAL_STATES[state]
  const orbStyle = {
    '--orb-color': config.color,
    '--orb-glow': config.glow,
    '--pulse-duration': `${config.pulseSeconds}s`,
  } as CSSProperties
  const elapsedSeconds = Math.max(0, Math.round(elapsedMs / 1000))

  return (
    <article className="panel hero-state-card">
      <div className="panel-title">
        <div>
          <span>OPERATOR VIEW</span>
          <h2>觀眾看見・儀表在看</h2>
        </div>
      </div>

      <div className="hero-state-body">
        <div className="mini-orb-wrap">
          <div className="mini-orb" style={orbStyle} />
        </div>
        <div className="hero-state-copy">
          <strong className={`hero-state-name state-text-${state}`}>{config.label}</strong>
          <small>{subtitle}</small>
        </div>
      </div>

      <div className="hero-state-stats">
        <div>
          <strong>{elapsedSeconds}</strong>
          <span>秒</span>
        </div>
        <div>
          <strong>{frameCount}</strong>
          <span>幀</span>
        </div>
        <div>
          <strong>{confidence.toFixed(2)}</strong>
          <span>信心</span>
        </div>
      </div>

      <div className="state-buttons hero-state-buttons">
        {VISUAL_STATE_ORDER.map((key) => (
          <button
            type="button"
            key={key}
            className={state === key ? 'active' : ''}
            disabled={mode !== 'demo'}
            onClick={() => onSelectState?.(key)}
          >
            {VISUAL_STATES[key].label}
          </button>
        ))}
      </div>
    </article>
  )
}

import { EMOTION_LABELS } from '../types/emotion'

interface ConfidenceBarsProps {
  scores: Record<string, number>
}
export function ConfidenceBars({ scores }: ConfidenceBarsProps) {
  return (
    <div className="confidence-list">
      {EMOTION_LABELS.map((label) => {
        const value = scores[label] ?? 0
        return (
          <div className="confidence-row" key={label}>
            <span>{label}</span>
            <div className="confidence-track">
              <div
                className="confidence-fill"
                style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
              />
            </div>
            <strong>{Math.round(value * 100)}%</strong>
          </div>
        )
      })}
    </div>
  )
}

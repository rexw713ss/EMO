import type { HistoryPoint, VisualStateKey, VisualStateTransition } from '../types/emotion'

export interface CurrentStateRun {
  state: VisualStateKey
  startedAt: number
  elapsedMs: number
  confidence: number
  frameCount: number
}

/**
 * Derives visual-state-level timeline info from the raw per-frame history
 * buffer. The backend's `trend.recent_transitions` tracks the underlying
 * 8-class model label, not the 4-state visual grouping shown in the
 * dashboard, so the transition log and "current state duration" the
 * redesign needs are computed here instead of from the server payload.
 */
export function deriveCurrentStateRun(history: HistoryPoint[]): CurrentStateRun | null {
  if (history.length === 0) return null
  const latest = history[history.length - 1]
  let startIndex = history.length - 1
  while (
    startIndex > 0 &&
    history[startIndex - 1].visualState === latest.visualState
  ) {
    startIndex -= 1
  }
  const runPoints = history.slice(startIndex)
  return {
    state: latest.visualState,
    startedAt: runPoints[0].timestamp,
    elapsedMs: latest.timestamp - runPoints[0].timestamp,
    confidence: latest.confidence,
    frameCount: runPoints.length,
  }
}

export function deriveVisualStateTransitions(
  history: HistoryPoint[],
  limit = 20,
): VisualStateTransition[] {
  if (history.length < 2) return []
  const transitions: VisualStateTransition[] = []
  let runStart = history[0]
  let previous = history[0]

  for (let i = 1; i < history.length; i += 1) {
    const point = history[i]
    if (point.visualState !== previous.visualState) {
      transitions.push({
        from: runStart.visualState,
        to: point.visualState,
        startedAt: runStart.timestamp,
        endedAt: point.timestamp,
        durationMs: previous.timestamp - runStart.timestamp,
        confidenceAtEnd: previous.confidence,
      })
      runStart = point
    }
    previous = point
  }

  return transitions.slice(-limit).reverse()
}

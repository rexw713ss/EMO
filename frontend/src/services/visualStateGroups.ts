import type { EmotionLabel, VisualStateKey } from '../types/emotion'

/**
 * Mirrors VISUAL_STATE_GROUPS in api_server.py. Kept in sync manually — the
 * backend enforces at startup that every one of the 8 model classes maps to
 * exactly one of these 4 groups, so this mapping is stable.
 */
export const VISUAL_STATE_GROUPS: Record<Exclude<VisualStateKey, 'unknown'>, EmotionLabel[]> = {
  calm: ['neutral'],
  pleasant: ['happy'],
  alert: ['anger', 'fear', 'surprise'],
  low: ['sad', 'contempt', 'disgust'],
}

export const VISUAL_STATE_ORDER: Exclude<VisualStateKey, 'unknown'>[] = [
  'calm',
  'pleasant',
  'alert',
  'low',
]

export interface GroupedConfidence {
  key: Exclude<VisualStateKey, 'unknown'>
  total: number
  members: { label: EmotionLabel; value: number }[]
}

export function groupConfidenceScores(
  scores: Record<string, number>,
): GroupedConfidence[] {
  return VISUAL_STATE_ORDER.map((key) => {
    const members = VISUAL_STATE_GROUPS[key].map((label) => ({
      label,
      value: scores[label] ?? 0,
    }))
    const total = members.reduce((sum, member) => sum + member.value, 0)
    return { key, total, members }
  })
}

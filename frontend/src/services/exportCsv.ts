import { EMOTION_LABELS, type HistoryPoint } from '../types/emotion'

const csvCell = (value: string | number | boolean) =>
  `"${String(value).replaceAll('"', '""')}"`

export function exportHistoryCsv(history: HistoryPoint[]) {
  if (history.length === 0) return

  const header = [
    'timestamp',
    'face_detected',
    'emotion',
    'visual_state',
    'confidence',
    'inference_ms',
    'server_ms',
    ...EMOTION_LABELS,
  ]
  const rows = history.map((point) => [
    new Date(point.timestamp).toISOString(),
    point.faceDetected,
    point.emotion,
    point.visualState,
    point.confidence,
    point.inferenceMs,
    point.serverMs,
    ...EMOTION_LABELS.map((label) => point.scores[label] ?? 0),
  ])
  const csv = [header, ...rows]
    .map((row) => row.map(csvCell).join(','))
    .join('\r\n')

  const blob = new Blob([`\uFEFF${csv}`], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  const stamp = new Date().toISOString().replaceAll(':', '-').replace(/\.\d{3}Z$/, 'Z')
  anchor.href = url
  anchor.download = `emotion-session-${stamp}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

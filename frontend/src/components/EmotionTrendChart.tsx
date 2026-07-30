import type { HistoryPoint, VisualStateKey } from '../types/emotion'

const COLORS: Record<string, string> = {
  calm: '#70d6e8',
  pleasant: '#ffe073',
  alert: '#ff7d6e',
  low: '#aa91ff',
  unknown: '#7e8996',
}

const VISUAL_STATE_LABELS: Record<VisualStateKey, string> = {
  calm: '平靜',
  pleasant: '愉悅',
  alert: '緊張',
  low: '低落',
  unknown: '未知',
}

interface EmotionTrendChartProps {
  history: HistoryPoint[]
}

export function EmotionTrendChart({ history }: EmotionTrendChartProps) {
  const points = history.slice(-100)
  const chartWidth = 720
  const chartHeight = 240
  const left = 76
  const right = 16
  const top = 16
  const bottom = 24
  const plotWidth = chartWidth - left - right
  const plotHeight = chartHeight - top - bottom
  const states: VisualStateKey[] = ['calm', 'pleasant', 'alert', 'low', 'unknown']
  const yFor = (state: VisualStateKey) => {
    const index = states.indexOf(state)
    return top + (Math.max(index, 0) / (states.length - 1)) * plotHeight
  }
  const xFor = (index: number) =>
    left + (points.length <= 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth)

  return (
    <div className="trend-chart-wrap">
      <svg
        className="trend-chart"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        role="img"
        aria-label="最近情緒時間趨勢"
      >
        {states.map((state) => {
          const y = yFor(state)
          return (
            <g key={state}>
              <line x1={left} x2={chartWidth - right} y1={y} y2={y} />
              <text x={left - 10} y={y + 4} textAnchor="end">
                {VISUAL_STATE_LABELS[state]}
              </text>
            </g>
          )
        })}
        {points.length > 1 && (
          <polyline
            className="trend-line"
            points={points
              .map((point, index) => `${xFor(index)},${yFor(point.visualState)}`)
              .join(' ')}
          />
        )}
        {points.map((point, index) => (
          <circle
            key={`${point.timestamp}-${index}`}
            cx={xFor(index)}
            cy={yFor(point.visualState)}
            r="3.5"
            fill={COLORS[point.visualState]}
          >
            <title>
              {new Date(point.timestamp).toLocaleTimeString()} ·{' '}
              {VISUAL_STATE_LABELS[point.visualState]} · 模型 {point.emotion} ·{' '}
              {Math.round(point.confidence * 100)}%
            </title>
          </circle>
        ))}
        {points.length === 0 && (
          <text className="empty-chart-label" x={left + plotWidth / 2} y={chartHeight / 2}>
            尚無即時資料
          </text>
        )}
      </svg>
    </div>
  )
}

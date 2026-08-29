import { useMemo, useState } from 'react'
import { groupConfidenceScores, VISUAL_STATE_ORDER } from '../services/visualStateGroups'
import { VISUAL_STATES } from '../services/visualStates'
import type { HistoryPoint, VisualStateKey } from '../types/emotion'

const COLORS: Record<string, string> = {
  calm: '#70d6e8',
  pleasant: '#ffe073',
  alert: '#ff7d6e',
  low: '#aa91ff',
  unknown: '#7e8996',
}

const RANGE_OPTIONS: { seconds: number; label: string }[] = [
  { seconds: 90, label: '90 秒' },
  { seconds: 600, label: '10 分鐘' },
  { seconds: 3600, label: '1 小時' },
]

const MAX_PLOT_POINTS = 180
const TRACK_HEIGHT = 56
const BAND_HEIGHT = 14
const CHART_WIDTH = 760
const LEFT_GUTTER = 68
const RIGHT_GUTTER = 12
const TOP_PADDING = 6
const TRACK_GAP = 6

interface EmotionTrendChartProps {
  history: HistoryPoint[]
}

export function EmotionTrendChart({ history }: EmotionTrendChartProps) {
  const [rangeSeconds, setRangeSeconds] = useState(90)

  const points = useMemo(() => {
    if (history.length === 0) return []
    const latestTimestamp = history[history.length - 1].timestamp
    const withinRange = history.filter(
      (point) => latestTimestamp - point.timestamp <= rangeSeconds * 1000,
    )
    if (withinRange.length <= MAX_PLOT_POINTS) return withinRange
    const step = Math.ceil(withinRange.length / MAX_PLOT_POINTS)
    return withinRange.filter((_, index) => index % step === 0)
  }, [history, rangeSeconds])

  const plotWidth = CHART_WIDTH - LEFT_GUTTER - RIGHT_GUTTER
  const chartHeight =
    TOP_PADDING + BAND_HEIGHT + TRACK_GAP + VISUAL_STATE_ORDER.length * (TRACK_HEIGHT + TRACK_GAP)

  const xFor = (index: number) =>
    LEFT_GUTTER +
    (points.length <= 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth)

  const trackTop = (trackIndex: number) =>
    TOP_PADDING + BAND_HEIGHT + TRACK_GAP + trackIndex * (TRACK_HEIGHT + TRACK_GAP)

  const groupedByPoint = useMemo(
    () => points.map((point) => groupConfidenceScores(point.scores)),
    [points],
  )

  return (
    <div className="trend-chart-wrap">
      <div className="trend-chart-legend">
        <div className="trend-chart-legend-states">
          {VISUAL_STATE_ORDER.map((key) => (
            <span key={key} className="trend-legend-item">
              <i style={{ background: COLORS[key] }} />
              {VISUAL_STATES[key].label}
            </span>
          ))}
        </div>
        <div className="trend-range-select">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.seconds}
              type="button"
              className={rangeSeconds === option.seconds ? 'active' : ''}
              onClick={() => setRangeSeconds(option.seconds)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {points.length === 0 ? (
        <p className="empty-state">尚無即時資料</p>
      ) : (
        <svg
          className="trend-chart"
          viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`}
          role="img"
          aria-label="狀態脈動：主導狀態色帶與四軌趨勢"
        >
          {/* dominant-state color band */}
          {points.map((point, index) => {
            const segmentWidth = plotWidth / Math.max(1, points.length - 1 || 1)
            return (
              <rect
                key={`band-${point.timestamp}-${index}`}
                x={xFor(index) - segmentWidth / 2}
                y={TOP_PADDING}
                width={segmentWidth + 1}
                height={BAND_HEIGHT}
                fill={COLORS[point.visualState]}
                opacity={0.85}
              />
            )
          })}

          {VISUAL_STATE_ORDER.map((state, trackIndex) => {
            const top = trackTop(trackIndex)
            const baseline = top + TRACK_HEIGHT
            const yFor = (value: number) => baseline - Math.min(1, Math.max(0, value)) * TRACK_HEIGHT

            const linePoints = groupedByPoint
              .map((grouped, index) => {
                const entry = grouped.find((item) => item.key === state)
                return `${xFor(index)},${yFor(entry?.total ?? 0)}`
              })
              .join(' ')

            return (
              <g key={state}>
                <line x1={LEFT_GUTTER} x2={CHART_WIDTH - RIGHT_GUTTER} y1={baseline} y2={baseline} />
                <text x={LEFT_GUTTER - 10} y={top + TRACK_HEIGHT / 2 + 4} textAnchor="end">
                  {VISUAL_STATES[state].label}
                </text>
                {points.length > 1 && (
                  <polyline
                    className="trend-line"
                    style={{ stroke: COLORS[state] }}
                    points={linePoints}
                  />
                )}
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}

export function stateColor(key: VisualStateKey): string {
  return COLORS[key]
}

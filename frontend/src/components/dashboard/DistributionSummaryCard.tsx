import { useEffect, useState } from 'react'
import { fetchDistributionSummary } from '../../services/distributionApi'
import { VISUAL_STATE_ORDER } from '../../services/visualStateGroups'
import { VISUAL_STATES } from '../../services/visualStates'
import type { DistributionRange, DistributionSummary } from '../../types/emotion'

export function DistributionSummaryCard() {
  const [range, setRange] = useState<DistributionRange>('today')
  const [summary, setSummary] = useState<DistributionSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchDistributionSummary(range)
      .then((result) => {
        if (!cancelled) {
          setSummary(result)
          setError(null)
        }
      })
      .catch((cause) => {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : '無法載入分佈摘要')
        }
      })
    return () => {
      cancelled = true
    }
  }, [range])

  const totalCount = summary?.states.reduce((sum, item) => sum + item.count, 0) ?? 0

  return (
    <article className="panel distribution-panel">
      <div className="panel-title">
        <div>
          <span>DISTRIBUTION</span>
          <h2>分佈摘要</h2>
        </div>
        <div className="range-toggle">
          <button
            type="button"
            className={range === 'today' ? 'active' : ''}
            onClick={() => setRange('today')}
          >
            今日
          </button>
          <button
            type="button"
            className={range === 'week' ? 'active' : ''}
            onClick={() => setRange('week')}
          >
            本週
          </button>
        </div>
      </div>

      {error && <p className="inline-error">{error}</p>}

      {!error && totalCount > 0 && (
        <div className="distribution-bar">
          {VISUAL_STATE_ORDER.map((key) => {
            const item = summary?.states.find((state) => state.key === key)
            const pct = item ? (item.count / totalCount) * 100 : 0
            return (
              <span
                key={key}
                style={{ width: `${pct}%`, background: VISUAL_STATES[key].color }}
              />
            )
          })}
        </div>
      )}

      {!error && (!summary || totalCount === 0) && (
        <p className="empty-state">目前尚無{range === 'today' ? '今日' : '本週'}資料。</p>
      )}

      {!error && summary && totalCount > 0 && (
        <>
          <table className="distribution-table">
            <thead>
              <tr>
                <th>狀態</th>
                <th>次數</th>
                <th>平均信心</th>
                <th>平均持續</th>
              </tr>
            </thead>
            <tbody>
              {VISUAL_STATE_ORDER.map((key) => {
                const item = summary.states.find((state) => state.key === key)
                if (!item) return null
                return (
                  <tr key={key}>
                    <td>
                      <span
                        className="grouped-confidence-dot"
                        style={{ background: VISUAL_STATES[key].color }}
                      />
                      {VISUAL_STATES[key].label}
                    </td>
                    <td>{item.count}</td>
                    <td>{Math.round(item.avg_confidence * 100)}%</td>
                    <td>{Math.round(item.avg_duration_ms / 1000)}s</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {summary.top_transition && (
            <p className="distribution-footnote">
              最常見轉換：{VISUAL_STATES[summary.top_transition.from].label} →{' '}
              {VISUAL_STATES[summary.top_transition.to].label} ·{' '}
              {summary.top_transition.count} 次
            </p>
          )}
        </>
      )}
    </article>
  )
}

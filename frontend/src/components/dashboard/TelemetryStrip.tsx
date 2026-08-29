import { useMemo } from 'react'
import type { EmotionResponse, HistoryPoint } from '../../types/emotion'

interface TelemetryStripProps {
  latest: EmotionResponse | null
  history: HistoryPoint[]
}

function estimateFps(history: HistoryPoint[]): number | null {
  const recent = history.slice(-10)
  if (recent.length < 2) return null
  const spanMs = recent[recent.length - 1].timestamp - recent[0].timestamp
  if (spanMs <= 0) return null
  return ((recent.length - 1) * 1000) / spanMs
}

export function TelemetryStrip({ latest, history }: TelemetryStripProps) {
  const fps = useMemo(() => estimateFps(history), [history])
  const lastUpdated = latest ? new Date(latest.timestamp_ms).toLocaleTimeString() : '—'

  return (
    <div className="telemetry-strip">
      <div className="telemetry-items">
        <span>
          延遲 <strong>{latest ? `${latest.performance.inference_ms.toFixed(0)}ms` : '—'}</strong>
        </span>
        <span>
          伺服器 <strong>{latest ? `${latest.performance.server_ms.toFixed(0)}ms` : '—'}</strong>
        </span>
        <span>
          FPS <strong>{fps ? fps.toFixed(1) : '—'}</strong>
        </span>
        <span>
          已收影格 <strong>{history.length}</strong>
        </span>
        <span>
          裝置 <strong>{latest?.performance.device ?? '—'}</strong>
        </span>
        <span>
          TTA <strong>{latest?.performance.accuracy_mode ? '開啟' : '關閉'}</strong>
        </span>
      </div>
      <div className="telemetry-updated">更新 {lastUpdated}</div>
    </div>
  )
}

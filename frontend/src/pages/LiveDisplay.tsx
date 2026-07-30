import { CameraFeed } from '../components/CameraFeed'
import { EmotionOrb } from '../components/EmotionOrb'
import type { CameraStatus } from '../hooks/useCamera'
import { VISUAL_STATES } from '../services/visualStates'
import type {
  ConnectionStatus,
  EmotionResponse,
  VisualStateKey,
} from '../types/emotion'

interface LiveDisplayProps {
  mode: 'demo' | 'live'
  demoState: VisualStateKey
  liveState: VisualStateKey
  result: EmotionResponse | null
  safeMode: boolean
  paused: boolean
  stream: MediaStream | null
  cameraStatus: CameraStatus
  cameraError: string | null
  connectionStatus: ConnectionStatus
  connectionError: string | null
  onSelectDemoState: (state: VisualStateKey) => void
  onStartCamera: () => void
  onStopCamera: () => void
  onFrame: (frame: Blob) => boolean
}

const DEMO_STATES: VisualStateKey[] = ['calm', 'pleasant', 'alert', 'low']

export function LiveDisplay({
  mode,
  demoState,
  liveState,
  result,
  safeMode,
  paused,
  stream,
  cameraStatus,
  cameraError,
  connectionStatus,
  connectionError,
  onSelectDemoState,
  onStartCamera,
  onStopCamera,
  onFrame,
}: LiveDisplayProps) {
  const isLive = mode === 'live'
  const state = isLive ? liveState : demoState
  const statusText = !isLive
    ? 'Demo Mode · 每四秒輪播'
    : paused
      ? '分析已暫停'
      : !stream
        ? '等待攝影機同意'
        : connectionStatus !== 'connected'
          ? '模型連線中'
          : result?.face_detected
            ? `模型結果 · ${result.emotion.label}`
            : '未偵測到人臉'

  return (
    <main className="display-page">
      <EmotionOrb
        state={state}
        confidence={isLive ? result?.visual_state.confidence : 0.86}
        safeMode={safeMode}
        connectionStatus={isLive ? connectionStatus : undefined}
        statusText={statusText}
      />

      {!isLive ? (
        <div className="demo-controls glass-panel">
          <div>
            <span className="eyebrow">DEMO MODE</span>
            <strong>視覺狀態預覽</strong>
          </div>
          <div className="state-buttons">
            {DEMO_STATES.map((key) => (
              <button
                type="button"
                key={key}
                className={demoState === key ? 'active' : ''}
                onClick={() => onSelectDemoState(key)}
              >
                {VISUAL_STATES[key].label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <aside className="live-side-panel">
          {stream ? (
            <>
              <CameraFeed
                stream={stream}
                status={cameraStatus}
                result={result}
                captureEnabled={!paused && connectionStatus === 'connected'}
                onFrame={onFrame}
              />
              <div className="camera-actions">
                <button className="button danger" type="button" onClick={onStopCamera}>
                  停止攝影機
                </button>
                <span>JPEG · 640 px · 約 4 FPS</span>
              </div>
              {connectionError && (
                <p className="inline-error" role="alert">
                  {connectionError}
                </p>
              )}
            </>
          ) : (
            <div className="consent-card glass-panel">
              <span className="consent-icon" aria-hidden="true">
                ◉
              </span>
              <div className="eyebrow">CAMERA CONSENT</div>
              <h2>開始偵測</h2>
              <p>
                啟動後，瀏覽器會要求攝影機權限。影格只送往你設定的 FastAPI，
                僅在記憶體中處理，不會由本介面保存。
              </p>
              {cameraError && (
                <p className="inline-error" role="alert">
                  {cameraError}
                </p>
              )}
              <button
                className="button primary wide"
                type="button"
                onClick={onStartCamera}
                disabled={cameraStatus === 'requesting'}
              >
                {cameraStatus === 'requesting' ? '等待攝影機權限…' : '同意並開啟攝影機'}
              </button>
            </div>
          )}
        </aside>
      )}
    </main>
  )
}

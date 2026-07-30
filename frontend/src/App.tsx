import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { FrameSender } from './components/FrameSender'
import { LiveSessionFlow } from './components/LiveSessionFlow'
import { useCamera } from './hooks/useCamera'
import { useEmotionSocket } from './hooks/useEmotionSocket'
import { Dashboard } from './pages/Dashboard'
import { LiveDisplay } from './pages/LiveDisplay'
import { API_HTTP_URL, API_WS_URL } from './services/config'
import { exportHistoryCsv } from './services/exportCsv'
import {
  deleteEmotionSession,
  saveEmotionSession,
} from './services/sessionApi'
import {
  EMOTION_LABELS,
  type EmotionSessionPayload,
  type HistoryPoint,
  type SessionFlowPhase,
  type StoredEmotionSession,
  type UserSessionForm,
  type VisualStateKey,
} from './types/emotion'

type AppMode = 'demo' | 'live'
type AppPage = 'display' | 'dashboard'

const DEMO_STATES: VisualStateKey[] = ['calm', 'pleasant', 'alert', 'low']
const MAX_HISTORY_POINTS = 1200
const LIVE_SESSION_DURATION_MS = 5000

interface SessionCaptureBuffer {
  active: boolean
  startedAt: number
  endedAt: number | null
  sampleCount: number
  faceDetectedSamples: number
  scoreSums: Record<string, number>
  visualStateCounts: Record<VisualStateKey, number>
}

const emptyScoreSums = () =>
  Object.fromEntries(EMOTION_LABELS.map((emotion) => [emotion, 0]))

const emptyVisualStateCounts = (): Record<VisualStateKey, number> => ({
  calm: 0,
  pleasant: 0,
  alert: 0,
  low: 0,
  unknown: 0,
})

function App() {
  const [mode, setMode] = useState<AppMode>('demo')
  const [page, setPage] = useState<AppPage>('display')
  const [safeMode, setSafeMode] = useState(false)
  const [paused, setPaused] = useState(false)
  const [demoState, setDemoState] = useState<VisualStateKey>('calm')
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [sessionPhase, setSessionPhase] = useState<SessionFlowPhase>('idle')
  const [countdownSeconds, setCountdownSeconds] = useState(5)
  const [detectionElapsedSeconds, setDetectionElapsedSeconds] = useState(0)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [savedSession, setSavedSession] = useState<StoredEmotionSession | null>(
    null,
  )
  const [deleteBusy, setDeleteBusy] = useState(false)
  const lastTimestampRef = useRef(0)
  const sessionCaptureRef = useRef<SessionCaptureBuffer | null>(null)
  const camera = useCamera()
  const socket = useEmotionSocket({
    enabled: mode === 'live' && Boolean(camera.stream),
    url: API_WS_URL,
  })

  useEffect(() => {
    if (mode !== 'demo') return
    const timer = window.setInterval(() => {
      setDemoState((current) => {
        const index = DEMO_STATES.indexOf(current)
        return DEMO_STATES[(index + 1) % DEMO_STATES.length]
      })
    }, 4000)
    return () => window.clearInterval(timer)
  }, [mode])

  useEffect(() => {
    const result = socket.latest
    if (!result || result.timestamp_ms === lastTimestampRef.current) return
    lastTimestampRef.current = result.timestamp_ms
    const point: HistoryPoint = {
      timestamp: result.timestamp_ms,
      emotion: result.face_detected ? result.emotion.label : 'unknown',
      visualState: result.visual_state.key,
      confidence: result.emotion.confidence,
      scores: result.emotion.smoothed_scores,
      faceDetected: result.face_detected,
      inferenceMs: result.performance.inference_ms,
      serverMs: result.performance.server_ms,
    }
    const capture = sessionCaptureRef.current
    if (capture?.active) {
      capture.sampleCount += 1
      if (point.faceDetected) {
        capture.faceDetectedSamples += 1
        for (const emotion of EMOTION_LABELS) {
          capture.scoreSums[emotion] += point.scores[emotion] ?? 0
        }
        capture.visualStateCounts[point.visualState] += 1
      }
    }
    setHistory((current) => [...current.slice(-(MAX_HISTORY_POINTS - 1)), point])
  }, [socket.latest])

  useEffect(() => {
    if (
      mode !== 'live' ||
      !camera.stream ||
      socket.status !== 'connected' ||
      paused ||
      sessionPhase !== 'idle'
    ) {
      return
    }

    sessionCaptureRef.current = {
      active: true,
      startedAt: Date.now(),
      endedAt: null,
      sampleCount: 0,
      faceDetectedSamples: 0,
      scoreSums: emptyScoreSums(),
      visualStateCounts: emptyVisualStateCounts(),
    }
    setCountdownSeconds(5)
    setDetectionElapsedSeconds(0)
    setSessionError(null)
    setSavedSession(null)
    setSessionPhase('countdown')
  }, [camera.stream, mode, paused, sessionPhase, socket.status])

  useEffect(() => {
    if (sessionPhase !== 'countdown' || !sessionCaptureRef.current) return

    const updateCountdown = () => {
      const capture = sessionCaptureRef.current
      if (!capture?.active) return
      const remaining = Math.max(
        0,
        Math.ceil(
          (capture.startedAt + LIVE_SESSION_DURATION_MS - Date.now()) / 1000,
        ),
      )
      setCountdownSeconds(remaining)
      if (remaining === 0) {
        setSessionPhase('detecting')
      }
    }

    updateCountdown()
    const timer = window.setInterval(updateCountdown, 100)
    return () => window.clearInterval(timer)
  }, [sessionPhase])

  useEffect(() => {
    if (sessionPhase !== 'detecting' || !sessionCaptureRef.current) return
    const updateElapsed = () => {
      const capture = sessionCaptureRef.current
      if (!capture?.active) return
      setDetectionElapsedSeconds(
        Math.max(0, Math.floor((Date.now() - capture.startedAt) / 1000)),
      )
    }
    updateElapsed()
    const timer = window.setInterval(updateElapsed, 1000)
    return () => window.clearInterval(timer)
  }, [sessionPhase])

  const liveState = useMemo<VisualStateKey>(() => {
    if (
      !camera.stream ||
      socket.status !== 'connected' ||
      !socket.latest?.face_detected
    ) {
      return 'unknown'
    }
    return socket.latest.visual_state.key
  }, [camera.stream, socket.latest, socket.status])

  const changeMode = (nextMode: AppMode) => {
    if (nextMode === mode) return
    if (nextMode === 'demo') {
      camera.stop()
      socket.clearLatest()
      setPaused(false)
      resetSessionFlow()
    }
    setMode(nextMode)
  }

  const clearHistory = () => {
    setHistory([])
    lastTimestampRef.current = 0
    socket.reset()
  }

  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
      } else {
        await document.documentElement.requestFullscreen()
      }
    } catch {
      // Browsers can reject full-screen requests based on local policy.
    }
  }

  const stopCamera = () => {
    resetSessionFlow()
    camera.stop()
    socket.clearLatest()
    setPaused(false)
  }

  function resetSessionFlow() {
    if (sessionCaptureRef.current) {
      sessionCaptureRef.current.active = false
    }
    sessionCaptureRef.current = null
    setSessionPhase('idle')
    setCountdownSeconds(5)
    setDetectionElapsedSeconds(0)
    setSessionError(null)
    setSavedSession(null)
    setDeleteBusy(false)
  }

  const buildSessionPayload = (
    form: UserSessionForm,
  ): EmotionSessionPayload | null => {
    const capture = sessionCaptureRef.current
    if (!capture) return null
    const averageScores = Object.fromEntries(
      EMOTION_LABELS.map((emotion) => [
        emotion,
        capture.faceDetectedSamples > 0
          ? capture.scoreSums[emotion] / capture.faceDetectedSamples
          : 0,
      ]),
    )
    const dominantVisualState =
      (
        Object.entries(capture.visualStateCounts) as [
          VisualStateKey,
          number,
        ][]
      )
        .filter(([, count]) => count > 0)
        .sort((left, right) => right[1] - left[1])[0]?.[0] ?? 'unknown'

    return {
      participant_code: form.participantCode.trim(),
      display_name: form.displayName.trim() || null,
      note: form.note.trim() || null,
      started_at_ms: capture.startedAt,
      ended_at_ms: capture.endedAt ?? Date.now(),
      sample_count: capture.sampleCount,
      face_detected_samples: capture.faceDetectedSamples,
      dominant_visual_state: dominantVisualState,
      average_scores: averageScores,
    }
  }

  const submitSession = async (form: UserSessionForm) => {
    const payload = buildSessionPayload(form)
    if (!payload) {
      setSessionError('找不到本次偵測資料，請重新開始。')
      return
    }
    setSessionPhase('saving')
    setSessionError(null)
    try {
      const stored = await saveEmotionSession(payload)
      setSavedSession(stored)
      setSessionPhase('saved')
    } catch (cause) {
      setSessionError(cause instanceof Error ? cause.message : '資料庫儲存失敗')
      setSessionPhase('form')
    }
  }

  const finishSessionDetection = () => {
    const capture = sessionCaptureRef.current
    if (!capture?.active) {
      setSessionError('目前沒有進行中的偵測。')
      return
    }
    capture.active = false
    capture.endedAt = Date.now()
    setPaused(true)
    setSessionPhase('form')
  }

  const startNextSession = () => {
    socket.reset()
    sessionCaptureRef.current = null
    setSavedSession(null)
    setSessionError(null)
    setPaused(false)
    setSessionPhase('idle')
  }

  const deleteSavedSession = async () => {
    if (!savedSession) return
    setDeleteBusy(true)
    setSessionError(null)
    try {
      await deleteEmotionSession(savedSession.id)
      startNextSession()
    } catch (cause) {
      setSessionError(cause instanceof Error ? cause.message : '刪除資料失敗')
    } finally {
      setDeleteBusy(false)
    }
  }

  const sessionActive =
    sessionPhase === 'countdown' || sessionPhase === 'detecting'

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setPage('display')}>
          <span className="brand-mark" aria-hidden="true" />
          <span>
            <strong>Emotion Spectrum</strong>
            <small>REAL-TIME SIGNAL INTERFACE</small>
          </span>
        </button>

        <nav className="primary-nav" aria-label="主要頁面">
          <button
            type="button"
            className={page === 'display' ? 'active' : ''}
            onClick={() => setPage('display')}
          >
            情緒球
          </button>
          <button
            type="button"
            className={page === 'dashboard' ? 'active' : ''}
            onClick={() => setPage('dashboard')}
          >
            Dashboard
          </button>
        </nav>

        <div className="topbar-actions">
          <div className="mode-switch" aria-label="資料模式">
            <button
              type="button"
              className={mode === 'demo' ? 'active' : ''}
              onClick={() => changeMode('demo')}
            >
              Demo
            </button>
            <button
              type="button"
              className={mode === 'live' ? 'active' : ''}
              onClick={() => changeMode('live')}
            >
              Live
            </button>
          </div>
          <button
            className={`icon-button ${safeMode ? 'active' : ''}`}
            type="button"
            onClick={() => setSafeMode((value) => !value)}
            aria-pressed={safeMode}
            title="安全模式：降低亮度與動態"
          >
            安全
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={toggleFullscreen}
            title="切換全螢幕"
          >
            全螢幕
          </button>
        </div>
      </header>

      {page === 'display' ? (
        <LiveDisplay
          mode={mode}
          demoState={demoState}
          liveState={liveState}
          result={socket.latest}
          safeMode={safeMode}
          paused={paused}
          stream={camera.stream}
          cameraStatus={camera.status}
          cameraError={camera.error}
          connectionStatus={socket.status}
          connectionError={socket.error}
          onSelectDemoState={setDemoState}
          onStartCamera={camera.start}
          onStopCamera={stopCamera}
          onFrame={socket.sendFrame}
        />
      ) : (
        <>
          {mode === 'live' && camera.stream && (
            <FrameSender
              stream={camera.stream}
              enabled={!paused && socket.status === 'connected'}
              onFrame={socket.sendFrame}
            />
          )}
          <Dashboard
            latest={socket.latest}
            history={history}
            paused={paused}
            sessionActive={sessionActive}
            sessionElapsedSeconds={detectionElapsedSeconds}
            onTogglePaused={() => setPaused((value) => !value)}
            onFinishSession={finishSessionDetection}
            onClear={clearHistory}
            onExport={() => exportHistoryCsv(history)}
          />
        </>
      )}

      {mode === 'live' && camera.stream && (
        <LiveSessionFlow
          phase={sessionPhase}
          secondsRemaining={countdownSeconds}
          elapsedSeconds={detectionElapsedSeconds}
          error={sessionError}
          savedSession={savedSession}
          deleteBusy={deleteBusy}
          onSubmit={submitSession}
          onFinish={finishSessionDetection}
          onNext={startNextSession}
          onDelete={deleteSavedSession}
          onCancel={stopCamera}
        />
      )}

      <footer className="privacy-footer">
        <p>
          本工具只分析可見表情訊號，不能判定心理狀態、人格或醫療診斷。影像不落地保存。
        </p>
        <span>
          API <code>{API_HTTP_URL}</code>
        </span>
      </footer>
    </div>
  )
}

export default App

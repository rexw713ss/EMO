import { useEffect, useRef } from 'react'
import type { CameraStatus } from '../hooks/useCamera'
import type { EmotionResponse } from '../types/emotion'

interface CameraFeedProps {
  stream: MediaStream | null
  status: CameraStatus
  result: EmotionResponse | null
  captureEnabled: boolean
  onFrame: (frame: Blob) => boolean
}
export function CameraFeed({
  stream,
  status,
  result,
  captureEnabled,
  onFrame,
}: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const encodingRef = useRef(false)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    video.srcObject = stream
    if (stream) {
      void video.play().catch(() => undefined)
    }
  }, [stream])

  useEffect(() => {
    if (!captureEnabled || !stream) return

    const timer = window.setInterval(() => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (
        !video ||
        !canvas ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        encodingRef.current
      ) {
        return
      }

      const scale = Math.min(1, 640 / video.videoWidth)
      canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
      canvas.height = Math.max(1, Math.round(video.videoHeight * scale))
      const context = canvas.getContext('2d', { alpha: false })
      if (!context) return

      context.drawImage(video, 0, 0, canvas.width, canvas.height)
      encodingRef.current = true
      canvas.toBlob(
        (blob) => {
          if (blob) onFrame(blob)
          encodingRef.current = false
        },
        'image/jpeg',
        0.72,
      )
    }, 250)

    return () => {
      window.clearInterval(timer)
      encodingRef.current = false
    }
  }, [captureEnabled, onFrame, stream])

  const showBox = Boolean(result?.face_detected && result.bbox)

  return (
    <div className="camera-feed">
      <video
        ref={videoRef}
        muted
        playsInline
        className="camera-video"
        aria-label="即時攝影機畫面"
      />
      {showBox && result && (
        <svg
          className="face-overlay"
          viewBox={`0 0 ${result.frame.width} ${result.frame.height}`}
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          <rect
            x={result.bbox!.x}
            y={result.bbox!.y}
            width={result.bbox!.width}
            height={result.bbox!.height}
            rx="12"
          />
        </svg>
      )}
      <canvas ref={canvasRef} hidden aria-hidden="true" />
      <div className="camera-badge">
        <span className={stream ? 'live-indicator' : 'idle-indicator'} />
        {status === 'ready' ? 'Camera on · memory only' : 'Camera off'}
      </div>
      {stream && result && !result.face_detected && (
        <div className="no-face-hint">未偵測到人臉</div>
      )}
    </div>
  )
}

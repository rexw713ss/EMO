import { useEffect, useRef } from 'react'

interface FrameSenderProps {
  stream: MediaStream
  enabled: boolean
  onFrame: (frame: Blob) => boolean
}
/**
 * Keeps live inference running while the visual camera card is not mounted
 * (for example, while the Dashboard page is visible).
 */
export function FrameSender({ stream, enabled, onFrame }: FrameSenderProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const encodingRef = useRef(false)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    video.srcObject = stream
    void video.play().catch(() => undefined)
    return () => {
      video.srcObject = null
    }
  }, [stream])

  useEffect(() => {
    if (!enabled) return
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
  }, [enabled, onFrame])

  return (
    <div className="headless-capture" aria-hidden="true">
      <video ref={videoRef} muted playsInline />
      <canvas ref={canvasRef} />
    </div>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'

export type CameraStatus =
  | 'idle'
  | 'requesting'
  | 'ready'
  | 'denied'
  | 'error'
  | 'stopped'

export function useCamera() {
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [status, setStatus] = useState<CameraStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const stop = useCallback(() => {
    releaseStream()
    setStream(null)
    setStatus('stopped')
    setError(null)
  }, [releaseStream])

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('error')
      setError('此瀏覽器或目前連線環境不支援攝影機存取。請使用 HTTPS 或 localhost。')
      return
    }

    releaseStream()
    setStream(null)
    setStatus('requesting')
    setError(null)

    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      })
      streamRef.current = nextStream
      setStream(nextStream)
      setStatus('ready')
    } catch (cause) {
      const mediaError = cause as DOMException
      const denied =
        mediaError.name === 'NotAllowedError' || mediaError.name === 'SecurityError'
      setStatus(denied ? 'denied' : 'error')
      setError(
        denied
          ? '攝影機權限遭拒。請在瀏覽器網站設定中允許權限後再試一次。'
          : `無法開啟攝影機：${mediaError.message || mediaError.name}`,
      )
    }
  }, [releaseStream])

  useEffect(
    () => () => {
      releaseStream()
    },
    [releaseStream],
  )

  return { stream, status, error, start, stop }
}

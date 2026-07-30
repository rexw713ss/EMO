import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  ConnectionStatus,
  EmotionResponse,
  ReadyMessage,
  SocketMessage,
} from '../types/emotion'

interface UseEmotionSocketOptions {
  enabled: boolean
  url: string
}
export function useEmotionSocket({ enabled, url }: UseEmotionSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>('idle')
  const [latest, setLatest] = useState<EmotionResponse | null>(null)
  const [ready, setReady] = useState<ReadyMessage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const pendingFrameRef = useRef(false)
  const reconnectTimerRef = useRef<number | null>(null)
  const reconnectAttemptRef = useRef(0)
  const enabledRef = useRef(enabled)

  enabledRef.current = enabled

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!enabledRef.current) return
    clearReconnectTimer()
    socketRef.current?.close()
    pendingFrameRef.current = false
    setStatus(reconnectAttemptRef.current > 0 ? 'reconnecting' : 'connecting')

    const socket = new WebSocket(url)
    socket.binaryType = 'arraybuffer'
    socketRef.current = socket

    socket.onopen = () => {
      if (socket !== socketRef.current) return
      reconnectAttemptRef.current = 0
      setStatus('connected')
      setError(null)
    }

    socket.onmessage = (event) => {
      if (socket !== socketRef.current || typeof event.data !== 'string') return
      try {
        const message = JSON.parse(event.data) as SocketMessage
        if (message.type === 'ready') {
          setReady(message)
          setStatus('connected')
          return
        }
        if (message.type === 'emotion') {
          pendingFrameRef.current = false
          setLatest(message)
          setError(null)
          return
        }
        if (message.type === 'error') {
          pendingFrameRef.current = false
          setError(message.message)
        }
      } catch {
        pendingFrameRef.current = false
        setError('後端回傳了無法解析的訊息。')
      }
    }

    socket.onerror = () => {
      if (socket === socketRef.current) {
        setError('無法連線情緒模型服務。')
      }
    }

    socket.onclose = () => {
      if (socket !== socketRef.current) return
      socketRef.current = null
      pendingFrameRef.current = false
      setReady(null)

      if (!enabledRef.current) {
        setStatus('idle')
        return
      }

      setStatus('offline')
      reconnectAttemptRef.current += 1
      const delay = Math.min(1000 * 2 ** (reconnectAttemptRef.current - 1), 8000)
      reconnectTimerRef.current = window.setTimeout(connect, delay)
      setStatus('reconnecting')
    }
  }, [clearReconnectTimer, url])

  useEffect(() => {
    if (!enabled) {
      clearReconnectTimer()
      socketRef.current?.close()
      socketRef.current = null
      pendingFrameRef.current = false
      reconnectAttemptRef.current = 0
      setReady(null)
      setStatus('idle')
      return
    }

    connect()
    return () => {
      clearReconnectTimer()
      socketRef.current?.close()
      socketRef.current = null
      pendingFrameRef.current = false
    }
  }, [clearReconnectTimer, connect, enabled])

  const sendFrame = useCallback((frame: Blob) => {
    const socket = socketRef.current
    if (
      !socket ||
      socket.readyState !== WebSocket.OPEN ||
      pendingFrameRef.current ||
      socket.bufferedAmount > 512_000
    ) {
      return false
    }
    pendingFrameRef.current = true
    socket.send(frame)
    return true
  }, [])

  const reset = useCallback(() => {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'reset' }))
    }
    pendingFrameRef.current = false
    setLatest(null)
    setError(null)
  }, [])

  const clearLatest = useCallback(() => {
    setLatest(null)
    setError(null)
    pendingFrameRef.current = false
  }, [])

  return {
    status,
    latest,
    ready,
    error,
    sendFrame,
    reset,
    clearLatest,
  }
}

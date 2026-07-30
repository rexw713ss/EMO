const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '')

export const API_HTTP_URL = trimTrailingSlash(
  import.meta.env.VITE_API_HTTP_URL || 'http://localhost:8000',
)

export const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || 'ws://localhost:8000/ws/emotion'

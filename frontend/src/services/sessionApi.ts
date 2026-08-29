import { API_HTTP_URL } from './config'
import type {
  EmotionSessionPayload,
  StoredEmotionSession,
  StoredSessionsResponse,
} from '../types/emotion'

async function responseError(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string }
    return body.detail || `HTTP ${response.status}`
  } catch {
    return `HTTP ${response.status}`
  }
}
export async function saveEmotionSession(
  payload: EmotionSessionPayload,
): Promise<StoredEmotionSession> {
  const response = await fetch(`${API_HTTP_URL}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
  return (await response.json()) as StoredEmotionSession
}

export async function listEmotionSessions(
  limit = 20,
): Promise<StoredSessionsResponse> {
  const response = await fetch(`${API_HTTP_URL}/api/sessions?limit=${limit}`)
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
  return (await response.json()) as StoredSessionsResponse
}

export async function deleteEmotionSession(sessionId: string): Promise<void> {
  const response = await fetch(
    `${API_HTTP_URL}/api/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
}

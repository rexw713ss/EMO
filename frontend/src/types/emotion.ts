export const EMOTION_LABELS = [
  'anger',
  'contempt',
  'disgust',
  'fear',
  'happy',
  'neutral',
  'sad',
  'surprise',
] as const

export type EmotionLabel = (typeof EMOTION_LABELS)[number] | 'unknown'
export type VisualStateKey = 'calm' | 'pleasant' | 'alert' | 'low' | 'unknown'
export type ConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'offline'

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface EmotionDetails {
  label: EmotionLabel
  confidence: number
  raw_label: EmotionLabel
  raw_confidence: number
  scores: Record<string, number>
  smoothed_scores: Record<string, number>
}

export interface VisualState {
  key: VisualStateKey
  label: string
  confidence: number
  scores: Partial<Record<VisualStateKey, number>>
}

export interface EmotionTransition {
  from: EmotionLabel
  to: EmotionLabel
  duration_frames: number
  timestamp_ms: number
}

export interface EmotionTrend {
  dominant_emotion: EmotionLabel
  duration_frames: number
  stability: number
  distribution: Record<string, number>
  recent_transitions: EmotionTransition[]
}

export interface PerformanceInfo {
  inference_ms: number
  server_ms: number
  device: string
  accuracy_mode: boolean
}

export interface EmotionResponse {
  type: 'emotion'
  schema_version: string
  timestamp_ms: number
  face_detected: boolean
  emotion: EmotionDetails
  visual_state: VisualState
  trend: EmotionTrend
  bbox: BoundingBox | null
  frame: {
    width: number
    height: number
  }
  performance: PerformanceInfo
}

export interface ReadyMessage {
  type: 'ready'
  schema_version: string
  device: string
  accuracy_mode: boolean
}

export interface ErrorMessage {
  type: 'error'
  message: string
}

export type SocketMessage =
  | EmotionResponse
  | ReadyMessage
  | ErrorMessage
  | { type: 'pong'; timestamp_ms: number }
  | { type: 'reset'; ok: boolean }
  | { type: 'config'; accuracy_mode: boolean }

export interface HistoryPoint {
  timestamp: number
  emotion: EmotionLabel
  visualState: VisualStateKey
  confidence: number
  scores: Record<string, number>
  faceDetected: boolean
  inferenceMs: number
  serverMs: number
}

export type SessionFlowPhase =
  | 'idle'
  | 'countdown'
  | 'detecting'
  | 'form'
  | 'saving'
  | 'saved'

export interface UserSessionForm {
  participantCode: string
  displayName: string
  note: string
}

export interface EmotionSessionPayload {
  participant_code: string
  display_name: string | null
  note: string | null
  started_at_ms: number
  ended_at_ms: number
  sample_count: number
  face_detected_samples: number
  dominant_visual_state: VisualStateKey
  average_scores: Record<string, number>
}

export interface StoredEmotionSession extends EmotionSessionPayload {
  id: string
  created_at_ms: number
}

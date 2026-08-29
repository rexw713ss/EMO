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

export interface StoredSessionsResponse {
  items: StoredEmotionSession[]
  count: number
}

export interface VisualStateTransition {
  from: VisualStateKey
  to: VisualStateKey
  startedAt: number
  endedAt: number
  durationMs: number
  confidenceAtEnd: number
}

export type DistributionRange = 'today' | 'week'

export interface DistributionStateSummary {
  key: VisualStateKey
  count: number
  avg_confidence: number
  avg_duration_ms: number
}

export interface DistributionTransitionSummary {
  from: VisualStateKey
  to: VisualStateKey
  count: number
}

export interface DistributionSummary {
  range: DistributionRange
  states: DistributionStateSummary[]
  top_transition: DistributionTransitionSummary | null
}

export interface PerClassMetric {
  label: EmotionLabel
  precision: number
  recall: number
  f1: number
  support: number
}

export interface SubgroupMetric {
  condition: string
  accuracy: number
  sample_count: number
}

export interface DatasetCandidate {
  name: string
  class_count: number
  has_contempt: boolean
  notes: string
  status: 'candidate' | 'needs_license' | 'in_use'
}

export interface ModelEvaluationData {
  updated_at: string
  accuracy_pct: number
  tta_accuracy_pct: number
  sample_count: number
  target_sample_count: number
  confidence_interval_pct: number
  class_names: EmotionLabel[]
  confusion_matrix: number[][]
  per_class_metrics: PerClassMetric[]
  subgroup_metrics: SubgroupMetric[]
  dataset_candidates: DatasetCandidate[]
  next_steps: string[]
  is_estimate: boolean
  estimate_note: string
}

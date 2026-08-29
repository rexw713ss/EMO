import { API_HTTP_URL } from './config'
import type { ModelEvaluationData } from '../types/emotion'

export async function fetchModelEvaluation(): Promise<ModelEvaluationData> {
  const response = await fetch(`${API_HTTP_URL}/api/model-eval`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return (await response.json()) as ModelEvaluationData
}

import { API_HTTP_URL } from './config'
import type { DistributionRange, DistributionSummary } from '../types/emotion'

export async function fetchDistributionSummary(
  range: DistributionRange,
): Promise<DistributionSummary> {
  const response = await fetch(
    `${API_HTTP_URL}/api/analytics/distribution?range=${range}`,
  )
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return (await response.json()) as DistributionSummary
}

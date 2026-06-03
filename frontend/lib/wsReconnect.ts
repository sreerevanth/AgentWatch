/** WebSocket reconnection helpers for the Live Feed (#57). */

export type LiveFeedStatus = 'connecting' | 'streaming' | 'reconnecting' | 'failed'

export const WS_BACKOFF_BASE_MS = 1000
export const WS_BACKOFF_MAX_MS = 30_000

export function wsBackoffDelayMs(attempt: number): number {
  const delay = WS_BACKOFF_BASE_MS * 2 ** attempt
  return Math.min(delay, WS_BACKOFF_MAX_MS)
}

export function parseMaxReconnectAttempts(): number {
  const raw = process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS
  if (!raw) return 8
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 8
}

export function nextLiveFeedStatus(
  current: LiveFeedStatus,
  event: 'open' | 'close' | 'max_attempts',
): LiveFeedStatus {
  if (event === 'open') return 'streaming'
  if (event === 'max_attempts') return 'failed'
  if (event === 'close') {
    if (current === 'connecting') return 'reconnecting'
    if (current === 'streaming') return 'reconnecting'
    if (current === 'reconnecting') return 'reconnecting'
  }
  return current
}

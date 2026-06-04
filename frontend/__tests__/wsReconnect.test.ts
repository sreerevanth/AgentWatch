import {
  LiveFeedStatus,
  nextLiveFeedStatus,
  parseMaxReconnectAttempts,
  wsBackoffDelayMs,
} from '../lib/wsReconnect'

describe('wsBackoffDelayMs', () => {
  it('uses exponential backoff capped at 30s', () => {
    expect(wsBackoffDelayMs(0)).toBe(1000)
    expect(wsBackoffDelayMs(1)).toBe(2000)
    expect(wsBackoffDelayMs(2)).toBe(4000)
    expect(wsBackoffDelayMs(10)).toBe(30_000)
  })
})

describe('nextLiveFeedStatus', () => {
  it('transitions through reconnecting to streaming', () => {
    let status: LiveFeedStatus = 'connecting'
    status = nextLiveFeedStatus(status, 'close')
    expect(status).toBe('reconnecting')
    status = nextLiveFeedStatus(status, 'open')
    expect(status).toBe('streaming')
  })

  it('enters failed after max attempts', () => {
    expect(nextLiveFeedStatus('reconnecting', 'max_attempts')).toBe('failed')
  })
})

describe('parseMaxReconnectAttempts', () => {
  const original = process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS

  afterEach(() => {
    if (original === undefined) {
      delete process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS
    } else {
      process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS = original
    }
  })

  it('defaults to 8', () => {
    delete process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS
    expect(parseMaxReconnectAttempts()).toBe(8)
  })

  it('reads env override', () => {
    process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS = '3'
    expect(parseMaxReconnectAttempts()).toBe(3)
  })
})

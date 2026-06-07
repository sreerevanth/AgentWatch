import { useEffect, useRef, useState } from 'react'

import { AgentEvent, createEventSocket } from './api'
import {
  LiveFeedStatus,
  nextLiveFeedStatus,
  parseMaxReconnectAttempts,
  wsBackoffDelayMs,
} from './wsReconnect'

export function useLiveEventSocket(
  onEvent: (event: AgentEvent) => void,
  refresh: () => void,
): { status: LiveFeedStatus; reconnectElapsedSec: number } {
  const [status, setStatus] = useState<LiveFeedStatus>('connecting')
  const [reconnectElapsedSec, setReconnectElapsedSec] = useState(0)
  const onEventRef = useRef(onEvent)
  const refreshRef = useRef(refresh)

  useEffect(() => {
    onEventRef.current = onEvent
    refreshRef.current = refresh
  }, [onEvent, refresh])

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    let cancelled = false
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let elapsedTimer: ReturnType<typeof setInterval> | undefined
    let attempt = 0
    let disconnectedAt: number | null = null
    const maxAttempts = parseMaxReconnectAttempts()

    const clearTimers = () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (elapsedTimer) clearInterval(elapsedTimer)
      reconnectTimer = undefined
      elapsedTimer = undefined
    }

    const startElapsedTicker = () => {
      if (elapsedTimer) clearInterval(elapsedTimer)
      elapsedTimer = setInterval(() => {
        if (disconnectedAt === null) return
        setReconnectElapsedSec(Math.floor((Date.now() - disconnectedAt) / 1000))
      }, 1000)
    }

    const connect = () => {
      if (cancelled) return
      clearTimers()
      socket?.close()
      socket = createEventSocket((event) => {
        onEventRef.current(event)
        refreshRef.current()
      })

      socket.onopen = () => {
        attempt = 0
        disconnectedAt = null
        setReconnectElapsedSec(0)
        setStatus('streaming')
      }

      socket.onclose = () => {
        if (cancelled) return
        setStatus((prev) => {
          const next = nextLiveFeedStatus(prev, 'close')
          if (next === 'reconnecting' && disconnectedAt === null) {
            disconnectedAt = Date.now()
            startElapsedTicker()
          }
          return next
        })

        attempt += 1
        if (attempt > maxAttempts) {
          clearTimers()
          setStatus('failed')
          return
        }

        const delay = wsBackoffDelayMs(attempt - 1)
        reconnectTimer = setTimeout(connect, delay)
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    setStatus('connecting')
    connect()

    return () => {
      cancelled = true
      clearTimers()
      socket?.close()
    }
  }, [])

  return { status, reconnectElapsedSec }
}

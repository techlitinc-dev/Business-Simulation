import { useEffect, useRef, useState } from 'react'

import { useAuthStore } from '@/stores/auth-store'
import { useSimulationStore } from '@/stores/simulation'
import { API_URL } from '@/lib/constants'
import type { WsEnvelope } from '@/features/simulation/types'

export type ConnectionStatus = 'connecting' | 'open' | 'closed'

const MAX_RETRIES = 5

/**
 * Build a WebSocket URL for a channel path like `/ws/reports/{id}`,
 * attaching the current access token as a query param.
 */
function buildSocketUrl(channelPath: string): string {
  const accessToken = useAuthStore.getState().getAccessToken()
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  // Same-origin when API_URL is relative/empty (production nginx proxy);
  // otherwise use the configured API host.
  const host = API_URL ? new URL(API_URL).host : window.location.host
  return `${protocol}://${host}${channelPath}?token=${encodeURIComponent(accessToken ?? '')}`
}

/**
 * Generic authenticated channel socket. Opens
 * `ws(s)://<api-host>{channelPath}?token=...`, exposes the latest raw frame
 * as `lastMessage`, and auto-reconnects with exponential backoff (max 5).
 * Used for non-simulation channels (e.g. deep-report progress).
 */
export function useChannelSocket(channelPath: string | undefined) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('closed')
  const [lastMessage, setLastMessage] = useState<string | null>(null)
  const retriesRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!channelPath) return
    const accessToken = useAuthStore.getState().getAccessToken()
    if (!accessToken) return

    let disposed = false
    let retryTimer: ReturnType<typeof setTimeout> | undefined

    const connect = () => {
      if (disposed) return
      setConnectionStatus('connecting')

      const ws = new WebSocket(buildSocketUrl(channelPath))
      wsRef.current = ws

      ws.onopen = () => {
        retriesRef.current = 0
        setConnectionStatus('open')
      }

      ws.onmessage = (event) => {
        setLastMessage(event.data as string)
      }

      ws.onclose = () => {
        if (disposed) return
        setConnectionStatus('closed')
        if (retriesRef.current < MAX_RETRIES) {
          const delay = 500 * 2 ** retriesRef.current
          retriesRef.current += 1
          retryTimer = setTimeout(connect, delay)
        }
      }
    }

    connect()

    return () => {
      disposed = true
      if (retryTimer) clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [channelPath])

  return { connectionStatus, lastMessage }
}

/**
 * Live simulation socket. Opens `ws(s)://<api-host>/ws/simulations/{id}?token=...`,
 * dispatches envelopes into the Zustand simulation store, and auto-reconnects
 * with exponential backoff (max 5 tries).
 */
export function useSimulationSocket(runId: string | undefined) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('closed')
  const retriesRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!runId) return
    const accessToken = useAuthStore.getState().getAccessToken()
    if (!accessToken) return

    let disposed = false
    let retryTimer: ReturnType<typeof setTimeout> | undefined

    const connect = () => {
      if (disposed) return
      setConnectionStatus('connecting')

      const ws = new WebSocket(buildSocketUrl(`/ws/simulations/${runId}`))
      wsRef.current = ws

      ws.onopen = () => {
        retriesRef.current = 0
        setConnectionStatus('open')
      }

      ws.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data as string) as WsEnvelope
          const store = useSimulationStore.getState()
          switch (envelope.type) {
            case 'snapshot':
              store.setStatus(envelope.data.status)
              break
            case 'tick':
              store.appendTick(envelope.data)
              break
            case 'event':
              store.appendEvent(envelope.data)
              break
            case 'status':
              store.setStatus(envelope.data.status)
              break
            case 'progress':
              store.setProgress(envelope.data)
              break
          }
        } catch {
          // Ignore malformed frames.
        }
      }

      ws.onclose = () => {
        if (disposed) return
        setConnectionStatus('closed')
        if (retriesRef.current < MAX_RETRIES) {
          const delay = 500 * 2 ** retriesRef.current
          retriesRef.current += 1
          retryTimer = setTimeout(connect, delay)
        }
      }
    }

    connect()

    return () => {
      disposed = true
      if (retryTimer) clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [runId])

  return connectionStatus
}

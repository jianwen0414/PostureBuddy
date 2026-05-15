'use client'

import { useEffect, useRef } from 'react'
import { useDashboardStore } from '@/store/useDashboardStore'
import { buildSubscribe, buildUnsubscribe, parseIncoming } from '@/lib/rosbridge'
import { createMockWebSocket } from '@/lib/mockData'
import type { RosPostureStatusMsg, RosFatigueMetricsMsg, RosHriStatusMsg, RosCompressedImageMsg, WebSocketLike } from '@/types/ros'

const TOPICS = [
  { topic: '/posture_status', type: 'posture_buddy/PostureStatus' },
  { topic: '/fatigue_metrics', type: 'posture_buddy/FatigueMetrics' },
  { topic: '/hri_execution_status', type: 'posture_buddy/HriStatus' },
] as const

const IS_MOCK = process.env.NEXT_PUBLIC_MOCK_WS === 'true'

export function useRosBridge(wsUrl: string): void {
  const applyPostureUpdate = useDashboardStore((s) => s.applyPostureUpdate)
  const applyFatigueUpdate = useDashboardStore((s) => s.applyFatigueUpdate)
  const applyHriUpdate = useDashboardStore((s) => s.applyHriUpdate)
  const applyCameraFrame = useDashboardStore((s) => s.applyCameraFrame)
  const setConnectionState = useDashboardStore((s) => s.setConnectionState)

  const actionsRef = useRef({ applyPostureUpdate, applyFatigueUpdate, applyHriUpdate, applyCameraFrame, setConnectionState })
  actionsRef.current = { applyPostureUpdate, applyFatigueUpdate, applyHriUpdate, applyCameraFrame, setConnectionState }

  useEffect(() => {
    let destroyed = false
    let reconnectTimer: ReturnType<typeof setTimeout>
    let currentWs: WebSocketLike | null = null

    function connect() {
      actionsRef.current.setConnectionState('connecting')

      const ws: WebSocketLike = IS_MOCK
        ? createMockWebSocket()
        : (new WebSocket(wsUrl) as unknown as WebSocketLike)

      currentWs = ws

      ws.onopen = () => {
        if (destroyed) return
        actionsRef.current.setConnectionState('connected')
        TOPICS.forEach((t) => ws.send(buildSubscribe(t.topic, t.type)))
        const camTopic = useDashboardStore.getState().cameraTopicName
        ws.send(buildSubscribe(camTopic, 'sensor_msgs/CompressedImage'))
      }

      ws.onmessage = (event: MessageEvent) => {
        if (destroyed) return
        const msg = parseIncoming(event.data)
        if (!msg || msg.op !== 'publish') return
        const camTopic = useDashboardStore.getState().cameraTopicName

        switch (msg.topic) {
          case '/posture_status':
            actionsRef.current.applyPostureUpdate(msg.msg as RosPostureStatusMsg)
            break
          case '/fatigue_metrics':
            actionsRef.current.applyFatigueUpdate(msg.msg as RosFatigueMetricsMsg)
            break
          case '/hri_execution_status':
            actionsRef.current.applyHriUpdate(msg.msg as RosHriStatusMsg)
            break
          default:
            if (msg.topic === camTopic) {
              actionsRef.current.applyCameraFrame(msg.msg as RosCompressedImageMsg)
            }
        }
      }

      ws.onerror = () => {
        if (!destroyed) actionsRef.current.setConnectionState('error')
      }

      ws.onclose = () => {
        if (destroyed) return
        actionsRef.current.setConnectionState('disconnected')
        reconnectTimer = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      destroyed = true
      clearTimeout(reconnectTimer)
      if (currentWs && currentWs.readyState === currentWs.OPEN) {
        TOPICS.forEach((t) => currentWs!.send(buildUnsubscribe(t.topic)))
      }
      currentWs?.close()
    }
  }, [wsUrl]) // eslint-disable-line react-hooks/exhaustive-deps
}

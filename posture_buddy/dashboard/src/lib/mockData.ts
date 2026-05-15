import type { PostureState, FatigueLevel, WebSocketLike } from '@/types/ros'

function pickPosture(current: PostureState, tick: number, changeAt: number): PostureState {
  if (tick < changeAt) return current
  const r = Math.random()
  if (r < 0.6) return 'GOOD'
  if (r < 0.9) return 'BAD'
  return 'ABSENT'
}

function getFatigue(degradSec: number): FatigueLevel {
  if (degradSec >= 180) return 'HIGH'
  if (degradSec >= 60) return 'MEDIUM'
  return 'LOW'
}

export function createMockWebSocket(): WebSocketLike {
  const mock: WebSocketLike = {
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    readyState: 0,
    OPEN: 1,
    send(_data: string) {},
    close() {},
  }

  let sessionSec = 0
  let degradSec = 0
  let posture: PostureState = 'GOOD'
  let nextChangeAt = 5 + Math.floor(Math.random() * 5)
  let tick = 0
  let lastEmittedTrigger = 0
  let trigger1Fired = false
  let trigger2Fired = false
  let closed = false
  let interval: ReturnType<typeof setInterval> | null = null

  const emit = (msg: object) => {
    if (mock.onmessage && !closed) {
      mock.onmessage({ data: JSON.stringify(msg) } as MessageEvent)
    }
  }

  mock.close = () => {
    closed = true
    ;(mock as { readyState: number }).readyState = 3
    if (interval) clearInterval(interval)
    mock.onclose?.({} as CloseEvent)
  }

  setTimeout(() => {
    if (closed) return
    ;(mock as { readyState: number }).readyState = 1
    mock.onopen?.({} as Event)

    interval = setInterval(() => {
      if (closed) return
      tick++
      sessionSec++

      posture = pickPosture(posture, tick, nextChangeAt)
      if (tick >= nextChangeAt) {
        nextChangeAt = tick + 5 + Math.floor(Math.random() * 8)
      }

      if (posture === 'BAD') degradSec++
      else if (posture === 'ABSENT') degradSec = Math.max(0, degradSec - 1)

      const fatigue = getFatigue(degradSec)

      let triggerCode = 0
      if (!trigger1Fired && sessionSec >= 120) {
        triggerCode = 1
        trigger1Fired = true
      } else if (fatigue === 'HIGH' && !trigger2Fired) {
        triggerCode = 2
        trigger2Fired = true
      }

      const isSpeaking = triggerCode !== 0
      if (triggerCode !== 0) lastEmittedTrigger = triggerCode
      if (fatigue !== 'HIGH') trigger2Fired = false

      // Camera frame every 3 ticks
      if (tick % 3 === 0) {
        emit({
          op: 'publish',
          topic: '/camera/image_raw/compressed',
          msg: {
            format: 'jpeg',
            data: '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJQAB/9k=',
          },
        })
      }

      emit({ op: 'publish', topic: '/posture_status', msg: { posture_state: posture } })
      emit({
        op: 'publish',
        topic: '/fatigue_metrics',
        msg: {
          current_session_duration_sec: sessionSec,
          rolling_bad_posture_sec: degradSec,
          fatigue_level: fatigue,
        },
      })
      emit({
        op: 'publish',
        topic: '/hri_execution_status',
        msg: {
          is_speaking: isSpeaking,
          last_executed_trigger: isSpeaking ? triggerCode : lastEmittedTrigger,
        },
      })
    }, 1000)
  }, 600)

  return mock
}

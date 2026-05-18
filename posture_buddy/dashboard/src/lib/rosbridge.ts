import type { RosBridgeMessage } from '@/types/ros'

export function buildSubscribe(topic: string, type: string): string {
  return JSON.stringify({ op: 'subscribe', topic, type })
}

export function buildUnsubscribe(topic: string): string {
  return JSON.stringify({ op: 'unsubscribe', topic })
}

export function parseIncoming(raw: string): RosBridgeMessage | null {
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.op === 'string') return parsed as RosBridgeMessage
    return null
  } catch {
    return null
  }
}

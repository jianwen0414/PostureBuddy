export interface RosPostureStatusMsg {
  posture_state: 'GOOD' | 'BAD' | 'ABSENT'
}

export interface RosFatigueMetricsMsg {
  current_session_duration_sec: number
  rolling_bad_posture_sec: number
  fatigue_level: 'LOW' | 'MEDIUM' | 'HIGH'
}

export interface RosHriStatusMsg {
  is_speaking: boolean
  last_executed_trigger: number
  robot_message?: string
  user_message?: string
  conversation?: string[]
}

export interface RosBridgeMessage<T = unknown> {
  op: string
  topic?: string
  msg?: T
  type?: string
  id?: string
}

export type PostureState = 'GOOD' | 'BAD' | 'ABSENT'
export type FatigueLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type SystemStatus = 'Idle' | 'Speaking' | 'Alert'
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface DashboardState {
  posture: PostureState
  sessionTimeSec: number
  degradationTimeSec: number
  fatigueLevel: FatigueLevel
  systemStatus: SystemStatus
  connectionState: ConnectionState
  lastUpdatedAt: number | null
}

export type TriggerCode = 0 | 1 | 2

export interface AlertEntry {
  id: string
  triggerCode: TriggerCode
  label: string
  timestamp: number
  postureAtTime: PostureState
}

export interface WellnessStats {
  goodPosturePct: number
  sessionCount: number
  totalGoodSec: number
  totalBadSec: number
}

/**
 * One sample of session telemetry captured every time M3 publishes a fatigue
 * update (~1 Hz). Used to draw the live timeline chart and the post-session
 * report. Bounded ring so memory stays flat over long sessions.
 */
export interface TimelineSample {
  t: number
  sessionSec: number
  goodPct: number
  badRollingSec: number
  fatigueLevel: FatigueLevel
  posture: PostureState
}

export interface RosCompressedImageMsg {
  format: string
  data: string
}

export interface WebSocketLike {
  onopen: ((event: Event) => void) | null
  onmessage: ((event: MessageEvent) => void) | null
  onclose: ((event: CloseEvent) => void) | null
  onerror: ((event: Event) => void) | null
  readyState: number
  readonly OPEN: number
  send(data: string): void
  close(): void
}

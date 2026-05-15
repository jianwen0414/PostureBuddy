import { create } from 'zustand'
import { formatTrigger } from '@/lib/formatters'
import type {
  DashboardState,
  AlertEntry,
  WellnessStats,
  ConnectionState,
  RosPostureStatusMsg,
  RosFatigueMetricsMsg,
  RosHriStatusMsg,
  RosCompressedImageMsg,
  TriggerCode,
} from '@/types/ros'

interface DashboardStore extends DashboardState {
  alerts: AlertEntry[]
  wellnessStats: WellnessStats
  _lastTrigger: number
  cameraFrame: string | null
  cameraTopicName: string

  applyPostureUpdate: (msg: RosPostureStatusMsg) => void
  applyFatigueUpdate: (msg: RosFatigueMetricsMsg) => void
  applyHriUpdate: (msg: RosHriStatusMsg) => void
  applyCameraFrame: (msg: RosCompressedImageMsg) => void
  setConnectionState: (s: ConnectionState) => void
}

const initialWellness: WellnessStats = {
  goodPosturePct: 0,
  sessionCount: 0,
  totalGoodSec: 0,
  totalBadSec: 0,
}

export const useDashboardStore = create<DashboardStore>()((set, get) => ({
  posture: 'ABSENT',
  sessionTimeSec: 0,
  degradationTimeSec: 0,
  fatigueLevel: 'LOW',
  systemStatus: 'Idle',
  connectionState: 'connecting',
  lastUpdatedAt: null,
  alerts: [],
  wellnessStats: initialWellness,
  _lastTrigger: 0,
  cameraFrame: null,
  cameraTopicName: process.env.NEXT_PUBLIC_CAMERA_TOPIC ?? '/camera/image_raw/compressed',

  applyPostureUpdate: (msg) =>
    set({
      posture: msg.posture_state,
      lastUpdatedAt: Date.now(),
    }),

  applyFatigueUpdate: (msg) => {
    const totalSec = msg.current_session_duration_sec
    const totalBad = msg.rolling_bad_posture_sec
    const totalGood = Math.max(totalSec - totalBad, 0)
    const goodPosturePct = totalSec > 0 ? Math.round((totalGood / totalSec) * 100) : 0

    set((state) => ({
      sessionTimeSec: msg.current_session_duration_sec,
      degradationTimeSec: msg.rolling_bad_posture_sec,
      fatigueLevel: msg.fatigue_level,
      lastUpdatedAt: Date.now(),
      wellnessStats: {
        ...state.wellnessStats,
        goodPosturePct,
        totalGoodSec: totalGood,
        totalBadSec: totalBad,
      },
    }))
  },

  applyHriUpdate: (msg) => {
    const state = get()
    const incomingTrigger = msg.last_executed_trigger as TriggerCode
    const shouldAdd =
      incomingTrigger !== 0 && incomingTrigger !== state._lastTrigger

    const newAlerts: AlertEntry[] = shouldAdd
      ? [
          {
            id: crypto.randomUUID(),
            triggerCode: incomingTrigger,
            label: formatTrigger(incomingTrigger),
            timestamp: Date.now(),
            postureAtTime: state.posture,
          },
          ...state.alerts,
        ].slice(0, 50)
      : state.alerts

    set({
      systemStatus: msg.is_speaking
        ? incomingTrigger === 2
          ? 'Alert'
          : 'Speaking'
        : 'Idle',
      lastUpdatedAt: Date.now(),
      alerts: newAlerts,
      _lastTrigger: shouldAdd ? incomingTrigger : state._lastTrigger,
    })
  },

  applyCameraFrame: (msg) =>
    set({ cameraFrame: `data:image/${msg.format};base64,${msg.data}` }),

  setConnectionState: (s) => set({ connectionState: s }),
}))

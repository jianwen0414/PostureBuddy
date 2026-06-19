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
  TimelineSample,
  TriggerCode,
} from '@/types/ros'

const TIMELINE_CAPACITY = 240   // ~4 minutes of 1 Hz samples — bounded ring

interface DashboardStore extends DashboardState {
  alerts: AlertEntry[]
  wellnessStats: WellnessStats
  conversation: string[]
  _lastTrigger: number
  cameraFrame: string | null
  cameraTopicName: string
  timeline: TimelineSample[]
  reportOpen: boolean
  maxBadStreakSec: number
  _lastBadRollingSec: number   // internal: detect streak resets vs. growth

  applyPostureUpdate: (msg: RosPostureStatusMsg) => void
  applyFatigueUpdate: (msg: RosFatigueMetricsMsg) => void
  applyHriUpdate: (msg: RosHriStatusMsg) => void
  applyCameraFrame: (msg: RosCompressedImageMsg) => void
  setConnectionState: (s: ConnectionState) => void
  setReportOpen: (open: boolean) => void
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
  conversation: [],
  _lastTrigger: 0,
  cameraFrame: null,
  cameraTopicName: process.env.NEXT_PUBLIC_CAMERA_TOPIC ?? '/camera/image_raw/compressed',
  timeline: [],
  reportOpen: false,
  maxBadStreakSec: 0,
  _lastBadRollingSec: 0,

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
    const now = Date.now()

    set((state) => {
      // Approximate max continuous bad streak: M3's rolling_bad_posture_sec
      // grows monotonically while the user is BAD, and resets / drops when
      // they sit up or the rolling window slides. We track the peak value.
      const nextMaxStreak = Math.max(state.maxBadStreakSec, totalBad)

      // If M3 reset the session (session_dur went down), clear the timeline
      // so the chart shows the new session cleanly. Same behavior the user
      // already experiences from the 60s-absent reset in fatigue_state_node.
      const sessionReset = totalSec < state.sessionTimeSec
      const baseTimeline = sessionReset ? [] : state.timeline

      const sample: TimelineSample = {
        t: now,
        sessionSec: totalSec,
        goodPct: goodPosturePct,
        badRollingSec: totalBad,
        fatigueLevel: msg.fatigue_level,
        posture: state.posture,
      }
      const nextTimeline =
        baseTimeline.length >= TIMELINE_CAPACITY
          ? [...baseTimeline.slice(baseTimeline.length - TIMELINE_CAPACITY + 1), sample]
          : [...baseTimeline, sample]

      return {
        sessionTimeSec: totalSec,
        degradationTimeSec: totalBad,
        fatigueLevel: msg.fatigue_level,
        lastUpdatedAt: now,
        wellnessStats: {
          ...state.wellnessStats,
          goodPosturePct,
          totalGoodSec: totalGood,
          totalBadSec: totalBad,
        },
        timeline: nextTimeline,
        maxBadStreakSec: sessionReset ? 0 : nextMaxStreak,
        _lastBadRollingSec: totalBad,
      }
    })
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
      conversation: msg.conversation ?? state.conversation,
      _lastTrigger: shouldAdd ? incomingTrigger : state._lastTrigger,
    })
  },

  applyCameraFrame: (msg) =>
    set({ cameraFrame: `data:image/${msg.format};base64,${msg.data}` }),

  setConnectionState: (s) => set({ connectionState: s }),
  setReportOpen: (open) => set({ reportOpen: open }),
}))

'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import PulsingDot from '@/components/shared/PulsingDot'
import { formatSeconds } from '@/lib/formatters'
import type { ConnectionState, SystemStatus } from '@/types/ros'

const CONNECTION_CONFIG: Record<ConnectionState, { label: string; color: 'green' | 'amber' | 'red'; textColor: string }> = {
  connected:    { label: 'Live',         color: 'green', textColor: 'text-emerald-400' },
  connecting:   { label: 'Connecting…',  color: 'amber', textColor: 'text-amber-400' },
  disconnected: { label: 'Offline',      color: 'red',   textColor: 'text-red-400' },
  error:        { label: 'Error',        color: 'red',   textColor: 'text-red-400' },
}

const STATUS_CONFIG: Record<SystemStatus, { color: 'green' | 'amber' | 'red' | 'gray'; textColor: string; ring: string }> = {
  Idle:     { color: 'gray',  textColor: 'text-slate-400', ring: 'ring-slate-700/60' },
  Speaking: { color: 'green', textColor: 'text-sky-300',   ring: 'ring-sky-500/40' },
  Alert:    { color: 'red',   textColor: 'text-red-300',   ring: 'ring-red-500/40' },
}

export default function Header() {
  const connectionState = useDashboardStore((s) => s.connectionState)
  const systemStatus = useDashboardStore((s) => s.systemStatus)
  const goodPct = useDashboardStore((s) => s.wellnessStats.goodPosturePct)
  const sessionSec = useDashboardStore((s) => s.sessionTimeSec)
  const setReportOpen = useDashboardStore((s) => s.setReportOpen)

  const conn = CONNECTION_CONFIG[connectionState]
  const status = STATUS_CONFIG[systemStatus]

  return (
    <header className="flex flex-shrink-0 items-center justify-between gap-4 border-b border-slate-800/80 bg-slate-900/80 px-5 py-2 backdrop-blur-md">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/30 to-cyan-500/20 ring-1 ring-violet-400/30">
          <span className="text-base" aria-hidden>🤖</span>
        </div>
        <div className="hidden sm:flex flex-col leading-tight">
          <span className="text-sm font-display font-black tracking-tight text-slate-100">
            PostureBuddy
          </span>
          <span className="text-[10px] font-display text-slate-500 tracking-widest uppercase">
            Workspace Wellness Monitor
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 text-xs">
        <div className="flex items-center gap-2 rounded-md bg-slate-800/60 px-3 py-1.5 ring-1 ring-slate-700/60">
          <span className="text-[10px] font-display uppercase tracking-widest text-slate-500">Session</span>
          <span className="font-data font-bold tabular-nums text-slate-100">{formatSeconds(sessionSec)}</span>
        </div>
        <div className="hidden md:flex items-center gap-2 rounded-md bg-slate-800/60 px-3 py-1.5 ring-1 ring-slate-700/60">
          <span className="text-[10px] font-display uppercase tracking-widest text-slate-500">Good</span>
          <span className="font-data font-bold tabular-nums text-cyan-300">{goodPct}%</span>
        </div>
        <div className={`flex items-center gap-2 rounded-md bg-slate-800/60 px-3 py-1.5 ring-1 ${status.ring}`}>
          <PulsingDot color={status.color} size="sm" />
          <span className={`text-[10px] font-display font-bold tracking-widest uppercase ${status.textColor}`}>
            {systemStatus}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setReportOpen(true)}
          className="flex items-center gap-1.5 rounded-md bg-violet-500/15 px-3 py-1.5 ring-1 ring-violet-400/40 hover:bg-violet-500/25 hover:ring-violet-400/70 transition-colors"
          aria-label="Open session wellness report"
        >
          <span aria-hidden className="text-[11px]">📋</span>
          <span className="text-[10px] font-display font-bold tracking-widest uppercase text-violet-200">
            Report
          </span>
        </button>
        <div className="flex items-center gap-2 rounded-md bg-slate-800/60 px-3 py-1.5 ring-1 ring-slate-700/60">
          <PulsingDot color={conn.color} size="sm" />
          <span className={`text-[10px] font-display font-bold tracking-widest uppercase ${conn.textColor}`}>
            {conn.label}
          </span>
        </div>
      </div>
    </header>
  )
}

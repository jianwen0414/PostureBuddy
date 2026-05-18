'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import { formatMinutesSeconds } from '@/lib/formatters'

const WINDOW_SEC = 1200 // 20-minute rolling window

function getBarColor(pct: number): { bar: string; glow: string } {
  if (pct >= 60) return { bar: 'bg-red-400',    glow: 'shadow-red-500/30' }
  if (pct >= 30) return { bar: 'bg-amber-400',  glow: 'shadow-amber-500/30' }
  return             { bar: 'bg-emerald-400',  glow: 'shadow-emerald-500/30' }
}

export default function DegradationPanel() {
  const degradationTimeSec = useDashboardStore((s) => s.degradationTimeSec)
  const pct = Math.min(Math.round((degradationTimeSec / WINDOW_SEC) * 100), 100)
  const { bar, glow } = getBarColor(pct)

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-t-2 border-t-amber-400 border-slate-700/50 bg-amber-400/5 p-5 shadow-xl shadow-amber-500/5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400">
          Bad Posture Time
        </span>
        <span className="text-xs font-data text-slate-400">
          20-min window
        </span>
      </div>

      <div className="flex items-end gap-3 mb-3">
        <span className="text-2xl font-data font-bold text-slate-100 tabular-nums">
          {formatMinutesSeconds(degradationTimeSec)}
        </span>
        <span className="text-slate-500 text-sm font-display mb-0.5">
          / {formatMinutesSeconds(WINDOW_SEC)}
        </span>
        <span
          className={`ml-auto text-lg font-data font-bold tabular-nums transition-colors duration-300 ${
            pct >= 60 ? 'text-red-400' : pct >= 30 ? 'text-amber-400' : 'text-emerald-400'
          }`}
        >
          {pct}%
        </span>
      </div>

      <div className="relative h-3 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full rounded-full transition-all duration-700 ${bar} shadow-lg ${glow}`}
          style={{ width: `${pct}%` }}
        />
        {/* threshold markers */}
        <div className="absolute left-[30%] top-0 h-full w-px bg-slate-600/50" />
        <div className="absolute left-[60%] top-0 h-full w-px bg-slate-600/50" />
      </div>

      <div className="flex justify-between mt-1.5">
        <span className="text-emerald-500/60 text-xs font-display">Good</span>
        <span className="text-amber-500/60 text-xs font-display">Caution</span>
        <span className="text-red-500/60 text-xs font-display">High</span>
      </div>
    </div>
  )
}

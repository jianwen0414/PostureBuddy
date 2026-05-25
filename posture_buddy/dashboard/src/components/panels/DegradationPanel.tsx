'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import { formatMinutesSeconds } from '@/lib/formatters'

const WINDOW_SEC = 1200 // 20-minute rolling window

function getBarColor(pct: number): { bar: string; glow: string; text: string } {
  if (pct >= 60) return { bar: 'bg-red-400',    glow: 'shadow-red-500/30',    text: 'text-red-400' }
  if (pct >= 30) return { bar: 'bg-amber-400',  glow: 'shadow-amber-500/30',  text: 'text-amber-400' }
  return             { bar: 'bg-emerald-400',  glow: 'shadow-emerald-500/30', text: 'text-emerald-400' }
}

export default function DegradationPanel() {
  const degradationTimeSec = useDashboardStore((s) => s.degradationTimeSec)
  const pct = Math.min(Math.round((degradationTimeSec / WINDOW_SEC) * 100), 100)
  const { bar, glow, text } = getBarColor(pct)

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-t-2 border-t-amber-400 border-slate-700/50 bg-amber-400/5 px-3 py-3 shadow-xl shadow-amber-500/5">
      <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500 mb-2">
        Bad Posture · 20-min
      </span>

      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-xl font-data font-bold text-slate-100 tabular-nums leading-none">
          {formatMinutesSeconds(degradationTimeSec)}
        </span>
        <span className={`ml-auto text-base font-data font-bold tabular-nums ${text} transition-colors duration-300`}>
          {pct}%
        </span>
      </div>

      <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full rounded-full transition-all duration-700 ${bar} shadow-lg ${glow}`}
          style={{ width: `${pct}%` }}
        />
        <div className="absolute left-[30%] top-0 h-full w-px bg-slate-600/50" />
        <div className="absolute left-[60%] top-0 h-full w-px bg-slate-600/50" />
      </div>
    </div>
  )
}

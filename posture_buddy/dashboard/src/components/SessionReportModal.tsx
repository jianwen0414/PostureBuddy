'use client'

import { useEffect, useMemo } from 'react'
import { useDashboardStore } from '@/store/useDashboardStore'
import { formatSeconds } from '@/lib/formatters'
import type { FatigueLevel } from '@/types/ros'

function gradeFromGoodPct(pct: number): { letter: string; tone: string; desc: string } {
  if (pct >= 90) return { letter: 'A', tone: 'text-emerald-300', desc: 'Excellent posture discipline' }
  if (pct >= 75) return { letter: 'B', tone: 'text-cyan-300',    desc: 'Solid session — minor lapses' }
  if (pct >= 60) return { letter: 'C', tone: 'text-amber-300',   desc: 'Room to improve' }
  if (pct >= 40) return { letter: 'D', tone: 'text-orange-300',  desc: 'Frequent slouching detected' }
  return            { letter: 'F', tone: 'text-red-300',     desc: 'Posture needs serious attention' }
}

function fatigueDistribution(samples: { fatigueLevel: FatigueLevel }[]): Record<FatigueLevel, number> {
  const out: Record<FatigueLevel, number> = { LOW: 0, MEDIUM: 0, HIGH: 0 }
  for (const s of samples) out[s.fatigueLevel] += 1
  return out
}

export default function SessionReportModal() {
  const open = useDashboardStore((s) => s.reportOpen)
  const setOpen = useDashboardStore((s) => s.setReportOpen)
  const session = useDashboardStore((s) => s.sessionTimeSec)
  const wellness = useDashboardStore((s) => s.wellnessStats)
  const alerts = useDashboardStore((s) => s.alerts)
  const timeline = useDashboardStore((s) => s.timeline)
  const maxBadStreak = useDashboardStore((s) => s.maxBadStreakSec)

  // Escape closes
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, setOpen])

  const dist = useMemo(() => fatigueDistribution(timeline), [timeline])
  const grade = gradeFromGoodPct(wellness.goodPosturePct)
  const triggerCount = alerts.length
  const stretchCount = alerts.filter((a) => a.triggerCode === 1).length
  const urgentCount = alerts.filter((a) => a.triggerCode === 2).length
  const totalDistSamples = dist.LOW + dist.MEDIUM + dist.HIGH || 1

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Session wellness report"
      onClick={() => setOpen(false)}
    >
      <div
        className="relative w-[min(640px,92vw)] max-h-[88vh] overflow-y-auto rounded-2xl border border-violet-400/30 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl shadow-violet-500/20"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          aria-label="Close report"
          onClick={() => setOpen(false)}
          className="absolute top-3 right-3 flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition"
        >
          ✕
        </button>

        {/* Header */}
        <div className="mb-4">
          <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-violet-300">
            Wellness Report
          </span>
          <h2 className="mt-1 text-2xl font-display font-black tracking-tight text-slate-100">
            Session Summary
          </h2>
          <p className="text-xs font-display text-slate-500 mt-1">
            Snapshot of the current session as observed by PostureBuddy.
          </p>
        </div>

        {/* Grade + headline */}
        <div className="flex items-center gap-5 rounded-xl border border-slate-700/50 bg-slate-800/40 p-4 mb-5">
          <div className={`text-6xl font-display font-black leading-none ${grade.tone}`}>
            {grade.letter}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-data font-bold text-cyan-300 tabular-nums leading-none">
                {wellness.goodPosturePct}
                <span className="text-2xl text-slate-400">%</span>
              </span>
              <span className="text-sm font-display text-slate-400">good posture</span>
            </div>
            <span className="text-xs font-display text-slate-500 mt-1 block">{grade.desc}</span>
          </div>
        </div>

        {/* Key stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
          <Stat label="Duration" value={formatSeconds(session)} tone="text-slate-100" />
          <Stat label="Good Time" value={formatSeconds(wellness.totalGoodSec)} tone="text-cyan-300" />
          <Stat label="Bad Time" value={formatSeconds(wellness.totalBadSec)} tone="text-amber-300" />
          <Stat label="Max Bad Streak" value={formatSeconds(maxBadStreak)} tone="text-red-300" />
        </div>

        {/* Alerts */}
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4 mb-4">
          <div className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500 mb-2">
            Alerts Delivered
          </div>
          <div className="grid grid-cols-3 gap-3">
            <AlertCount label="Total" value={triggerCount} tone="text-slate-100" />
            <AlertCount label="Stretch" value={stretchCount} tone="text-amber-300" />
            <AlertCount label="Urgent" value={urgentCount} tone="text-red-300" />
          </div>
        </div>

        {/* Fatigue distribution bar */}
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4 mb-4">
          <div className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500 mb-2">
            Time in Each Fatigue Level
          </div>
          {timeline.length === 0 ? (
            <span className="text-xs font-display text-slate-600">No samples yet.</span>
          ) : (
            <>
              <div className="flex h-3 overflow-hidden rounded-full bg-slate-900 ring-1 ring-slate-700/50">
                <div className="bg-emerald-400" style={{ width: `${(dist.LOW / totalDistSamples) * 100}%` }} />
                <div className="bg-amber-400" style={{ width: `${(dist.MEDIUM / totalDistSamples) * 100}%` }} />
                <div className="bg-red-400" style={{ width: `${(dist.HIGH / totalDistSamples) * 100}%` }} />
              </div>
              <div className="flex justify-between mt-2 text-[10px] font-data text-slate-400 tabular-nums">
                <span>LOW {formatSeconds(dist.LOW)}</span>
                <span>MED {formatSeconds(dist.MEDIUM)}</span>
                <span>HIGH {formatSeconds(dist.HIGH)}</span>
              </div>
            </>
          )}
        </div>

        {/* Recommendation */}
        <div className="rounded-xl border border-violet-400/20 bg-violet-400/5 p-4">
          <div className="text-[10px] font-display font-semibold uppercase tracking-widest text-violet-300 mb-1">
            Recommendation
          </div>
          <p className="text-sm font-display text-slate-300 leading-relaxed">
            {wellness.goodPosturePct >= 80
              ? 'Great session — keep this baseline. Take a 5-minute walk before your next focused block to lock it in.'
              : urgentCount > 0
              ? 'Multiple urgent alerts fired today. Try lowering your monitor by 2–3 cm and check that your hips are deeper than your knees.'
              : 'Set a reminder to reset your posture every 20 minutes. Standing micro-breaks help most when paired with a quick neck stretch.'}
          </p>
        </div>

        <div className="mt-5 text-center text-[10px] font-display tracking-widest uppercase text-slate-600">
          Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">Esc</kbd> or click outside to close
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2">
      <div className="text-[10px] font-display uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`mt-1 font-data font-bold tabular-nums text-base leading-tight ${tone}`}>
        {value}
      </div>
    </div>
  )
}

function AlertCount({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="text-center">
      <div className={`text-2xl font-data font-bold tabular-nums ${tone}`}>{value}</div>
      <div className="text-[10px] font-display uppercase tracking-widest text-slate-500">{label}</div>
    </div>
  )
}

'use client'

import { useEffect, useRef, useState } from 'react'
import { useDashboardStore } from '@/store/useDashboardStore'
import { formatSeconds } from '@/lib/formatters'

const SESSION_TARGET = 1500 // 25 minutes

export default function SessionTimerPanel() {
  const sessionTimeSec = useDashboardStore((s) => s.sessionTimeSec)
  const lastUpdatedAt = useDashboardStore((s) => s.lastUpdatedAt)

  const [displaySec, setDisplaySec] = useState(sessionTimeSec)
  const anchorRef = useRef({ base: sessionTimeSec, time: lastUpdatedAt ?? Date.now() })

  useEffect(() => {
    anchorRef.current = { base: sessionTimeSec, time: Date.now() }
    setDisplaySec(sessionTimeSec)
  }, [sessionTimeSec])

  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - anchorRef.current.time) / 1000)
      setDisplaySec(anchorRef.current.base + elapsed)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const progress = Math.min(displaySec / SESSION_TARGET, 1)
  const r = 52
  const circumference = 2 * Math.PI * r
  const strokeDash = circumference * progress

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-t-2 border-t-sky-400 border-slate-700/50 bg-sky-400/5 p-5 shadow-xl shadow-sky-500/10">
      <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400 mb-3">
        Session Time
      </span>

      <div className="flex flex-1 items-center justify-center gap-5">
        <div className="relative flex-shrink-0">
          <svg width="124" height="124" viewBox="0 0 124 124">
            <circle cx="62" cy="62" r={r} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="8" />
            <circle
              cx="62"
              cy="62"
              r={r}
              fill="none"
              stroke="#38bdf8"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${strokeDash} ${circumference}`}
              transform="rotate(-90, 62, 62)"
              style={{
                transition: 'stroke-dasharray 1s linear',
                filter: 'drop-shadow(0 0 6px #38bdf880)',
              }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-slate-500 text-xs font-display">
              {Math.round(progress * 100)}%
            </span>
          </div>
        </div>

        <div className="flex flex-col">
          <span className="text-3xl font-data font-bold text-slate-100 tabular-nums tracking-tight">
            {formatSeconds(displaySec)}
          </span>
          <span className="text-slate-500 text-xs font-display mt-1">
            Target: 25 min
          </span>
        </div>
      </div>
    </div>
  )
}

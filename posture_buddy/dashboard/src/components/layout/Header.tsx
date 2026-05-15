'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import PulsingDot from '@/components/shared/PulsingDot'
import type { ConnectionState } from '@/types/ros'

const CONNECTION_CONFIG: Record<ConnectionState, { label: string; color: 'green' | 'amber' | 'red'; textColor: string }> = {
  connected:    { label: 'Live',         color: 'green', textColor: 'text-emerald-400' },
  connecting:   { label: 'Connecting…',  color: 'amber', textColor: 'text-amber-400' },
  disconnected: { label: 'Offline',      color: 'red',   textColor: 'text-red-400' },
  error:        { label: 'Error',        color: 'red',   textColor: 'text-red-400' },
}

export default function Header() {
  const connectionState = useDashboardStore((s) => s.connectionState)
  const cfg = CONNECTION_CONFIG[connectionState]

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 bg-slate-900/80 backdrop-blur-md border-b border-slate-800/80">
      <div className="flex items-center gap-3">
        <span className="text-xl" aria-hidden>🤖</span>
        <div className="flex flex-col leading-tight">
          <span className="text-base font-display font-black tracking-tight text-slate-100">
            PostureBuddy
          </span>
          <span className="text-xs font-display text-slate-500 tracking-wide">
            Module 5 — Telemetry
          </span>
        </div>
        <div className="hidden sm:block h-6 w-px bg-slate-700 mx-1" />
        <span className="hidden sm:block text-xs font-display text-slate-600 tracking-wider uppercase">
          Workspace Wellness Monitor
        </span>
      </div>

      <div className="flex items-center gap-2">
        <PulsingDot color={cfg.color} />
        <span className={`text-xs font-display font-semibold ${cfg.textColor}`}>
          {cfg.label}
        </span>
      </div>
    </header>
  )
}

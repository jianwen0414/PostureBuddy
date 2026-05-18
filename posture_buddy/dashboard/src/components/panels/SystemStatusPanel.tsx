'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import { formatRelative, formatTrigger } from '@/lib/formatters'
import type { TriggerCode } from '@/types/ros'

function RobotIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" width="40" height="40" className={className} aria-hidden>
      <rect x="10" y="14" width="20" height="16" rx="3" fill="currentColor" opacity="0.9" />
      <rect x="14" y="18" width="4" height="4" rx="1" fill="rgba(0,0,0,0.4)" />
      <rect x="22" y="18" width="4" height="4" rx="1" fill="rgba(0,0,0,0.4)" />
      <rect x="17" y="24" width="6" height="2" rx="1" fill="rgba(0,0,0,0.3)" />
      <line x1="20" y1="10" x2="20" y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="20" cy="8" r="2.5" fill="currentColor" opacity="0.7" />
      <line x1="6" y1="18" x2="10" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="34" y1="18" x2="30" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function SpeakingVisualizer() {
  return (
    <div className="flex items-end gap-1 h-8">
      <div className="w-2 rounded-full bg-sky-400 animate-speak-bar1 shadow-[0_0_8px_2px_rgba(56,189,248,0.5)]" style={{ height: 12 }} />
      <div className="w-2 rounded-full bg-sky-400 animate-speak-bar2 shadow-[0_0_8px_2px_rgba(56,189,248,0.5)]" style={{ height: 20 }} />
      <div className="w-2 rounded-full bg-sky-400 animate-speak-bar3 shadow-[0_0_8px_2px_rgba(56,189,248,0.5)]" style={{ height: 8 }} />
      <div className="w-2 rounded-full bg-sky-400 animate-speak-bar2 shadow-[0_0_8px_2px_rgba(56,189,248,0.5)]" style={{ height: 16 }} />
      <div className="w-2 rounded-full bg-sky-400 animate-speak-bar1 shadow-[0_0_8px_2px_rgba(56,189,248,0.5)]" style={{ height: 10 }} />
    </div>
  )
}

function AlertTriangle() {
  return (
    <svg viewBox="0 0 40 36" width="44" height="40" aria-hidden>
      <path
        d="M20 2 L38 34 L2 34 Z"
        fill="rgba(239,68,68,0.2)"
        stroke="#ef4444"
        strokeWidth="2"
        strokeLinejoin="round"
        className="animate-pulse-dot"
      />
      <text x="20" y="28" textAnchor="middle" fill="#ef4444" fontSize="16" fontWeight="bold">!</text>
    </svg>
  )
}

export default function SystemStatusPanel() {
  const systemStatus = useDashboardStore((s) => s.systemStatus)
  const alerts = useDashboardStore((s) => s.alerts)
  const lastAlert = alerts[0]

  const borderColor =
    systemStatus === 'Alert'
      ? 'border-t-red-400'
      : systemStatus === 'Speaking'
      ? 'border-t-sky-400'
      : 'border-t-slate-600'

  const bg =
    systemStatus === 'Alert'
      ? 'bg-red-400/5'
      : systemStatus === 'Speaking'
      ? 'bg-sky-400/5'
      : 'bg-slate-800/30'

  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-xl border border-t-2 ${borderColor} border-slate-700/50 ${bg} p-5 shadow-xl transition-all duration-500`}
    >
      <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400 mb-3">
        System Status
      </span>

      <div className="flex flex-1 items-center gap-4">
        <div className="flex-shrink-0">
          {systemStatus === 'Idle' && <RobotIcon className="text-slate-500" />}
          {systemStatus === 'Speaking' && <SpeakingVisualizer />}
          {systemStatus === 'Alert' && <AlertTriangle />}
        </div>

        <div className="flex flex-col min-w-0">
          <span
            className={`text-xl font-display font-bold transition-colors duration-300 ${
              systemStatus === 'Alert'
                ? 'text-red-400'
                : systemStatus === 'Speaking'
                ? 'text-sky-400'
                : 'text-slate-400'
            }`}
          >
            {systemStatus}
          </span>

          {lastAlert ? (
            <div className="mt-1 min-w-0">
              <span className="text-xs text-slate-500 font-display block truncate">
                Last: {formatTrigger(lastAlert.triggerCode as TriggerCode)}
              </span>
              <span className="text-xs text-slate-600 font-data">
                {formatRelative(lastAlert.timestamp)}
              </span>
            </div>
          ) : (
            <span className="text-xs text-slate-600 font-display mt-1">No alerts yet</span>
          )}
        </div>
      </div>
    </div>
  )
}

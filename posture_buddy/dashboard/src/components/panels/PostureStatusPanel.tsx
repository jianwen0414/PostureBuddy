'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import PulsingDot from '@/components/shared/PulsingDot'
import type { PostureState } from '@/types/ros'

const POSTURE_CONFIG = {
  GOOD: {
    label: 'GOOD',
    color: 'text-posture-good',
    borderColor: 'border-t-posture-good',
    glow: 'shadow-cyan-500/10',
    dotColor: 'green' as const,
    bg: 'bg-cyan-400/5',
    desc: 'Sitting upright',
  },
  BAD: {
    label: 'BAD',
    color: 'text-posture-bad',
    borderColor: 'border-t-posture-bad',
    glow: 'shadow-amber-500/10',
    dotColor: 'amber' as const,
    bg: 'bg-amber-400/5',
    desc: 'Posture needs correction',
  },
  ABSENT: {
    label: 'ABSENT',
    color: 'text-posture-absent',
    borderColor: 'border-t-posture-absent',
    glow: 'shadow-slate-500/10',
    dotColor: 'gray' as const,
    bg: 'bg-slate-800/40',
    desc: 'No user detected',
  },
}

function PostureFigure({ posture }: { posture: PostureState }) {
  const strokeWidth = 3.5
  const base = 'transition-all duration-500'
  return (
    <svg viewBox="0 0 80 120" width="64" height="92" aria-hidden>
      <g
        className={base}
        style={{
          opacity: posture === 'GOOD' ? 1 : 0, stroke: '#22d3ee', fill: 'none',
          strokeWidth, strokeLinecap: 'round', strokeLinejoin: 'round',
          transition: 'opacity 0.5s ease',
        }}
      >
        <circle cx="40" cy="16" r="11" fill="#22d3ee22" />
        <line x1="40" y1="27" x2="40" y2="42" />
        <line x1="20" y1="48" x2="60" y2="48" />
        <line x1="40" y1="48" x2="40" y2="88" />
        <line x1="27" y1="88" x2="53" y2="88" />
        <polyline points="20,48 10,62 18,74" />
        <polyline points="60,48 70,62 62,74" />
      </g>
      <g
        className={base}
        style={{
          opacity: posture === 'BAD' ? 1 : 0, stroke: '#f59e0b', fill: 'none',
          strokeWidth, strokeLinecap: 'round', strokeLinejoin: 'round',
          transition: 'opacity 0.5s ease',
        }}
      >
        <circle cx="52" cy="13" r="11" fill="#f59e0b22" />
        <line x1="50" y1="24" x2="42" y2="40" />
        <line x1="18" y1="50" x2="56" y2="46" />
        <path d="M 39 50 Q 50 65 44 88" />
        <line x1="30" y1="88" x2="52" y2="90" />
        <polyline points="18,50 8,66 16,78" />
        <polyline points="56,46 66,60 58,72" />
      </g>
      <g
        className={base}
        style={{
          opacity: posture === 'ABSENT' ? 1 : 0, stroke: '#6b7280', fill: 'none',
          strokeWidth: strokeWidth - 0.5, strokeLinecap: 'round', strokeLinejoin: 'round',
          strokeDasharray: '4 4', transition: 'opacity 0.5s ease',
        }}
      >
        <circle cx="40" cy="16" r="11" />
        <line x1="40" y1="27" x2="40" y2="42" />
        <line x1="20" y1="48" x2="60" y2="48" />
        <line x1="40" y1="48" x2="40" y2="88" />
        <line x1="27" y1="88" x2="53" y2="88" />
        <polyline points="20,48 10,62 18,74" />
        <polyline points="60,48 70,62 62,74" />
      </g>
    </svg>
  )
}

export default function PostureStatusPanel() {
  const posture = useDashboardStore((s) => s.posture)
  const connectionState = useDashboardStore((s) => s.connectionState)
  const cfg = POSTURE_CONFIG[posture]

  return (
    <div
      className={`relative flex flex-shrink-0 items-center gap-4 overflow-hidden rounded-xl border border-t-2 ${cfg.borderColor} border-slate-700/50 ${cfg.bg} px-4 py-3 shadow-xl ${cfg.glow} transition-all duration-500`}
    >
      <div className="flex-shrink-0">
        <PostureFigure posture={posture} />
      </div>

      <div className="flex flex-col min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500">
            Posture
          </span>
          {connectionState === 'connected' && <PulsingDot color={cfg.dotColor} size="sm" />}
        </div>
        <span className={`text-3xl font-display font-black tracking-tight leading-none ${cfg.color} transition-colors duration-500`}>
          {cfg.label}
        </span>
        <span className="text-slate-500 text-xs font-display mt-1.5 truncate">
          {cfg.desc}
        </span>
      </div>
    </div>
  )
}

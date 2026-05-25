'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import GaugeRing from '@/components/shared/GaugeRing'
import type { FatigueLevel } from '@/types/ros'

const FATIGUE_CONFIG: Record<FatigueLevel, { value: 0 | 1 | 2; color: string; borderColor: string; bg: string; desc: string }> = {
  LOW:    { value: 0, color: 'text-fatigue-low',    borderColor: 'border-t-fatigue-low',    bg: 'bg-emerald-400/5', desc: 'Looking great' },
  MEDIUM: { value: 1, color: 'text-fatigue-medium', borderColor: 'border-t-fatigue-medium', bg: 'bg-amber-400/5',   desc: 'Take a break' },
  HIGH:   { value: 2, color: 'text-fatigue-high',   borderColor: 'border-t-fatigue-high',   bg: 'bg-red-400/5',     desc: 'Rest now' },
}

export default function FatigueLevelPanel() {
  const fatigueLevel = useDashboardStore((s) => s.fatigueLevel)
  const cfg = FATIGUE_CONFIG[fatigueLevel]

  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-xl border border-t-2 ${cfg.borderColor} border-slate-700/50 ${cfg.bg} px-3 py-3 shadow-xl transition-all duration-500`}
    >
      <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500 mb-2">
        Fatigue
      </span>

      <div className="flex items-center gap-3">
        <GaugeRing value={cfg.value} size={68} />
        <div className="flex flex-col min-w-0">
          <span className={`text-xl font-display font-black tracking-tight ${cfg.color} transition-colors duration-500 leading-none`}>
            {fatigueLevel}
          </span>
          <span className="text-slate-500 text-[10px] font-display mt-1 truncate">{cfg.desc}</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-2.5">
        {(['LOW', 'MEDIUM', 'HIGH'] as FatigueLevel[]).map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              level === fatigueLevel
                ? FATIGUE_CONFIG[level].color.replace('text-', 'bg-')
                : 'bg-slate-700/60'
            }`}
          />
        ))}
      </div>
    </div>
  )
}

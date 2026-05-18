'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import GaugeRing from '@/components/shared/GaugeRing'
import type { FatigueLevel } from '@/types/ros'

const FATIGUE_CONFIG: Record<FatigueLevel, { value: 0 | 1 | 2; color: string; borderColor: string; bg: string; desc: string }> = {
  LOW:    { value: 0, color: 'text-fatigue-low',    borderColor: 'border-t-fatigue-low',    bg: 'bg-emerald-400/5', desc: 'Looking great' },
  MEDIUM: { value: 1, color: 'text-fatigue-medium', borderColor: 'border-t-fatigue-medium', bg: 'bg-amber-400/5',   desc: 'Take a break soon' },
  HIGH:   { value: 2, color: 'text-fatigue-high',   borderColor: 'border-t-fatigue-high',   bg: 'bg-red-400/5',     desc: 'Rest recommended' },
}

export default function FatigueLevelPanel() {
  const fatigueLevel = useDashboardStore((s) => s.fatigueLevel)
  const cfg = FATIGUE_CONFIG[fatigueLevel]

  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-xl border border-t-2 ${cfg.borderColor} border-slate-700/50 ${cfg.bg} p-5 shadow-xl transition-all duration-500`}
    >
      <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400 mb-2">
        Fatigue Level
      </span>

      <div className="flex flex-1 items-center justify-center gap-4">
        <GaugeRing value={cfg.value} size={120} />

        <div className="flex flex-col">
          <span
            className={`text-3xl font-display font-black tracking-tight ${cfg.color} transition-colors duration-500`}
          >
            {fatigueLevel}
          </span>
          <span className="text-slate-500 text-xs font-display mt-1">{cfg.desc}</span>

          <div className="flex flex-col gap-1 mt-3">
            {(['LOW', 'MEDIUM', 'HIGH'] as FatigueLevel[]).map((level) => (
              <div key={level} className="flex items-center gap-2">
                <div
                  className={`h-1.5 w-1.5 rounded-full transition-all duration-300 ${
                    level === fatigueLevel
                      ? `${FATIGUE_CONFIG[level].color.replace('text-', 'bg-')} scale-150`
                      : 'bg-slate-700'
                  }`}
                />
                <span
                  className={`text-xs font-display transition-colors duration-300 ${
                    level === fatigueLevel ? FATIGUE_CONFIG[level].color : 'text-slate-600'
                  }`}
                >
                  {level}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

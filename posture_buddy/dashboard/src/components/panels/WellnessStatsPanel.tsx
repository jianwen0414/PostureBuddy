'use client'

import { PieChart, Pie, Cell, Tooltip } from 'recharts'
import { useDashboardStore } from '@/store/useDashboardStore'
import { formatSeconds } from '@/lib/formatters'

const COLORS = { good: '#22d3ee', bad: '#f59e0b', empty: '#1e293b' }

export default function WellnessStatsPanel() {
  const wellnessStats = useDashboardStore((s) => s.wellnessStats)
  const alertCount = useDashboardStore((s) => s.alerts.length)

  const hasData = wellnessStats.totalGoodSec + wellnessStats.totalBadSec > 0
  const data = hasData
    ? [
        { name: 'Good', value: wellnessStats.totalGoodSec },
        { name: 'Bad', value: wellnessStats.totalBadSec },
      ]
    : [{ name: 'No data', value: 1 }]

  return (
    <div className="relative flex flex-shrink-0 flex-col overflow-hidden rounded-xl border border-t-2 border-t-cyan-400 border-slate-700/50 bg-cyan-400/5 px-4 py-3 shadow-xl">
      <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500 mb-2">
        Wellness Stats
      </span>

      <div className="flex items-center gap-3">
        <div className="relative flex-shrink-0">
          <PieChart width={88} height={88}>
            <Pie
              data={data}
              dataKey="value"
              outerRadius={42}
              innerRadius={28}
              paddingAngle={hasData ? 2 : 0}
              stroke="none"
            >
              {hasData ? (
                <>
                  <Cell fill={COLORS.good} />
                  <Cell fill={COLORS.bad} />
                </>
              ) : (
                <Cell fill={COLORS.empty} />
              )}
            </Pie>
            {hasData && (
              <Tooltip
                formatter={(value) => [formatSeconds(Number(value)), '']}
                contentStyle={{
                  background: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-space-mono)',
                }}
                itemStyle={{ color: '#e2e8f0' }}
              />
            )}
          </PieChart>
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-data font-bold text-cyan-300 tabular-nums">
              {wellnessStats.goodPosturePct}%
            </span>
          </div>
        </div>

        <div className="flex flex-1 min-w-0 flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[10px] font-display uppercase tracking-widest text-slate-500">Good</span>
            <span className="font-data text-cyan-300 tabular-nums text-xs">{formatSeconds(wellnessStats.totalGoodSec)}</span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[10px] font-display uppercase tracking-widest text-slate-500">Bad</span>
            <span className="font-data text-amber-300 tabular-nums text-xs">{formatSeconds(wellnessStats.totalBadSec)}</span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[10px] font-display uppercase tracking-widest text-slate-500">Alerts</span>
            <span className="font-data text-slate-200 tabular-nums text-xs">{alertCount}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

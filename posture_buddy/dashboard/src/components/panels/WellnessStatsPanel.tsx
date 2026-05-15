'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useDashboardStore } from '@/store/useDashboardStore'
import StatCard from '@/components/shared/StatCard'
import { formatSeconds } from '@/lib/formatters'

const COLORS = { good: '#22d3ee', bad: '#f59e0b', empty: '#1e293b' }

export default function WellnessStatsPanel() {
  const wellnessStats = useDashboardStore((s) => s.wellnessStats)
  const alertCount = useDashboardStore((s) => s.alerts.length)
  const sessionTimeSec = useDashboardStore((s) => s.sessionTimeSec)

  const hasData = wellnessStats.totalGoodSec + wellnessStats.totalBadSec > 0

  const data = hasData
    ? [
        { name: 'Good', value: wellnessStats.totalGoodSec },
        { name: 'Bad', value: wellnessStats.totalBadSec },
      ]
    : [{ name: 'No data', value: 1 }]

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-t-2 border-t-cyan-400 border-slate-700/50 bg-cyan-400/3 p-5 shadow-xl">
      <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400 mb-3">
        Wellness Stats
      </span>

      <div className="flex items-center gap-6 mb-4">
        <div className="flex-shrink-0 w-28 h-28">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                outerRadius={52}
                innerRadius={34}
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
          </ResponsiveContainer>
        </div>

        <div className="flex flex-col">
          <span className="text-5xl font-data font-bold text-posture-good leading-none">
            {wellnessStats.goodPosturePct}
            <span className="text-2xl text-slate-400">%</span>
          </span>
          <span className="text-slate-400 text-sm font-display mt-1">
            great posture this session
          </span>
          <div className="flex gap-3 mt-2">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-cyan-400" />
              <span className="text-slate-500 text-xs font-display">Good</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-amber-400" />
              <span className="text-slate-500 text-xs font-display">Bad</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Session" value={formatSeconds(sessionTimeSec)} />
        <StatCard label="Good Time" value={formatSeconds(wellnessStats.totalGoodSec)} />
        <StatCard label="Alerts" value={String(alertCount)} />
      </div>
    </div>
  )
}

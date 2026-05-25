'use client'

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts'
import { useDashboardStore } from '@/store/useDashboardStore'
import { formatSeconds } from '@/lib/formatters'
import type { TimelineSample } from '@/types/ros'

interface ChartPoint {
  sessionSec: number
  goodPct: number
  fatigueLevel: TimelineSample['fatigueLevel']
}

const FATIGUE_STROKE: Record<TimelineSample['fatigueLevel'], string> = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
}

export default function SessionTimelinePanel() {
  const timeline = useDashboardStore((s) => s.timeline)
  const fatigueLevel = useDashboardStore((s) => s.fatigueLevel)

  // Render even with one sample so the panel has visible structure as soon as
  // M3 starts publishing.
  const data: ChartPoint[] = timeline.map((s) => ({
    sessionSec: s.sessionSec,
    goodPct: s.goodPct,
    fatigueLevel: s.fatigueLevel,
  }))

  const stroke = FATIGUE_STROKE[fatigueLevel]

  return (
    <div className="relative flex flex-shrink-0 flex-col overflow-hidden rounded-xl border border-t-2 border-t-violet-400 border-slate-700/50 bg-violet-400/5 px-3 pt-3 pb-1 shadow-xl shadow-violet-500/5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500">
          Session Timeline · Good %
        </span>
        <span className="text-[10px] font-data tabular-nums text-slate-500">
          {timeline.length}s
        </span>
      </div>

      <div className="h-20 w-full">
        {data.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-[11px] font-display text-slate-600">
              Waiting for first fatigue update…
            </span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="timelineFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.55} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <XAxis dataKey="sessionSec" hide />
              <YAxis domain={[0, 100]} hide />
              {/* Threshold guide at 80% — what we'd consider a healthy session */}
              <ReferenceLine y={80} stroke="rgba(148,163,184,0.25)" strokeDasharray="3 3" />
              <Tooltip
                cursor={{ stroke: 'rgba(148,163,184,0.4)' }}
                formatter={(value) => [`${Number(value)}%`, 'Good posture']}
                labelFormatter={(label) => `t = ${formatSeconds(Number(label))}`}
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: '11px',
                  padding: '4px 8px',
                  fontFamily: 'var(--font-space-mono)',
                }}
                itemStyle={{ color: '#e2e8f0' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Area
                type="monotone"
                dataKey="goodPct"
                stroke={stroke}
                strokeWidth={2}
                fill="url(#timelineFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

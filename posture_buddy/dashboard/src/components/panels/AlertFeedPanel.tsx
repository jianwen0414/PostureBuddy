'use client'

import { useAlertHistory } from '@/hooks/useAlertHistory'
import { formatRelative } from '@/lib/formatters'
import StatusBadge from '@/components/shared/StatusBadge'
import type { TriggerCode } from '@/types/ros'

const TRIGGER_ICONS: Record<TriggerCode, string> = {
  0: '⚪',
  1: '🏃',
  2: '⚠️',
}

export default function AlertFeedPanel() {
  const alerts = useAlertHistory(50)

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-t-2 border-t-slate-500 border-slate-700/50 bg-slate-800/20 p-4 shadow-xl">
      <div className="flex flex-shrink-0 items-center justify-between mb-2">
        <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500">
          Alert Feed
        </span>
        {alerts.length > 0 && (
          <span className="text-[10px] font-data bg-slate-700/50 text-slate-300 px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center min-h-0">
          <span className="text-2xl">✅</span>
          <span className="text-slate-500 text-sm font-display">No alerts yet</span>
          <span className="text-slate-600 text-xs font-display">Great posture!</span>
        </div>
      ) : (
        <div className="flex flex-1 min-h-0 flex-col gap-1.5 overflow-y-auto pr-1 scrollbar-hide">
          {alerts.map((alert, i) => (
            <div
              key={alert.id}
              className="flex flex-shrink-0 items-start gap-2.5 bg-slate-800/50 border border-slate-700/40 rounded-lg px-2.5 py-2 animate-slide-in"
              style={{ animationDelay: i === 0 ? '0ms' : undefined }}
            >
              <span className="text-base flex-shrink-0 mt-0.5" aria-hidden>
                {TRIGGER_ICONS[alert.triggerCode as TriggerCode]}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-display font-semibold text-slate-200 truncate">
                    {alert.label}
                  </span>
                  <StatusBadge
                    label={alert.postureAtTime}
                    variant={alert.postureAtTime.toLowerCase() as 'good' | 'bad' | 'absent'}
                  />
                </div>
                <span className="text-[10px] text-slate-500 font-data mt-0.5 block">
                  {formatRelative(alert.timestamp)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

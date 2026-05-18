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
  const alerts = useAlertHistory(10)

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-t-2 border-t-slate-500 border-slate-700/50 bg-slate-800/20 p-5 shadow-xl h-full">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-display font-semibold uppercase tracking-widest text-slate-400">
          Alert Feed
        </span>
        {alerts.length > 0 && (
          <span className="text-xs font-data bg-slate-700/50 text-slate-400 px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
          <span className="text-2xl">✅</span>
          <span className="text-slate-500 text-sm font-display">No alerts yet</span>
          <span className="text-slate-600 text-xs font-display">Great posture!</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2 overflow-y-auto max-h-64 pr-1 scrollbar-hide">
          {alerts.map((alert, i) => (
            <div
              key={alert.id}
              className="flex items-start gap-3 bg-slate-800/50 border border-slate-700/40 rounded-lg p-3 animate-slide-in"
              style={{ animationDelay: i === 0 ? '0ms' : undefined }}
            >
              <span className="text-lg flex-shrink-0 mt-0.5" aria-hidden>
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
                <span className="text-xs text-slate-500 font-data mt-0.5 block">
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

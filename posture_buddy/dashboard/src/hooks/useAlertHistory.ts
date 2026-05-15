'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import type { AlertEntry } from '@/types/ros'

export function useAlertHistory(maxDisplay = 10): AlertEntry[] {
  const alerts = useDashboardStore((s) => s.alerts)
  return alerts.slice(0, maxDisplay)
}

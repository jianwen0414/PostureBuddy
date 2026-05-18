'use client'

import PostureStatusPanel from '@/components/panels/PostureStatusPanel'
import SessionTimerPanel from '@/components/panels/SessionTimerPanel'
import FatigueLevelPanel from '@/components/panels/FatigueLevelPanel'
import WellnessStatsPanel from '@/components/panels/WellnessStatsPanel'
import SystemStatusPanel from '@/components/panels/SystemStatusPanel'
import DegradationPanel from '@/components/panels/DegradationPanel'
import AlertFeedPanel from '@/components/panels/AlertFeedPanel'
import CameraFeedPanel from '@/components/panels/CameraFeedPanel'

export default function DashboardGrid() {
  return (
    <main className="p-4 lg:p-6">
      {/*
        Desktop (lg+): 3-column grid
          Row 1: PostureStatus | SessionTimer | FatigueLevel
          Row 2: WellnessStats (col-span-2) | AlertFeed (row-span-2)
          Row 3: DegradationPanel | SystemStatus

        Tablet (md): 2-column
        Mobile: 1-column
      */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {/* Row 1 */}
        <PostureStatusPanel />
        <SessionTimerPanel />
        <FatigueLevelPanel />

        {/* Row 2 — WellnessStats spans 2 cols on lg, AlertFeed spans 2 rows */}
        <div className="lg:col-span-2">
          <WellnessStatsPanel />
        </div>

        {/* AlertFeed: spans 2 rows on lg */}
        <div className="row-span-1 lg:row-span-2">
          <AlertFeedPanel />
        </div>

        {/* Row 3 — spans 2 cols on lg, split by Degradation + System */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          <DegradationPanel />
          <SystemStatusPanel />
        </div>

        {/* Row 4 — Camera feed, full width */}
        <div className="col-span-1 md:col-span-2 lg:col-span-3">
          <CameraFeedPanel />
        </div>
      </div>
    </main>
  )
}

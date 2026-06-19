'use client'

import PostureStatusPanel from '@/components/panels/PostureStatusPanel'
import FatigueLevelPanel from '@/components/panels/FatigueLevelPanel'
import WellnessStatsPanel from '@/components/panels/WellnessStatsPanel'
import DegradationPanel from '@/components/panels/DegradationPanel'
import AlertFeedPanel from '@/components/panels/AlertFeedPanel'
import CameraFeedPanel from '@/components/panels/CameraFeedPanel'
import SessionTimelinePanel from '@/components/panels/SessionTimelinePanel'
import ConversationPanel from '@/components/panels/ConversationPanel'

/**
 * Viewport-fit layout (lg+): camera section is height-bound and locked to
 * the camera's 4:3 aspect — no letterboxing, no wasted space. The side
 * column flex-fills the remaining horizontal space. Alerts get the only
 * internal scroll. Sub-lg falls back to a single scrollable column.
 */
export default function DashboardGrid() {
  return (
    <main className="flex-1 min-h-0 overflow-y-auto lg:overflow-hidden p-3 sm:p-4">
      <div className="flex h-full min-h-0 flex-col gap-3 sm:gap-4 lg:flex-row">
        <section className="min-h-[280px] lg:h-full lg:min-h-0 lg:aspect-[4/3] lg:flex-shrink-0">
          <CameraFeedPanel />
        </section>

        <aside className="flex flex-1 min-w-0 min-h-0 flex-col gap-3 sm:gap-4">
          <PostureStatusPanel />

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <FatigueLevelPanel />
            <DegradationPanel />
          </div>

          <WellnessStatsPanel />

          <SessionTimelinePanel />

          <div className="min-h-[240px]">
            <ConversationPanel />
          </div>

          <div className="flex-1 min-h-0">
            <AlertFeedPanel />
          </div>
        </aside>
      </div>
    </main>
  )
}

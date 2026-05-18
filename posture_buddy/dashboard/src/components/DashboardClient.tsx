'use client'

import { useRosBridge } from '@/hooks/useRosBridge'
import Header from '@/components/layout/Header'
import DashboardGrid from '@/components/layout/DashboardGrid'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:9090'

export default function DashboardClient() {
  useRosBridge(WS_URL)

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <DashboardGrid />
    </div>
  )
}

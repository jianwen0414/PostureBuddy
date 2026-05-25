'use client'

import { useDashboardStore } from '@/store/useDashboardStore'
import PulsingDot from '@/components/shared/PulsingDot'

function CornerBrackets({ color = 'border-violet-500/40' }: { color?: string }) {
  const cls = `absolute w-4 h-4 ${color}`
  return (
    <>
      <div className={`${cls} top-3 left-3 border-t-2 border-l-2`} />
      <div className={`${cls} top-3 right-3 border-t-2 border-r-2`} />
      <div className={`${cls} bottom-3 left-3 border-b-2 border-l-2`} />
      <div className={`${cls} bottom-3 right-3 border-b-2 border-r-2`} />
    </>
  )
}

function NoSignalState({ topicName }: { topicName: string }) {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden">
      <CornerBrackets />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(139,92,246,0.04) 23px, rgba(139,92,246,0.04) 24px),
            repeating-linear-gradient(90deg, transparent, transparent 23px, rgba(139,92,246,0.04) 23px, rgba(139,92,246,0.04) 24px)
          `,
        }}
      />
      <div
        className="absolute left-0 right-0 h-12 pointer-events-none animate-scan-sweep"
        style={{
          background: 'linear-gradient(180deg, transparent 0%, rgba(139,92,246,0.06) 40%, rgba(139,92,246,0.12) 50%, rgba(139,92,246,0.06) 60%, transparent 100%)',
        }}
      />
      <div className="relative mb-5 z-10">
        <svg viewBox="0 0 80 80" width="72" height="72" className="animate-pulse-dot" aria-hidden>
          <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(139,92,246,0.35)" strokeWidth="1.5" strokeDasharray="5 4" />
          <rect x="18" y="27" width="44" height="30" rx="5" fill="rgba(139,92,246,0.12)" stroke="rgba(139,92,246,0.5)" strokeWidth="1.5" />
          <circle cx="40" cy="42" r="10" fill="none" stroke="rgba(139,92,246,0.5)" strokeWidth="1.5" />
          <circle cx="40" cy="42" r="5" fill="rgba(139,92,246,0.2)" />
          <path d="M 29 27 L 33 21 L 47 21 L 51 27" fill="rgba(139,92,246,0.12)" stroke="rgba(139,92,246,0.5)" strokeWidth="1.5" strokeLinejoin="round" />
          <circle cx="55" cy="35" r="2.5" fill="rgba(139,92,246,0.6)" />
        </svg>
      </div>
      <div className="z-10 text-center flex flex-col items-center gap-1.5">
        <span className="text-slate-300 text-base font-display font-bold tracking-widest uppercase">
          Awaiting Signal
          <span className="animate-blink-cursor ml-0.5 text-violet-400">_</span>
        </span>
        <span className="text-slate-600 text-xs font-data tracking-wide">{topicName}</span>
        <span className="text-slate-700 text-xs font-display mt-1">No frames received yet</span>
      </div>
    </div>
  )
}

function LiveFeedState({ frame, topicName }: { frame: string; topicName: string }) {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg bg-black animate-camera-acquire">
      <img
        src={frame}
        alt="Robot camera feed"
        draggable={false}
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 55%, rgba(2,6,23,0.55) 100%)',
        }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.06) 3px, rgba(0,0,0,0.06) 4px)',
        }}
      />

      <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm border border-red-500/30 rounded px-2 py-1 z-10">
        <PulsingDot color="red" size="sm" />
        <span className="text-white text-xs font-data font-bold tracking-widest">LIVE</span>
      </div>

      <CornerBrackets color="border-violet-400/60" />

      <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm border border-violet-500/30 rounded px-2 py-1 z-10">
        <span className="text-violet-200 text-[10px] font-data tracking-wider uppercase">
          neck &amp; spine vectors
        </span>
      </div>

      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-2 bg-gradient-to-t from-black/80 to-transparent z-10">
        <span className="text-slate-400 text-xs font-data truncate">{topicName}</span>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div className="h-1 w-1 rounded-full bg-violet-400" />
          <div className="h-1 w-1 rounded-full bg-violet-400/60" />
          <div className="h-1 w-1 rounded-full bg-violet-400/30" />
        </div>
      </div>
    </div>
  )
}

export default function CameraFeedPanel() {
  const cameraFrame = useDashboardStore((s) => s.cameraFrame)
  const cameraTopicName = useDashboardStore((s) => s.cameraTopicName)

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-t-2 border-t-violet-400 border-slate-700/50 bg-slate-950 shadow-xl shadow-violet-500/5">
      {/* Panel title — absolute overlay so the image truly fills the panel */}
      <div className="absolute top-2 left-1/2 z-20 -translate-x-1/2 rounded-full bg-black/55 px-3 py-1 backdrop-blur-sm ring-1 ring-violet-500/25">
        <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-violet-200">
          Camera Feed · Skeleton Overlay
        </span>
      </div>

      {cameraFrame ? (
        <LiveFeedState frame={cameraFrame} topicName={cameraTopicName} />
      ) : (
        <NoSignalState topicName={cameraTopicName} />
      )}
    </div>
  )
}

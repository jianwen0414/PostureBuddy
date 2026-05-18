'use client'

type Color = 'green' | 'amber' | 'red' | 'blue' | 'gray'

const colorMap: Record<Color, { dot: string; ping: string }> = {
  green:  { dot: 'bg-emerald-400', ping: 'bg-emerald-400' },
  amber:  { dot: 'bg-amber-400',   ping: 'bg-amber-400' },
  red:    { dot: 'bg-red-400',     ping: 'bg-red-400' },
  blue:   { dot: 'bg-sky-400',     ping: 'bg-sky-400' },
  gray:   { dot: 'bg-slate-500',   ping: 'bg-slate-500' },
}

interface PulsingDotProps {
  color?: Color
  size?: 'sm' | 'md'
}

export default function PulsingDot({ color = 'green', size = 'sm' }: PulsingDotProps) {
  const { dot, ping } = colorMap[color]
  const sz = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3'

  return (
    <span className="relative flex items-center justify-center">
      <span className={`animate-ping-dot absolute inline-flex rounded-full ${ping} ${sz} opacity-60`} />
      <span className={`relative inline-flex rounded-full ${dot} ${sz}`} />
    </span>
  )
}

'use client'

interface GaugeRingProps {
  value: 0 | 1 | 2
  size?: number
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444'] // low, medium, high

export default function GaugeRing({ value, size = 160 }: GaugeRingProps) {
  const strokeWidth = 12
  const r = (size - strokeWidth * 2) / 2
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * r
  const arcDegrees = 240
  const arcLength = (arcDegrees / 360) * circumference
  const fillRatio = (value + 1) / 3
  const fillLength = fillRatio * arcLength
  const rotationDeg = 150

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label={`Fatigue level: ${['LOW', 'MEDIUM', 'HIGH'][value]}`}
    >
      {/* Track arc */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="rgba(148,163,184,0.15)"
        strokeWidth={strokeWidth}
        strokeDasharray={`${arcLength} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(${rotationDeg}, ${cx}, ${cy})`}
      />
      {/* Fill arc */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={COLORS[value]}
        strokeWidth={strokeWidth}
        strokeDasharray={`${fillLength} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(${rotationDeg}, ${cx}, ${cy})`}
        style={{
          transition: 'stroke-dasharray 0.6s ease, stroke 0.4s ease',
          filter: `drop-shadow(0 0 6px ${COLORS[value]}80)`,
        }}
      />
      {/* Tick marks at LOW/MEDIUM/HIGH boundaries */}
      {[1 / 3, 2 / 3].map((ratio, i) => {
        const angle = ((rotationDeg + arcDegrees * ratio) * Math.PI) / 180
        const innerR = r - strokeWidth / 2 - 4
        const outerR = r + strokeWidth / 2 + 2
        return (
          <line
            key={i}
            x1={cx + innerR * Math.cos(angle)}
            y1={cy + innerR * Math.sin(angle)}
            x2={cx + outerR * Math.cos(angle)}
            y2={cy + outerR * Math.sin(angle)}
            stroke="rgba(148,163,184,0.3)"
            strokeWidth={2}
          />
        )
      })}
    </svg>
  )
}

type Variant =
  | 'good' | 'bad' | 'absent'
  | 'low' | 'medium' | 'high'
  | 'idle' | 'speaking' | 'alert'
  | 'connected' | 'connecting' | 'disconnected' | 'error'

const variantStyles: Record<Variant, string> = {
  good:         'bg-cyan-400/15 text-cyan-300 border-cyan-400/30',
  bad:          'bg-amber-400/15 text-amber-300 border-amber-400/30',
  absent:       'bg-slate-700/40 text-slate-400 border-slate-600/30',
  low:          'bg-emerald-400/15 text-emerald-300 border-emerald-400/30',
  medium:       'bg-amber-400/15 text-amber-300 border-amber-400/30',
  high:         'bg-red-400/15 text-red-300 border-red-400/30',
  idle:         'bg-slate-700/40 text-slate-400 border-slate-600/30',
  speaking:     'bg-sky-400/15 text-sky-300 border-sky-400/30',
  alert:        'bg-red-400/15 text-red-300 border-red-400/30',
  connected:    'bg-emerald-400/15 text-emerald-300 border-emerald-400/30',
  connecting:   'bg-amber-400/15 text-amber-300 border-amber-400/30',
  disconnected: 'bg-red-400/15 text-red-300 border-red-400/30',
  error:        'bg-red-400/15 text-red-300 border-red-400/30',
}

interface StatusBadgeProps {
  label: string
  variant: Variant
}

export default function StatusBadge({ label, variant }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border font-display tracking-wide ${variantStyles[variant]}`}
    >
      {label}
    </span>
  )
}

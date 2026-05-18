interface StatCardProps {
  label: string
  value: string
  unit?: string
  accent?: string
}

export default function StatCard({ label, value, unit, accent }: StatCardProps) {
  return (
    <div className={`bg-slate-800/60 border border-slate-700/50 rounded-lg p-3 flex flex-col gap-1 ${accent ? `border-t-2 border-t-[${accent}]` : ''}`}>
      <span className="text-slate-500 text-xs font-display uppercase tracking-wider">{label}</span>
      <span className="text-slate-100 text-sm font-data font-bold">
        {value}
        {unit && <span className="text-slate-500 text-xs ml-1 font-display font-normal">{unit}</span>}
      </span>
    </div>
  )
}

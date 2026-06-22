export function parseServerDt(dt: string): Date {
  const hasOffset = dt.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dt)
  return new Date(hasOffset ? dt : dt + 'Z')
}

export function formatDateTime(dt: string): string {
  const d = parseServerDt(dt)
  const today = new Date()
  const toMidnight = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate())
  const diffDays = Math.round((toMidnight(d).getTime() - toMidnight(today).getTime()) / 86_400_000)
  const dateLabel =
    diffDays === -1 ? 'Yesterday' :
    diffDays === 0  ? 'Today' :
    diffDays === 1  ? 'Tomorrow' :
    d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  return `${dateLabel}, ${time}`
}

import type { Match } from '../types'

export function groupByStage(matches: Match[]): Map<string, Match[]> {
  const map = new Map<string, Match[]>()
  for (const m of matches) {
    const key = m.stage_name ?? 'Unknown Stage'
    const group = map.get(key) ?? []
    group.push(m)
    map.set(key, group)
  }
  return map
}

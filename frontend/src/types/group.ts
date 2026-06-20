import type { TeamRead } from './team'

export interface Group {
  id: number
  name: string
  tournament_id: number
  winner_team_id: number | null
  winner: TeamRead | null
  start_date: string | null
  end_date: string | null
}

export interface GroupCreate {
  name: string
  tournament_id: number
  winner_team_id?: number
}

export type GroupUpdate = Partial<Omit<GroupCreate, 'tournament_id'>>

export interface Stage {
  id: number
  name: string
  tournament_id: number
  winner_team_id: number | null
  winner: TeamRead | null
  start_date: string | null
  end_date: string | null
}

export interface StageCreate {
  name: string
  tournament_id: number
  winner_team_id?: number
}

export interface StageUpdate {
  name?: string
  winner_team_id?: number | null
}

import type { TeamRead } from './team'

export interface StageRead {
  id: number
  name: string
  tournament_id: number
  winner_team_id: number | null
  winner_points: number | null
}

export interface Match {
  id: number
  tournament_id: number | null
  home_team_id: number | null
  away_team_id: number | null
  stage_id: number | null
  start_datetime: string
  home_goals: number | null
  away_goals: number | null
  football_data_org_id: number | null
  home_team: TeamRead | null
  away_team: TeamRead | null
  stage_name: string | null
  tv_channel: string | null
}

export interface MatchCreate {
  tournament_id: number
  start_datetime: string
  home_team_id?: number
  away_team_id?: number
  stage_id?: number
  home_goals?: number
  away_goals?: number
  football_data_org_id?: number
  tv_channel?: string
}

export interface MatchUpdate extends Partial<Omit<MatchCreate, 'tournament_id' | 'home_goals' | 'away_goals' | 'tv_channel'>> {
  home_goals?: number | null
  away_goals?: number | null
  tv_channel?: string | null
}

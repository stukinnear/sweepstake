import type { TeamRead } from './team'

export type PredictionsOpen = 'automatic' | 'open' | 'closed'

export interface ProviderTournament {
  id: string
  name: string
  area: string | null
  current_season_start: string | null
  current_season_end: string | null
  emblem_url: string | null
  provider: 'football-data-org' | 'thesportsdb' | string
}


export interface TournamentUser {
  id: number
  user_name: string | null
  stake_paid: boolean
}

export interface Tournament {
  id: number
  name: string
  stake: string | null
  join_code: string | null
  external_provider: string | null
  external_id: string | null
  first_place_team_id: number | null
  second_place_team_id: number | null
  third_place_team_id: number | null
  first_place_points: number | null
  second_place_points: number | null
  third_place_points: number | null
  match_winner_points: number | null
  match_score_points: number | null
  group_winner_points: number | null
  stage_winner_points: number | null
  predictions_open: PredictionsOpen
  provider_update_status: string | null
  provider_update_message: string | null
  provider_updated_at: string | null
  provider_update_match_count: number | null
  provider_update_team_count: number | null
  admin_lst: TournamentUser[]
  participant_lst: TournamentUser[]
  start_date: string | null
  end_date: string | null
  first_place: TeamRead | null
  second_place: TeamRead | null
  third_place: TeamRead | null
}

export interface TournamentCreate {
  name: string
  stake?: string | null
  external_provider?: string | null
  external_id?: string | null
  first_place_team_id?: number
  second_place_team_id?: number
  third_place_team_id?: number
  first_place_points?: number
  second_place_points?: number
  third_place_points?: number
  match_winner_points?: number
  match_score_points?: number
  group_winner_points?: number | null
  stage_winner_points?: number | null
  predictions_open?: PredictionsOpen
}

export type TournamentUpdate = Partial<TournamentCreate>

export interface TournamentMemberUpdate {
  user_id: number
  role: 'admin' | 'participant'
  action: 'add' | 'remove'
}

export interface TournamentStakePaidUpdate {
  user_id: number
  stake_paid: boolean
}

export type TournamentAdminAction =
  | 'send-payment-reminder'
  | 'update-tournament'
  | 'send-welcome-email'

export interface TournamentAdminActionRequest {
  action: TournamentAdminAction
}

import type { TeamRead } from './team'

export interface LeaderboardEntry {
  rank: number
  user_id: number
  user_name: string | null
  total_points: number
}

export interface UserPredictionMatch {
  user_id: number
  user_name: string | null
  home_score: number | null
  away_score: number | null
  points_earned: number | null
}

export interface MatchStats {
  match_id: number
  start_datetime: string | null
  home_goals: number | null
  away_goals: number | null
  predictions: UserPredictionMatch[]
}

export interface WinnerPredictionUser {
  user_id: number
  user_name: string | null
  points_earned: number | null
}

/** Flattened TeamRead fields + users who predicted that team. All team fields are
 *  nullable to accommodate the no-prediction bucket (users who made no prediction). */
export interface WinnerPredictionGroup {
  id: number | null
  name: string | null
  iso_code: string | null
  image_url: string | null
  football_data_org_id: number | null
  group_id: number | null
  tournament_id: number | null
  group_name: string | null
  users: WinnerPredictionUser[]
}

export interface GroupStats {
  group_id: number
  actual_winner_team_id: number | null
  actual_winner_team: TeamRead | null
  predictions: WinnerPredictionGroup[]
}

export interface StageStats {
  stage_id: number
  actual_winner_team_id: number | null
  actual_winner_team: TeamRead | null
  predictions: WinnerPredictionGroup[]
}

export interface TournamentStats {
  tournament_id: number
  first_place_team_id: number | null
  first_place_team: TeamRead | null
  second_place_team_id: number | null
  second_place_team: TeamRead | null
  third_place_team_id: number | null
  third_place_team: TeamRead | null
  predictions: WinnerPredictionGroup[]
}

export interface ParticipantActivity {
  user_id: number
  user_name: string | null
  tournament_predictions: number
  group_predictions: number
  stage_predictions: number
  match_predictions: number
}

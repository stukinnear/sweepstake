import type { TeamRead } from './team'

// Tournament predictions
export interface TournamentPrediction {
  tournament_id: number
  user_id: number
  winner_team_id: number | null
  winner_team: TeamRead | null
  points_earned: number | null
}

export interface TournamentPredictionUpsert {
  tournament_id: number
  winner_team_id?: number
}

// Group predictions
export interface GroupPrediction {
  group_id: number
  user_id: number
  winner_team_id: number | null
  winner_team: TeamRead | null
  points_earned: number | null
}

export interface GroupPredictionUpsert {
  group_id: number
  winner_team_id?: number
}

// Stage predictions
export interface StagePrediction {
  stage_id: number
  user_id: number
  winner_team_id: number | null
  winner_team: TeamRead | null
  points_earned: number | null
}

export interface StagePredictionUpsert {
  stage_id: number
  winner_team_id?: number
}

// Match predictions
export interface MatchPrediction {
  match_id: number
  user_id: number
  home_score: number | null
  away_score: number | null
  points_earned: number | null
}

export interface MatchPredictionUpsert {
  match_id: number
  home_score?: number
  away_score?: number
}

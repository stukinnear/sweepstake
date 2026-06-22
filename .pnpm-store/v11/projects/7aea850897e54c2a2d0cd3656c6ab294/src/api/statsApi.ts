import { baseApi, addPolling } from './baseApi'
import type { LeaderboardEntry, MatchStats, GroupStats, StageStats, TournamentStats, ParticipantActivity } from '../types'

export const statsApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    getLeaderboard: build.query<LeaderboardEntry[], number>({
      query: (tournamentId) => `/stats/leaderboard/${tournamentId}`,
      providesTags: (_result, _error, tournamentId) => [{ type: 'Leaderboard', id: tournamentId }],
      keepUnusedDataFor: 60 * 60 * 3,
    }),
    getMatchStats: build.query<MatchStats, number>({
      query: (matchId) => `/stats/match/${matchId}`,
      providesTags: (_result, _error, matchId) => [{ type: 'MatchStats', id: matchId }],
      keepUnusedDataFor: 60 * 60 * 3,
    }),
    getGroupStats: build.query<GroupStats, number>({
      query: (groupId) => `/stats/group/${groupId}`,
      providesTags: (_result, _error, groupId) => [{ type: 'GroupStats', id: groupId }],
      keepUnusedDataFor: 60 * 60 * 3,
    }),
    getStageStats: build.query<StageStats, number>({
      query: (stageId) => `/stats/stage/${stageId}`,
      providesTags: (_result, _error, stageId) => [{ type: 'StageStats', id: stageId }],
      keepUnusedDataFor: 60 * 60 * 3,
    }),
    getTournamentStats: build.query<TournamentStats, number>({
      query: (tournamentId) => `/stats/tournament/${tournamentId}`,
      providesTags: (_result, _error, tournamentId) => [{ type: 'TournamentStats', id: tournamentId }],
      keepUnusedDataFor: 60 * 60 * 3,
    }),
    getParticipantActivity: build.query<ParticipantActivity[], number>({
      query: (tournamentId) => `/stats/participant-activity/${tournamentId}`,
      providesTags: (_result, _error, tournamentId) => [{ type: 'Leaderboard', id: tournamentId }],
      keepUnusedDataFor: 60 * 5,
    }),
  }),
})

const {
  useGetLeaderboardQuery: _useGetLeaderboardQuery,
  useGetMatchStatsQuery: _useGetMatchStatsQuery,
  useGetGroupStatsQuery: _useGetGroupStatsQuery,
  useGetStageStatsQuery: _useGetStageStatsQuery,
  useGetTournamentStatsQuery: _useGetTournamentStatsQuery,
  useGetParticipantActivityQuery: _useGetParticipantActivityQuery,
} = statsApi

export const useGetLeaderboardQuery = addPolling(_useGetLeaderboardQuery, 60 * 3 * 1000)
export const useGetMatchStatsQuery = addPolling(_useGetMatchStatsQuery, 60 * 3 * 1000)
export const useGetGroupStatsQuery = addPolling(_useGetGroupStatsQuery, 60 * 3 * 1000)
export const useGetStageStatsQuery = addPolling(_useGetStageStatsQuery, 60 * 3 * 1000)
export const useGetTournamentStatsQuery = addPolling(_useGetTournamentStatsQuery, 60 * 3 * 1000)
export const useGetParticipantActivityQuery = addPolling(_useGetParticipantActivityQuery, 60 * 5 * 1000)

import { baseApi, addPolling } from './baseApi'
import type {
  TournamentPrediction,
  TournamentPredictionUpsert,
  GroupPrediction,
  GroupPredictionUpsert,
  StagePrediction,
  StagePredictionUpsert,
  MatchPrediction,
  MatchPredictionUpsert,
} from '../types'

// Tournament predictions
export const tournamentPredictionApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    upsertTournamentPrediction: build.mutation<TournamentPrediction, TournamentPredictionUpsert & { userId?: number }>({
      query: ({ userId, ...body }) => ({ url: '/predict/tournament', method: 'POST', body, params: userId !== undefined ? { user_id: userId } : undefined }),
      async onQueryStarted({ tournament_id }, { dispatch, queryFulfilled }) {
        try {
          const { data: p } = await queryFulfilled
          const patch = (args: { tournamentId: number; userId?: number }) =>
            dispatch(tournamentPredictionApi.util.updateQueryData('getTournamentPredictions', args, (draft) => {
              const i = draft.findIndex((x) => x.user_id === p.user_id)
              if (i >= 0) draft[i] = p; else draft.push(p)
            }))
          patch({ tournamentId: tournament_id })
          patch({ tournamentId: tournament_id, userId: p.user_id })
        } catch { /* ignore */ }
      },
    }),
    getTournamentPredictions: build.query<TournamentPrediction[], { tournamentId: number; userId?: number }>({
      query: ({ tournamentId, userId }) => ({ url: `/predict/tournament/${tournamentId}`, params: userId !== undefined ? { user_id: userId } : undefined }),
      providesTags: (result, _error, { tournamentId, userId }) => [
        { type: 'TournamentPrediction' as const, id: `LIST-${tournamentId}` },
        ...(result ? result.map((p) => ({ type: 'TournamentPrediction' as const, id: `${p.user_id}-${p.tournament_id}` })) : [{ type: 'TournamentPrediction' as const, id: `${userId}-${tournamentId}` }]),
      ],
    }),
    deleteTournamentPrediction: build.mutation<void, { tournamentId: number; userId?: number }>({
      query: ({ tournamentId, userId }) => ({ url: `/predict/tournament/${tournamentId}`, method: 'DELETE', params: userId !== undefined ? { user_id: userId } : undefined }),
      invalidatesTags: (_result, _error, { tournamentId, userId }) => [{ type: 'TournamentPrediction', id: `${userId}-${tournamentId}` }],
    }),
  }),
})

const {
  useUpsertTournamentPredictionMutation,
  useGetTournamentPredictionsQuery: _useGetTournamentPredictionsQuery,
  useDeleteTournamentPredictionMutation,
} = tournamentPredictionApi

export const useGetTournamentPredictionsQuery = addPolling(_useGetTournamentPredictionsQuery, 60 * 60 * 1000)
export { useUpsertTournamentPredictionMutation, useDeleteTournamentPredictionMutation }

// Group predictions
export const groupPredictionApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    upsertGroupPrediction: build.mutation<GroupPrediction, GroupPredictionUpsert & { userId?: number; tournamentId?: number }>({
      query: ({ userId, tournamentId: _tournamentId, ...body }) => ({ url: '/predict/group', method: 'POST', body, params: userId !== undefined ? { user_id: userId } : undefined }),
      async onQueryStarted({ tournamentId }, { dispatch, queryFulfilled }) {
        if (tournamentId === undefined) return
        try {
          const { data: p } = await queryFulfilled
          const patch = (args: { tournamentId: number; userId?: number }) =>
            dispatch(groupPredictionApi.util.updateQueryData('listGroupPredictions', args, (draft) => {
              const i = draft.findIndex((x) => x.group_id === p.group_id && x.user_id === p.user_id)
              if (i >= 0) draft[i] = p; else draft.push(p)
            }))
          patch({ tournamentId })
          patch({ tournamentId, userId: p.user_id })
        } catch { /* ignore */ }
      },
    }),
    getGroupPredictions: build.query<GroupPrediction[], { groupId: number; userId?: number }>({
      query: ({ groupId, userId }) => ({ url: `/predict/group/${groupId}`, params: userId !== undefined ? { user_id: userId } : undefined }),
      providesTags: (result, _error, { groupId, userId }) => result ? result.map((p) => ({ type: 'GroupPrediction' as const, id: `${p.user_id}-${p.group_id}` })) : [{ type: 'GroupPrediction' as const, id: `${userId}-${groupId}` }],
    }),
    listGroupPredictions: build.query<GroupPrediction[], { tournamentId: number; userId?: number }>({
      query: ({ tournamentId, userId }) => ({ url: '/predict/group', params: { tournament_id: tournamentId, ...(userId !== undefined ? { user_id: userId } : {}) } }),
      providesTags: (result, _error, { tournamentId, userId }) => [
        { type: 'GroupPrediction' as const, id: `LIST-${tournamentId}` },
        ...(result ? result.map((p) => ({ type: 'GroupPrediction' as const, id: `${p.user_id}-${p.group_id}` })) : [{ type: 'GroupPrediction' as const, id: `${userId}-${tournamentId}` }]),
      ],
    }),
  }),
})

const {
  useUpsertGroupPredictionMutation,
  useGetGroupPredictionsQuery: _useGetGroupPredictionsQuery,
  useListGroupPredictionsQuery: _useListGroupPredictionsQuery,
} = groupPredictionApi

export const useGetGroupPredictionsQuery = addPolling(_useGetGroupPredictionsQuery, 60 * 60 * 1000)
export const useListGroupPredictionsQuery = addPolling(_useListGroupPredictionsQuery, 60 * 60 * 1000)
export { useUpsertGroupPredictionMutation }

// Stage predictions
export const stagePredictionApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    upsertStagePrediction: build.mutation<StagePrediction, StagePredictionUpsert & { userId?: number; tournamentId?: number }>({
      query: ({ userId, tournamentId: _tournamentId, ...body }) => ({ url: '/predict/stage', method: 'POST', body, params: userId !== undefined ? { user_id: userId } : undefined }),
      async onQueryStarted({ tournamentId }, { dispatch, queryFulfilled }) {
        if (tournamentId === undefined) return
        try {
          const { data: p } = await queryFulfilled
          const patch = (args: { tournamentId: number; userId?: number }) =>
            dispatch(stagePredictionApi.util.updateQueryData('listStagePredictions', args, (draft) => {
              const i = draft.findIndex((x) => x.stage_id === p.stage_id && x.user_id === p.user_id)
              if (i >= 0) draft[i] = p; else draft.push(p)
            }))
          patch({ tournamentId })
          patch({ tournamentId, userId: p.user_id })
        } catch { /* ignore */ }
      },
    }),
    getStagePredictions: build.query<StagePrediction[], { stageId: number; userId?: number }>({
      query: ({ stageId, userId }) => ({ url: `/predict/stage/${stageId}`, params: userId !== undefined ? { user_id: userId } : undefined }),
      providesTags: (result, _error, { stageId, userId }) => result ? result.map((p) => ({ type: 'StagePrediction' as const, id: `${p.user_id}-${p.stage_id}` })) : [{ type: 'StagePrediction' as const, id: `${userId}-${stageId}` }],
    }),
    listStagePredictions: build.query<StagePrediction[], { tournamentId: number; userId?: number }>({
      query: ({ tournamentId, userId }) => ({ url: '/predict/stage', params: { tournament_id: tournamentId, ...(userId !== undefined ? { user_id: userId } : {}) } }),
      providesTags: (result, _error, { tournamentId, userId }) => [
        { type: 'StagePrediction' as const, id: `LIST-${tournamentId}` },
        ...(result ? result.map((p) => ({ type: 'StagePrediction' as const, id: `${p.user_id}-${p.stage_id}` })) : [{ type: 'StagePrediction' as const, id: `${userId}-${tournamentId}` }]),
      ],
    }),
  }),
})

const {
  useUpsertStagePredictionMutation,
  useGetStagePredictionsQuery: _useGetStagePredictionsQuery,
  useListStagePredictionsQuery: _useListStagePredictionsQuery,
} = stagePredictionApi

export const useGetStagePredictionsQuery = addPolling(_useGetStagePredictionsQuery, 60 * 60 * 1000)
export const useListStagePredictionsQuery = addPolling(_useListStagePredictionsQuery, 60 * 60 * 1000)
export { useUpsertStagePredictionMutation }

// Match predictions
export const matchPredictionApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    upsertMatchPrediction: build.mutation<MatchPrediction, MatchPredictionUpsert & { userId?: number; tournamentId?: number }>({
      query: ({ userId, tournamentId: _tournamentId, ...body }) => ({ url: '/predict/match', method: 'POST', body, params: userId !== undefined ? { user_id: userId } : undefined }),
      async onQueryStarted({ tournamentId }, { dispatch, queryFulfilled }) {
        if (tournamentId === undefined) return
        try {
          const { data: p } = await queryFulfilled
          const patch = (args: { tournamentId: number; userId?: number }) =>
            dispatch(matchPredictionApi.util.updateQueryData('listMatchPredictions', args, (draft) => {
              const i = draft.findIndex((x) => x.match_id === p.match_id && x.user_id === p.user_id)
              if (i >= 0) draft[i] = p; else draft.push(p)
            }))
          patch({ tournamentId })
          patch({ tournamentId, userId: p.user_id })
        } catch { /* ignore */ }
      },
    }),
    getMatchPredictions: build.query<MatchPrediction[], { matchId: number; userId?: number }>({
      query: ({ matchId, userId }) => ({ url: `/predict/match/${matchId}`, params: userId !== undefined ? { user_id: userId } : undefined }),
      providesTags: (result, _error, { matchId, userId }) => result ? result.map((p) => ({ type: 'MatchPrediction' as const, id: `${p.user_id}-${p.match_id}` })) : [{ type: 'MatchPrediction' as const, id: `${userId}-${matchId}` }],
    }),
    listMatchPredictions: build.query<MatchPrediction[], { tournamentId: number; userId?: number }>({
      query: ({ tournamentId, userId }) => ({ url: '/predict/match', params: { tournament_id: tournamentId, ...(userId !== undefined ? { user_id: userId } : {}) } }),
      providesTags: (result, _error, { tournamentId, userId }) => [
        { type: 'MatchPrediction' as const, id: `LIST-${tournamentId}` },
        ...(result ? result.map((p) => ({ type: 'MatchPrediction' as const, id: `${p.user_id}-${p.match_id}` })) : [{ type: 'MatchPrediction' as const, id: `${userId}-${tournamentId}` }]),
      ],
    }),
  }),
})

const {
  useUpsertMatchPredictionMutation,
  useGetMatchPredictionsQuery: _useGetMatchPredictionsQuery,
  useListMatchPredictionsQuery: _useListMatchPredictionsQuery,
} = matchPredictionApi

export const useGetMatchPredictionsQuery = addPolling(_useGetMatchPredictionsQuery, 60 * 60 * 1000)
export const useListMatchPredictionsQuery = addPolling(_useListMatchPredictionsQuery, 60 * 60 * 1000)
export { useUpsertMatchPredictionMutation }

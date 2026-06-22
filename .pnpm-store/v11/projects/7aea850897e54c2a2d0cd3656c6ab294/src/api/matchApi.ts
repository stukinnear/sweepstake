import { baseApi, addPolling } from './baseApi'
import type { Match, MatchCreate, MatchUpdate } from '../types'

export const matchApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listMatches: build.query<Match[], number>({
      query: (tournamentId) => `/match?tournament_id=${tournamentId}`,
      providesTags: (result) =>
        result
          ? [...result.map(({ id }) => ({ type: 'Match' as const, id })), { type: 'Match' as const, id: 'LIST' }]
          : [{ type: 'Match' as const, id: 'LIST' }],
    }),

    getMatch: build.query<Match, number>({
      query: (id) => `/match/${id}`,
      providesTags: (_result, _err, id) => [{ type: 'Match', id }],
    }),

    createMatch: build.mutation<Match, MatchCreate>({
      query: (body) => ({ url: '/match', method: 'POST', body }),
      async onQueryStarted(body, { dispatch, queryFulfilled }) {
        const { data: newMatch } = await queryFulfilled
        dispatch(
          matchApi.util.updateQueryData('listMatches', body.tournament_id, (draft) => {
            draft.push(newMatch)
          })
        )
      },
    }),

    updateMatch: build.mutation<Match, { id: number; tournamentId: number; data: MatchUpdate }>({
      query: ({ id, data }) => ({ url: `/match/${id}`, method: 'PATCH', body: data }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          matchApi.util.updateQueryData('listMatches', tournamentId, (draft) => {
            const i = draft.findIndex((m) => m.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
      },
    }),

    deleteMatch: build.mutation<void, { id: number; tournamentId: number }>({
      query: ({ id }) => ({ url: `/match/${id}`, method: 'DELETE' }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          matchApi.util.updateQueryData('listMatches', tournamentId, (draft) => {
            const i = draft.findIndex((m) => m.id === id)
            if (i !== -1) draft.splice(i, 1)
          })
        )
        try { await queryFulfilled }
        catch { patch.undo() }
      },
    }),
  }),
})

const {
  useListMatchesQuery: _useListMatchesQuery,
  useGetMatchQuery: _useGetMatchQuery,
  useCreateMatchMutation,
  useUpdateMatchMutation,
  useDeleteMatchMutation,
} = matchApi

export const useListMatchesQuery = addPolling(_useListMatchesQuery, 60 * 60 * 1000)
export const useGetMatchQuery = addPolling(_useGetMatchQuery, 60 * 60 * 1000)

export { useCreateMatchMutation, useUpdateMatchMutation, useDeleteMatchMutation }

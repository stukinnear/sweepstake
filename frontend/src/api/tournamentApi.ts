import { baseApi, addPolling } from './baseApi'
import type { Tournament, TournamentCreate, TournamentUpdate, TournamentMemberUpdate, TournamentStakePaidUpdate, TournamentAdminAction } from '../types'

export const tournamentApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listTournaments: build.query<Tournament[], void>({
      query: () => '/tournament',
      providesTags: (result) =>
        result ? [...result.map(({ id }) => ({ type: 'Tournament' as const, id }))] : [{ type: 'Tournament', id: 'undefined' }],
    }),

    getTournament: build.query<Tournament, number>({
      query: (id) => `/tournament/${id}`,
      providesTags: (_result, _err, id) => [{ type: 'Tournament', id }],
    }),

    createTournament: build.mutation<Tournament, TournamentCreate>({
      query: (body) => ({ url: '/tournament', method: 'POST', body }),
      async onQueryStarted(_body, { dispatch, queryFulfilled }) {
        const { data: newTournament } = await queryFulfilled
        dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            draft.push(newTournament)
          })
        )
      },
    }),

    updateTournament: build.mutation<Tournament, { id: number; data: TournamentUpdate }>({
      query: ({ id, data }) => ({ url: `/tournament/${id}`, method: 'PATCH', body: data }),
      async onQueryStarted({ id }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
        dispatch(tournamentApi.util.updateQueryData('getTournament', id, () => updated))
      },
    }),

    deleteTournament: build.mutation<void, number>({
      query: (id) => ({ url: `/tournament/${id}`, method: 'DELETE' }),
      async onQueryStarted(id, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
            if (i !== -1) draft.splice(i, 1)
          })
        )
        try { await queryFulfilled }
        catch { patch.undo() }
      },
    }),

    manageTournamentMember: build.mutation<Tournament | void, { id: number; data: TournamentMemberUpdate }>({
      query: ({ id, data }) => ({ url: `/tournament/${id}/members`, method: 'PATCH', body: data }),
      async onQueryStarted({ id }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        if (!updated) return
        dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
        dispatch(tournamentApi.util.updateQueryData('getTournament', id, () => updated))
      },
    }),

    setStakePaid: build.mutation<Tournament, { id: number; data: TournamentStakePaidUpdate }>({
      query: ({ id, data }) => ({ url: `/tournament/${id}/stake-paid`, method: 'PATCH', body: data }),
      async onQueryStarted({ id }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
        dispatch(tournamentApi.util.updateQueryData('getTournament', id, () => updated))
      },
    }),

    joinTournament: build.mutation<Tournament, string>({
      query: (join_code) => ({ url: `/tournament/join/${join_code}`, method: 'POST' }),
      async onQueryStarted(_join_code, { dispatch, queryFulfilled }) {
        const { data: newTournament } = await queryFulfilled
        dispatch(
          tournamentApi.util.updateQueryData('listTournaments', undefined, (draft) => {
            if (!draft.find((t) => t.id === newTournament.id)) draft.push(newTournament)
          })
        )
      },
    }),

    sendAdminAction: build.mutation<void, { id: number; action: TournamentAdminAction }>({
      query: ({ id, action }) => ({ url: `/tournament/${id}/action`, method: 'POST', body: { action } }),
    }),
  }),
})

const {
  useListTournamentsQuery: _useListTournamentsQuery,
  useGetTournamentQuery: _useGetTournamentQuery,
  useCreateTournamentMutation,
  useUpdateTournamentMutation,
  useDeleteTournamentMutation,
  useManageTournamentMemberMutation,
  useSetStakePaidMutation,
  useJoinTournamentMutation,
  useSendAdminActionMutation,
} = tournamentApi

export const useListTournamentsQuery = addPolling(_useListTournamentsQuery, 60 * 60 * 1000)
export const useGetTournamentQuery = addPolling(_useGetTournamentQuery, 60 * 60 * 1000)

export {
  useCreateTournamentMutation,
  useUpdateTournamentMutation,
  useDeleteTournamentMutation,
  useManageTournamentMemberMutation,
  useSetStakePaidMutation,
  useJoinTournamentMutation,
  useSendAdminActionMutation,
}

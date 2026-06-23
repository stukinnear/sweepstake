import { baseApi, addPolling } from './baseApi'
import type { Team, TeamCreate, TeamUpdate } from '../types'

export const teamApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listTeams: build.query<Team[], number>({
      query: (tournamentId) => `/team?tournament_id=${tournamentId}`,
      providesTags: (result) =>
        result
          ? [...result.map(({ id }) => ({ type: 'Team' as const, id })), { type: 'Team' as const, id: 'LIST' }]
          : [{ type: 'Team' as const, id: 'LIST' }],
    }),

    getTeam: build.query<Team, number>({
      query: (id) => `/team/${id}`,
      providesTags: (_result, _err, id) => [{ type: 'Team', id }],
    }),

    createTeam: build.mutation<Team, TeamCreate>({
      query: (body) => ({ url: '/team', method: 'POST', body }),
      async onQueryStarted(body, { dispatch, queryFulfilled }) {
        const { data: newTeam } = await queryFulfilled
        dispatch(
          teamApi.util.updateQueryData('listTeams', body.tournament_id, (draft) => {
            draft.push(newTeam)
          })
        )
      },
    }),

    updateTeam: build.mutation<Team, { id: number; tournamentId: number; data: TeamUpdate }>({
      query: ({ id, data }) => ({ url: `/team/${id}`, method: 'PATCH', body: data }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          teamApi.util.updateQueryData('listTeams', tournamentId, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
      },
    }),

    deleteTeam: build.mutation<void, { id: number; tournamentId: number }>({
      query: ({ id }) => ({ url: `/team/${id}`, method: 'DELETE' }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          teamApi.util.updateQueryData('listTeams', tournamentId, (draft) => {
            const i = draft.findIndex((t) => t.id === id)
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
  useListTeamsQuery: _useListTeamsQuery,
  useGetTeamQuery: _useGetTeamQuery,
  useCreateTeamMutation,
  useUpdateTeamMutation,
  useDeleteTeamMutation,
} = teamApi

export const useListTeamsQuery = addPolling(_useListTeamsQuery, 60 * 60 * 1000)
export const useGetTeamQuery = addPolling(_useGetTeamQuery, 60 * 60 * 1000)

export { useCreateTeamMutation, useUpdateTeamMutation, useDeleteTeamMutation }


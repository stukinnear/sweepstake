import { baseApi, addPolling } from './baseApi'
import type { Group, GroupCreate, GroupUpdate, Stage, StageCreate, StageUpdate } from '../types'

export const groupApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    // Groups
    listGroups: build.query<Group[], number>({
      query: (tournamentId) => `/group?tournament_id=${tournamentId}`,
      providesTags: (result) =>
        result ? [...result.map(({ id }) => ({ type: 'Group' as const, id }))] : [{ type: 'Group', id: 'undefined' }],
    }),

    getGroup: build.query<Group, number>({
      query: (id) => `/group/${id}`,
      providesTags: (_result, _err, id) => [{ type: 'Group', id }],
    }),

    createGroup: build.mutation<Group, GroupCreate>({
      query: (body) => ({ url: '/group', method: 'POST', body }),
      async onQueryStarted(body, { dispatch, queryFulfilled }) {
        const { data: newGroup } = await queryFulfilled
        dispatch(
          groupApi.util.updateQueryData('listGroups', body.tournament_id, (draft) => {
            draft.push(newGroup)
          })
        )
      },
    }),

    updateGroup: build.mutation<Group, { id: number; tournamentId: number; data: GroupUpdate }>({
      query: ({ id, data }) => ({ url: `/group/${id}`, method: 'PATCH', body: data }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          groupApi.util.updateQueryData('listGroups', tournamentId, (draft) => {
            const i = draft.findIndex((g) => g.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
      },
    }),

    deleteGroup: build.mutation<void, { id: number; tournamentId: number }>({
      query: ({ id }) => ({ url: `/group/${id}`, method: 'DELETE' }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          groupApi.util.updateQueryData('listGroups', tournamentId, (draft) => {
            const i = draft.findIndex((g) => g.id === id)
            if (i !== -1) draft.splice(i, 1)
          })
        )
        try { await queryFulfilled }
        catch { patch.undo() }
      },
    }),

    // Stages
    listStages: build.query<Stage[], number>({
      query: (tournamentId) => `/stage?tournament_id=${tournamentId}`,
      providesTags: (result) =>
        result ? [...result.map(({ id }) => ({ type: 'Stage' as const, id }))] : [{ type: 'Stage', id: 'undefined' }],
    }),

    getStage: build.query<Stage, number>({
      query: (id) => `/stage/${id}`,
      providesTags: (_result, _err, id) => [{ type: 'Stage', id }],
    }),

    createStage: build.mutation<Stage, StageCreate>({
      query: (body) => ({ url: '/stage', method: 'POST', body }),
      async onQueryStarted(body, { dispatch, queryFulfilled }) {
        const { data: newStage } = await queryFulfilled
        dispatch(
          groupApi.util.updateQueryData('listStages', body.tournament_id, (draft) => {
            draft.push(newStage)
          })
        )
      },
    }),

    updateStage: build.mutation<Stage, { id: number; tournamentId: number; data: StageUpdate }>({
      query: ({ id, data }) => ({ url: `/stage/${id}`, method: 'PATCH', body: data }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const { data: updated } = await queryFulfilled
        dispatch(
          groupApi.util.updateQueryData('listStages', tournamentId, (draft) => {
            const i = draft.findIndex((s) => s.id === id)
            if (i !== -1) draft[i] = updated
          })
        )
      },
    }),

    deleteStage: build.mutation<void, { id: number; tournamentId: number }>({
      query: ({ id }) => ({ url: `/stage/${id}`, method: 'DELETE' }),
      async onQueryStarted({ id, tournamentId }, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          groupApi.util.updateQueryData('listStages', tournamentId, (draft) => {
            const i = draft.findIndex((s) => s.id === id)
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
  useListGroupsQuery: _useListGroupsQuery,
  useGetGroupQuery: _useGetGroupQuery,
  useCreateGroupMutation,
  useUpdateGroupMutation,
  useDeleteGroupMutation,
  useListStagesQuery: _useListStagesQuery,
  useGetStageQuery: _useGetStageQuery,
  useCreateStageMutation,
  useUpdateStageMutation,
  useDeleteStageMutation,
} = groupApi

export const useListGroupsQuery = addPolling(_useListGroupsQuery, 60 * 60 * 1000)
export const useGetGroupQuery = addPolling(_useGetGroupQuery, 60 * 60 * 1000)
export const useListStagesQuery = addPolling(_useListStagesQuery, 60 * 60 * 1000)
export const useGetStageQuery = addPolling(_useGetStageQuery, 60 * 60 * 1000)

export {
  useCreateGroupMutation,
  useUpdateGroupMutation,
  useDeleteGroupMutation,
  useCreateStageMutation,
  useUpdateStageMutation,
  useDeleteStageMutation,
}

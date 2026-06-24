import { baseApi } from './baseApi'
import type { ProviderDiagnostics, ProviderTournament } from '../types'

export const providerApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listProviderTournaments: build.query<ProviderTournament[], void>({
      query: () => '/providers/tournaments',
    }),
    getProviderDiagnostics: build.query<ProviderDiagnostics, number>({
      query: (tournamentId) => `/providers/diagnostics/${tournamentId}`,
      providesTags: (_result, _error, tournamentId) => [
        { type: 'ProviderDiagnostics' as const, id: tournamentId },
      ],
    }),
  }),
})

export const { useListProviderTournamentsQuery, useGetProviderDiagnosticsQuery } = providerApi

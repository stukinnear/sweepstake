import { baseApi } from './baseApi'
import type { ProviderTournament } from '../types'

export const providerApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listProviderTournaments: build.query<ProviderTournament[], void>({
      query: () => '/providers/tournaments',
    }),
  }),
})

export const { useListProviderTournamentsQuery } = providerApi

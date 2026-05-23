import { baseApi } from './baseApi'
import type { FootballDataOrgTournament } from '../types'

export const footballDataOrgApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    listFootballDataOrgTournaments: build.query<FootballDataOrgTournament[], void>({
      query: () => '/football-data-org/tournaments',
    }),
  }),
})

export const { useListFootballDataOrgTournamentsQuery } = footballDataOrgApi

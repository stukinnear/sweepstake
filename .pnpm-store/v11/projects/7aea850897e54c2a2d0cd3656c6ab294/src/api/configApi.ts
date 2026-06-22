import { baseApi } from './baseApi'

export interface AppConfig {
  sentry_dsn: string
  app_version: string
  demo_mode: boolean
  only_superusers_can_create_tournaments: boolean
}

export const configApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    getConfig: build.query<AppConfig, void>({
      query: () => '/config',
    }),
  }),
})

export const { useGetConfigQuery } = configApi

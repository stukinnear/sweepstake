import { createApi, fetchBaseQuery, type BaseQueryFn, type FetchArgs, type FetchBaseQueryError } from '@reduxjs/toolkit/query/react'
import { addApiError } from '../store/apiErrorSlice'

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/'

const rawBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: 'include',
})

/**
 * Wraps rawBaseQuery with automatic token refresh on 401.
 * The backend uses HttpOnly cookie-based JWT — on 401 we call /auth/refresh
 * (which rotates the session and sets new cookies), then retry the original request.
 */
const baseQueryWithReauth: BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError> = async (
  args,
  api,
  extraOptions,
) => {
  const url = typeof args === 'string' ? args : args.url
  const method = (typeof args === 'string' ? 'GET' : (args.method ?? 'GET')).toUpperCase()
  console.log(`[API] ${method} ${url}`)

  let result = await rawBaseQuery(args, api, extraOptions)

  if (result.error) {
    console.warn(`[API] ${method} ${url} → ${result.error.status}`, result.error)
  } else {
    console.log(`[API] ${method} ${url} → OK`)
  }

  const isAuthEndpoint = url.startsWith('/auth/')

  if (result.error?.status === 401) {
    console.log('[API] POST /auth/refresh (token refresh)')
    const refreshResult = await rawBaseQuery(
      { url: '/auth/refresh', method: 'POST' },
      api,
      extraOptions,
    )

    if (!refreshResult.error) {
      console.log(`[API] ${method} ${url} (retry after refresh)`)
      result = await rawBaseQuery(args, api, extraOptions)
      if (result.error) {
        console.warn(`[API] ${method} ${url} retry → ${result.error.status}`, result.error)
      } else {
        console.log(`[API] ${method} ${url} retry → OK`)
      }
    } else {
      console.warn('[API] POST /auth/refresh → failed', refreshResult.error)
    }
  }

  if (result.error && !isAuthEndpoint && result.error.status !== 401) {
    const data = result.error && 'data' in result.error ? (result.error.data as { detail?: string | Array<{ msg: string }> } | undefined) : undefined
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) && detail.length > 0 ? detail.map((e) => e.msg).join(', ') : 'Something went wrong. Please try again.'
    api.dispatch(
      addApiError({
        id: `${Date.now()}-${Math.random()}`,
        message,
        url,
        status: result.error.status,
      }),
    )
  }

  return result
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function addPolling<T extends (arg: any, options?: any) => any>(hook: T, pollingInterval: number): T {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return ((arg: any, options?: any) =>
    hook(arg, { pollingInterval, skipPollingIfUnfocused: true, ...options })) as T
}

export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Me', 'Tournament', 'Team', 'Group', 'Stage', 'Match', 'Prediction', 'TournamentPrediction', 'GroupPrediction', 'StagePrediction', 'MatchPrediction', 'Leaderboard', 'MatchStats', 'GroupStats', 'StageStats', 'TournamentStats'],
  keepUnusedDataFor: 60 * 60 * 24 * 2,
  refetchOnMountOrArgChange: 60 * 60,
  refetchOnFocus: true,
  endpoints: () => ({}),
})

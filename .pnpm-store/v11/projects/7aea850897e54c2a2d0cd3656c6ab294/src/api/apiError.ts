import type { FetchBaseQueryError } from '@reduxjs/toolkit/query'
import type { SerializedError } from '@reduxjs/toolkit'

/** Extracts a human-readable message from an RTK Query error, falling back to `fallback`. */
export function getApiErrorMessage(
  error: FetchBaseQueryError | SerializedError | undefined,
  fallback: string,
): string {
  if (!error) return fallback
  if ('data' in error) {
    const detail = (error.data as { detail?: string | Array<{ msg: string }> })?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((e) => e.msg).join(', ')
    }
    return fallback
  }
  return fallback
}

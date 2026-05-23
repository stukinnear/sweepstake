import type { FetchBaseQueryError } from '@reduxjs/toolkit/query'
import type { SerializedError } from '@reduxjs/toolkit'

/** Extracts a human-readable message from an RTK Query error, falling back to `fallback`. */
export function getApiErrorMessage(
  error: FetchBaseQueryError | SerializedError | undefined,
  fallback: string,
): string {
  if (!error) return fallback
  if ('data' in error) {
    return (error.data as { detail?: string })?.detail ?? fallback
  }
  return fallback
}

import { useEffect } from 'react'
import { AlertTriangle, RefreshCw, X } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { dismissApiError } from '../store/apiErrorSlice'

const AUTO_DISMISS_MS = 8000

function ErrorToast({ id, message, status }: { id: string; message: string; status: number | string }) {
  const dispatch = useAppDispatch()
  const dismiss = () => dispatch(dismissApiError(id))

  useEffect(() => {
    const timer = setTimeout(dismiss, AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg bg-red-950/90 px-4 py-3 shadow-lg ring-1 ring-red-500/40 backdrop-blur-sm"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-400" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-red-200">
          Request failed{typeof status === 'number' ? ` (${status})` : ''}
        </p>
        <p className="mt-0.5 text-xs text-red-300/80">{message}</p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="shrink-0 text-red-400 transition hover:text-red-200"
        aria-label="Reload page"
      >
        <RefreshCw className="size-4" />
      </button>
      <button
        onClick={dismiss}
        className="shrink-0 text-red-400 transition hover:text-red-200"
        aria-label="Dismiss"
      >
        <X className="size-4" />
      </button>
    </div>
  )
}

export function ApiErrorNotification() {
  const errors = useAppSelector((state) => state.apiError.errors)
  if (errors.length === 0) return null

  return (
    <div className="fixed bottom-16 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
      {errors.map((e) => (
        <ErrorToast key={e.id} id={e.id} message={e.message} status={e.status} />
      ))}
    </div>
  )
}

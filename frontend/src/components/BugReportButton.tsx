import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'

export function BugReportButton() {
  const feedback = Sentry.getFeedback()
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!feedback || !buttonRef.current) return
    return feedback.attachTo(buttonRef.current)
  }, [feedback])

  if (!feedback) return null

  return (
    <button
      ref={buttonRef}
      className="fixed bottom-4 right-4 z-50 flex items-center gap-1.5 rounded-full bg-gray-800/90 px-3 py-2 text-xs font-medium text-gray-200 shadow-lg ring-1 ring-white/10 backdrop-blur-sm transition hover:bg-gray-700/90 hover:text-white dark:bg-gray-700/90 dark:hover:bg-gray-600/90"
      aria-label="Report a bug"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 16 16"
        fill="currentColor"
        className="size-3.5 shrink-0"
        aria-hidden="true"
      >
        <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm-.75 3.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5ZM8 11.5a.875.875 0 1 1 0-1.75.875.875 0 0 1 0 1.75Z" />
      </svg>
      Report a Bug
    </button>
  )
}

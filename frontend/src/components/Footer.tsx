import { useState } from 'react'
import { ModalShell, ModalBody } from '../modals/base'
import { useGetConfigQuery } from '../api/configApi'

type ModalType = 'credits' | 'privacy' | null

export function Footer() {
  const [open, setOpen] = useState<ModalType>(null)
  const { data: config } = useGetConfigQuery()

  return (
    <>
      <footer className="w-full bg-black text-gray-400 text-xs py-3 px-4 flex items-center justify-center gap-6">
        <button
          type="button"
          onClick={() => setOpen('credits')}
          className="hover:text-white transition-colors"
        >
          Credits
        </button>
        <button
          type="button"
          onClick={() => setOpen('privacy')}
          className="hover:text-white transition-colors"
        >
          Your Data
        </button>
        <a
          href="https://github.com/vanalmsick/sweepstake"
          target="_blank"
          rel="noopener"
          className="hover:text-white transition-colors"
        >
          Open Source Project
        </a>
      </footer>

      {open === 'credits' && (
        <ModalShell title="Credits" onClose={() => setOpen(null)}>
          <ModalBody>
            <ul className="space-y-3 text-sm text-gray-700 dark:text-gray-300 list-disc list-inside">
              <li>
                This is an Open Source project under the{' '}
                <strong>SSPL v1.0 license</strong> on{' '}
                <a
                  href="https://github.com/vanalmsick/sweepstake"
                  target="_blank"
                  rel="noopener"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  github.com/vanalmsick/sweepstake
                </a>
                .
              </li>
              <li>
                Background image free to use from{' '}
                <a
                  href="https://unsplash.com/photos/soccer-field-qCrKTET_09o"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  unsplash.com
                </a>
                .
              </li>
              <li>
                Logo free to use from{' '}
                <a
                  href="https://www.svgrepo.com/svg/390331/football-ball-soccer"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  svgrepo.com
                </a>
                .
              </li>
              <li>Team images from football-data.org.</li>
              <li>
                Tailwind CSS design elements with icons from{' '}
                <a
                  href="https://lucide.dev"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Lucide
                </a>{' '}
                for React.
              </li>
            </ul>
          </ModalBody>
        </ModalShell>
      )}

      {open === 'privacy' && (
        <ModalShell
          title="Your Data"
          onClose={() => setOpen(null)}
          maxWidth="max-w-lg"
        >
          <ModalBody>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              No data is sold or shared with anyone. If you delete your account,
              all your data is unrecoverably deleted. There may be backups
              containing your user data for a few more weeks until the retention
              period is exceeded.
            </p>
            {config?.sentry_dsn && (
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                <a
                  href="https://sentry.io"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Sentry.io
                </a>{' '}
                error and performance monitoring is enabled. In line with EU GDPR,
                errors are reported anonymised (no personally identifiable
                information) to the administrator, along with basic performance
                statistics (e.g. loading speed) for approximately 25&nbsp;% of
                sessions to detect malfunctions. Please see Sentry.io's data
                privacy policy for details.
              </p>
            )}
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              No user statistics or other analytics are collected by the website
              itself. The data you see when using the app is the data that is
              saved — for example your personal profile, predictions, and points.
            </p>
          </ModalBody>
        </ModalShell>
      )}
    </>
  )
}

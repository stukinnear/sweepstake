import type { ReactNode } from 'react'
import { Footer } from './Footer'

interface PageShellProps {
  children: ReactNode
  /** 'auth'  → narrow card (max-w-sm), centered vertically — for Login/Register
   *  'default' → wide card (max-w-4xl), aligned to top — for app pages
   */
  variant?: 'default' | 'auth'
}

export function PageShell({ children, variant = 'default' }: PageShellProps) {
  const isAuth = variant === 'auth'

  return (
    <>
      {/* ── Fixed background: image + dark overlay ── */}
      <div className="fixed inset-0 -z-10 bg-app bg-cover bg-center" aria-hidden="true" />
      <div className="fixed inset-0 -z-10 bg-black/80" aria-hidden="true" />

      {/* ── Scrollable content layer ── */}
      <div
        className={[
          'relative z-10 min-h-screen w-full',
          // On small screens fill the whole viewport; on sm+ center the card
          isAuth
            ? 'sm:flex sm:items-center sm:justify-center sm:p-6'
            : 'sm:flex sm:items-start sm:justify-center sm:p-6 sm:pt-10',
        ].join(' ')}
      >
        {/* ── Page card ── */}
        <div
          className={[
            // Base — full-screen on mobile
            'w-full min-h-screen bg-white text-gray-900',
            // Dark mode
            'dark:bg-gray-900 dark:text-gray-100',
            // Rounded card on sm+; background becomes visible around it
            'sm:min-h-0 sm:rounded-lg sm:shadow-2xl sm:ring-1 sm:ring-white/20 sm:overflow-hidden',
            // Width cap
            isAuth ? 'sm:max-w-sm' : 'sm:max-w-4xl',
          ].join(' ')}
        >
          {children}
          {!isAuth && <Footer />}
        </div>
      </div>
    </>
  )
}

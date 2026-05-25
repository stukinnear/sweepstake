import { useState, type ReactNode } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { AlertCircle, CheckCircle } from 'lucide-react'
import type { Tournament } from '../types/tournament'

export function StakeText({ text }: { text: string }) {
  const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/g
  const parts = text.split(urlRegex)
  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (/^https?:\/\//i.test(part) || /^www\./i.test(part)) {
          const href = /^www\./i.test(part) ? `https://${part}` : part
          return (
            <a key={i} href={href} target="_blank" rel="noopener noreferrer"
               className="text-blue-600 dark:text-blue-400 underline break-all hover:text-blue-800 dark:hover:text-blue-300">
              {part}
            </a>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}

interface TournamentPageHeaderProps {
  tournament: Tournament
  currentUserId?: number | null
  /** Extra buttons rendered next to "← Back to Overview" (e.g. the admin Edit button). */
  rightActions?: ReactNode
  /** When set, an extra "{viewingUserName}'s Predictions" nav item is shown. */
  viewingUserId?: number | null
  viewingUserName?: string | null
}

export function TournamentPageHeader({
  tournament,
  currentUserId,
  rightActions,
  viewingUserId,
  viewingUserName,
}: TournamentPageHeaderProps) {
  type NavItem = { label: string; to: string; end: boolean; special?: boolean }
  const navItems: NavItem[] = [
    { label: 'Overview',        to: `/tournament/${tournament.id}`,                  end: true },
    { label: 'Leaderboard',     to: `/tournament/${tournament.id}/leaderboard`,      end: true },
    { label: 'My Predictions',  to: `/tournament/${tournament.id}/predictions/my`,   end: true },
  ]
  if (viewingUserId != null) {
    navItems.push({
      label: `${viewingUserName ?? 'User'}'s Predictions`,
      to: `/tournament/${tournament.id}/predictions/${viewingUserId}`,
      end: true,
      special: true,
    })
  }

  const myEntry = tournament.participant_lst.find((p) => p.id === currentUserId)
  const paid = myEntry?.stake_paid ?? false

  const [copied, setCopied] = useState(false)
  function handleCopyJoinCode() {
    if (!tournament.join_code) return
    const base = window.location.origin
    const text =
      `Hi, I am taking part in the "${tournament.name}" SweepStake.\n` +
      `It would be even more fun if you'd join, too.\n` +
      `Here is the link to join: ${base}?join=${tournament.join_code}\n` +
      `Join code: ${tournament.join_code}`
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const stakeBadge = tournament.stake ? (
    <span className={[
      'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap',
      paid
        ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400'
        : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400',
    ].join(' ')}>
      {paid ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
      {paid ? 'Stake paid' : 'Stake unpaid'}
    </span>
  ) : null

  const joinCodeEl = tournament.join_code ? (
    <p className="text-sm text-gray-500 dark:text-gray-400">
      Join code:{' '}
      <span
        onClick={handleCopyJoinCode}
        className="relative group cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 transition"
      >
        {tournament.join_code}
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900 text-xs px-2 py-1 opacity-0 group-hover:opacity-100 transition pointer-events-none">
          {copied ? 'Copied!' : 'Click to copy'}
        </span>
      </span>
    </p>
  ) : null

  return (
    <>
      <div>
      {/* Mobile layout (hidden on sm+) */}
      <div className="flex flex-col gap-1.5 sm:hidden">
        {/* Row 1: back + edit */}
        <div className="flex items-center justify-between gap-2">
          <Link
            to="/overview"
            className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
          >
            ← Back to Overview
          </Link>
          {rightActions && <div className="flex items-center gap-2">{rightActions}</div>}
        </div>
        {/* Row 2: tournament name */}
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        {/* Row 3: join code (left) + stake badge (right) */}
        {(joinCodeEl || stakeBadge) && (
          <div className="flex items-center justify-between gap-2">
            {joinCodeEl ?? <span />}
            {stakeBadge}
          </div>
        )}
        {/* Row 4: stake text */}
        {tournament.stake && (
          <p className="text-sm text-gray-700 dark:text-gray-300">
            <StakeText text={tournament.stake} />
          </p>
        )}
      </div>

      {/* Desktop layout (hidden below sm) */}
      <div className="hidden sm:flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{tournament.name}</h1>
          {joinCodeEl && <div className="mt-1">{joinCodeEl}</div>}
          {tournament.stake && (
            <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
              <StakeText text={tournament.stake} />
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <Link
              to="/overview"
              className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition whitespace-nowrap"
            >
              ← Back to Overview
            </Link>
            {rightActions}
          </div>
          {stakeBadge}
        </div>
      </div>
      </div>

      <nav className="flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-800 p-1 w-fit max-w-full overflow-x-auto">
        {navItems.map(({ label, to, end, special }) => (
          <NavLink
            key={label}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                'rounded-full px-4 py-1.5 text-sm font-medium transition',
                isActive
                  ? special
                    ? 'bg-blue-600 dark:bg-blue-500 text-white shadow-sm'
                    : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
              ].join(' ')
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}

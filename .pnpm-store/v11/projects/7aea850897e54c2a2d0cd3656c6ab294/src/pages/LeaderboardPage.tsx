import { useParams, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useGetTournamentQuery } from '../api/tournamentApi'
import { useGetLeaderboardQuery } from '../api/statsApi'
import { useAppSelector } from '../store/hooks'
import { PageShell } from '../components/PageShell'
import { TournamentPageHeader } from '../components/TournamentPageHeader'

export function LeaderboardPage() {
  const { id } = useParams<{ id: string }>()
  const tournamentId = Number(id)
  const currentUser = useAppSelector((state) => state.auth.user)
  const navigate = useNavigate()
  const { data: tournament, isLoading: tLoading, error: tError } = useGetTournamentQuery(tournamentId)
  const { data: leaderboard, isLoading: lLoading, error: lError } = useGetLeaderboardQuery(tournamentId)

  if (tLoading) {
    return (
      <PageShell>
        <div className="flex h-48 items-center justify-center p-8 text-gray-500 dark:text-gray-400">
          Loading tournament…
        </div>
      </PageShell>
    )
  }

  if (tError || !tournament) {
    return (
      <PageShell>
        <div className="p-6 sm:p-8 text-red-500 dark:text-red-400">Tournament not found.</div>
      </PageShell>
    )
  }

  const today = new Date().toISOString().slice(0, 10)
  const isAdmin = tournament.admin_lst.some((a) => a.id === currentUser?.id)
  const hasStarted = tournament.start_date != null && tournament.start_date <= today
  const canViewPredictions = isAdmin || hasStarted

  return (
    <PageShell>
      <div className="p-6 sm:p-8 space-y-8">
        <TournamentPageHeader
          tournament={tournament}
          currentUserId={currentUser?.id}
        />

        {/* Leaderboard */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Leaderboard</h2>

          {lLoading && (
            <p className="text-gray-500 dark:text-gray-400">Loading leaderboard…</p>
          )}

          {lError && (
            <p className="text-red-500 dark:text-red-400">Failed to load leaderboard.</p>
          )}

          {!lLoading && !lError && (!leaderboard || leaderboard.length === 0) && (
            <p className="text-gray-500 dark:text-gray-400">No scores yet.</p>
          )}

          {leaderboard && leaderboard.length > 0 && (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              {leaderboard.map((entry) => (
                <li key={entry.user_id}>
                  <button
                    onClick={canViewPredictions ? () => navigate(`/tournament/${tournamentId}/predictions/${entry.user_id}`) : undefined}
                    className={`w-full flex items-center gap-4 px-4 py-3 transition text-left ${
                      canViewPredictions ? 'hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer' : 'cursor-default'
                    } ${
                      entry.user_id === currentUser?.id
                        ? 'bg-blue-50 dark:bg-blue-900/20'
                        : 'bg-white dark:bg-gray-800'
                    }`}
                    aria-label={canViewPredictions ? `View ${entry.user_name ?? 'user'}'s predictions` : undefined}
                  >
                    <span className="w-8 text-center text-sm font-semibold text-gray-500 dark:text-gray-400 tabular-nums">
                      {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `#${entry.rank}`}
                    </span>
                    <span className="flex-1 flex items-center gap-1.5 text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {entry.user_name ?? '—'}
                      {canViewPredictions && <Search size={13} className="text-gray-400 flex-shrink-0" />}
                    </span>
                    <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 tabular-nums">
                      {entry.total_points} pts
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PageShell>
  )
}

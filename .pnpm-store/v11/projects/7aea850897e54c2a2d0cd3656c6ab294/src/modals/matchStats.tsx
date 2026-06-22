import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { ModalShell, ModalBody } from './base'
import { useGetMatchStatsQuery } from '../api/statsApi'
import { formatDateTime } from '../utils/datetime'
import { useAppSelector } from '../store/hooks'
import type { Match } from '../types'

export function MatchStatsModal({
  matchId,
  tournamentId,
  match,
  onClose,
}: {
  matchId: number
  tournamentId: number
  match: Match | undefined
  onClose: () => void
}) {
  const { data: stats, isLoading, error } = useGetMatchStatsQuery(matchId)
  const homeWins =
    stats?.home_goals != null &&
    stats?.away_goals != null &&
    stats.home_goals >= stats.away_goals
  const predictions = stats?.predictions
    .filter((p) => p.home_score != null && p.away_score != null)
    .map((p) => ({
      ...p,
      winner:
        p.home_score != null && p.away_score != null
          ? p.home_score > p.away_score
            ? 1
            : p.home_score < p.away_score
              ? -1
              : 0
          : null,
      winner_score:
        p.home_score != null && p.away_score != null
          ? p.home_score >= p.away_score
            ? p.home_score
            : p.away_score
          : null,
      loser_score:
        p.home_score != null && p.away_score != null
          ? p.home_score < p.away_score
            ? p.home_score
            : p.away_score
          : null,
    }))
    .sort((a, b) =>
      // 1. winner: asc if home wins (closest to correct winner first), desc if away wins; nulls last
      (homeWins
        ? (b.winner ?? Infinity) - (a.winner ?? Infinity)
        : (a.winner ?? -Infinity) - (b.winner ?? -Infinity)) ||
      // 2. winner_score: desc (higher winning score first); nulls last
      (b.winner_score ?? -1) - (a.winner_score ?? -1) ||
      // 3. if homeWins: sort loser_score: asc (closest to correct loser score first); if away wins: sort loser_score: desc (closest to correct loser score first); nulls last
      (homeWins
        ? (a.loser_score ?? Infinity) - (b.loser_score ?? Infinity)
        : (b.loser_score ?? -Infinity) - (a.loser_score ?? -Infinity))
    )
  console.log('debug prediction sorting', predictions)
  const navigate = useNavigate()
  const currentUserId = useAppSelector((state) => state.auth.user?.id)

  const homeTeam = match?.home_team?.name ?? '?'
  const awayTeam = match?.away_team?.name ?? '?'

  return (
    <ModalShell title={`${homeTeam} vs ${awayTeam}`} onClose={onClose} maxWidth="max-w-lg">
      <ModalBody>
        {isLoading && (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading stats…</p>
        )}
        {error && (
          <p className="text-sm text-red-500 dark:text-red-400">Failed to load match stats.</p>
        )}
        {stats && (
          <div className="flex flex-col gap-5 max-h-[65vh]">
            <div className="text-center py-1 flex-shrink-0">
              <span className="text-3xl font-bold font-mono text-gray-900 dark:text-gray-100">
                {stats.home_goals != null && stats.away_goals != null
                  ? `${stats.home_goals} – ${stats.away_goals}`
                  : '– : –'}
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Final Score</p>
              {stats.start_datetime && (
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  {formatDateTime(stats.start_datetime)}
                </p>
              )}
            </div>

            {(predictions ?? []).length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No predictions were made for this match.
              </p>
            ) : (
              <div className="overflow-y-auto flex-1 min-h-0">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white dark:bg-gray-900">
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left pb-2 font-medium text-gray-500 dark:text-gray-400">
                      Player
                    </th>
                    <th className="text-center pb-2 font-medium text-gray-500 dark:text-gray-400">
                      Prediction
                    </th>
                    <th className="text-right pb-2 font-medium text-gray-500 dark:text-gray-400">
                      Points
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
                  {(predictions ?? []).map((p) => (
                      <tr
                        key={p.user_id}
                        onClick={() => {
                          onClose()
                          navigate(`/tournament/${tournamentId}/predictions/${p.user_id}`)
                        }}
                        className={`cursor-pointer transition hover:bg-gray-100 dark:hover:bg-gray-700/50 ${
                          p.user_id === currentUserId ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                        }`}
                        aria-label={`View ${p.user_name ?? 'user'}'s predictions`}
                      >
                        <td className="py-2.5 px-3 text-gray-900 dark:text-gray-100">
                          <span className="inline-flex items-center gap-1.5">
                            {p.user_name ?? '—'}
                            <Search size={13} className="text-gray-400 flex-shrink-0" />
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono text-gray-700 dark:text-gray-300">
                          {p.home_score != null && p.away_score != null
                            ? `${p.home_score} – ${p.away_score}`
                            : '—'}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {p.points_earned != null ? (
                            <span className="font-semibold text-green-600 dark:text-green-400">
                              +{p.points_earned}
                            </span>
                          ) : (
                            <span className="text-gray-400 dark:text-gray-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              </div>
            )}
          </div>
        )}
      </ModalBody>
    </ModalShell>
  )
}

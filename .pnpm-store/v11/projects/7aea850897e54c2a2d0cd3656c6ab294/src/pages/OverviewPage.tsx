import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { UserPlus, Plus, LogOut, Settings } from 'lucide-react'
import { useListTournamentsQuery } from '../api/tournamentApi'
import { useLogoutMutation } from '../api/authApi'
import { useGetConfigQuery } from '../api/configApi'
import { useAppSelector } from '../store/hooks'
import { PageShell } from '../components/PageShell'
import { SettingsModal } from '../modals/user'
import { JoinTournamentModal } from '../modals/user'
import { CreateTournamentModal } from '../modals/tournament'

export function OverviewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const inboundJoinCode = searchParams.get('join') ?? ''
  const { data: tournaments, isLoading, error } = useListTournamentsQuery()
  const { data: config } = useGetConfigQuery()
  const currentUser = useAppSelector((state) => state.auth.user)
  const canCreate = !config?.only_superusers_can_create_tournaments || !!currentUser?.is_superuser
  const [logout] = useLogoutMutation()
  const [showSettings, setShowSettings] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(!!inboundJoinCode)
  const [joinCode, setJoinCode] = useState(inboundJoinCode)

  useEffect(() => {
    if (inboundJoinCode) {
      navigate('/overview', { replace: true })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleLogout() {
    await logout()
  }

  return (
    <PageShell>
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
      {showCreate && <CreateTournamentModal onClose={() => setShowCreate(false)} />}
      {showJoin && <JoinTournamentModal onClose={() => { setShowJoin(false); setJoinCode('') }} initialCode={joinCode} />}
      <div className="p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">SweepStakes</h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">Select a SweepStake to get started.</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            {/* Row 1: account buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSettings(true)}
                className="rounded-full border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:border-gray-400 hover:text-gray-900 dark:hover:border-gray-400 dark:hover:text-gray-100 transition inline-flex items-center gap-1.5"
              >
                <Settings size={15} />
                <span className="hidden sm:inline">Settings</span>
              </button>
              <button
                onClick={handleLogout}
                className="rounded-full border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:border-red-400 hover:text-red-600 dark:hover:border-red-500 dark:hover:text-red-400 transition inline-flex items-center gap-1.5"
              >
                <LogOut size={15} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
            {/* Row 2: competition buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <button
                onClick={() => { setJoinCode(''); setShowJoin(true) }}
                className="rounded-full border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition inline-flex items-center justify-center gap-1.5"
              >
                <UserPlus size={15} />
                Join SweepStake
              </button>
              <span title={!canCreate ? 'Only admins can create a SweepStake' : undefined}>
                <button
                  onClick={() => canCreate && setShowCreate(true)}
                  disabled={!canCreate}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition inline-flex items-center justify-center gap-1.5 ${canCreate ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}`}
                >
                  <Plus size={15} />
                  Create SweepStake
                </button>
              </span>
            </div>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          {isLoading && (
            <p className="text-gray-500 dark:text-gray-400">Loading tournaments…</p>
          )}

          {error && (
            <p className="text-red-500 dark:text-red-400">Failed to load tournaments.</p>
          )}

          {!isLoading && !error && tournaments?.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400">No tournaments found.</p>
          )}

          {[...(tournaments ?? [])]
            .sort((a, b) => {
              const endA = a.end_date ?? ''
              const endB = b.end_date ?? ''
              if (endB !== endA) return endB < endA ? -1 : 1
              const startA = a.start_date ?? ''
              const startB = b.start_date ?? ''
              return startA < startB ? -1 : startA > startB ? 1 : 0
            })
            .map((tournament) => {
              const adminNames = tournament.admin_lst.map((u) => u.user_name).filter(Boolean).join(', ')
              const dateRange = [tournament.start_date, tournament.end_date].filter(Boolean).join(' – ')
              return (
                <button
                  key={tournament.id}
                  onClick={() => navigate(`/tournament/${tournament.id}`)}
                  className="w-full rounded-lg border border-gray-200 bg-white px-5 py-4 text-left shadow-sm transition hover:border-blue-400 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-base font-semibold text-gray-900 dark:text-gray-100">
                      {tournament.name}
                    </span>
                    {dateRange && (
                      <span className="shrink-0 text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                        {dateRange}
                      </span>
                    )}
                  </div>
                  {adminNames && (
                    <span className="mt-0.5 block text-sm text-gray-500 dark:text-gray-400">
                      by {adminNames}
                    </span>
                  )}
                </button>
              )
            })}
        </div>
      </div>
    </PageShell>
  )
}

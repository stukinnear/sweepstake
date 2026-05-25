import { useState, useEffect, Fragment } from 'react'
import { useParams, Navigate, useSearchParams } from 'react-router-dom'
import { Dices, Search } from 'lucide-react'
import { GroupStatsModal, StageStatsModal, TournamentStatsModal } from '../modals/winnerStats'
import { useGetTournamentQuery } from '../api/tournamentApi'
import { useListMatchesQuery } from '../api/matchApi'
import { useListTeamsQuery } from '../api/teamApi'
import { useListGroupsQuery, useListStagesQuery } from '../api/groupApi'
import {
  useListMatchPredictionsQuery,
  useUpsertMatchPredictionMutation,
  useGetTournamentPredictionsQuery,
  useUpsertTournamentPredictionMutation,
  useListGroupPredictionsQuery,
  useUpsertGroupPredictionMutation,
  useListStagePredictionsQuery,
  useUpsertStagePredictionMutation,
} from '../api/predictionApi'
import { useAppSelector } from '../store/hooks'
import { PageShell } from '../components/PageShell'
import { Countdown, ElapsedTime } from '../components/Countdown'
import { TournamentPageHeader } from '../components/TournamentPageHeader'
import { parseServerDt, formatDateTime } from '../utils/datetime'
import { groupByStage } from '../utils/match'
import type { MatchPrediction } from '../types'
import type { TeamRead } from '../types/team'
import { MatchStatsModal } from '../modals/matchStats'

// ---------------------------------------------------------------------------
// Poisson-based random score generation
// ---------------------------------------------------------------------------
function poissonSample(lambda: number): number {
  const threshold = Math.exp(-lambda)
  let product = Math.random()
  let count = 0
  while (product > threshold) {
    product *= Math.random()
    count++
  }
  return count
}

function generateScore({
  homeLambda = 1.36,
  awayLambda = 1.06,
  homeAttack = 1.0,
  homeDefence = 1.0,
  awayAttack = 1.0,
  awayDefence = 1.0,
}: {
  homeLambda?: number; awayLambda?: number
  homeAttack?: number; homeDefence?: number
  awayAttack?: number; awayDefence?: number
} = {}): { home: number; away: number } {
  return {
    home: poissonSample(homeLambda * homeAttack * awayDefence),
    away: poissonSample(awayLambda * awayAttack * homeDefence),
  }
}

/** Winner pick card for Tournament / Group / Stage predictions */
function TeamSelect({
  label,
  teams,
  currentTeamId,
  isOwn,
  disabled,
  pointsEarned,
  startDate,
  winnerTeam,
  secondPlace,
  thirdPlace,
  onSelect,
  onStatsClick,
  featured = false,
}: {
  label: string
  teams: TeamRead[]
  currentTeamId: number | null | undefined
  isOwn: boolean
  disabled?: boolean
  pointsEarned?: number | null
  startDate?: string | null
  winnerTeam?: TeamRead | null
  secondPlace?: TeamRead | null
  thirdPlace?: TeamRead | null
  onSelect: (teamId: number | null) => void
  onStatsClick?: () => void
  featured?: boolean
}) {
  const selectedTeam = teams.find((t) => t.id === currentTeamId)

  const daysLeft = (() => {
    if (!isOwn || disabled || !startDate) return null
    const todayMidnight = (() => { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), t.getDate()) })()
    const target = new Date(startDate + 'T00:00:00')
    const d = Math.round((target.getTime() - todayMidnight.getTime()) / 86_400_000)
    return d > 0 ? d : null
  })()

  if (featured) {
    return (
      <div
        className={`relative rounded-2xl border-2 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 dark:from-amber-950/40 dark:via-yellow-900/20 dark:to-orange-950/30 border-amber-200 dark:border-amber-700/60 px-6 py-5${onStatsClick ? ' cursor-pointer' : ''}`}
        onClick={onStatsClick ?? undefined}
      >
        <div className="flex items-start justify-between mb-4">
          <p className="text-sm text-amber-700/80 dark:text-amber-400/80">{label}</p>
          <div className="flex items-center gap-2">
            {pointsEarned != null && (
              <span className="inline-flex items-center rounded-full bg-green-100 dark:bg-green-900/50 px-2.5 py-0.5 text-xs font-bold text-green-700 dark:text-green-400">
                +{pointsEarned} pts
              </span>
            )}
            {isOwn && disabled && currentTeamId != null && pointsEarned == null && (
              <span className="text-xs italic text-amber-600/70 dark:text-amber-400/60">🤞 fingers crossed</span>
            )}
            {isOwn && disabled && currentTeamId == null && pointsEarned == null && (
              <span className="text-xs italic text-gray-400 dark:text-gray-500"><span className="text-[0.8em]">❌</span> missed cutoff</span>
            )}
            {isOwn && !disabled && pointsEarned == null && daysLeft != null && (
              <span className="text-xs italic text-amber-600/70 dark:text-amber-400/60">
                {daysLeft === 1 ? '1 day left' : `${daysLeft} days left`}
              </span>
            )}
            {onStatsClick && (
              <button onClick={onStatsClick} className="text-amber-500/70 hover:text-blue-500 dark:hover:text-blue-400 transition" aria-label="View stats">
                <Search size={15} />
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex-shrink-0 h-14 w-14 rounded-full overflow-hidden border-2 flex items-center justify-center ${
            selectedTeam
              ? 'border-amber-300 dark:border-amber-600 bg-amber-100/60 dark:bg-amber-900/20'
              : 'border-dashed border-amber-300/60 dark:border-amber-700/40 bg-amber-100/40 dark:bg-amber-900/10'
          }`}>
            {selectedTeam?.image_url ? (
              <img src={selectedTeam.image_url} alt={selectedTeam.name} decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover" />
            ) : (
              <span className="text-2xl opacity-20">🏆</span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            {!isOwn || disabled ? (
              <p className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {selectedTeam?.name ?? <span className="text-gray-400 dark:text-gray-500 font-normal text-base italic">No pick yet</span>}
              </p>
            ) : (
              <>
                {selectedTeam && (
                  <p className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-1.5 truncate">{selectedTeam.name}</p>
                )}
                <select
                  value={currentTeamId ?? ''}
                  onChange={(e) => onSelect(e.target.value === '' ? null : Number(e.target.value))}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full rounded-xl border border-amber-300 dark:border-amber-700 bg-white/80 dark:bg-gray-800/80 text-sm text-gray-900 dark:text-gray-100 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="">— pick a team —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </>
            )}
          </div>
          {(winnerTeam || secondPlace || thirdPlace) && (
            <div className="flex-shrink-0 flex flex-col items-end gap-0.5">
              {([['1st', winnerTeam], ['2nd', secondPlace], ['3rd', thirdPlace]] as [string, TeamRead | null | undefined][]).map(([place, team]) =>
                team ? (
                  <div key={place} className="flex items-center gap-1">
                    <span className="text-xs italic text-amber-700/40 dark:text-amber-400/40 whitespace-nowrap">{place}</span>
                    {team.image_url && (
                      <img src={team.image_url} alt={team.name} decoding="async" referrerPolicy="no-referrer" className="h-3.5 w-3.5 rounded-full object-cover border border-amber-200 dark:border-amber-700/60 flex-shrink-0" />
                    )}
                    <span className="text-xs italic text-amber-700/50 dark:text-amber-400/50 whitespace-nowrap">{team.name}</span>
                  </div>
                ) : null
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Default group / stage card
  const isActive = isOwn && !disabled

  return (
    <div
      className={`rounded-xl border bg-white dark:bg-gray-800 overflow-hidden ${isActive ? 'border-blue-200 dark:border-blue-800/50' : 'border-gray-200 dark:border-gray-700'}${onStatsClick ? ' cursor-pointer' : ''}`}
      onClick={onStatsClick ?? undefined}
    >
      <div className={`flex items-center justify-between px-3.5 py-2 border-b ${
        isActive
          ? 'bg-blue-50/70 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/40'
          : 'bg-gray-50 dark:bg-gray-700/40 border-gray-100 dark:border-gray-700'
      }`}>
        <span className={`text-xs font-semibold uppercase tracking-wider ${
          isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
        }`}>
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {winnerTeam && (
            <div className="flex items-center gap-1">
              {winnerTeam.image_url && (
                <img src={winnerTeam.image_url} alt={winnerTeam.name} decoding="async" referrerPolicy="no-referrer" className="h-3.5 w-3.5 rounded-full object-cover border border-gray-200 dark:border-gray-600 flex-shrink-0" />
              )}
              <span className="text-xs italic text-gray-400 dark:text-gray-500 whitespace-nowrap">{winnerTeam.iso_code ?? winnerTeam.name}</span>
            </div>
          )}
          {pointsEarned != null && (
            <span className="rounded-full bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400 text-xs font-bold px-2 py-0.5 leading-tight">
              +{pointsEarned} pts
            </span>
          )}
          {isOwn && disabled && currentTeamId != null && pointsEarned == null && (
            <span className="text-xs italic text-gray-400 dark:text-gray-500">🤞 fingers crossed</span>
          )}
          {isOwn && disabled && currentTeamId == null && pointsEarned == null && (
            <span className="text-xs italic text-gray-400 dark:text-gray-500"><span className="text-[0.8em]">❌</span> missed cutoff</span>
          )}
          {isActive && pointsEarned == null && daysLeft != null && (
            <span className="text-xs italic text-gray-400 dark:text-gray-500">
              {daysLeft === 1 ? '1 day left' : `${daysLeft} days left`}
            </span>
          )}
          {onStatsClick && (
            <button onClick={onStatsClick} className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition" aria-label="View stats">
              <Search size={12} />
            </button>
          )}
        </div>
      </div>
      <div className="px-3.5 py-3">
        {!isActive ? (
          <div className="flex items-center gap-2.5">
            {selectedTeam?.image_url ? (
              <img src={selectedTeam.image_url} alt={selectedTeam.name}
                decoding="async" referrerPolicy="no-referrer" className="h-8 w-8 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-600" />
            ) : (
              <span className="h-8 w-8 flex-shrink-0 rounded-full bg-gray-100 dark:bg-gray-700 border border-dashed border-gray-300 dark:border-gray-600 inline-block" />
            )}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium truncate ${selectedTeam ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-500 italic'}`}>
                {selectedTeam?.name ?? 'No pick'}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              {selectedTeam?.image_url ? (
                <img src={selectedTeam.image_url} alt={selectedTeam.name}
                  decoding="async" referrerPolicy="no-referrer" className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-600" />
              ) : (
                <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-100 dark:bg-gray-700 border border-dashed border-gray-200 dark:border-gray-600 inline-block" />
              )}
              <select
                value={currentTeamId ?? ''}
                onChange={(e) => onSelect(e.target.value === '' ? null : Number(e.target.value))}
                className="flex-1 min-w-0 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100 py-1.5 px-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">— pick a team —</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** Controlled score input pair that saves on blur */
function ScoreInput({
  matchId,
  prediction,
  isOwn,
  disabled,
  userId,
  tournamentId,
  onBeforeSave,
}: {
  matchId: number
  prediction: MatchPrediction | undefined
  isOwn: boolean
  disabled?: boolean
  /** When set, passed as user_id to the mutation (admin editing another user). */
  userId?: number
  tournamentId?: number
  /** Return false to cancel the save. */
  onBeforeSave?: () => boolean
}) {
  const [home, setHome] = useState<string>(prediction?.home_score?.toString() ?? '')
  const [away, setAway] = useState<string>(prediction?.away_score?.toString() ?? '')
  const [upsert] = useUpsertMatchPredictionMutation()

  // Re-sync inputs when prediction changes externally (e.g. bulk random fill)
  useEffect(() => {
    setHome(prediction?.home_score?.toString() ?? '')
    setAway(prediction?.away_score?.toString() ?? '')
  }, [prediction?.home_score, prediction?.away_score])

  function save() {
    if (onBeforeSave && !onBeforeSave()) return
    const h = home === '' ? undefined : Number(home)
    const a = away === '' ? undefined : Number(away)
    upsert({ match_id: matchId, home_score: h, away_score: a, ...(userId !== undefined ? { userId } : {}), ...(tournamentId !== undefined ? { tournamentId } : {}) })
  }

  if (!isOwn || disabled) {
    const h = prediction?.home_score
    const a = prediction?.away_score
    return (
      <span className="min-w-[80px] text-center text-sm font-mono font-semibold text-gray-500 dark:text-gray-400">
        {h != null && a != null ? `${h} – ${a}` : '— : —'}
      </span>
    )
  }

  return (
    <div className="flex items-center gap-1 min-w-[80px] justify-center">
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        autoComplete="off"
        data-form-type="other"
        data-lpignore="true"
        name="home-goals"
        value={home}
        onChange={(e) => setHome(e.target.value.replace(/[^0-9]/g, ''))}
        onBlur={save}
        className="w-9 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-center text-sm font-mono font-semibold text-gray-900 dark:text-gray-100 py-0.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
      <span className="text-gray-500 dark:text-gray-400 font-mono">–</span>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        autoComplete="off"
        data-form-type="other"
        data-lpignore="true"
        name="away-goals"
        value={away}
        onChange={(e) => setAway(e.target.value.replace(/[^0-9]/g, ''))}
        onBlur={save}
        className="w-9 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-center text-sm font-mono font-semibold text-gray-900 dark:text-gray-100 py-0.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
    </div>
  )
}

export function PredictionsPage() {
  const { id, userId } = useParams<{ id: string; userId: string }>()
  const tournamentId = Number(id)
  const isMy = userId === 'my'
  const currentUser = useAppSelector((state) => state.auth.user)
  const [searchParams, setSearchParams] = useSearchParams()
  const statsMatchId = searchParams.get('match') ? Number(searchParams.get('match')) : null
  const statsGroupId = searchParams.get('group') ? Number(searchParams.get('group')) : null
  const statsStageId = searchParams.get('stage') ? Number(searchParams.get('stage')) : null
  const statsTournamentId = searchParams.get('tournament') ? Number(searchParams.get('tournament')) : null

  const today = new Date().toISOString().slice(0, 10)

  // Numeric user ID whose predictions we're fetching
  const targetUserId: number | undefined = isMy
    ? currentUser?.id
    : (userId ? Number(userId) : undefined)

  const validTargetId = targetUserId != null && !isNaN(targetUserId) && targetUserId > 0

  // True when viewing own predictions (either via /my or own numeric ID)
  const isViewingOwn = isMy || (currentUser != null && targetUserId === currentUser.id)

  function openStats(key: 'match' | 'group' | 'stage' | 'tournament', value: number) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set(key, String(value))
      return next
    }, { replace: true })
  }

  function closeStats(key: 'match' | 'group' | 'stage' | 'tournament') {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete(key)
      return next
    }, { replace: true })
  }

  const { data: tournament, isLoading: tLoading, error: tError } = useGetTournamentQuery(tournamentId)
  const { data: matches, isLoading: mLoading, error: mError } = useListMatchesQuery(tournamentId)
  const { data: teams = [] } = useListTeamsQuery(tournamentId)
  const { data: groups = [] } = useListGroupsQuery(tournamentId)
  const { data: stages = [] } = useListStagesQuery(tournamentId)

  const { data: matchPredictions, refetch: refetchMatchPredictions } = useListMatchPredictionsQuery(
    { tournamentId, userId: targetUserId }, { skip: !validTargetId },
  )
  const { data: tournamentPredictions } = useGetTournamentPredictionsQuery(
    { tournamentId, userId: targetUserId }, { skip: !validTargetId },
  )
  const { data: groupPredictions = [] } = useListGroupPredictionsQuery(
    { tournamentId, userId: targetUserId }, { skip: !validTargetId },
  )
  const { data: stagePredictions = [] } = useListStagePredictionsQuery(
    { tournamentId, userId: targetUserId }, { skip: !validTargetId },
  )

  const [upsertTournamentPred] = useUpsertTournamentPredictionMutation()
  const [upsertGroupPred] = useUpsertGroupPredictionMutation()
  const [upsertStagePred] = useUpsertStagePredictionMutation()
  const [upsertMatchPred] = useUpsertMatchPredictionMutation()
  const [, setRenderTick] = useState(0)
  const [isGeneratingRandom, setIsGeneratingRandom] = useState(false)

  useEffect(() => {
    if (!matches) return
    const now = Date.now()
    const timeouts = matches.flatMap((m) => {
      const startMs = parseServerDt(m.start_datetime).getTime()
      const endMs = startMs + 100 * 60 * 1000
      const delay = endMs - now
      if (now >= startMs && delay > 0) {
        return [setTimeout(() => setRenderTick((n) => n + 1), delay)]
      }
      return []
    })
    return () => timeouts.forEach(clearTimeout)
  }, [matches])

  // Redirect bare /predictions → /predictions/my
  if (!userId && currentUser) {
    return <Navigate to={`/tournament/${id}/predictions/my`} replace />
  }
  // Redirect /predictions/:ownId → /predictions/my
  if (!isMy && currentUser && validTargetId && targetUserId === currentUser.id) {
    return <Navigate to={`/tournament/${id}/predictions/my`} replace />
  }

  // Derived state that depends on tournament data
  const isAdmin = tournament?.admin_lst.some((u) => u.id === currentUser?.id) ?? false
  // True when viewing *another* user's predictions
  const isViewingOther = !isViewingOwn && validTargetId
  // Admins see all predictions of other users in edit mode; non-admins see restricted read-only
  const adminEditingOther = isViewingOther && isAdmin
  const restrictToPublished = isViewingOther && !isAdmin
  // Edit inputs enabled for own predictions or admin editing another user
  const isEditable = isViewingOwn || adminEditingOther

  // User whose predictions we're viewing (for the nav item label)
  const viewingUser = isViewingOther
    ? (tournament?.participant_lst.find((p) => p.id === targetUserId)
       ?? tournament?.admin_lst.find((a) => a.id === targetUserId))
    : null

  function confirmAdminEdit(): boolean {
    const name = viewingUser?.user_name ?? 'this user'
    return window.confirm(`Are you sure you want to edit ${name}'s predictions?`)
  }

  async function handleGenerateRandomScores() {
    const now = new Date()
    const upcoming = (matches ?? []).filter((m) => new Date(m.start_datetime) > now)
    setIsGeneratingRandom(true)
    try {
      for (const match of upcoming) {
        const { home, away } = generateScore()
        await upsertMatchPred({ match_id: match.id, home_score: home, away_score: away, tournamentId })
        // Small delay to avoid overwhelming the api server - i.e. 100 requests would take ~6.6 seconds 
        await new Promise((r) => setTimeout(r, 66))
      }
    } finally {
      setIsGeneratingRandom(false)
      refetchMatchPredictions()
    }
  }

  const predictionMap = new Map((matchPredictions ?? []).map((p) => [p.match_id, p]))
  const groupPredMap = new Map(groupPredictions.map((p) => [p.group_id, p]))
  const stagePredMap = new Map(stagePredictions.map((p) => [p.stage_id, p]))
  const tournamentWinnerTeamId = tournamentPredictions?.[0]?.winner_team_id ?? null

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

  // Filter matches visible to non-admin viewers of another user's predictions
  const nowMs = Date.now()
  const allMatches = [...(matches ?? [])]
    .sort((a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime())
  const visibleMatches = restrictToPublished
    ? allMatches.filter((m) => parseServerDt(m.start_datetime).getTime() <= nowMs)
    : allMatches
  const grouped = groupByStage(visibleMatches)

  // Sections visible to non-admin viewers (only if already started)
  const showTournamentSection =
    !!(tournament.first_place_points || tournament.second_place_points || tournament.third_place_points) &&
    (!restrictToPublished || (tournament.start_date != null && tournament.start_date <= today))

  const visibleGroups = (restrictToPublished
    ? groups.filter((g) => g.start_date != null && g.start_date <= today)
    : groups)

  const visibleStages = (restrictToPublished
    ? stages.filter((s) => s.start_date != null && s.start_date <= today)
    : stages)

  // For admin editing another user, override disabled so all inputs are editable
  const tournamentDisabled = adminEditingOther
    ? false
    : (tournament.start_date != null && tournament.start_date <= today)

  return (
    <PageShell>
      {statsMatchId != null && (
        <MatchStatsModal
          matchId={statsMatchId}
          tournamentId={tournamentId}
          match={matches?.find((m) => m.id === statsMatchId)}
          onClose={() => closeStats('match')}
        />
      )}
      {statsGroupId != null && (() => {
        const g = groups.find((g) => g.id === statsGroupId)
        return g ? (
          <GroupStatsModal
            groupId={statsGroupId}
            groupName={g.name.toLowerCase().includes('group') ? g.name : `Group ${g.name}`}
            tournamentId={tournamentId}
            onClose={() => closeStats('group')}
          />
        ) : null
      })()}
      {statsStageId != null && (() => {
        const s = stages.find((s) => s.id === statsStageId)
        return s ? (
          <StageStatsModal
            stageId={statsStageId}
            stageName={s.name}
            tournamentId={tournamentId}
            onClose={() => closeStats('stage')}
          />
        ) : null
      })()}
      {statsTournamentId != null && (
        <TournamentStatsModal
          tournamentId={tournamentId}
          tournamentName={tournament.name}
          onClose={() => closeStats('tournament')}
        />
      )}
      <div className="p-6 sm:p-8 space-y-8">
        <TournamentPageHeader
          tournament={tournament}
          currentUserId={currentUser?.id}
          viewingUserId={isViewingOther ? targetUserId : undefined}
          viewingUserName={viewingUser?.user_name ?? undefined}
        />

        {/* Tournament winner */}
        {showTournamentSection && (
          <section>
            <h2 className="text-lg font-semibold mb-3">🏆 Tournament Winner</h2>
            <TeamSelect
              label="Who will win the tournament?"
              featured
              teams={teams}
              currentTeamId={tournamentWinnerTeamId}
              isOwn={isEditable}
              disabled={tournamentDisabled}
              pointsEarned={tournamentPredictions?.[0]?.points_earned ?? null}
              startDate={tournament.start_date}
              winnerTeam={tournament.first_place}
              secondPlace={tournament.second_place}
              thirdPlace={tournament.third_place}
              onSelect={(teamId) => {
                if (adminEditingOther && !confirmAdminEdit()) return
                upsertTournamentPred({
                  tournament_id: tournamentId,
                  winner_team_id: teamId ?? undefined,
                  ...(adminEditingOther ? { userId: targetUserId } : {}),
                })
              }}
              onStatsClick={
                tournament.start_date != null && tournament.start_date <= today
                  ? () => openStats('tournament', tournamentId)
                  : undefined
              }
            />
          </section>
        )}

        {/* Stage winners */}
        {visibleStages.length > 0 && !!tournament.stage_winner_points && (
          <section>
            <h2 className="text-lg font-semibold mb-3">🏅 Stage Winners
              <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-500 normal-case tracking-normal">
                +{tournament.stage_winner_points} pts each
              </span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {visibleStages.map((stage) => {
                const stageStarted = stage.start_date != null ? stage.start_date <= today : false
                const stageDisabled = adminEditingOther ? false : stageStarted
                return (
                  <TeamSelect
                    key={stage.id}
                    label={stage.name}
                    teams={teams}
                    currentTeamId={stagePredMap.get(stage.id)?.winner_team_id ?? null}
                    isOwn={isEditable}
                    disabled={stageDisabled}
                    pointsEarned={stagePredMap.get(stage.id)?.points_earned ?? null}
                    startDate={stage.start_date}
                    winnerTeam={stage.winner}
                    onSelect={(teamId) => {
                      if (adminEditingOther && !confirmAdminEdit()) return
                      upsertStagePred({
                        stage_id: stage.id,
                        winner_team_id: teamId ?? undefined,
                        tournamentId,
                        ...(adminEditingOther ? { userId: targetUserId } : {}),
                      })
                    }}
                    onStatsClick={stageStarted ? () => openStats('stage', stage.id) : undefined}
                  />
                )
              })}
            </div>
          </section>
        )}

        {/* Group winners */}
        {visibleGroups.length > 0 && !!tournament.group_winner_points && (
          <section>
            <h2 className="text-lg font-semibold mb-3">🥇 Group Winners</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {visibleGroups.map((group) => {
                const groupTeams = teams.filter((t) => t.group_id === group.id)
                const groupStarted = group.start_date != null ? group.start_date <= today : false
                const groupDisabled = adminEditingOther ? false : groupStarted
                return (
                  <TeamSelect
                    key={group.id}
                    label={group.name.toLowerCase().includes('group') ? `${group.name}` : `Group ${group.name}`}
                    teams={groupTeams.length > 0 ? groupTeams : teams}
                    currentTeamId={groupPredMap.get(group.id)?.winner_team_id ?? null}
                    isOwn={isEditable}
                    disabled={groupDisabled}
                    pointsEarned={groupPredMap.get(group.id)?.points_earned ?? null}
                    startDate={group.start_date}
                    winnerTeam={group.winner}
                    onSelect={(teamId) => {
                      if (adminEditingOther && !confirmAdminEdit()) return
                      upsertGroupPred({
                        group_id: group.id,
                        winner_team_id: teamId ?? undefined,
                        tournamentId,
                        ...(adminEditingOther ? { userId: targetUserId } : {}),
                      })
                    }}
                    onStatsClick={groupStarted ? () => openStats('group', group.id) : undefined}
                  />
                )
              })}
            </div>
          </section>
        )}

        {/* Upcoming match score predictions */}
        {!!(tournament.match_score_points || tournament.match_winner_points) && (
          <section>
            <div className="flex items-center justify-between gap-4 mb-3">
              <h2 className="text-lg font-semibold">
                ⚽ Match Predictions
              </h2>
              {isViewingOwn && (
                <button
                  onClick={handleGenerateRandomScores}
                  disabled={isGeneratingRandom}
                  className="inline-flex items-center gap-1.5 rounded-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <Dices size={13} className={isGeneratingRandom ? 'animate-spin' : ''} />
                  <span className="relative">
                    <span className={isGeneratingRandom ? 'invisible' : undefined}>Random scores</span>
                    {isGeneratingRandom && <span className="absolute inset-0 flex items-center">Generating…</span>}
                  </span>
                </button>
              )}
            </div>

            {mLoading && <p className="text-gray-500 dark:text-gray-400">Loading matches…</p>}
            {mError && <p className="text-red-500 dark:text-red-400">Failed to load matches.</p>}
            {!mLoading && !mError && grouped.size === 0 && (
              <p className="text-gray-500 dark:text-gray-400">No matches.</p>
            )}

            {(() => { let nowLineInserted = false; const renderNowMs = Date.now(); return Array.from(grouped.entries()).map(([stage, stageMatches]) => (
              <div key={stage} className="mb-6">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                  {stage}
                </h3>
                <ul className="grid grid-cols-1 md:grid-cols-[auto_1fr_auto_1fr_auto] gap-x-2 gap-y-2">
                  {stageMatches.map((match) => {
                    const matchStartMs = parseServerDt(match.start_datetime).getTime()
                    const isLive = matchStartMs <= renderNowMs && renderNowMs <= matchStartMs + 100 * 60 * 1000
                    if (isLive) nowLineInserted = true
                    const showNow = !nowLineInserted && matchStartMs >= renderNowMs
                    if (showNow) nowLineInserted = true
                    // For admin editing another user, never disable match inputs
                    const matchDisabled = adminEditingOther ? false : matchStartMs <= renderNowMs
                    return (
                      <Fragment key={match.id}>
                        {showNow && (
                          <li className="md:col-span-5 flex items-center gap-2 pointer-events-none select-none">
                            <span className="relative flex h-3 w-3 flex-shrink-0">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                              <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
                            </span>
                            <span className="flex-1 h-0.5 bg-red-500 relative overflow-hidden rounded-full">
                              <span className="animate-now-line-left bg-gradient-to-r from-transparent via-white to-transparent" />
                            </span>
                            <span className="text-xs font-semibold text-red-500 whitespace-nowrap animate-now-text tabular-nums">
                              <Countdown targetMs={matchStartMs} onZero={() => setRenderTick(n => n + 1)} />
                            </span>
                            <span className="flex-1 h-0.5 bg-red-500 relative overflow-hidden rounded-full">
                              <span className="animate-now-line bg-gradient-to-r from-transparent via-white to-transparent" />
                            </span>
                            <span className="text-xs font-semibold text-red-500 whitespace-nowrap animate-now-text">Now</span>
                          </li>
                        )}
                        <li
                          className={[
                            'relative md:col-span-5 grid grid-cols-[1fr_auto_1fr] md:grid-cols-subgrid items-center gap-x-2 gap-y-1 rounded-lg border bg-white dark:bg-gray-800 pl-4 pr-10 md:pr-4 py-3',
                            isLive ? 'animate-live-border' : 'border-gray-200 dark:border-gray-700',
                            matchStartMs <= renderNowMs ? 'cursor-pointer' : '',
                          ].join(' ')}
                          onClick={matchStartMs <= renderNowMs ? () => setSearchParams((prev) => {
                            const next = new URLSearchParams(prev)
                            next.set('match', String(match.id))
                            return next
                          }, { replace: true }) : undefined}
                        >
                          <span className="row-start-1 col-start-1 md:row-auto md:col-auto text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                            {isLive ? (
                              <span className="flex items-center gap-1.5">
                                <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                                </span>
                                <span className="font-semibold text-red-500 animate-now-text tabular-nums">
                                  Live <ElapsedTime
                                    startMs={matchStartMs}
                                    maxMs={matchStartMs + 100 * 60 * 1000}
                                    onMax={() => setRenderTick((n) => n + 1)}
                                  />
                                </span>
                              </span>
                            ) : (
                              formatDateTime(match.start_datetime)
                            )}
                          </span>
                          <div className="row-start-2 col-start-1 md:row-auto md:col-auto flex items-center justify-end gap-2 px-2">
                            <span className="text-sm text-right text-gray-900 dark:text-gray-100 truncate">
                              <span className="md:hidden">{match.home_team?.iso_code ?? match.home_team?.name ?? '—'}</span>
                              <span className="hidden md:inline">{match.home_team?.name ?? '—'}</span>
                            </span>
                            {match.home_team?.image_url ? (
                              <img src={match.home_team.image_url} alt={match.home_team.name}
                                decoding="async" referrerPolicy="no-referrer" className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-700" />
                            ) : (
                              <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 inline-block" />
                            )}
                          </div>
                          <div className="row-start-2 col-start-2 md:row-auto md:col-auto flex justify-center items-center" onClick={(e) => e.stopPropagation()}>
                            <ScoreInput
                              matchId={match.id}
                              prediction={predictionMap.get(match.id)}
                              isOwn={isEditable}
                              disabled={matchDisabled || isGeneratingRandom}
                              userId={adminEditingOther ? targetUserId : undefined}
                              tournamentId={tournamentId}
                              onBeforeSave={adminEditingOther ? confirmAdminEdit : undefined}
                            />
                          </div>
                          <div className="row-start-2 col-start-3 md:row-auto md:col-auto flex items-center justify-start gap-2 px-2">
                            {match.away_team?.image_url ? (
                              <img src={match.away_team.image_url} alt={match.away_team.name}
                                decoding="async" referrerPolicy="no-referrer" className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-700" />
                            ) : (
                              <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 inline-block" />
                            )}
                            <span className="text-sm text-left text-gray-900 dark:text-gray-100 truncate">
                              <span className="md:hidden">{match.away_team?.iso_code ?? match.away_team?.name ?? '—'}</span>
                              <span className="hidden md:inline">{match.away_team?.name ?? '—'}</span>
                            </span>
                          </div>
                          {/* Mobile-only: actual match score centred in row 1 between date and status */}
                          {match.home_goals != null && match.away_goals != null && (
                            <div className="flex md:hidden row-start-1 col-start-2 justify-center items-center self-center">
                              <span className="text-xs italic text-gray-400 dark:text-gray-500 whitespace-nowrap font-mono">
                                (Match: {match.home_goals}-{match.away_goals})
                              </span>
                            </div>
                          )}
                          <div className="row-start-1 col-start-3 md:row-auto md:col-auto justify-self-end flex items-center gap-1.5">
                            <div className="flex flex-col items-end gap-0.5">
                              {(() => {
                                const pred = predictionMap.get(match.id)
                                const isPast = matchStartMs <= renderNowMs
                                const actualScore = match.home_goals != null && match.away_goals != null ? (
                                  <span className="hidden md:inline text-xs italic text-gray-400 dark:text-gray-500 whitespace-nowrap font-mono">
                                    (Match: {match.home_goals}-{match.away_goals})
                                  </span>
                                ) : null
                                if (pred?.points_earned != null) {
                                  return (
                                    <>
                                      <span className="text-xs font-semibold text-green-600 dark:text-green-400 whitespace-nowrap">
                                        +{pred.points_earned} pts
                                      </span>
                                      {actualScore}
                                    </>
                                  )
                                }
                                if (isPast && isEditable) {
                                  const hasPrediction = pred?.home_score != null && pred?.away_score != null
                                  if (hasPrediction) {
                                    return (
                                      <>
                                        <span className="text-xs italic text-amber-600/70 dark:text-amber-400/60 whitespace-nowrap">🤞 fingers crossed</span>
                                        {actualScore}
                                      </>
                                    )
                                  }
                                  return (
                                    <>
                                      <span className="text-xs italic text-gray-400 dark:text-gray-500 whitespace-nowrap"><span className="text-[0.8em]">❌</span> <span className="md:hidden">missed</span><span className="hidden md:inline">missed cutoff</span></span>
                                      {actualScore}
                                    </>
                                  )
                                }
                                return match.tv_channel ? (
                                  <span className="text-xs font-medium text-gray-400 dark:text-gray-500 whitespace-nowrap">
                                    {match.tv_channel}
                                  </span>
                                ) : null
                              })()}
                            </div>
                            {matchStartMs <= renderNowMs && (
                              <button
                                onClick={() =>
                                  setSearchParams((prev) => {
                                    const next = new URLSearchParams(prev)
                                    next.set('match', String(match.id))
                                    return next
                                  }, { replace: true })
                                }
                                className="hidden md:inline-flex text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition flex-shrink-0"
                                aria-label="View match stats"
                              >
                                <Search size={14} />
                              </button>
                            )}
                          </div>
                          {matchStartMs <= renderNowMs && (
                            <button
                              onClick={() =>
                                setSearchParams((prev) => {
                                  const next = new URLSearchParams(prev)
                                  next.set('match', String(match.id))
                                  return next
                                }, { replace: true })
                              }
                              className="md:hidden absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition"
                              aria-label="View match stats"
                            >
                              <Search size={14} />
                            </button>
                          )}
                        </li>
                      </Fragment>
                    )
                  })}
                </ul>
              </div>
            ))})()}
          </section>
        )}
      </div>
    </PageShell>
  )
}

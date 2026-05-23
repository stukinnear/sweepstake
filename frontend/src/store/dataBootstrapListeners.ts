/**
 * Data bootstrap listeners.
 *
 * When the tournament list is fetched successfully, automatically prefetch
 * matches and all prediction types for every tournament the user belongs to.
 * This file is imported as a side-effect in store.ts to register the listeners.
 */
import { listenerMiddleware } from './listenerMiddleware'
import { baseApi } from '../api/baseApi'
import { authApi } from '../api/authApi'
import { tournamentApi } from '../api/tournamentApi'
import { matchApi } from '../api/matchApi'
import { tournamentPredictionApi, groupPredictionApi, stagePredictionApi, matchPredictionApi } from '../api/predictionApi'

// On successful logout, wipe the entire RTK Query cache so no stale
// user-specific data remains in the store.
listenerMiddleware.startListening({
  matcher: authApi.endpoints.logout.matchFulfilled,
  effect: (_action, listenerApi) => {
    listenerApi.dispatch(baseApi.util.resetApiState())
  },
})

listenerMiddleware.startListening({
  matcher: tournamentApi.endpoints.listTournaments.matchFulfilled,
  effect: async (action, listenerApi) => {
    const tournaments = action.payload

    for (const tournament of tournaments) {
      const id = tournament.id

      // Prefetch in parallel — fire-and-forget; RTK Query deduplicates in-flight requests.
      listenerApi.dispatch(matchApi.endpoints.listMatches.initiate(id))
      listenerApi.dispatch(tournamentPredictionApi.endpoints.getTournamentPredictions.initiate({ tournamentId: id }))
      listenerApi.dispatch(groupPredictionApi.endpoints.listGroupPredictions.initiate({ tournamentId: id }))
      listenerApi.dispatch(stagePredictionApi.endpoints.listStagePredictions.initiate({ tournamentId: id }))
      listenerApi.dispatch(matchPredictionApi.endpoints.listMatchPredictions.initiate({ tournamentId: id }))
    }
  },
})

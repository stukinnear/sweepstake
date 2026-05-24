import { lazy, Suspense, useEffect, useRef } from 'react'
import { Routes, Route, Navigate, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAppSelector } from './store/hooks'
import { useGetMeQuery } from './api/authApi'
import { useListTournamentsQuery } from './api/tournamentApi'
import { BugReportButton } from './components/BugReportButton'

const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((m) => ({ default: m.RegisterPage })))
const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })))
const OverviewPage = lazy(() => import('./pages/OverviewPage').then((m) => ({ default: m.OverviewPage })))
const TournamentPage = lazy(() => import('./pages/TournamentPage').then((m) => ({ default: m.TournamentPage })))
const PredictionsPage = lazy(() => import('./pages/PredictionsPage').then((m) => ({ default: m.PredictionsPage })))
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage').then((m) => ({ default: m.LeaderboardPage })))

function PageFallback() {
  return (
    <div className="flex h-screen items-center justify-center bg-gray-900">
      <span className="text-gray-400">Loading…</span>
    </div>
  )
}

/** Redirects already-authenticated users away from guest-only pages (e.g. /login, /register). */
function GuestRoute() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const bootstrapped = useAppSelector((state) => state.auth.bootstrapped)
  const location = useLocation()
  const { isLoading } = useGetMeQuery(undefined, { skip: bootstrapped })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900">
        <span className="text-gray-400">Loading…</span>
      </div>
    )
  }

  if (isAuthenticated) {
    const params = new URLSearchParams(location.search)
    const redirectTo = params.get('redirect')
    const joinCode = params.get('join')
    const dest = redirectTo ?? '/overview'
    const destWithJoin = joinCode ? `${dest}${dest.includes('?') ? '&' : '?'}join=${encodeURIComponent(joinCode)}` : dest
    return <Navigate to={destWithJoin} replace />
  }

  return <Outlet />
}

function ProtectedRoute() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const bootstrapped = useAppSelector((state) => state.auth.bootstrapped)
  const location = useLocation()
  // Skip getMe once we know the user is not authenticated — prevents spurious
  // re-fetches (and the resulting 401 + refresh attempt) after logout.
  const { isLoading } = useGetMeQuery(undefined, { skip: bootstrapped && !isAuthenticated })
  useListTournamentsQuery(undefined, { skip: !isAuthenticated })
  const wasAuthenticated = useRef(false)

  useEffect(() => {
    wasAuthenticated.current = isAuthenticated
  }, [isAuthenticated])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900">
        <span className="text-gray-400">Loading…</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    // Do not add ?redirect= when logging out (was previously authenticated).
    if (wasAuthenticated.current) {
      return <Navigate to="/login" replace />
    }
    const redirect = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?redirect=${redirect}`} replace />
  }

  return <Outlet />
}

/** Redirects to /login whenever the user transitions from authenticated → unauthenticated. */
function AuthRedirect() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const navigate = useNavigate()
  const wasAuthenticated = useRef(false)

  useEffect(() => {
    if (wasAuthenticated.current && !isAuthenticated) {
      navigate('/login', { replace: true })
    }
    wasAuthenticated.current = isAuthenticated
  }, [isAuthenticated, navigate])

  return null
}

export default function App() {
  return (
    <>
    <AuthRedirect />
    <BugReportButton />
    <Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<HomePage />} />

        {/* Redirects to /overview if already logged in */}
        <Route element={<GuestRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes — require an active session */}
        <Route element={<ProtectedRoute />}>
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/tournament/:id" element={<TournamentPage />} />
          <Route path="/tournament/:id/leaderboard" element={<LeaderboardPage />} />
          <Route path="/tournament/:id/predictions" element={<PredictionsPage />} />
          <Route path="/tournament/:id/predictions/:userId" element={<PredictionsPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
    </>
  )
}

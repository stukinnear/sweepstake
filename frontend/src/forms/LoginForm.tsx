import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useLoginMutation } from '../api/authApi'
import { tournamentApi } from '../api/tournamentApi'
import { useAppDispatch } from '../store/hooks'
import { getApiErrorMessage } from '../api/apiError'
import { useGetConfigQuery } from '../api/configApi'

export function LoginForm() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirectTo = searchParams.get('redirect')
  const joinCode = searchParams.get('join')
  const dispatch = useAppDispatch()
  const [login, { isLoading, error }] = useLoginMutation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { data: config } = useGetConfigQuery()

  useEffect(() => {
    if (config?.demo_mode && !email && !password) {
      setEmail('test@example.com')
      setPassword('Password')
    }
  }, [config?.demo_mode])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await login({ email, password }).unwrap()
      if (redirectTo) {
        navigate(redirectTo, { replace: true })
        return
      }
      if (joinCode) {
        navigate(`/overview?join=${encodeURIComponent(joinCode)}`)
        return
      }
      const tournaments = await dispatch(
        tournamentApi.endpoints.listTournaments.initiate()
      ).unwrap()
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const active = tournaments.filter((t) => {
        if (!t.end_date) return false
        const cutoff = new Date(t.end_date)
        cutoff.setDate(cutoff.getDate() + 5)
        return today <= cutoff
      })
      navigate(active.length === 1 ? `/tournament/${active[0].id}${config?.demo_mode ? '?guide=admin' : ''}` : '/overview')
    } catch {
      // error shown below
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <h1 className="text-3xl font-extrabold tracking-tight text-center text-gray-900 dark:text-white mb-2">
        Sweep<span className="text-teal-500">Stake</span>
      </h1>
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Sign in</h2>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{getApiErrorMessage(error, 'Login failed')}</p>
      )}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-base sm:text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:focus:ring-teal-400"
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-base sm:text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:focus:ring-teal-400"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !email || !password}
        className="w-full rounded bg-teal-600 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 dark:bg-teal-500 dark:hover:bg-teal-600"
      >
        {isLoading ? 'Signing in…' : 'Sign in'}
      </button>
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        No account?{' '}
        <Link to={`/register${searchParams.toString() ? `?${searchParams.toString()}` : ''}`} className="text-teal-600 hover:underline dark:text-teal-400">
          Register
        </Link>
      </p>
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        <Link to="/forgot-password" className="text-teal-600 hover:underline dark:text-teal-400">
          Forgot password?
        </Link>
      </p>
    </form>
  )
}

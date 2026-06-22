import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useForgotPasswordMutation } from '../api/authApi'
import { getApiErrorMessage } from '../api/apiError'

export function ForgotPasswordForm() {
  const [forgotPassword, { isLoading, error }] = useForgotPasswordMutation()
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await forgotPassword({ email }).unwrap()
      setSubmitted(true)
    } catch {
      // error shown below
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <h1 className="text-3xl font-extrabold tracking-tight text-center text-gray-900 dark:text-white mb-2">
        Sweep<span className="text-teal-500">Stake</span>
      </h1>
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Reset password</h2>
      {submitted ? (
        <p className="text-sm text-green-600 dark:text-green-400">
          If that email is registered you will receive a reset link shortly.
        </p>
      ) : (
        <>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Enter your email address and we'll send you a link to reset your password.
          </p>
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">
              {getApiErrorMessage(error, 'Something went wrong')}
            </p>
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
          <button
            type="submit"
            disabled={isLoading || !email}
            className="w-full rounded bg-teal-600 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 dark:bg-teal-500 dark:hover:bg-teal-600"
          >
            {isLoading ? 'Sending…' : 'Send reset link'}
          </button>
        </>
      )}
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        <Link to="/login" className="text-teal-600 hover:underline dark:text-teal-400">
          Back to sign in
        </Link>
      </p>
    </form>
  )
}

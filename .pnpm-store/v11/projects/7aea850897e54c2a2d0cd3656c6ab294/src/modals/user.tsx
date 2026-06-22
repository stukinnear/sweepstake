import { useState } from 'react'
import { Check } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useUpdateMeMutation, useChangePasswordMutation, useDeleteMeMutation } from '../api/authApi'
import { useJoinTournamentMutation } from '../api/tournamentApi'
import { useAppSelector } from '../store/hooks'
import type { Gender } from '../types'
import {
  BtnDanger,
  BtnPrimary,
  BtnSecondary,
  ErrorMsg,
  FieldLabel,
  ModalBody,
  ModalFooter,
  ModalShell,
  fieldClass,
} from './base'

const fieldErrorClass =
  'w-full rounded border border-red-500 dark:border-red-500 bg-white dark:bg-gray-800 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:opacity-50 disabled:cursor-not-allowed'


export function SettingsModal({ onClose }: { onClose: () => void }) {
  const user = useAppSelector((state) => state.auth.user)
  const [updateMe, { isLoading: isSaving }] = useUpdateMeMutation()
  const [changePassword, { isLoading: isChangingPassword }] = useChangePasswordMutation()
  const [deleteMe, { isLoading: isDeleting }] = useDeleteMeMutation()
  const isLoading = isSaving || isChangingPassword || isDeleting

  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [userName, setUserName] = useState(user?.user_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [gender, setGender] = useState<Gender | ''>(user?.gender ?? '')
  const [error, setError] = useState<string | null>(null)

  const [repeatEmail, setRepeatEmail] = useState('')

  const originalEmail = user?.email ?? ''
  const emailChanged = email !== originalEmail
  const emailConfirmed = !emailChanged || (email.length > 0 && email === repeatEmail)
  const showRepeatEmail = emailChanged && !emailConfirmed
  const emailMismatch = showRepeatEmail

  const [newPassword, setNewPassword] = useState('')
  const [repeatNewPassword, setRepeatNewPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')

  const newPasswordFilled = newPassword.length > 0
  const newPasswordConfirmed = !newPasswordFilled || (newPassword.length > 0 && newPassword === repeatNewPassword)
  const showRepeatPassword = newPasswordFilled && !newPasswordConfirmed
  const passwordMismatch = showRepeatPassword
  const canSave = emailConfirmed && newPasswordConfirmed && (!newPasswordFilled || currentPassword.length > 0)

  async function handleDeleteAccount() {
    const confirmed = window.confirm(
      'Are you sure you want to permanently delete your account?\n\n' +
      'This will delete all your predictions and any competition where you are the last admin. ' +
      'This action cannot be undone.'
    )
    if (!confirmed) return
    try {
      await deleteMe().unwrap()
      onClose()
    } catch {
      setError('Failed to delete account. Please try again.')
    }
  }

  async function handleSave() {
    if (!canSave) return
    setError(null)
    try {
      await updateMe({
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        user_name: userName || undefined,
        email: email || undefined,
        gender: (gender as Gender) || undefined,
      }).unwrap()
      if (newPasswordFilled) {
        await changePassword({ current_password: currentPassword, new_password: newPassword }).unwrap()
      }
      onClose()
    } catch {
      setError('Failed to save changes. Please try again.')
    }
  }

  return (
    <ModalShell title="Profile Settings" onClose={onClose}>
      <ModalBody>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>First name</FieldLabel>
            <input
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              disabled={isLoading}
              className={fieldClass}
            />
          </div>
          <div>
            <FieldLabel>Last name</FieldLabel>
            <input
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              disabled={isLoading}
              className={fieldClass}
            />
          </div>
        </div>
        <div>
          <FieldLabel>Username</FieldLabel>
          <input
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            disabled={isLoading}
            className={fieldClass}
          />
        </div>
        <div>
          <FieldLabel>Email</FieldLabel>
          <div className="relative">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              className={`${emailMismatch ? fieldErrorClass : fieldClass}${emailConfirmed && emailChanged ? ' pr-9' : ''}`}
            />
            {emailConfirmed && emailChanged && (
              <Check className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-green-500" aria-hidden="true" />
            )}
          </div>
        </div>
        {showRepeatEmail && (
          <div>
            <FieldLabel>Repeat new email</FieldLabel>
            <input
              type="email"
              value={repeatEmail}
              onChange={(e) => setRepeatEmail(e.target.value)}
              disabled={isLoading}
              className={emailMismatch ? fieldErrorClass : fieldClass}
            />
          </div>
        )}
        <div>
          <FieldLabel>Gender</FieldLabel>
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value as Gender | '')}
            disabled={isLoading}
            className={fieldClass}
          >
            <option value="">— not specified —</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <hr className="border-gray-200 dark:border-gray-700" />

        {/* New password */}
        <div>
          <FieldLabel>New password</FieldLabel>
          <div className="relative">
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isLoading}
              className={`${passwordMismatch ? fieldErrorClass : fieldClass}${newPasswordConfirmed && newPasswordFilled ? ' pr-9' : ''}`}
            />
            {newPasswordConfirmed && newPasswordFilled && (
              <Check className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-green-500" aria-hidden="true" />
            )}
          </div>
        </div>

        {showRepeatPassword && (
          <div>
            <FieldLabel>Repeat new password</FieldLabel>
            <input
              type="password"
              value={repeatNewPassword}
              onChange={(e) => setRepeatNewPassword(e.target.value)}
              disabled={isLoading}
              className={passwordMismatch ? fieldErrorClass : fieldClass}
            />
          </div>
        )}

        {newPasswordFilled && (
          <div>
            <FieldLabel>Current password</FieldLabel>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={isLoading}
              className={fieldClass}
            />
          </div>
        )}

        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter justify="between">
        <BtnDanger onClick={handleDeleteAccount} disabled={isLoading} loading={isDeleting}>
          Delete Account
        </BtnDanger>
        <div className="flex items-center gap-2">
          <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
          <BtnPrimary onClick={handleSave} disabled={isLoading || !canSave} loading={isSaving || isChangingPassword}>
            {isSaving || isChangingPassword ? 'Saving…' : 'Save'}
          </BtnPrimary>
        </div>
      </ModalFooter>
    </ModalShell>
  )
}

export function JoinTournamentModal({ onClose, initialCode }: { onClose: () => void; initialCode?: string }) {
  const navigate = useNavigate()
  const [joinTournament, { isLoading }] = useJoinTournamentMutation()
  const [joinCode, setJoinCode] = useState(initialCode ?? '')
  const [error, setError] = useState<string | null>(null)

  const JOIN_CODE_RE = /^[A-Za-z0-9]{0,8}\d{8}$/

  function validateJoinCode(code: string): string | null {
    if (!code) return 'Please enter a join code.'
    if (code.length < 8 || code.length > 16) return 'Join code must be 8–16 characters.'
    if (!JOIN_CODE_RE.test(code)) return 'Join code must be 0–8 alphanumeric characters followed by exactly 8 digits, with no spaces or special characters.'
    return null
  }

  async function handleJoin() {
    const trimmed = joinCode.trim()
    const validationError = validateJoinCode(trimmed)
    if (validationError) { setError(validationError); return }
    setError(null)
    try {
      const tournament = await joinTournament(trimmed).unwrap()
      onClose()
      navigate(`/tournament/${tournament.id}?guide=participant`)
    } catch {
      setError('Invalid join code or you are already a member.')
    }
  }

  return (
    <ModalShell title="Join Competition" onClose={onClose} maxWidth="max-w-sm">
      <ModalBody>
        <div>
          <FieldLabel>Join code</FieldLabel>
          <input
            autoFocus
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
            placeholder="Enter join code…"
            disabled={isLoading}
            className={fieldClass}
          />
          {joinCode.trim() && validateJoinCode(joinCode.trim()) && (
            <p className="mt-2 text-xs text-red-500">{validateJoinCode(joinCode.trim())}</p>
          )}
        </div>
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter>
        <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
        <BtnPrimary onClick={handleJoin} disabled={isLoading || !!validateJoinCode(joinCode.trim())} loading={isLoading}>
          {isLoading ? 'Joining…' : 'Join'}
        </BtnPrimary>
      </ModalFooter>
    </ModalShell>
  )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUpdateMeMutation } from '../api/authApi'
import { useJoinTournamentMutation } from '../api/tournamentApi'
import { useAppSelector } from '../store/hooks'
import type { Gender } from '../types'
import {
  BtnPrimary,
  BtnSecondary,
  ErrorMsg,
  FieldLabel,
  ModalBody,
  ModalFooter,
  ModalShell,
  fieldClass,
} from './base'

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const user = useAppSelector((state) => state.auth.user)
  const [updateMe, { isLoading }] = useUpdateMeMutation()

  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [userName, setUserName] = useState(user?.user_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [gender, setGender] = useState<Gender | ''>(user?.gender ?? '')
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    setError(null)
    try {
      await updateMe({
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        user_name: userName || undefined,
        email: email || undefined,
        gender: (gender as Gender) || undefined,
      }).unwrap()
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
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            className={fieldClass}
          />
        </div>
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
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter>
        <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
        <BtnPrimary onClick={handleSave} disabled={isLoading} loading={isLoading}>
          {isLoading ? 'Saving…' : 'Save'}
        </BtnPrimary>
      </ModalFooter>
    </ModalShell>
  )
}

export function JoinTournamentModal({ onClose, initialCode }: { onClose: () => void; initialCode?: string }) {
  const navigate = useNavigate()
  const [joinTournament, { isLoading }] = useJoinTournamentMutation()
  const [joinCode, setJoinCode] = useState(initialCode ?? '')
  const [error, setError] = useState<string | null>(null)

  async function handleJoin() {
    if (!joinCode.trim()) return
    setError(null)
    try {
      const tournament = await joinTournament(joinCode.trim()).unwrap()
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
        </div>
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter>
        <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
        <BtnPrimary onClick={handleJoin} disabled={isLoading || !joinCode.trim()} loading={isLoading}>
          {isLoading ? 'Joining…' : 'Join'}
        </BtnPrimary>
      </ModalFooter>
    </ModalShell>
  )
}

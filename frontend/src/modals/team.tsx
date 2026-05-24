import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useListGroupsQuery, useCreateGroupMutation, useUpdateGroupMutation, useDeleteGroupMutation } from '../api/groupApi'
import { useListTeamsQuery, useCreateTeamMutation, useUpdateTeamMutation, useDeleteTeamMutation } from '../api/teamApi'
import {
  BtnDanger,
  BtnPrimary,
  BtnSecondary,
  ErrorMsg,
  FieldLabel,
  ModalBackdrop,
  ModalBody,
  ModalBox,
  ModalFooter,
  ModalHeader,
  ModalShell,
  fieldClass,
} from './base'

// ---------------------------------------------------------------------------
// Shared form fields for team name / iso / image / group
// ---------------------------------------------------------------------------

function TeamFormFields({
  name,
  setName,
  isoCode,
  setIsoCode,
  imageUrl,
  setImageUrl,
  groupId,
  setGroupId,
  groups,
  autoFocus,
  onEnter,
  disabled,
}: {
  name: string
  setName: (v: string) => void
  isoCode: string
  setIsoCode: (v: string) => void
  imageUrl: string
  setImageUrl: (v: string) => void
  groupId: string
  setGroupId: (v: string) => void
  groups: { id: number; name: string }[]
  autoFocus?: boolean
  onEnter?: () => void
  disabled?: boolean
}) {
  return (
    <>
      <div>
        <FieldLabel>Name</FieldLabel>
        <input
          autoFocus={autoFocus}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onEnter?.()}
          disabled={disabled}
          className={fieldClass}
        />
      </div>
      <div>
        <FieldLabel>ISO code</FieldLabel>
        <input
          type="text"
          value={isoCode}
          onChange={(e) => setIsoCode(e.target.value)}
          placeholder="e.g. DE"
          disabled={disabled}
          className={fieldClass}
        />
      </div>
      <div>
        <FieldLabel>Image URL</FieldLabel>
        <input
          type="url"
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          placeholder="https://…"
          disabled={disabled}
          className={fieldClass}
        />
      </div>
      <div>
        <FieldLabel>Group</FieldLabel>
        <select value={groupId} onChange={(e) => setGroupId(e.target.value)} disabled={disabled} className={fieldClass}>
          <option value="">— no group —</option>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// EditTeamModal
// ---------------------------------------------------------------------------

export function EditTeamModal({
  team,
  tournamentId,
  onClose,
}: {
  team: { id: number; name: string; iso_code: string | null; image_url: string | null; group_id: number | null }
  tournamentId: number
  onClose: () => void
}) {
  const { data: groups = [] } = useListGroupsQuery(tournamentId)
  const [updateTeam, { isLoading: isSaving }] = useUpdateTeamMutation()
  const [deleteTeam, { isLoading: isDeleting }] = useDeleteTeamMutation()
  const isLoading = isSaving || isDeleting

  const [name, setName] = useState(team.name)
  const [isoCode, setIsoCode] = useState(team.iso_code ?? '')
  const [imageUrl, setImageUrl] = useState(team.image_url ?? '')
  const [groupId, setGroupId] = useState(team.group_id?.toString() ?? '')
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    if (!name.trim()) return
    setError(null)
    try {
      await updateTeam({
        id: team.id,
        tournamentId,
        data: {
          name: name.trim(),
          iso_code: isoCode.trim() || undefined,
          image_url: imageUrl.trim() || undefined,
          group_id: groupId ? Number(groupId) : undefined,
        },
      }).unwrap()
      onClose()
    } catch {
      setError('Failed to save changes. Please try again.')
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return
    setError(null)
    try {
      await deleteTeam({ id: team.id, tournamentId }).unwrap()
      onClose()
    } catch {
      setError('Failed to delete team. Please try again.')
    }
  }

  return (
    <ModalShell title="Edit Team" onClose={onClose} zIndex="z-[80]" maxWidth="max-w-sm">
      <ModalBody>
        <TeamFormFields
          name={name} setName={setName}
          isoCode={isoCode} setIsoCode={setIsoCode}
          imageUrl={imageUrl} setImageUrl={setImageUrl}
          groupId={groupId} setGroupId={setGroupId}
          groups={groups}
          disabled={isLoading}
        />
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter justify="between">
        <BtnDanger onClick={handleDelete} disabled={isLoading} loading={isDeleting}>
          {isDeleting ? 'Deleting…' : 'Delete'}
        </BtnDanger>
        <div className="flex gap-2">
          <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
          <BtnPrimary onClick={handleSave} disabled={isLoading || !name.trim()} loading={isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </BtnPrimary>
        </div>
      </ModalFooter>
    </ModalShell>
  )
}

// ---------------------------------------------------------------------------
// AddTeamModal
// ---------------------------------------------------------------------------

export function AddTeamModal({
  tournamentId,
  onCreated,
  onClose,
}: {
  tournamentId: number
  onCreated: (teamId: number) => void
  onClose: () => void
}) {
  const { data: groups = [] } = useListGroupsQuery(tournamentId)
  const [createTeam, { isLoading: isSaving }] = useCreateTeamMutation()

  const [name, setName] = useState('')
  const [isoCode, setIsoCode] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [groupId, setGroupId] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    if (!name.trim()) return
    setError(null)
    try {
      const team = await createTeam({
        name: name.trim(),
        tournament_id: tournamentId,
        iso_code: isoCode.trim() || undefined,
        image_url: imageUrl.trim() || undefined,
        group_id: groupId ? Number(groupId) : undefined,
      }).unwrap()
      onCreated(team.id)
      onClose()
    } catch {
      setError('Failed to create team. Please try again.')
    }
  }

  return (
    <ModalShell title="Add Team" onClose={onClose} zIndex="z-[80]" maxWidth="max-w-sm">
      <ModalBody>
        <TeamFormFields
          name={name} setName={setName}
          isoCode={isoCode} setIsoCode={setIsoCode}
          imageUrl={imageUrl} setImageUrl={setImageUrl}
          groupId={groupId} setGroupId={setGroupId}
          groups={groups}
          autoFocus
          onEnter={handleSave}
          disabled={isSaving}
        />
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter>
        <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
        <BtnPrimary onClick={handleSave} disabled={isSaving || !name.trim()} loading={isSaving}>
          {isSaving ? 'Saving…' : 'Add'}
        </BtnPrimary>
      </ModalFooter>
    </ModalShell>
  )
}

// ---------------------------------------------------------------------------
// TeamPickerModal
// ---------------------------------------------------------------------------

export function TeamPickerModal({
  tournamentId,
  onSelect,
  onClose,
}: {
  tournamentId: number
  onSelect: (teamId: number) => void
  onClose: () => void
}) {
  const { data: teams = [] } = useListTeamsQuery(tournamentId)
  const { data: groups = [] } = useListGroupsQuery(tournamentId)
  const [createGroup, { isLoading: isCreatingGroup }] = useCreateGroupMutation()
  const [updateGroup] = useUpdateGroupMutation()
  const [deleteGroup] = useDeleteGroupMutation()
  const [newGroupName, setNewGroupName] = useState('')
  const [createGroupError, setCreateGroupError] = useState<string | null>(null)
  const [editingTeam, setEditingTeam] = useState<(typeof teams)[number] | null>(null)
  const [showAddTeam, setShowAddTeam] = useState(false)

  // Group teams by group_name (null → "No group")
  const groupedTeams: { groupName: string; groupId: number | null; teamList: typeof teams }[] = []
  const byGroup = new Map<string, { groupId: number | null; teamList: typeof teams }>()
  for (const t of teams) {
    const key = t.group_name ?? 'No group'
    const entry = byGroup.get(key) ?? { groupId: t.group_id, teamList: [] }
    entry.teamList.push(t)
    byGroup.set(key, entry)
  }
  const orderedGroupNames = groups.map((g) => g.name)
  const groupsWithTeams = groups
    .filter((g) => (byGroup.get(g.name)?.teamList.length ?? 0) > 0)
    .sort((a, b) => a.name.localeCompare(b.name))
  const groupsWithoutTeams = groups
    .filter((g) => (byGroup.get(g.name)?.teamList.length ?? 0) === 0)
    .sort((a, b) => a.name.localeCompare(b.name))
  for (const g of [...groupsWithTeams, ...groupsWithoutTeams]) {
    const entry = byGroup.get(g.name)
    groupedTeams.push({ groupName: g.name, groupId: g.id, teamList: entry?.teamList ?? [] })
  }
  for (const [key, entry] of byGroup.entries()) {
    if (!orderedGroupNames.includes(key)) {
      groupedTeams.push({ groupName: key, groupId: entry.groupId, teamList: entry.teamList })
    }
  }

  async function handleCreateGroup() {
    if (!newGroupName.trim()) return
    setCreateGroupError(null)
    try {
      await createGroup({ name: newGroupName.trim(), tournament_id: tournamentId }).unwrap()
      setNewGroupName('')
    } catch {
      setCreateGroupError('Failed to create group.')
    }
  }

  async function handleGroupWinnerChange(groupId: number, teamId: number | null) {
    await updateGroup({
      id: groupId,
      tournamentId,
      data: { winner_team_id: teamId ?? undefined },
    })
  }

  return (
    <ModalBackdrop zIndex="z-[70]">
      {editingTeam && (
        <EditTeamModal
          team={editingTeam}
          tournamentId={tournamentId}
          onClose={() => setEditingTeam(null)}
        />
      )}
      {showAddTeam && (
        <AddTeamModal
          tournamentId={tournamentId}
          onCreated={() => {}}
          onClose={() => setShowAddTeam(false)}
        />
      )}
      <ModalBox maxWidth="max-w-sm" flex>
        <ModalHeader title="Select Team" onClose={onClose}>
          <button
            type="button"
            onClick={() => setShowAddTeam(true)}
            className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 transition"
            title="Add new team"
          >
            <Plus size={12} />
            Team
          </button>
        </ModalHeader>
        <div className="overflow-y-auto flex-1 px-4 py-3 space-y-3 max-h-[80vh]">
          {groupedTeams.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 px-2">
              No teams yet. Add one above.
            </p>
          )}
          {groupedTeams.map(({ groupName, groupId, teamList }) => {
            const group = groups.find((g) => g.id === groupId)
            const winnerId = group?.winner_team_id ?? null
            return (
              <div key={groupName}>
                <div className="flex items-center justify-between px-2 mb-1">
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {groupName}
                  </p>
                  <div className="flex items-center gap-2">
                    {groupId != null && teamList.length > 0 && (
                      <select
                        value={winnerId ?? ''}
                        onChange={(e) => handleGroupWinnerChange(groupId, e.target.value ? Number(e.target.value) : null)}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-400"
                      >
                        <option value="">— winner —</option>
                        {teamList.map((t) => (
                          <option key={t.id} value={t.id}>{t.name}</option>
                        ))}
                      </select>
                    )}
                    {teamList.length === 0 && groupId != null && (
                      <button
                        type="button"
                        onClick={() => deleteGroup({ id: groupId, tournamentId })}
                        className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition"
                        title="Delete group"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
                <ul className="space-y-1">
                  {teamList.map((t) => (
                    <li key={t.id}>
                      <div className="flex items-center gap-1 group rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition pr-1">
                        <button
                          type="button"
                          onClick={() => { onSelect(t.id); onClose() }}
                          className="flex-1 flex items-center gap-3 px-3 py-2 text-sm text-left text-gray-900 dark:text-gray-100"
                        >
                          {t.image_url ? (
                            <img
                              src={t.image_url}
                              alt={t.name}
                              decoding="async"
                              className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-700"
                            />
                          ) : (
                            <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 inline-block" />
                          )}
                          {t.name}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingTeam(t)}
                          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition flex-shrink-0 p-1"
                          title="Edit team"
                        >
                          <Pencil size={13} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreateGroup() }}
              placeholder="New group name…"
              disabled={isCreatingGroup}
              className="flex-1 rounded border border-dashed border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="button"
              onClick={handleCreateGroup}
              disabled={isCreatingGroup || !newGroupName.trim()}
              className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 disabled:opacity-40 transition flex-shrink-0"
              title="Add group"
            >
              <Plus size={15} />
            </button>
          </div>
          {createGroupError && <p className="text-xs text-red-500 mt-1">{createGroupError}</p>}
        </div>
      </ModalBox>
    </ModalBackdrop>
  )
}

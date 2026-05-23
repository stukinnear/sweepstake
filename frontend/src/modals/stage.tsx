import { useState, useEffect } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import {
  useListStagesQuery,
  useCreateStageMutation,
  useUpdateStageMutation,
  useDeleteStageMutation,
} from '../api/groupApi'
import { useListTeamsQuery } from '../api/teamApi'
import { BtnPrimary, ModalBackdrop, ModalBox, ModalFooter, ModalHeader, fieldClass } from './base'

export function StageManagerModal({
  tournamentId,
  onClose,
}: {
  tournamentId: number
  onClose: () => void
}) {
  const { data: stages = [] } = useListStagesQuery(tournamentId)
  const { data: teams = [] } = useListTeamsQuery(tournamentId)
  const [createStage, { isLoading: isCreating }] = useCreateStageMutation()
  const [updateStage, { isLoading: isUpdating }] = useUpdateStageMutation()
  const [deleteStage, { isLoading: isDeleting }] = useDeleteStageMutation()
  const isLoading = isCreating || isUpdating || isDeleting
  const [editNames, setEditNames] = useState<Record<number, string>>({})
  const [editWinners, setEditWinners] = useState<Record<number, string>>({})
  const [newName, setNewName] = useState('')

  useEffect(() => {
    setEditNames((prev) => {
      const next = { ...prev }
      for (const s of stages) {
        if (!(s.id in next)) next[s.id] = s.name
      }
      return next
    })
    setEditWinners((prev) => {
      const next = { ...prev }
      for (const s of stages) {
        if (!(s.id in next)) next[s.id] = s.winner_team_id?.toString() ?? ''
      }
      return next
    })
  }, [stages])

  async function handleRename(id: number) {
    const name = editNames[id]?.trim()
    const original = stages.find((s) => s.id === id)?.name
    if (!name || name === original) return
    await updateStage({ id, tournamentId, data: { name } })
  }

  async function handleWinnerChange(id: number, value: string) {
    setEditWinners((prev) => ({ ...prev, [id]: value }))
    await updateStage({ id, tournamentId, data: { winner_team_id: value ? Number(value) : null } })
  }

  async function handleCreate() {
    if (!newName.trim()) return
    await createStage({ name: newName.trim(), tournament_id: tournamentId }).unwrap()
    setNewName('')
  }

  return (
    <ModalBackdrop zIndex="z-[60]">
      <ModalBox maxWidth="max-w-sm">
        <ModalHeader title="Manage Stages" onClose={onClose} />
        <div className="px-6 py-4 space-y-2 max-h-80 overflow-y-auto">
          <div className="flex items-center gap-2 pb-1">
            <span className="flex-1 min-w-0 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Stage
            </span>
            <span className="flex-1 min-w-0 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Winner
            </span>
            <span className="w-[15px] flex-shrink-0" />
          </div>
          {stages.map((s) => (
            <div key={s.id} className="flex items-center gap-2">
              <input
                type="text"
                value={editNames[s.id] ?? s.name}
                onChange={(e) =>
                  setEditNames((prev) => ({ ...prev, [s.id]: e.target.value }))
                }
                onBlur={() => handleRename(s.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') e.currentTarget.blur()
                }}
                disabled={isLoading}
                className={`flex-1 min-w-0 ${fieldClass}`}
              />
              <select
                value={editWinners[s.id] ?? ''}
                onChange={(e) => handleWinnerChange(s.id, e.target.value)}
                disabled={isLoading}
                className={`flex-1 min-w-0 ${fieldClass}`}
              >
                <option value="">— No winner —</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => {
                  const name = editNames[s.id] ?? s.name
                  if (
                    window.confirm(
                      `Delete stage "${name}"? This cannot be undone and all matches in this stage will re-assigned to "Unknown Stage".`,
                    )
                  ) {
                    deleteStage({ id: s.id, tournamentId })
                  }
                }}
                disabled={isLoading}
                className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 disabled:opacity-40 transition flex-shrink-0"
                title="Delete stage"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate()
              }}
              placeholder="New stage name…"
              disabled={isLoading}
              className="flex-1 rounded border border-dashed border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="button"
              onClick={handleCreate}
              disabled={isLoading || !newName.trim()}
              className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 disabled:opacity-40 transition flex-shrink-0"
              title="Add stage"
            >
              <Plus size={15} />
            </button>
          </div>
        </div>
        <ModalFooter>
          <BtnPrimary onClick={onClose}>Done</BtnPrimary>
        </ModalFooter>
      </ModalBox>
    </ModalBackdrop>
  )
}

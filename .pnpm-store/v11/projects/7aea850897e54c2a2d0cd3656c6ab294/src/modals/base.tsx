import { useEffect } from 'react'
import { Loader2, X } from 'lucide-react'

export function useScrollLock() {
  useEffect(() => {
    const count = parseInt(document.body.dataset.modalCount ?? '0', 10)
    document.body.dataset.modalCount = String(count + 1)
    document.body.classList.add('overflow-hidden')
    return () => {
      const next = parseInt(document.body.dataset.modalCount ?? '1', 10) - 1
      document.body.dataset.modalCount = String(next)
      if (next === 0) document.body.classList.remove('overflow-hidden')
    }
  }, [])
}

export const fieldClass =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed'

export function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
      {children}
    </label>
  )
}

export function ErrorMsg({ msg }: { msg: string | null }) {
  if (!msg) return null
  return <p className="text-sm text-red-500">{msg}</p>
}

/** Backdrop overlay. Automatically applies scroll-lock while mounted. */
export function ModalBackdrop({
  zIndex = 'z-50',
  children,
}: {
  zIndex?: string
  children: React.ReactNode
}) {
  useScrollLock()
  return (
    <div
      className={`fixed inset-0 ${zIndex} flex items-center justify-center bg-black/40 backdrop-blur-sm p-4`}
    >
      {children}
    </div>
  )
}

export function ModalBox({
  maxWidth = 'max-w-md',
  flex = false,
  children,
}: {
  maxWidth?: string
  flex?: boolean
  children: React.ReactNode
}) {
  return (
    <div
      className={[
        'w-full rounded-xl bg-white dark:bg-gray-900 shadow-xl',
        maxWidth,
        flex ? 'flex flex-col' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}

export function ModalHeader({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="flex items-center gap-2">
        {children}
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
        >
          <X size={20} />
        </button>
      </div>
    </div>
  )
}

export function ModalBody({
  children,
  scrollable,
  maxHeight,
  flex,
}: {
  children: React.ReactNode
  scrollable?: boolean
  maxHeight?: string
  flex?: boolean
}) {
  return (
    <div
      className={[
        'px-6 py-5 space-y-4',
        scrollable ? `${maxHeight ?? 'max-h-[70vh]'} overflow-y-auto` : '',
        flex ? 'overflow-y-auto flex-1' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}

export function ModalFooter({
  justify = 'end',
  children,
}: {
  justify?: 'end' | 'between'
  children: React.ReactNode
}) {
  return (
    <div
      className={[
        'flex items-center px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0',
        justify === 'between' ? 'justify-between' : 'justify-end gap-2',
      ].join(' ')}
    >
      {children}
    </div>
  )
}

/** Convenience wrapper: backdrop + box + header. Children are body/footer. */
export function ModalShell({
  title,
  onClose,
  zIndex = 'z-50',
  maxWidth = 'max-w-md',
  children,
}: {
  title: string
  onClose: () => void
  zIndex?: string
  maxWidth?: string
  children: React.ReactNode
}) {
  return (
    <ModalBackdrop zIndex={zIndex}>
      <ModalBox maxWidth={maxWidth}>
        <ModalHeader title={title} onClose={onClose} />
        {children}
      </ModalBox>
    </ModalBackdrop>
  )
}

export function BtnPrimary({
  onClick,
  disabled,
  loading,
  children,
}: {
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex items-center gap-1.5 rounded-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-1.5 text-sm font-medium text-white transition"
    >
      {loading && <Loader2 className="animate-spin h-3.5 w-3.5" />}
      {children}
    </button>
  )
}

export function BtnSecondary({
  onClick,
  disabled,
  loading,
  children,
}: {
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex items-center gap-1.5 rounded-full border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition"
    >
      {loading && <Loader2 className="animate-spin h-3.5 w-3.5" />}
      {children}
    </button>
  )
}

export function BtnDanger({
  onClick,
  disabled,
  loading,
  children,
}: {
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex items-center gap-1.5 rounded-full border border-red-300 dark:border-red-700 px-4 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50 transition"
    >
      {loading && <Loader2 className="animate-spin h-3.5 w-3.5" />}
      {children}
    </button>
  )
}

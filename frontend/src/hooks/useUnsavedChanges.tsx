import { useEffect, useState } from 'react'
import { useBlocker } from 'react-router-dom'

export function UnsavedChangesDialog({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Unsaved Changes
        </h2>
        <p className="text-gray-600">
          You have unsaved changes. Are you sure you want to leave?
        </p>
        <div className="flex justify-end gap-3 pt-6">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Stay on Page
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-red-50 hover:text-red-600 hover:border-red-200"
          >
            Discard Changes
          </button>
        </div>
      </div>
    </div>
  )
}

export function useUnsavedChanges(isDirty: boolean) {
  const [showManualDialog, setShowManualDialog] = useState(false)
  const [manualConfirm, setManualConfirm] = useState<(() => void) | null>(null)

  const blocker = useBlocker(isDirty)

  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  const showDialog = blocker.state === 'blocked' || showManualDialog

  const dialog = showDialog ? (
    <UnsavedChangesDialog
      onConfirm={() => {
        if (blocker.state === 'blocked') {
          blocker.proceed?.()
          return
        }
        manualConfirm?.()
        setShowManualDialog(false)
        setManualConfirm(null)
      }}
      onCancel={() => {
        if (blocker.state === 'blocked') {
          blocker.reset?.()
          return
        }
        setShowManualDialog(false)
        setManualConfirm(null)
      }}
    />
  ) : null

  const promptConfirm = (onConfirmAction: () => void) => {
    setManualConfirm(() => onConfirmAction)
    setShowManualDialog(true)
  }

  return { dialog, promptConfirm }
}

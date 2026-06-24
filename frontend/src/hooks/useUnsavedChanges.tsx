import { useEffect, useState } from 'react'
import { useBlocker } from 'react-router-dom'
import UnsavedChangesDialog from '../components/UnsavedChangesDialog'

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

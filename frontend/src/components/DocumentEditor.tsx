import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

interface DocumentEditorProps {
  documentId: number
  initialContent: string
  onSave?: (
    content: string,
    source?: 'manual' | 'autosave'
  ) => Promise<void> | void
  onClose?: () => void
}

export default function DocumentEditor({
  documentId,
  initialContent,
  onSave,
  onClose,
}: DocumentEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [savedContent, setSavedContent] = useState(initialContent)
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const saveTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const [saveError, setSaveError] = useState('')
  const previewHtml = useMemo(
    () => DOMPurify.sanitize(marked.parse(content, { async: false }) as string),
    [content]
  )

  const handleSave = useCallback(async (source: 'manual' | 'autosave' = 'manual') => {
    setIsSaving(true)
    try {
      await onSave?.(content, source)
      setSavedContent(content)
      setSaveError('')
    } catch (error) {
      setSaveError(
        error instanceof Error ? error.message : 'Failed to save changes'
      )
    } finally {
      setIsSaving(false)
    }
  }, [content, onSave])

  // Auto-save after 2 seconds
  useEffect(() => {
    if (saveTimeoutRef.current !== null) {
      window.clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = null
    }

    if (content === savedContent) {
      return
    }

    saveTimeoutRef.current = window.setTimeout(() => {
      void handleSave('autosave')
    }, 2000)

    return () => {
      if (saveTimeoutRef.current !== null) {
        window.clearTimeout(saveTimeoutRef.current)
        saveTimeoutRef.current = null
      }
    }
  }, [content, handleSave, savedContent])

  useEffect(() => {
    setContent(initialContent)
    setSavedContent(initialContent)
    setSaveError('')
    setShowPreview(false)
  }, [documentId, initialContent])

  return (
    <div className="flex flex-col h-full border border-gray-200 rounded-xl overflow-hidden">
      <h2 id="document-editor-title" className="sr-only">
        Document editor
      </h2>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-gray-400">
            Document #{documentId}
          </span>
          <button
            type="button"
            onClick={() => setShowPreview((p) => !p)}
            aria-pressed={showPreview}
            aria-label={showPreview ? 'Switch to edit mode' : 'Switch to preview mode'}
            title={showPreview ? 'Switch to edit mode' : 'Switch to preview mode'}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {showPreview ? 'Edit' : 'Preview'}
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-sm"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            {saveError ? (
              <span className="text-red-500">{saveError}</span>
            ) : isSaving ? (
              <span className="text-gray-500">Saving...</span>
            ) : null}
          </span>
          <button
            type="button"
            onClick={() => void handleSave('manual')}
            disabled={isSaving}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving…' : 'Save'}
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close document editor"
              title="Close document editor"
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Editor / Preview area */}
      <div className="flex-1 overflow-auto">
        {showPreview ? (
          <div className="prose max-w-none p-6">
            <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
          </div>
        ) : (
          <div className="h-full">
            <CodeMirror
              value={content}
              height="100%"
              extensions={[markdown()]}
              onChange={(value) => {
                setContent(value)
                setSaveError('')
              }}
              className="h-full"
            />
          </div>
        )}
      </div>
    </div>
  )
}

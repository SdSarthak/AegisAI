import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '../services/api'

interface DocumentEditorProps {
  documentId: number
  initialContent: string
  onSave?: (content: string) => void
  onClose?: () => void
}

export default function DocumentEditor({
  documentId,
  initialContent,
  onSave,
  onClose,
}: DocumentEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const previewHtml = useMemo(
    () => DOMPurify.sanitize(marked.parse(content, { async: false }) as string),
    [content]
  )

  const handleSave = useCallback(async () => {
    setIsSaving(true)
    setSaveError(null)
    try {
      await api.put(`/documents/${documentId}`, { content })
      onSave?.(content)
    } catch (error) {
      console.error('Save failed:', error)
      setSaveError(
        error instanceof Error ? error.message : 'Failed to save changes'
      )
    }
    setIsSaving(false)
  }, [content, documentId, onSave])

  // Auto-save after 2 seconds
  useEffect(() => {
    if (content === initialContent) return

    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)

    saveTimeoutRef.current = setTimeout(async () => {
      await handleSave()
    }, 2000)

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [content, handleSave, initialContent])

  return (
    <div className="flex flex-col h-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <button
          type="button"
          onClick={() => setShowPreview((p) => !p)}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
        >
          {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {showPreview ? 'Edit' : 'Preview'}
        </button>
        <div className="flex items-center gap-3">
         {saveError && (
            <span className="text-sm text-red-500 dark:text-red-400">
              {saveError}
            </span>
          )}
          {isSaving && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Saving...
            </span>
          )} 
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 dark:bg-primary-700 text-white rounded-lg hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving…' : 'Save'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Editor / Preview area */}
      <div className="flex-1 overflow-auto bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        {showPreview ? (
          <div className="prose dark:prose-invert max-w-none p-6">
            <div dangerouslySetInnerHTML={{ __html: sanitizedPreview }} />
          </div>
        ) : (
          <div className="h-full">
            <CodeMirror
              value={content}
              height="100%"
              extensions={[markdown()]}
              onChange={(value) => setContent(value)}
              className="h-full"
            />
          </div>
        )}
      </div>
    </div>
  )
}


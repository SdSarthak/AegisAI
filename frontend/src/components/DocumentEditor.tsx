import { useState, useEffect, useCallback, useMemo } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
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
  const [saveTimeout, setSaveTimeout] = useState<ReturnType<typeof setTimeout> | null>(null)
  const sanitizedPreview = useMemo(() => {
    const renderedMarkdown = marked.parse(content, { async: false }) as string
    return DOMPurify.sanitize(renderedMarkdown)
  }, [content])
  const [saveError, setSaveError] = useState('')
  const handleSave = useCallback(async () => {
    setIsSaving(true)
    try {
      await api.put(`/documents/${documentId}`, { content })
      onSave?.(content)
      setSaveError('')
    } catch (error) {
      console.error('Save failed:', error)
      setSaveError('Failed to save changes')
    }
    setIsSaving(false)
  }, [content, documentId, onSave])

  // Auto-save after 2 seconds
  useEffect(() => {
    if (content === initialContent) return

    if (saveTimeout) clearTimeout(saveTimeout)

    const timeout = setTimeout(async () => {
      setIsSaving(true)
      await handleSave()
      setIsSaving(false)
    }, 2000)

    setSaveTimeout(timeout)

    return () => {
      if (timeout) clearTimeout(timeout)
    }
  }, [content, handleSave, initialContent, saveTimeout])

  return (
    <div className="flex flex-col h-full border border-gray-200 rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <button
          type="button"
          onClick={() => setShowPreview((p) => !p)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {showPreview ? 'Edit' : 'Preview'}
        </button>
        <div className="flex items-center gap-3">
          
          {saveError && (
  <span className="text-sm text-red-500">
    {saveError}
  </span>
  
)}
{isSaving && <span className="text-sm text-gray-500">Saving...</span>}
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving…' : 'Save'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
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

import { useState, useEffect } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { marked } from 'marked'

interface DocumentEditorProps {
  documentId: number
  initialContent: string
  onSave?: (content: string) => void
  onClose?: () => void
}

export default function DocumentEditor({
  initialContent,
  onSave,
  onClose,
}: DocumentEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)

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
  }, [content])

  const handleSave = async () => {
    setIsSaving(true)
    // Call PUT endpoint
    try {
      const response = await fetch(`/api/v1/documents/${documentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          // Add auth header if needed - check how other API calls are done in your app
        },
        body: JSON.stringify({ content })
      })

      if (response.ok) {
        onSave?.(content)
      }
    } catch (error) {
      console.error('Save failed:', error)
    }
    setIsSaving(false)
  }

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
            <div dangerouslySetInnerHTML={{ __html: marked(content) }} />
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
import { useState } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'

/**
 * DocumentEditor — in-browser Markdown editor for compliance documents.
 *
 * TODO (good first issue — static layout):
 *   - Install CodeMirror: `npm install @uiw/react-codemirror @codemirror/lang-markdown`
 *   - Render a CodeMirror editor pre-filled with `initialContent`.
 *   - Add a preview toggle button that renders the Markdown as HTML using
 *     `npm install marked` (or similar).
 *   - Acceptance criteria: the editor loads with content and the preview
 *     toggle switches between edit/preview views.
 *
 * TODO (help wanted — save logic):
 *   - Add a Save button that calls PUT /api/v1/documents/{id} with the
 *     edited content body.
 *   - Add auto-save with a 2-second debounce after the last keystroke.
 *   - Show a "Saved" / "Saving..." indicator in the top right corner.
 *   - Acceptance criteria: edits are persisted and reflected when the
 *     document is reloaded from the Documents list page.
 */

interface DocumentEditorProps {
  documentId: number
  initialContent: string
  onSave?: (content: string) => void
}

export default function DocumentEditor({
  initialContent,
  onSave,
}: DocumentEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    // TODO (help wanted): call PUT /api/v1/documents/{documentId}
    // await axios.put(`/api/v1/documents/${documentId}`, { content })
    onSave?.(content)
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
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving…' : 'Save'}
        </button>
      </div>

      {/* Editor / Preview area */}
      <div className="flex-1 overflow-auto">
        {showPreview ? (
          <div className="prose max-w-none p-6">
            {/* TODO (good first issue): render `content` as Markdown HTML using `marked` */}
            <p className="text-gray-400 text-sm">
              Markdown preview — install `marked` and render content here
            </p>
          </div>
        ) : (
          <div className="h-full">
            {/*
              TODO (good first issue): replace this textarea with a CodeMirror editor.
              Install: npm install @uiw/react-codemirror @codemirror/lang-markdown
              Import: import CodeMirror from '@uiw/react-codemirror'
                      import { markdown } from '@codemirror/lang-markdown'
            */}
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full p-6 font-mono text-sm resize-none focus:outline-none"
              placeholder="Document content (Markdown)…"
            />
          </div>
        )}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { MessageSquare, ChevronDown, ChevronUp, Loader2, BookOpen } from 'lucide-react'
import { ragApi } from '../services/api'

interface Source {
  title: string
  url?: string
  content?: string
}

interface RagResponse {
  answer: string
  sources: Source[]
}

export default function RagChat() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!query.trim()) return
    setLoading(true)
    setAnswer('')
    setSources([])
    setError('')
    setSourcesOpen(false)

    try {
      const data: RagResponse = await ragApi.query(query)
      setAnswer(data.answer)
      setSources(data.sources || [])
    } catch (err: any) {
      if (err.response?.status === 503) {
        setError('Knowledge base is not yet ready. Please ingest documents first.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-7 h-7 text-primary-600" />
          RAG Regulatory Intelligence
        </h1>
        <p className="text-gray-500 mt-1">
          Ask questions about EU AI Act, GDPR, ISO 42001 and get grounded answers.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 shadow-sm">
        <textarea
          className="w-full resize-none text-gray-800 placeholder-gray-400 outline-none text-sm"
          rows={3}
          placeholder="Ask a regulatory question... e.g. What are the obligations for high-risk AI systems?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit()
            }
          }}
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-4 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Answer */}
      {answer && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm mb-4">
          <div className="p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Answer</h2>
            <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">{answer}</p>
          </div>

          {/* Collapsible Sources */}
          {sources.length > 0 && (
            <div className="border-t border-gray-100">
              <button
                onClick={() => setSourcesOpen(!sourcesOpen)}
                className="w-full flex items-center justify-between px-5 py-3 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <span className="font-medium">Sources ({sources.length})</span>
                {sourcesOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {sourcesOpen && (
                <ul className="px-5 pb-4 space-y-2">
                  {sources.map((src, i) => (
                    <li key={i} className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                      {src.url ? (
                        <a href={src.url} target="_blank" rel="noopener noreferrer"
                          className="text-primary-600 hover:underline font-medium">
                          {src.title || src.url}
                        </a>
                      ) : (
                        <span className="font-medium">{src.title}</span>
                      )}
                      {src.content && (
                        <p className="text-gray-500 mt-1 text-xs">{src.content}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
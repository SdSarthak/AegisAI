import { useState } from 'react'
import { MessageSquare, Loader2, ExternalLink } from 'lucide-react'

export default function RagChat() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [answer, setAnswer] = useState('')

  const handleAsk = async () => {
    if (!question.trim()) return

    setLoading(true)

    // Placeholder interaction until backend API integration
    setTimeout(() => {
      setAnswer(
        'This is a placeholder AI-generated response for the RAG chat interface. Backend API integration will be implemented in a follow-up issue.'
      )
      setLoading(false)
    }, 1200)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">RAG Chat</h1>
        <p className="mt-2 text-gray-600">
          Ask compliance-related questions and view AI-generated answers with source references.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a compliance or AI governance question..."
          rows={5}
          className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />

        <div className="flex justify-end">
          <button
            onClick={handleAsk}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <MessageSquare className="w-4 h-4" />
                Ask
              </>
            )}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Answer
        </h2>

        {loading ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 rounded w-4/6"></div>
          </div>
        ) : answer ? (
          <p className="text-gray-700 leading-relaxed">{answer}</p>
        ) : (
          <p className="text-gray-500">
            Your AI-generated response will appear here.
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Source Citations
        </h2>

        <div className="space-y-3">
          <div className="flex items-start justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50 transition-colors">
            <div>
              <p className="font-medium text-gray-900">
                EU AI Act Documentation
              </p>
              <p className="text-sm text-gray-500">
                Placeholder citation reference for future RAG retrieval integration.
              </p>
            </div>

            <ExternalLink className="w-4 h-4 text-gray-400" />
          </div>

          <div className="flex items-start justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50 transition-colors">
            <div>
              <p className="font-medium text-gray-900">
                Compliance Assessment Report
              </p>
              <p className="text-sm text-gray-500">
                Additional placeholder citation card for UI demonstration.
              </p>
            </div>

            <ExternalLink className="w-4 h-4 text-gray-400" />
          </div>
        </div>
      </div>
    </div>
  )
}
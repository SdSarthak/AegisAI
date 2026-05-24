import { useState } from 'react'
import {
  AlertCircle,
  Bot,
  FileText,
  Loader2,
  Send,
  Sparkles,
  User,
} from 'lucide-react'

import CopyButton from '../components/CopyButton'
import { ragApi } from '../services/api'

interface RagSource {
  title: string
  excerpt: string
}

interface RagAnswer {
  answer: string
  sources: RagSource[]
  answer_id?: string
}

interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string
    }
  }
  message?: string
}

function isApiError(error: unknown): error is ApiError {
  return typeof error === 'object' && error !== null
}

function buildAnswerExport(answer: RagAnswer): string {
  return [
    'AI Response',
    answer.answer,
    '',
    'Source citations',
    ...answer.sources.map(
      (source, index) => `${index + 1}. ${source.title}\n${source.excerpt}`
    ),
  ].join('\n')
}

export default function RagChat() {
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState('')
  const [answer, setAnswer] = useState<RagAnswer | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedbackVote, setFeedbackVote] = useState<'up' | 'down' | null>(null)
  const [feedbackLoading, setFeedbackLoading] = useState(false)

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      setError('Please enter a question before asking.')
      setSubmittedQuestion('')
      setAnswer(null)
      return
    }

    setSubmittedQuestion(trimmedQuestion)
    setQuestion('')
    setIsLoading(true)
    setError(null)
    setAnswer(null)

    try {
      // ✅ REAL API CALL
      const data = await ragApi.query(trimmedQuestion)

      setAnswer({
        answer: data.answer,
        sources: data.sources || [],
      })
    } catch (err: unknown) {
<<<<<<< HEAD
      // ✅ ERROR HANDLING
      const apiError = isApiError(err) ? err : {}

      if (apiError.response?.status === 503) {
        setError('Index not ready. Please try again later.')
      } else if (apiError.response?.status === 401) {
        setError('Unauthorized. Please login again.')
      } else {
        setError(
          apiError.response?.data?.detail ||
            apiError.message ||
=======
      const error = err as {
        response?: {
          status?: number
          data?: {
            detail?: string
          }
        }
        message?: string
      }

      if (error.response?.status === 503) {
        setError('Index not ready. Please try again later.')
      } else if (error.response?.status === 401) {
        setError('Unauthorized. Please login again.')
      } else {
        setError(
          error.response?.data?.detail ||
            error.message ||
>>>>>>> e9cd207 (fix: resolve lint error in RagChat)
            'Unable to generate an answer right now.'
        )
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleFeedback = async (vote: 'up' | 'down') => {
    if (!answer?.answer_id || feedbackVote) return

    setFeedbackLoading(true)

    try {
      await ragApi.feedback({
        answer_id: answer.answer_id,
        vote,
      })

      setFeedbackVote(vote)
    } catch {
      // silently fail
    } finally {
      setFeedbackLoading(false)
    }
  }

  return (
    <div className="h-[calc(100vh-2rem)] md:h-[calc(100vh-4rem)] flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 sm:px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <div className="p-2 sm:p-3 bg-primary-50 rounded-xl">
            <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-primary-600" />
          </div>

          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
              Chatbot
            </h1>

            <p className="text-sm sm:text-base text-gray-600">
              Ask regulatory and compliance questions with source-backed answers
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 sm:space-y-8">
          {!submittedQuestion && !answer && !isLoading && !error && (
            <div className="min-h-[320px] sm:min-h-[420px] flex flex-col items-center justify-center text-center">
              <div className="p-3 sm:p-4 bg-primary-50 rounded-2xl mb-5">
                <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-primary-600" />
              </div>

              <h2 className="text-xl sm:text-2xl font-semibold text-gray-900">
                How can I help with AI compliance?
              </h2>

              <p className="text-sm sm:text-base text-gray-500 mt-2 max-w-xl">
                Ask about EU AI Act risk classification, compliance
                documentation, human oversight, or source-backed regulatory
                guidance.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-6 sm:mt-8 w-full">
                {[
                  'Does my system qualify as high-risk?',
                  'Which documents are needed for compliance?',
                  'What does human oversight require?',
                ].map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuestion(example)}
                    className="text-left bg-white border border-gray-200 rounded-xl p-4 text-sm text-gray-700 hover:border-primary-200 hover:bg-primary-50 transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}

          {(submittedQuestion || answer || isLoading || error) && (
            <div className="space-y-5 sm:space-y-6">
              {submittedQuestion && (
                <div className="flex justify-end">
                  <div className="w-full sm:w-auto sm:max-w-2xl bg-primary-600 text-white rounded-2xl sm:rounded-br-md px-4 sm:px-5 py-3 sm:py-4 shadow-sm">
                    <div className="flex items-start gap-3">
                      <User className="w-5 h-5 mt-0.5 flex-shrink-0" />

                      <p className="text-sm leading-6">
                        {submittedQuestion}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="w-full max-w-3xl bg-white border border-gray-200 rounded-2xl sm:rounded-bl-md px-4 sm:px-5 py-4 shadow-sm">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-primary-50 rounded-lg">
                        <Bot className="w-5 h-5 text-primary-600" />
                      </div>

                      <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
                        <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                        Searching knowledge base
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import { type FormEvent, useState } from 'react'
import {
  Bot,
  Loader2,
  Send,
  Sparkles,
  User,
} from 'lucide-react'

import { ragApi } from '../services/api'

interface RagSource {
  title: string
  excerpt: string
}

type RagSourceResponse = string | RagSource

interface RagAnswer {
  answer: string
  sources: RagSource[]
  answer_id?: string
}

interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string | Array<{ msg?: string }>
    }
  }
  message?: string
}

const RAG_QUESTION_MAX_LENGTH = 2000

function isApiError(error: unknown): error is ApiError {
  return typeof error === 'object' && error !== null
}

function normalizeSources(sources: RagSourceResponse[] = []): RagSource[] {
  return sources
    .map((source) => {
      if (typeof source === 'string') {
        return {
          title: source,
          excerpt: '',
        }
      }

      return source
    })
    .filter((source) => source.title.trim())
}

function getApiErrorMessage(error: ApiError): string {
  const detail = error.response?.data?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg || 'Validation error.'
  }

  return error.message || 'Unable to generate an answer right now.'
}

function buildAnswerExport(answer: RagAnswer): string {
  return [
    'AI Response',
    answer.answer,
    '',
    'Source citations',
    ...answer.sources.map(
      (source, index) =>
        `${index + 1}. ${source.title}\n${source.excerpt}`
    ),
  ].join('\n')
}

export default function RagChat() {
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState('')
  const [answer, setAnswer] = useState<RagAnswer | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAsk = async (e: FormEvent) => {
    e.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      setError('Please enter a question before asking.')
      setSubmittedQuestion('')
      setAnswer(null)
      return
    }

    if (trimmedQuestion.length > RAG_QUESTION_MAX_LENGTH) {
      setError(
        `Question is too long. Please keep it under ${RAG_QUESTION_MAX_LENGTH} characters.`
      )
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
      const data = await ragApi.query(trimmedQuestion)

      setAnswer({
        answer: data.answer,
        sources: normalizeSources(data.sources),
        answer_id: data.answer_id,
      })
    } catch (err: unknown) {
      const apiError = isApiError(err) ? err : {}

      if (apiError.response?.status === 503) {
        setError('Index not ready. Please try again later.')
      } else if (apiError.response?.status === 401) {
        setError('Unauthorized. Please login again.')
      } else {
        setError(getApiErrorMessage(apiError))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = () => {
    if (!answer) return

    const blob = new Blob([buildAnswerExport(answer)], {
      type: 'text/plain;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = 'rag-answer.txt'
    link.click()

    URL.revokeObjectURL(url)
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
                Ask about EU AI Act risk classification, compliance documentation,
                human oversight, or source-backed regulatory guidance.
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

                      <p className="text-sm leading-6">{submittedQuestion}</p>
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

              {!isLoading && error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">
                  {error}
                </div>
              )}

              {!isLoading && !error && answer && (
                <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
                  <div className="prose max-w-none">
                    <p className="text-gray-800 whitespace-pre-line">
                      {answer.answer}
                    </p>
                  </div>

                  {answer.sources.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">
                        Sources
                      </h3>

                      <div className="space-y-3">
                        {answer.sources.map((source, index) => (
                          <div
                            key={`${source.title}-${index}`}
                            className="border border-gray-200 rounded-lg p-3 bg-gray-50"
                          >
                            <p className="font-medium text-sm text-gray-900">
                              {source.title}
                            </p>

                            {source.excerpt && (
                              <p className="text-sm text-gray-600 mt-1">
                                {source.excerpt}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={handleExport}
                    className="mt-6 inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Export answer
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={handleAsk}
        className="border-t border-gray-200 bg-white p-4"
      >
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <textarea
            id="rag-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={RAG_QUESTION_MAX_LENGTH + 1}
            placeholder="Ask a compliance question..."
            rows={1}
            disabled={isLoading}
            className="min-w-0 flex-1 resize-none bg-transparent border-0 p-0 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-0 disabled:text-gray-500"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            aria-label="Ask question"
            title="Ask question"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-3 mt-2">
          <p className="text-xs text-gray-500">
            Ask compliance questions and get source-backed answers.
          </p>

          <p className="text-xs text-gray-400">
            {question.trim().length}/{RAG_QUESTION_MAX_LENGTH} characters
          </p>
        </div>
      </form>
    </div>
  )
}

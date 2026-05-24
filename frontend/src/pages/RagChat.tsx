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
  const [submittedQuestion, setSubmittedQuestion] =
    useState('')

  const [answer, setAnswer] =
    useState<RagAnswer | null>(null)

  const [isLoading, setIsLoading] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const handleAsk = async (
    e: React.FormEvent
  ) => {
    e.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      setError(
        'Please enter a question before asking.'
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
      const data = await ragApi.query(
        trimmedQuestion
      )

      setAnswer({
        answer: data.answer,
        sources: data.sources || [],
      })
    } catch (err: any) {
      if (err.response?.status === 503) {
        setError(
          'Index not ready. Please try again later.'
        )
      } else if (err.response?.status === 401) {
        setError(
          'Unauthorized. Please login again.'
        )
      } else {
        setError(
          err?.response?.data?.detail ||
            err.message ||
            'Unable to generate an answer right now.'
        )
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      className="
        h-[calc(100vh-2rem)] md:h-[calc(100vh-4rem)]
        flex flex-col
        bg-white dark:bg-gray-800
        rounded-xl
        border border-gray-200 dark:border-gray-700
        overflow-hidden
        transition-colors duration-200
      "
    >
      {/* Header */}
      <div
        className="
          px-4 sm:px-6 py-4
          border-b border-gray-200 dark:border-gray-700
          bg-white dark:bg-gray-800
        "
      >
        <div className="flex items-center gap-3">
          <div
            className="
              p-2 sm:p-3
              bg-primary-50 dark:bg-primary-900/20
              rounded-xl
            "
          >
            <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-primary-600 dark:text-primary-400" />
          </div>

          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
              Chatbot
            </h1>

            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
              Ask regulatory and compliance questions with source-backed answers
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 sm:space-y-8">
          {!submittedQuestion &&
            !answer &&
            !isLoading &&
            !error && (
              <div className="min-h-[320px] sm:min-h-[420px] flex flex-col items-center justify-center text-center">
                <div
                  className="
                    p-3 sm:p-4
                    bg-primary-50 dark:bg-primary-900/20
                    rounded-2xl
                    mb-5
                  "
                >
                  <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-primary-600 dark:text-primary-400" />
                </div>

                <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">
                  How can I help with AI compliance?
                </h2>

                <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-2 max-w-xl">
                  Ask about EU AI Act risk
                  classification, compliance
                  documentation, human oversight,
                  or source-backed regulatory
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
                      onClick={() =>
                        setQuestion(example)
                      }
                      className="
                        text-left
                        bg-white dark:bg-gray-800
                        border border-gray-200 dark:border-gray-700
                        rounded-xl
                        p-4
                        text-sm
                        text-gray-700 dark:text-gray-300
                        hover:border-primary-200
                        hover:bg-primary-50 dark:hover:bg-gray-700
                        transition-colors
                      "
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}

          {/* Messages */}
          {(submittedQuestion ||
            answer ||
            isLoading ||
            error) && (
            <div className="space-y-5 sm:space-y-6">
              {/* User Message */}
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

              {/* Loading */}
              {isLoading && (
                <div className="flex justify-start">
                  <div
                    className="
                      w-full max-w-3xl
                      bg-white dark:bg-gray-800
                      border border-gray-200 dark:border-gray-700
                      rounded-2xl sm:rounded-bl-md
                      px-4 sm:px-5 py-4
                      shadow-sm
                    "
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
                        <Bot className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                      </div>

                      <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                        <Loader2 className="w-4 h-4 animate-spin text-primary-600" />

                        Searching knowledge base
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error */}
              {!isLoading && error && (
                <div className="flex justify-start">
                  <div className="w-full max-w-3xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-2xl sm:rounded-bl-md px-4 sm:px-5 py-4 text-red-800 dark:text-red-300">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />

                      <div>
                        <h3 className="font-medium">
                          Unable to answer
                        </h3>

                        <p className="text-sm mt-1">
                          {error}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Answer */}
              {!isLoading &&
                !error &&
                answer && (
                  <div className="flex justify-start">
                    <div
                      className="
                        w-full max-w-3xl
                        bg-white dark:bg-gray-800
                        border border-gray-200 dark:border-gray-700
                        rounded-2xl sm:rounded-bl-md
                        px-4 sm:px-5 py-4
                        shadow-sm
                      "
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex-shrink-0">
                          <Bot className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                        </div>

                        <div className="space-y-5 min-w-0">
                          <div className="flex items-center justify-between gap-3">
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                              Generated answer
                            </h3>

                            <CopyButton
                              text={buildAnswerExport(
                                answer
                              )}
                              label="Copy Answer"
                              successMessage="Answer copied!"
                            />
                          </div>

                          <p className="text-gray-700 dark:text-gray-300 leading-7">
                            {answer.answer}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div
        className="
          border-t border-gray-200 dark:border-gray-700
          bg-white dark:bg-gray-800
          px-4 sm:px-6 py-3 sm:py-4
        "
      >
        <form
          onSubmit={handleAsk}
          className="max-w-4xl mx-auto"
        >
          <div
            className="
              flex items-end gap-2 sm:gap-3
              bg-gray-50 dark:bg-gray-900
              border border-gray-300 dark:border-gray-700
              rounded-2xl
              px-3 sm:px-4 py-3
              focus-within:ring-2 focus-within:ring-primary-500
            "
          >
            <textarea
              value={question}
              onChange={(e) =>
                setQuestion(e.target.value)
              }
              placeholder="Ask a compliance question..."
              rows={1}
              disabled={isLoading}
              className="
                min-w-0 flex-1 resize-none
                bg-transparent border-0 p-0
                text-sm
                text-gray-900 dark:text-white
                placeholder:text-gray-400
                focus:outline-none
              "
            />

            <button
              type="submit"
              disabled={isLoading}
              className="
                inline-flex items-center justify-center
                w-9 h-9 sm:w-10 sm:h-10
                bg-primary-600
                text-white
                rounded-xl
                hover:bg-primary-700
                disabled:opacity-50
              "
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
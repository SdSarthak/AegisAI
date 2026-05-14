import { useState } from 'react'
import { AlertCircle, Bot, FileText, Loader2, Send, Sparkles, User } from 'lucide-react'

interface RagSource {
  title: string
  excerpt: string
}

interface RagAnswer {
  answer: string
  sources: RagSource[]
}

export default function RagChat() {
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState('')
  const [answer, setAnswer] = useState<RagAnswer | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      // TODO: Replace this simulated response with the real RAG API call in the follow-up issue.
      // Suggested integration point:
      // const { data } = await api.post('/api/v1/rag/query', { question: trimmedQuestion })
      // setAnswer({ answer: data.answer, sources: data.sources })
      await new Promise((resolve) => setTimeout(resolve, 900)) // TODO (#73): replace with actual POST /api/v1/rag/query call

      if (trimmedQuestion.toLowerCase().includes('error')) {
        throw new Error('Simulated RAG service failure. Try another question.')
      }

      setAnswer({
        answer:
          'Based on the available compliance knowledge base, this question appears related to EU AI Act risk classification and documentation obligations. Once API wiring is added, this panel will show grounded answers generated from indexed regulatory sources.',
        sources: [
          {
            title: 'EU AI Act - Risk Classification Guidance',
            excerpt:
              'High-risk AI systems require risk management, technical documentation, logging, transparency, human oversight, accuracy, robustness, and cybersecurity controls.',
          },
          {
            title: 'AegisAI Compliance Knowledge Base',
            excerpt:
              'RAG responses should include source citations so users can verify which documents informed the generated answer.',
          },
        ],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate an answer right now.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-[calc(100vh-2rem)] md:h-[calc(100vh-4rem)] flex flex-col bg-white  rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 sm:p-3 bg-primary-50 rounded-xl">
            <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Chatbot</h1>
            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
              Ask regulatory and compliance questions with source-backed answers
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 sm:space-y-8">
          {!submittedQuestion && !answer && !isLoading && !error && (
            <div className="min-h-[320px] sm:min-h-[420px] flex flex-col items-center justify-center text-center">
              <div className="p-3 sm:p-4 bg-primary-50 rounded-2xl mb-5">
                <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-primary-600" />
              </div>
              <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">
                How can I help with AI compliance?
              </h2>
              <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-2 max-w-xl">
                Ask about EU AI Act risk classification, compliance documentation,
                human oversight, or source-backed regulatory guidance.
              </p>
              <div className=" grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-6 sm:mt-8 w-full">
                {[
                  'Does my system qualify as high-risk?',
                  'Which documents are needed for compliance?',
                  'What does human oversight require?',
                ].map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuestion(example)}
                    className="text-left bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300 hover:border-primary-200 hover:bg-primary-50 transition-colors"
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
                  <div className="w-full max-w-3xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-800 rounded-2xl sm:rounded-bl-md px-4 sm:px-5 py-4 shadow-sm">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-primary-50 dark:bg-gray-800 rounded-lg">
                        <Bot className="w-5 h-5 text-primary-600" />
                      </div>
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                        <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                        Searching knowledge base
                      </div>
                    </div>
                    <div className="space-y-3 animate-pulse">
                      <div className="h-3 bg-gray-200 rounded-full w-11/12" />
                      <div className="h-3 bg-gray-200 rounded-full w-full" />
                      <div className="h-3 bg-gray-200 rounded-full w-9/12" />
                      <div className="pt-4 mt-5 border-t border-gray-100 space-y-3">
                        <div className="h-3 bg-gray-200 rounded-full w-32" />
                        <div className="h-16 bg-gray-100 border border-gray-200 rounded-lg" />
                        <div className="h-16 bg-gray-100 border border-gray-200 rounded-lg" />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!isLoading && error && (
                <div className="flex justify-start">
                  <div className="w-full max-w-3xl bg-red-50 border border-red-200 rounded-2xl sm:rounded-bl-md px-4 sm:px-5 py-4 text-red-800">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                      <div>
                        <h3 className="font-medium">Unable to answer</h3>
                        <p className="text-sm mt-1">{error}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!isLoading && !error && answer && (
                <div className="flex justify-start">
                  <div className="w-full max-w-3xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-800 rounded-2xl sm:rounded-bl-md px-4 sm:px-5 py-4 shadow-sm">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-primary-50 dark:bg-gray-800 rounded-lg flex-shrink-0">
                        <Bot className="w-5 h-5 text-primary-600" />
                      </div>
                      <div className="space-y-5 min-w-0">
                        <p className="text-gray-700 leading-7">{answer.answer}</p>
                        <div className="border-t border-gray-100 pt-5">
                          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                            Source citations
                          </h3>
                          <div className="space-y-3">
                            {answer.sources.map((source) => (
                              <div
                                key={source.title}
                                className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4"
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <FileText className="w-4 h-4 text-primary-600" />
                                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                                    {source.title}
                                  </h4>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-300">{source.excerpt}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-700 px-4 sm:px-6 py-3 sm:py-4">
        <form onSubmit={handleAsk} className="max-w-4xl mx-auto">
          <div className="flex items-end gap-2 sm:gap-3 bg-gray-50 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-2xl px-3 sm:px-4 py-3 focus-within:ring-2 focus-within:ring-primary-500 focus-within:border-primary-500">
            <label htmlFor="rag-question" className="sr-only ">
              Question
            </label>
            <textarea
              id="rag-question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a compliance question..."
              rows={1}
              disabled={isLoading}
              className="min-w-0 flex-1 resize-none bg-transparent border-0 p-0 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-0 disabled:text-gray-500"
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
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Try typing `error` to preview the error state. 
              {/* TODO: This statement is just for testing. Remove it after integration of API */}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-300">
              Use this assistant to explore risk, documentation, and governance obligations.
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}

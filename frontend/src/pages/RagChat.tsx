import { useState, type FormEvent } from 'react'
import { Bot, FileText, Sparkles, Send } from 'lucide-react'

export default function RagChat() {
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState('')
  const [askCount, setAskCount] = useState(0)

  const handleAsk = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      return
    }

    setSubmittedQuestion(trimmedQuestion)
    setQuestion('')
    setAskCount((count) => count + 1)
  }

  const hasQuestion = submittedQuestion.length > 0

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700 dark:bg-primary-900/40 dark:text-primary-200">
              <Sparkles className="h-4 w-4" />
              RAG Chat
            </div>

            <div className="space-y-2">
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Ask a compliance question
              </h1>
              <p className="text-sm leading-6 text-gray-600 dark:text-gray-300">
                This page is the frontend shell for the future RAG chat experience.
                API wiring will be added in a follow-up issue.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-300">
            <p className="font-medium text-gray-900 dark:text-gray-100">Status</p>
            <p className="mt-1">UI scaffold only. No backend calls yet.</p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-xl bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/40 dark:text-primary-300">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Question
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Enter a prompt to reserve space for the chat flow.
              </p>
            </div>
          </div>

          <form onSubmit={handleAsk} className="space-y-4">
            <label htmlFor="rag-question" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Ask a question
            </label>

            <textarea
              id="rag-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="For example: What controls should I document for a high-risk AI system?"
              rows={5}
              className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-primary-400 dark:focus:ring-primary-900/40"
            />

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {askCount === 0
                  ? 'Answers and citations will render here after the API is wired.'
                  : 'This is a local-only placeholder interaction for the UI.'}
              </p>

              <button
                type="submit"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-white disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900"
                disabled={!question.trim()}
              >
                <Send className="h-4 w-4" />
                Ask
              </button>
            </div>
          </form>
        </div>

        <div className="space-y-6">
          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-xl bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/40 dark:text-primary-300">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Answer
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Placeholder response area for the future API result.
                </p>
              </div>
            </div>

            {hasQuestion ? (
              <div className="rounded-xl border border-dashed border-primary-200 bg-primary-50/60 p-4 text-sm leading-6 text-gray-700 dark:border-primary-900/60 dark:bg-primary-900/20 dark:text-gray-200">
                <p className="mb-2 font-medium text-gray-900 dark:text-gray-100">
                  Last question submitted
                </p>
                <p>{submittedQuestion}</p>
                <div className="mt-4 rounded-lg bg-white/80 p-4 text-gray-500 dark:bg-gray-950/60 dark:text-gray-300">
                  Answer content will appear here once the RAG API is connected.
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
                Ask a question to reserve the answer slot.
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-xl bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/40 dark:text-primary-300">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Source citations
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Placeholder cards for referenced documents.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {['Policy document placeholder', 'Internal guidance placeholder'].map(
                (source) => (
                  <div
                    key={source}
                    className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-950"
                  >
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {source}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-400">
                      Source excerpt placeholder will render here after the backend is wired.
                    </p>
                  </div>
                )
              )}
            </div>
          </section>
        </div>
      </section>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

interface RiskResult {
  risk_level: string
  confidence_score?: number
  reasoning?: string
}

interface RiskFormData {
  system_name: string
  description: string
  industry: string
  uses_biometric_data: boolean
  uses_ai_decision_making: boolean
  processes_sensitive_data: boolean
}

const initialFormState: RiskFormData = {
  system_name: '',
  description: '',
  industry: '',
  uses_biometric_data: false,
  uses_ai_decision_making: false,
  processes_sensitive_data: false,
}

export default function Classification() {
  const [formData, setFormData] =
    useState<RiskFormData>(initialFormState)

  const [result, setResult] =
    useState<RiskResult | null>(null)

  const [loading, setLoading] = useState(false)

  const [error, setError] = useState('')

  /**
   * Derived risk badge styling
   */
  const riskStyles = useMemo(() => {
    if (!result?.risk_level) {
      return {
        badge:
          'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
      }
    }

    switch (result.risk_level.toLowerCase()) {
      case 'high':
        return {
          badge:
            'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
        }

      case 'medium':
        return {
          badge:
            'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
        }

      case 'low':
        return {
          badge:
            'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
        }

      default:
        return {
          badge:
            'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
        }
    }
  }, [result])

  /**
   * Handle text + checkbox updates
   */
  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value, type } = e.target

    setFormData((prev) => ({
      ...prev,
      [name]:
        type === 'checkbox'
          ? (e.target as HTMLInputElement).checked
          : value,
    }))
  }

  /**
   * Submit risk classification
   */
  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault()

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await axios.post(
        '/api/v1/classification/classify',
        formData
      )

      setResult(response.data)
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail ||
            'Classification failed.'
        )
      } else {
        setError('Unexpected error occurred.')
      }
    } finally {
      setLoading(false)
    }
  }

  /**
   * Reset form
   */
  const handleReset = () => {
    setFormData(initialFormState)
    setResult(null)
    setError('')
  }

  useEffect(() => {
    document.title = 'Risk Classification • AegisAI'
  }, [])

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          AI Risk Classification
        </h1>

        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Assess your AI system under the EU AI Act
          compliance framework.
        </p>
      </div>

      {/* Form Card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm transition-colors dark:border-gray-700 dark:bg-gray-800">
        <form
          className="space-y-6"
          onSubmit={handleSubmit}
        >
          {/* System Name */}
          <div>
            <label
              htmlFor="system_name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              System Name
            </label>

            <input
              id="system_name"
              name="system_name"
              type="text"
              required
              value={formData.system_name}
              onChange={handleChange}
              className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 shadow-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="Enter AI system name"
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Description
            </label>

            <textarea
              id="description"
              name="description"
              rows={5}
              required
              value={formData.description}
              onChange={handleChange}
              className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 shadow-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="Describe your AI system..."
            />
          </div>

          {/* Industry */}
          <div>
            <label
              htmlFor="industry"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Industry
            </label>

            <select
              id="industry"
              name="industry"
              value={formData.industry}
              onChange={handleChange}
              required
              className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 shadow-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="">Select industry</option>
              <option value="healthcare">Healthcare</option>
              <option value="finance">Finance</option>
              <option value="education">Education</option>
              <option value="government">Government</option>
              <option value="retail">Retail</option>
              <option value="security">Security</option>
            </select>
          </div>

          {/* Checkboxes */}
          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex items-center gap-3 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
              <input
                type="checkbox"
                name="uses_biometric_data"
                checked={formData.uses_biometric_data}
                onChange={handleChange}
                className="h-4 w-4"
              />

              <span className="text-sm text-gray-700 dark:text-gray-300">
                Uses biometric data
              </span>
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
              <input
                type="checkbox"
                name="uses_ai_decision_making"
                checked={formData.uses_ai_decision_making}
                onChange={handleChange}
                className="h-4 w-4"
              />

              <span className="text-sm text-gray-700 dark:text-gray-300">
                Automated AI decisions
              </span>
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
              <input
                type="checkbox"
                name="processes_sensitive_data"
                checked={formData.processes_sensitive_data}
                onChange={handleChange}
                className="h-4 w-4"
              />

              <span className="text-sm text-gray-700 dark:text-gray-300">
                Processes sensitive data
              </span>
            </label>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-primary-600 px-6 py-2 text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading
                ? 'Analyzing...'
                : 'Classify Risk'}
            </button>

            <button
              type="button"
              onClick={handleReset}
              className="rounded-lg border border-gray-300 px-6 py-2 text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      {/* Result */}
      {result && (
        <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm transition-colors dark:border-gray-700 dark:bg-gray-800">
          <div className="flex flex-wrap items-center gap-4">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Classification Result
            </h2>

            <span
              className={`rounded-full px-4 py-1 text-sm font-medium ${riskStyles.badge}`}
            >
              {result.risk_level.toUpperCase()} RISK
            </span>
          </div>

          {typeof result.confidence_score ===
            'number' && (
            <p className="mt-4 text-gray-700 dark:text-gray-300">
              Confidence Score:{' '}
              <span className="font-semibold">
                {Math.round(
                  result.confidence_score * 100
                )}
                %
              </span>
            </p>
          )}

          {result.reasoning && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Reasoning
              </h3>

              <p className="mt-2 leading-relaxed text-gray-700 dark:text-gray-300">
                {result.reasoning}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
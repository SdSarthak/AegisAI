import React from 'react'
import { ClassificationResult } from '../../types/classification'
import { XCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import CopyButton from '../CopyButton'

interface ClassificationResultsProps {
  result: ClassificationResult | null
  resetClassification: () => void
}

function buildClassificationReport(result: ClassificationResult): string {
  return [
    `Risk Level: ${result.risk_level}`,
    `Confidence: ${Math.round(result.confidence * 100)}%`,
    '',
    'Reasoning',
    result.reasoning || result.reasons.join('\n'),
    '',
    'Legal Requirements',
    ...result.requirements.map((req, index) => `${index + 1}. ${req}`),
    '',
    'Action Plan',
    ...result.next_steps.map((step, index) => `${index + 1}. ${step}`),
  ].join('\n')
}

export default function ClassificationResults({ result, resetClassification }: ClassificationResultsProps) {
  if (!result) return null;

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'unacceptable':
        return <XCircle className="w-8 h-8 text-red-600" />
      case 'high':
        return <AlertTriangle className="w-8 h-8 text-orange-600" />
      case 'limited':
        return <Info className="w-8 h-8 text-yellow-600" />
      default:
        return <CheckCircle className="w-8 h-8 text-green-600" />
    }
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'unacceptable':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'high':
        return 'bg-orange-50 border-orange-200 text-orange-800'
      case 'limited':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      default:
        return 'bg-green-50 border-green-200 text-green-800'
    }
  }

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case 'unacceptable':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'limited':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default:
        return 'bg-green-100 text-green-800 border-green-200'
    }
  }

  const getReasoning = (classificationResult: ClassificationResult) =>
    classificationResult.reasoning || classificationResult.reasons.join('\n')

  return (
    <div className="space-y-6">
      <div className={`rounded-xl border p-6 ${getRiskColor(result.risk_level)}`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {getRiskIcon(result.risk_level)}
            <div>
              <h2 className="text-xl font-bold text-gray-900 capitalize">
                {result.risk_level} Risk
              </h2>
              <p className="text-sm text-gray-600">
                Confidence: {Math.round(result.confidence * 100)}%
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex w-fit items-center rounded-full border px-5 py-2 text-lg font-semibold capitalize ${getRiskBadgeColor(
                result.risk_level
              )}`}
            >
              {result.risk_level}
            </span>
            <CopyButton
              text={buildClassificationReport(result)}
              label="Copy Report"
              successMessage="Classification report copied!"
              className="shrink-0"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-medium text-gray-900 mb-2">Reasoning</h3>
        <p className="whitespace-pre-line text-sm text-gray-600">
          {getReasoning(result)}
        </p>
      </div>

      <button
        type="button"
        onClick={resetClassification}
        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
      >
        Classify Again
      </button>
    </div>
  )
}

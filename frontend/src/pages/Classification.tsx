import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'

import {
  AlertTriangle,
  CheckCircle,
  Info,
  XCircle,
} from 'lucide-react'

import ComplianceChecklist, {
  ChecklistItem,
} from '../components/ComplianceChecklist'
import CopyButton from '../components/CopyButton'

interface ClassificationResult {
  risk_level: string
  confidence: number
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

function buildClassificationReport(result: ClassificationResult): string {
  return [
    `Risk Level: ${result.risk_level}`,
    `Confidence: ${Math.round(result.confidence * 100)}%`,
    '',
    'Why this classification?',
    ...result.reasons.map((reason, index) => `${index + 1}. ${reason}`),
    '',
    'Legal Requirements',
    ...result.requirements.map((req, index) => `${index + 1}. ${req}`),
    '',
    'Action Plan',
    ...result.next_steps.map((step, index) => `${index + 1}. ${step}`),
  ].join('\n')
}

const CHECKLIST_ITEMS: Record<
  string,
  ChecklistItem[]
> = {
  high: [
    {
      id: 'tech-doc',
      label: 'Create Technical Documentation',
      article: 'Article 11',
      required: true,
    },
    {
      id: 'risk-assessment',
      label: 'Conduct Risk Assessment',
      article: 'Article 9',
      required: true,
    },
    {
      id: 'human-oversight',
      label: 'Establish Human Oversight',
      article: 'Article 14',
      required: true,
    },
    {
      id: 'conformity',
      label: 'EU Declaration of Conformity',
      article: 'Article 47',
      required: true,
    },
    {
      id: 'logging',
      label: 'Implement automatic logging',
      article: 'Article 12',
      required: true,
    },
  ],

  limited: [
    {
      id: 'transparency',
      label: 'Disclose AI interaction to users',
      article: 'Article 52',
      required: true,
    },
  ],

  minimal: [
    {
      id: 'best-practice',
      label: 'Follow voluntary AI best practices',
      required: false,
    },
  ],

  unacceptable: [],
}

export default function Classification() {
  const { systemId } = useParams()

  const [result, setResult] =
    useState<ClassificationResult | null>(
      null
    )

  const [formData, setFormData] = useState({
    use_case_category: 'hr_recruitment',
    is_safety_component: false,
    affects_fundamental_rights: true,
    uses_biometric_data: false,
    makes_automated_decisions: true,
    hr_recruitment_screening: true,
    hr_promotion_termination: false,
    credit_worthiness: false,
    insurance_risk_assessment: false,
    law_enforcement: false,
    border_control: false,
    justice_system: false,
    interacts_with_humans: true,
    generates_synthetic_content: false,
    emotion_recognition: false,
    biometric_categorization: false,
  })

  const classifyMutation = useMutation({
    mutationFn: () => {
      if (systemId) {
        return classificationApi.classifyAndSave(
          parseInt(systemId),
          formData
        )
      }

      return classificationApi.classify(
        formData
      )
    },

    onSuccess: (data) => {
      setResult(data)
    },
  })


  // Derive a live preliminary risk level from formData so the panel
  // updates in real-time as checkboxes are ticked, before the API call.
  const liveRiskLevel = useMemo((): string | null => {
    const {
      law_enforcement,
      border_control,
      justice_system,
      hr_recruitment_screening,
      hr_promotion_termination,
      credit_worthiness,
      insurance_risk_assessment,
      affects_fundamental_rights,
      makes_automated_decisions,
      is_safety_component,
      uses_biometric_data,
      biometric_categorization,
      emotion_recognition,
      interacts_with_humans,
      generates_synthetic_content,
    } = formData

    if (law_enforcement && uses_biometric_data && biometric_categorization) return 'unacceptable'

    const highRiskTriggers = [
      hr_recruitment_screening,
      hr_promotion_termination,
      credit_worthiness,
      insurance_risk_assessment,
      law_enforcement,
      border_control,
      justice_system,
      (affects_fundamental_rights && makes_automated_decisions),
      is_safety_component,
    ]
    if (highRiskTriggers.some(Boolean)) return 'high'

    if (interacts_with_humans || generates_synthetic_content || emotion_recognition) return 'limited'

    return 'minimal'
  }, [formData])

  // Only treat explicitly opt-in fields as "interaction" — fields that default
  // to true (affects_fundamental_rights, makes_automated_decisions,
  // hr_recruitment_screening, interacts_with_humans) would fire the preview
  // immediately on page load before the user does anything, which is misleading.
  const hasInteracted = useMemo(() => {
    return (
      formData.hr_recruitment_screening ||
      formData.hr_promotion_termination ||
      formData.credit_worthiness ||
      formData.insurance_risk_assessment ||
      formData.law_enforcement ||
      formData.border_control ||
      formData.justice_system ||
      formData.is_safety_component ||
      formData.uses_biometric_data ||
      formData.biometric_categorization ||
      formData.emotion_recognition ||
      formData.generates_synthetic_content
    )
  }, [formData])

  const getRiskIcon = (level: string) => {

    switch (level) {
      case 'unacceptable':
        return (
          <XCircle className="w-8 h-8 text-red-600" />
        )

      case 'high':
        return (
          <AlertTriangle className="w-8 h-8 text-orange-600" />
        )

      case 'limited':
        return (
          <Info className="w-8 h-8 text-yellow-600" />
        )

      default:
        return (
          <CheckCircle className="w-8 h-8 text-green-600" />
        )
    }
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'unacceptable':
        return 'bg-red-50 border-red-200'
      case 'high':
        return 'bg-orange-50 border-orange-200'
      case 'limited':
        return 'bg-yellow-50 border-yellow-200'
      default:
        return 'bg-green-50 border-green-200'
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Risk Classification
        </h1>

        <p className="text-gray-600 dark:text-gray-400">
          Determine your AI system's risk
          level under EU AI Act
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Questionnaire */}
        <div
          className="
            bg-white dark:bg-gray-800
            rounded-xl
            border border-gray-200 dark:border-gray-700
            p-6
            transition-colors duration-200
          "
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Classification Questionnaire
          </h2>

          <form className="space-y-6">
            {/* Use Case */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Primary Use Case
              </label>

              <select
                value={formData.use_case_category}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    use_case_category:
                      e.target.value,
                  })
                }
                className="
                  w-full
                  px-3 py-2
                  border border-gray-300 dark:border-gray-700
                  bg-white dark:bg-gray-900
                  text-gray-900 dark:text-white
                  rounded-lg
                "
              >
                <option value="hr_recruitment">
                  HR / Recruitment
                </option>

                <option value="credit_scoring">
                  Credit Scoring
                </option>

                <option value="healthcare">
                  Healthcare
                </option>

                <option value="education">
                  Education
                </option>

                <option value="customer_service">
                  Customer Service
                </option>

                <option value="other">
                  Other
                </option>
              </select>
            </div>

            {/* High Risk */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                High-Risk Indicators
                (Annex III)
              </h3>

              <div className="space-y-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.hr_recruitment_screening}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        hr_recruitment_screening: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>CV Screening / Candidate Ranking</strong>
                    <br />
                    AI filters CVs or ranks candidates for recruitment
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.hr_promotion_termination}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        hr_promotion_termination: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Promotion/Termination Decisions</strong>
                    <br />
                    AI influences employment status decisions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.credit_worthiness}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        credit_worthiness: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Credit Worthiness Assessment</strong>
                    <br />
                    AI evaluates creditworthiness or credit scoring
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.affects_fundamental_rights}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        affects_fundamental_rights: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Affects Fundamental Rights</strong>
                    <br />
                    Impacts employment, education, or essential services
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.makes_automated_decisions}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        makes_automated_decisions: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Automated Decision Making</strong>
                    <br />
                    Makes decisions without meaningful human review
                  </span>
                </label>
              </div>
            </div>

            {/* Button */}
            <button
              type="button"
              onClick={() =>
                classifyMutation.mutate()
              }
              disabled={
                classifyMutation.isPending
              }
              className="
                w-full py-3
                bg-primary-600
                text-white
                rounded-lg
                hover:bg-primary-700
                disabled:opacity-50
              "
            >
              {classifyMutation.isPending
                ? 'Classifying...'
                : 'Classify Risk Level'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="relative">
          {result ? (
            <div className={`rounded-xl border p-6 ${getRiskColor(result.risk_level)}`}>
              <div className="flex items-center gap-4 mb-6">
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

              {/* Reasons */}
              <div className="mb-6">
                <h3 className="font-medium text-gray-900 mb-2">Classification Reasons</h3>
                <ul className="space-y-2">
                  {result.reasons.map((reason, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-gray-400">•</span>
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Requirements */}
              <div className="mb-6">
                <h3 className="font-medium text-gray-900 mb-2">Compliance Requirements</h3>
                <ul className="space-y-2">
                  {result.requirements.map((req, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      {req}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Next Steps */}

              <div>
                <h3 className="font-medium text-gray-900 mb-2">Next Steps</h3>
                <ol className="space-y-2">
                  {result.next_steps.map((step, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="w-5 h-5 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs flex-shrink-0">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Compliance Checklist */}
              {result.risk_level !== 'unacceptable' && (
                <div className="mt-6">
                  <h3 className="font-medium text-gray-900 mb-3">
                    Compliance Checklist
                  </h3>

                    <ComplianceChecklist
                      systemId={Number(systemId || 0)}
                      riskLevel={
                        result.risk_level as
                        | 'minimal'
                        | 'limited'
                        | 'high'
                        | 'unacceptable'
                      }
                      items={CHECKLIST_ITEMS[result.risk_level] || []}
                    />
                  </div>
                )}
              </div>
           
          ) : hasInteracted && liveRiskLevel ? (
            // Live preview panel — shown when checkboxes are ticked but API hasn't been called yet
            <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm animate-in">
              <div className="flex items-center gap-3 mb-6">
                {getRiskIcon(liveRiskLevel)}
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-2xl font-black text-gray-900 capitalize tracking-tight">
                      {liveRiskLevel} Risk
                    </h2>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-500">
                      Preview
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 mt-0.5">
                    Submit the form for full analysis and compliance roadmap
                  </p>
                </div>
              </div>

              <div className={`rounded-xl p-4 mb-6 ${
                liveRiskLevel === 'unacceptable' ? 'bg-red-50 border border-red-100' :
                liveRiskLevel === 'high' ? 'bg-orange-50 border border-orange-100' :
                liveRiskLevel === 'limited' ? 'bg-yellow-50 border border-yellow-100' :
                'bg-green-50 border border-green-100'
              }`}>
                <p className={`text-sm font-medium ${
                  liveRiskLevel === 'unacceptable' ? 'text-red-800' :
                  liveRiskLevel === 'high' ? 'text-orange-800' :
                  liveRiskLevel === 'limited' ? 'text-yellow-800' :
                  'text-green-800'
                }`}>
                  {liveRiskLevel === 'unacceptable' && 'This system may be prohibited under EU AI Act Article 5. Review immediately.'}
                  {liveRiskLevel === 'high' && 'High-risk systems require technical documentation, conformity assessment, and human oversight (Annex III).'}
                  {liveRiskLevel === 'limited' && 'Limited-risk systems must meet transparency obligations under Article 52.'}
                  {liveRiskLevel === 'minimal' && 'Minimal risk — no mandatory obligations, but voluntary best practices are recommended.'}
                </p>
              </div>

              <p className="text-xs text-gray-400 text-center">
                This is a real-time estimate based on your selections. Click <strong>Classify Risk Level</strong> for the full AI Act analysis.
              </p>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">
                Complete the Questionnaire
              </h3>
              <p className="text-gray-500 mt-2">
                Answer the questions to determine your AI system's risk classification
                under the EU AI Act.
              </p>
              <div className="mt-8 flex justify-center gap-2">
                <div className="w-2 h-2 rounded-full bg-primary-200 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-primary-200 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-primary-200 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
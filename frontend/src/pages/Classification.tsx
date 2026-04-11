import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'

interface ClassificationResult {
  risk_level: string
  confidence: number
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

export default function Classification() {
  const { systemId } = useParams()
  const [result, setResult] = useState<ClassificationResult | null>(null)
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
        return classificationApi.classifyAndSave(parseInt(systemId), formData)
      }
      return classificationApi.classify(formData)
    },
    onSuccess: (data) => {
      setResult(data)
    },
  })

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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Classification</h1>
        <p className="text-gray-600">
          Determine your AI system's risk level under EU AI Act
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Questionnaire */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Classification Questionnaire
          </h2>

          <form className="space-y-6">
            {/* Use Case Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary Use Case
              </label>
              <select
                value={formData.use_case_category}
                onChange={(e) =>
                  setFormData({ ...formData, use_case_category: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="hr_recruitment">HR / Recruitment</option>
                <option value="credit_scoring">Credit Scoring</option>
                <option value="healthcare">Healthcare</option>
                <option value="education">Education</option>
                <option value="customer_service">Customer Service</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* High-Risk Indicators */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                High-Risk Indicators (Annex III)
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

            {/* Transparency Requirements */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                Transparency Indicators (Article 52)
              </h3>
              <div className="space-y-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.interacts_with_humans}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        interacts_with_humans: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Direct Human Interaction</strong>
                    <br />
                    System interacts directly with users (chatbot, assistant)
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.emotion_recognition}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        emotion_recognition: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Emotion Recognition</strong>
                    <br />
                    System detects or analyzes emotions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.generates_synthetic_content}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        generates_synthetic_content: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600">
                    <strong>Synthetic Content Generation</strong>
                    <br />
                    Generates deepfakes, AI images, or synthetic media
                  </span>
                </label>
              </div>
            </div>

            <button
              type="button"
              onClick={() => classifyMutation.mutate()}
              disabled={classifyMutation.isPending}
              className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {classifyMutation.isPending ? 'Classifying...' : 'Classify Risk Level'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div>
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
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

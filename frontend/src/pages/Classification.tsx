import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
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

const CHECKLIST_ITEMS: Record<string, ChecklistItem[]> = {
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
        <div className="relative">
          {result ? (
            <div className={`rounded-2xl border-0 p-8 glass animate-in overflow-hidden relative group`}>
              {/* Background Accent Gradient */}
              <div className={`absolute -right-20 -top-20 w-64 h-64 rounded-full blur-3xl opacity-20 transition-colors duration-500 ${
                result.risk_level === 'unacceptable' ? 'bg-red-500' :
                result.risk_level === 'high' ? 'bg-orange-500' :
                result.risk_level === 'limited' ? 'bg-yellow-500' : 'bg-green-500'
              }`} />
              
              <div className="relative z-10">
                <div className="flex items-start justify-between gap-4 mb-8">
                  <div className="flex items-center gap-5">
                    <div className={`p-4 rounded-2xl shadow-inner ${
                      result.risk_level === 'unacceptable' ? 'bg-red-100' :
                      result.risk_level === 'high' ? 'bg-orange-100' :
                      result.risk_level === 'limited' ? 'bg-yellow-100' : 'bg-green-100'
                    }`}>
                      {getRiskIcon(result.risk_level)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-2xl font-black text-gray-900 capitalize tracking-tight">
                          {result.risk_level} Risk
                        </h2>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          result.risk_level === 'unacceptable' ? 'bg-red-200 text-red-800' :
                          result.risk_level === 'high' ? 'bg-orange-200 text-orange-800' :
                          result.risk_level === 'limited' ? 'bg-yellow-200 text-yellow-800' : 'bg-green-200 text-green-800'
                        }`}>
                          AI Act Classified
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="w-32 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-1000 ease-out ${
                              result.confidence > 0.8 ? 'bg-green-500' : 'bg-yellow-500'
                            }`}
                            style={{ width: `${result.confidence * 100}%` }}
                          />
                        </div>
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          {Math.round(result.confidence * 100)}% Confidence
                        </p>
                      </div>
                    </div>
                  </div>

                  <CopyButton
                    text={buildClassificationReport(result)}
                    label="Copy Report"
                    successMessage="Classification report copied!"
                    className="shrink-0"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Left Column: Reasons & Requirements */}
                  <div className="space-y-8">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Why this classification?
                      </h3>
                      <ul className="space-y-3">
                        {result.reasons.map((reason, i) => (
                          <li key={i} className="text-sm text-gray-600 flex items-start gap-3 group/item">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-400 group-hover/item:scale-125 transition-transform" />
                            <span className="leading-relaxed">{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Legal Requirements
                      </h3>
                      <div className="bg-gray-50/50 rounded-xl p-4 border border-gray-100">
                        <ul className="space-y-3">
                          {result.requirements.map((req, i) => (
                            <li key={i} className="text-sm text-gray-700 flex items-start gap-3">
                              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                              <span className="font-medium">{req}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Next Steps & Checklist */}
                  <div className="space-y-8">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Action Plan
                      </h3>
                      <div className="space-y-4">
                        {result.next_steps.map((step, i) => (
                          <div key={i} className="flex gap-4 group/step">
                            <div className="flex flex-col items-center">
                              <div className="w-8 h-8 rounded-full bg-white border-2 border-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold shadow-sm group-hover/step:border-primary-500 group-hover/step:bg-primary-500 group-hover/step:text-white transition-all">
                                {i + 1}
                              </div>
                              {i < result.next_steps.length - 1 && (
                                <div className="w-0.5 h-full bg-primary-50 my-1" />
                              )}
                            </div>
                            <p className="text-sm text-gray-600 pt-1.5 leading-relaxed">{step}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Compliance Checklist Footer */}
                {result.risk_level !== 'unacceptable' && (
                  <div className="mt-10 pt-8 border-t border-gray-100">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-bold text-gray-900">
                        Interactive Compliance Checklist
                      </h3>
                      <span className="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-1 rounded">
                        {CHECKLIST_ITEMS[result.risk_level]?.length || 0} ITEMS REQUIRED
                      </span>
                    </div>

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
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center shadow-sm">
              <div className="w-20 h-20 bg-gray-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <AlertTriangle className="w-10 h-10 text-gray-300" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                Ready for Classification
              </h3>
              <p className="text-gray-500 max-w-sm mx-auto leading-relaxed">
                Complete the questionnaire to generate your AI Act risk profile and compliance roadmap.
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

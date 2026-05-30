import { useState, useMemo } from 'react'
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
    education_vocational_training: false,
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Risk Classification</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Determine your AI system's risk level under EU AI Act
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Questionnaire */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Classification Questionnaire
          </h2>

          <form className="space-y-6">
            {/* Use Case Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Primary Use Case
              </label>
              <select
                value={formData.use_case_category}
                onChange={(e) =>
                  setFormData({ ...formData, use_case_category: e.target.value })
                }
                className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
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
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                High-Risk Indicators (Annex III)
              </h3>
              <div className="space-y-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.hr_recruitment_screening}
                    onChange={(e) =>
                      setFormData({ ...formData, hr_recruitment_screening: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
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
                      setFormData({ ...formData, hr_promotion_termination: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Promotion / Termination Decisions</strong>
                    <br />
                    AI influences employment status decisions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.credit_worthiness}
                    onChange={(e) =>
                      setFormData({ ...formData, credit_worthiness: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Credit Worthiness Assessment</strong>
                    <br />
                    AI evaluates creditworthiness or credit scoring
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.insurance_risk_assessment}
                    onChange={(e) =>
                      setFormData({ ...formData, insurance_risk_assessment: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Insurance Risk Assessment</strong>
                    <br />
                    AI evaluates risk for insurance pricing or eligibility
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.law_enforcement}
                    onChange={(e) =>
                      setFormData({ ...formData, law_enforcement: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Law Enforcement Use</strong>
                    <br />
                    Used by police or judicial authorities for decisions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.border_control}
                    onChange={(e) =>
                      setFormData({ ...formData, border_control: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Border Control / Migration</strong>
                    <br />
                    Used for visa, asylum, or border management decisions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.justice_system}
                    onChange={(e) =>
                      setFormData({ ...formData, justice_system: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Justice System / Legal Aid</strong>
                    <br />
                    Assists courts or legal processes with decisions
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.is_safety_component}
                    onChange={(e) =>
                      setFormData({ ...formData, is_safety_component: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Safety-Critical Component</strong>
                    <br />
                    Part of a product regulated under EU safety legislation
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.uses_biometric_data}
                    onChange={(e) =>
                      setFormData({ ...formData, uses_biometric_data: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Uses Biometric Data</strong>
                    <br />
                    Processes fingerprints, face scans, or other biometrics
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.biometric_categorization}
                    onChange={(e) =>
                      setFormData({ ...formData, biometric_categorization: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Biometric Categorization</strong>
                    <br />
                    Categorizes people by race, gender, or political views from biometrics
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.affects_fundamental_rights}
                    onChange={(e) =>
                      setFormData({ ...formData, affects_fundamental_rights: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
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
                      setFormData({ ...formData, makes_automated_decisions: e.target.checked })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Automated Decision Making</strong>
                    <br />
                    Makes decisions without meaningful human review
                  </span>
                </label>

                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={formData.education_vocational_training}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        education_vocational_training: e.target.checked,
                      })
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    <strong>Education & Vocational Training</strong>
                    <br />
                    AI determines access to or assigns persons to educational institutions
                  </span>
                </label>
              </div>
            </div>

            {/* Transparency Requirements */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
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
                  <span className="text-sm text-gray-600 dark:text-gray-300">
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
                  <span className="text-sm text-gray-600 dark:text-gray-300">
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
                  <span className="text-sm text-gray-600 dark:text-gray-300">
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
        </div>        {/* Results */}
        <div className="relative">
          {result ? (
            <div className={`rounded-2xl border-0 p-8 bg-white dark:bg-gray-800 glass dark:glass-dark animate-in overflow-hidden relative group`}>
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
                      result.risk_level === 'unacceptable' ? 'bg-red-105 dark:bg-red-950/40' :
                      result.risk_level === 'high' ? 'bg-orange-105 dark:bg-orange-950/40' :
                      result.risk_level === 'limited' ? 'bg-yellow-105 dark:bg-yellow-950/40' : 'bg-green-105 dark:bg-green-950/40'
                    }`}>
                      {getRiskIcon(result.risk_level)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-2xl font-black text-gray-900 dark:text-white capitalize tracking-tight">
                          {result.risk_level} Risk
                        </h2>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          result.risk_level === 'unacceptable' ? 'bg-red-200 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                          result.risk_level === 'high' ? 'bg-orange-200 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
                          result.risk_level === 'limited' ? 'bg-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' : 'bg-green-200 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        }`}>
                          AI Act Classified
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="w-32 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-1000 ease-out ${
                              result.confidence > 0.8 ? 'bg-green-500' : 'bg-yellow-500'
                            }`}
                            style={{ width: `${result.confidence * 100}%` }}
                          />
                        </div>
                        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
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
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Why this classification?
                      </h3>
                      <ul className="space-y-3">
                        {result.reasons.map((reason, i) => (
                          <li key={i} className="text-sm text-gray-600 dark:text-gray-300 flex items-start gap-3 group/item">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-400 group-hover/item:scale-125 transition-transform" />
                            <span className="leading-relaxed">{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Legal Requirements
                      </h3>
                      <div className="bg-gray-50/50 dark:bg-gray-900/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
                        <ul className="space-y-3">
                          {result.requirements.map((req, i) => (
                            <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-3">
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
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-1.5 h-4 bg-primary-500 rounded-full"></span>
                        Action Plan
                      </h3>
                      <div className="space-y-4">
                        {result.next_steps.map((step, i) => (
                          <div key={i} className="flex gap-4 group/step">
                            <div className="flex flex-col items-center">
                              <div className="w-8 h-8 rounded-full bg-white dark:bg-gray-800 border-2 border-primary-100 dark:border-primary-900 text-primary-700 dark:text-primary-400 flex items-center justify-center text-xs font-bold shadow-sm group-hover/step:border-primary-500 group-hover/step:bg-primary-500 group-hover/step:text-white transition-all">
                                {i + 1}
                              </div>
                              {i < result.next_steps.length - 1 && (
                                <div className="w-0.5 h-full bg-primary-50 dark:bg-primary-950/40 my-1" />
                              )}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-300 pt-1.5 leading-relaxed">{step}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Compliance Checklist Footer */}
                {result.risk_level !== 'unacceptable' && (
                  <div className="mt-10 pt-8 border-t border-gray-100 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                        Interactive Compliance Checklist
                      </h3>
                      <span className="text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900 px-2 py-1 rounded">
                        {CHECKLIST_ITEMS[result.risk_level]?.length || 0} ITEMS REQUIRED
                      </span>
                    </div>

                    {systemId ? (
                      <ComplianceChecklist
                        systemId={Number(systemId)}
                        riskLevel={
                          result.risk_level as
                          | 'minimal'
                          | 'limited'
                          | 'high'
                          | 'unacceptable'
                        }
                        items={CHECKLIST_ITEMS[result.risk_level] || []}
                      />
                    ) : (
                      <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                        Save this AI system first to track checklist progress.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : hasInteracted && liveRiskLevel ? (
            // Live preview panel — shown when checkboxes are ticked but API hasn't been called yet
            <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-8 shadow-sm animate-in">
              <div className="flex items-center gap-3 mb-6">
                {getRiskIcon(liveRiskLevel)}
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-2xl font-black text-gray-900 dark:text-white capitalize tracking-tight">
                      {liveRiskLevel} Risk
                    </h2>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                      Preview
                    </span>
                  </div>
                  <p className="text-sm text-gray-450 dark:text-gray-400 mt-0.5">
                    Submit the form for full analysis and compliance roadmap
                  </p>
                </div>
              </div>

              <div className={`rounded-xl p-4 mb-6 ${
                liveRiskLevel === 'unacceptable' ? 'bg-red-50 dark:bg-red-950/20 border border-red-100 dark:border-red-900/50' :
                liveRiskLevel === 'high' ? 'bg-orange-50 dark:bg-orange-950/20 border border-orange-100 dark:border-orange-900/50' :
                liveRiskLevel === 'limited' ? 'bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-100 dark:border-yellow-900/50' :
                'bg-green-50 dark:bg-green-950/20 border border-green-100 dark:border-green-900/50'
              }`}>
                <p className={`text-sm font-medium ${
                  liveRiskLevel === 'unacceptable' ? 'text-red-800 dark:text-red-400' :
                  liveRiskLevel === 'high' ? 'text-orange-800 dark:text-orange-400' :
                  liveRiskLevel === 'limited' ? 'text-yellow-800 dark:text-yellow-400' :
                  'text-green-800 dark:text-green-400'
                }`}>
                  {liveRiskLevel === 'unacceptable' && 'This system may be prohibited under EU AI Act Article 5. Review immediately.'}
                  {liveRiskLevel === 'high' && 'High-risk systems require technical documentation, conformity assessment, and human oversight (Annex III).'}
                  {liveRiskLevel === 'limited' && 'Limited-risk systems must meet transparency obligations under Article 52.'}
                  {liveRiskLevel === 'minimal' && 'Minimal risk — no mandatory obligations, but voluntary best practices are recommended.'}
                </p>
              </div>

              <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
                This is a real-time estimate based on your selections. Click <strong>Classify Risk Level</strong> for the full AI Act analysis.
              </p>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-12 text-center shadow-sm">
              <div className="w-20 h-20 bg-gray-50 dark:bg-gray-900 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <AlertTriangle className="w-10 h-10 text-gray-300 dark:text-gray-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                Ready for Classification
              </h3>
              <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto leading-relaxed">
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
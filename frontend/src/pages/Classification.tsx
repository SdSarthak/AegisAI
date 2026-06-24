import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'
import { useUnsavedChanges } from '../hooks/useUnsavedChanges'
import {
  AlertTriangle,
  BarChart2,
  CheckCircle,
  ClipboardList,
  Info,
  type LucideIcon,
  Lock,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import ComplianceChecklist, {
  ChecklistItem,
} from '../components/ComplianceChecklist'
import CopyButton from '../components/CopyButton'

type Tab = 'questionnaire' | 'results' | 'requirements'
type RiskLevel = 'minimal' | 'limited' | 'high' | 'unacceptable'

interface ClassificationResult {
  risk_level: string
  confidence: number
  reasoning?: string
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

interface RequirementContent {
  title: string
  description: string
  obligations: string[]
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

const requirementContent: Record<string, RequirementContent> = {
  unacceptable: {
    title: 'Unacceptable Risk',
    description: 'This AI system is prohibited under Article 5 of the EU AI Act.',
    obligations: [
      'Cease deployment and operation of the AI system.',
      'Preserve records relating to design, deployment, use, and classification.',
      'Consult legal counsel before any further development or redeployment.',
    ],
  },
  high: {
    title: 'High Risk',
    description:
      'This AI system must meet the EU AI Act requirements for high-risk systems before being placed on the market or put into service.',
    obligations: [
      'Implement a quality management system (Art. 17).',
      'Prepare technical documentation (Art. 11 and Annex IV).',
      'Complete the applicable conformity assessment (Art. 43).',
      'Establish and maintain a risk management system (Art. 9).',
      'Apply data governance and data management practices (Art. 10).',
      'Provide transparency information and instructions for use (Art. 13).',
      'Enable effective human oversight (Art. 14).',
      'Ensure accuracy, robustness, and cybersecurity (Art. 15).',
      'Register the system in the EU database where required (Art. 49).',
      'Apply CE marking before placing the system on the market (Art. 48).',
      'Operate post-market monitoring (Art. 72).',
      'Report serious incidents as required (Art. 73).',
    ],
  },
  limited: {
    title: 'Limited Risk',
    description:
      'This AI system is subject to transparency obligations under Article 50 of the EU AI Act.',
    obligations: [
      'Disclose AI interaction to users (Art. 50(1)).',
      'Label AI-generated or manipulated content (Art. 50(4)).',
      'Inform persons exposed to emotion-recognition systems (Art. 50(3)).',
    ],
  },
  minimal: {
    title: 'Minimal Risk',
    description:
      'This AI system has no mandatory EU AI Act obligations based on the current classification.',
    obligations: [
      'No mandatory obligations apply.',
      'Document the classification reasoning.',
      'Re-evaluate the classification if the system scope or intended use changes.',
    ],
  },
}

const INITIAL_FORM_DATA = {
  use_case_category: 'hr_recruitment',
  is_safety_component: false,
  affects_fundamental_rights: true,
  makes_automated_decisions: true,
  uses_biometric_data: false,
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
}

export default function Classification() {
  const { systemId } = useParams()
  const [activeTab, setActiveTab] = useState<Tab>('questionnaire')
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [formData, setFormData] = useState(INITIAL_FORM_DATA)
  const isFormDirty = useMemo(
    () => JSON.stringify(formData) !== JSON.stringify(INITIAL_FORM_DATA),
    [formData],
  )
  const { dialog } = useUnsavedChanges(activeTab === 'questionnaire' && isFormDirty)

  const classifyMutation = useMutation({
    mutationFn: () => {
      if (systemId) {
        return classificationApi.classifyAndSave(parseInt(systemId), formData)
      }
      return classificationApi.classify(formData)
    },
    onSuccess: (data) => {
      setResult(data)
      setActiveTab('results')
    },
    onError: () => {
      setResult(null)
      setActiveTab('questionnaire')
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

  const getRequirementContent = (level: string) =>
    requirementContent[level] || requirementContent.minimal

  const getRiskLevel = (level: string): RiskLevel => {
    if (
      level === 'minimal' ||
      level === 'limited' ||
      level === 'high' ||
      level === 'unacceptable'
    ) {
      return level
    }

    return 'minimal'
  }

  const renderTabButton = (
    tab: Tab,
    label: string,
    Icon: LucideIcon,
    locked: boolean
  ) => {
    const isActive = activeTab === tab

    return (
      <button
        type="button"
        onClick={() => {
          if (!locked) {
            setActiveTab(tab)
          }
        }}
        disabled={locked}
        className={`flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
          isActive
            ? 'border-primary-600 text-primary-700'
            : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
        } ${locked ? 'opacity-50 cursor-not-allowed hover:border-transparent hover:text-gray-500' : ''}`}
      >
        <Icon className="w-4 h-4" />
        <span>{label}</span>
        {locked && <Lock className="w-3.5 h-3.5" />}
      </button>
    )
  }

  const resetClassification = () => {
    setResult(null)
    setActiveTab('questionnaire')
  }

  const renderQuestionnaire = () => (
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
                checked={formData.insurance_risk_assessment}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    insurance_risk_assessment: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    law_enforcement: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    border_control: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    justice_system: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    is_safety_component: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    uses_biometric_data: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
                  setFormData({
                    ...formData,
                    biometric_categorization: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
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
              <span className="text-sm text-gray-600">
                <strong>Education & Vocational Training</strong>
                <br />
                AI determines access to or assigns persons to educational institutions
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

        {classifyMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {classifyMutation.error instanceof Error
              ? classifyMutation.error.message
              : 'Unable to classify this system right now.'}
          </div>
        )}
      </form>
    </div>
  )

  const renderResults = () => {
    if (!result) {
      return null
    }

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

  const renderRequirements = () => {
    if (!result) {
      return null
    }

    const content = getRequirementContent(result.risk_level)
    const riskLevel = getRiskLevel(result.risk_level)

    return (
      <div className="space-y-6">
        <div className={`rounded-xl border p-6 ${getRiskColor(result.risk_level)}`}>
          <div className="flex items-start gap-4">
            <ShieldCheck className="w-8 h-8 flex-shrink-0" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">{content.title}</h2>
              <p className="mt-2 text-sm text-gray-600">{content.description}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-medium text-gray-900 mb-4">EU AI Act Obligations</h3>
          <ol className="space-y-3">
            {content.obligations.map((obligation, i) => (
              <li key={obligation} className="flex items-start gap-3 text-sm text-gray-600">
                <span className="w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0">
                  {i + 1}
                </span>
                <span>{obligation}</span>
              </li>
            ))}
          </ol>
        </div>

        {riskLevel !== 'unacceptable' && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-gray-900">
                Interactive Compliance Checklist
              </h3>
              <span className="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-1 rounded">
                {CHECKLIST_ITEMS[riskLevel]?.length || 0} ITEMS REQUIRED
              </span>
            </div>

            <ComplianceChecklist
              systemId={Number(systemId || 0)}
              riskLevel={riskLevel}
              items={CHECKLIST_ITEMS[riskLevel] || []}
            />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Risk Classification</h1>
          <p className="text-gray-600">
            Determine your AI system's risk level under EU AI Act
          </p>
        </div>

        <div className="border-b border-gray-200">
          <div className="flex gap-2 overflow-x-auto">
            {renderTabButton('questionnaire', 'Questionnaire', ClipboardList, false)}
            {renderTabButton('results', 'Results', BarChart2, !result)}
            {renderTabButton('requirements', 'Requirements', ShieldCheck, !result)}
          </div>
        </div>
      </div>

      {activeTab === 'questionnaire' && renderQuestionnaire()}
      {activeTab === 'results' && renderResults()}
      {activeTab === 'requirements' && renderRequirements()}

      {dialog}
    </div>
  )
}


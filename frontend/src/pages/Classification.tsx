import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'
import { BarChart2, ClipboardList, ShieldCheck, Lock, type LucideIcon } from 'lucide-react'
import ErrorBoundary from '../components/ErrorBoundary'
import QuestionnaireForm from '../components/classification/QuestionnaireForm'
import ClassificationResults from '../components/classification/ClassificationResults'
import ComplianceRequirements from '../components/classification/ComplianceRequirements'
import { ClassificationFormData, ClassificationResult, Tab } from '../types/classification'

export default function Classification() {
  const { systemId } = useParams()
  const [activeTab, setActiveTab] = useState<Tab>('questionnaire')
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [formData, setFormData] = useState<ClassificationFormData>({
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
      setActiveTab('results')
    },
    onError: () => {
      setResult(null)
      setActiveTab('questionnaire')
    },
  })

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

      <ErrorBoundary>
        {activeTab === 'questionnaire' && (
          <QuestionnaireForm
            formData={formData}
            setFormData={setFormData}
            classifyMutation={classifyMutation}
          />
        )}
        {activeTab === 'results' && (
          <ClassificationResults
            result={result}
            resetClassification={resetClassification}
          />
        )}
        {activeTab === 'requirements' && (
          <ComplianceRequirements
            result={result}
            systemId={systemId}
          />
        )}
      </ErrorBoundary>
    </div>
  )
}

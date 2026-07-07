import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Shield,
  Bot,
  FileCheck,
  FileText,
  ChevronRight,
  Loader2,
} from 'lucide-react'

import {
  aiSystemsApi,
  authApi,
  classificationApi,
  documentsApi,
} from '../services/api'

const STEPS = [
  {
    label: 'Register AI System',
    icon: Bot,
    description: 'Tell us about the AI system you want to track for compliance.',
  },
  {
    label: 'Run Classification',
    icon: FileCheck,
    description: 'Answer a short questionnaire to determine the EU AI Act risk level.',
  },
  {
    label: 'Generate Document',
    icon: FileText,
    description: 'Auto-generate your first compliance document.',
  },
]

export default function Onboarding() {
  const navigate = useNavigate()

  const [currentStep, setCurrentStep] = useState(0)
  const [systemId, setSystemId] = useState<number | null>(null)
  const [riskLevel, setRiskLevel] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [systemForm, setSystemForm] = useState({
    name: '',
    description: '',
    use_case: '',
    sector: '',
  })

  const [classificationForm, setClassificationForm] = useState({
    intended_purpose: '',
    target_users: '',
    uses_personal_data: false,
    affects_decision_making: false,
  })

  const [documentType, setDocumentType] = useState('technical_documentation')

  const isLastStep = currentStep === STEPS.length - 1
  const StepIcon = STEPS[currentStep].icon

  const handleCreateSystem = async () => {
    if (!systemForm.name.trim()) {
      setError('Please enter an AI system name.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const createdSystem = await aiSystemsApi.create({
        name: systemForm.name,
        description: systemForm.description,
        use_case: systemForm.use_case,
        sector: systemForm.sector,
      })

      setSystemId(createdSystem.id)
      setCurrentStep(1)
    } catch {
      setError('Failed to create AI system. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClassifySystem = async () => {
    if (!systemId) {
      setError('AI system was not created. Please go back and try again.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const classification = await classificationApi.classifyAndSave(systemId, {
        intended_purpose: classificationForm.intended_purpose,
        target_users: classificationForm.target_users,
        uses_personal_data: classificationForm.uses_personal_data,
        affects_decision_making: classificationForm.affects_decision_making,
      })

      const classificationResult = classification as {
  risk_level?: unknown
  riskLevel?: unknown
  classification?: unknown
}

const detectedRiskLevel =
  typeof classificationResult.risk_level === 'string'
    ? classificationResult.risk_level
    : typeof classificationResult.riskLevel === 'string'
      ? classificationResult.riskLevel
      : typeof classificationResult.classification === 'string'
        ? classificationResult.classification
        : 'classified'

setRiskLevel(detectedRiskLevel)

      setCurrentStep(2)
    } catch {
      setError('Failed to classify AI system. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateDocument = async () => {
    if (!systemId) {
      setError('AI system was not created. Please go back and try again.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      await documentsApi.generate({
        ai_system_id: systemId,
        document_type: documentType,
      })

      await authApi.updateMe({
        onboarding_completed: true,
      })

      navigate('/')
    } catch {
      setError('Failed to complete onboarding. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNext = () => {
    if (currentStep === 0) {
      void handleCreateSystem()
      return
    }

    if (currentStep === 1) {
      void handleClassifySystem()
      return
    }

    if (currentStep === 2) {
      void handleGenerateDocument()
    }
  }

  const handleBack = () => {
    setError(null)
    setCurrentStep((step) => Math.max(0, step - 1))
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-8">
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-8 w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-primary-600 dark:text-primary-400" />
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Welcome to AegisAI</h1>
        </div>

        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((step, index) => (
            <div key={step.label} className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  index < currentStep
                    ? 'bg-primary-600 text-white'
                    : idx === currentStep
                    ? 'border-2 border-primary-600 dark:border-primary-400 text-primary-600 dark:text-primary-400'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-505'
                }`}
              >
                {index + 1}
              </div>

              {index < STEPS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 ${idx < currentStep ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700'}`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <StepIcon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {STEPS[currentStep].label}
            </h2>
          </div>
          <p className="text-gray-600 dark:text-gray-400 text-sm">{STEPS[currentStep].description}</p>

          {/* TODO (good first issue): add step-specific form fields here */}
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 text-center text-sm text-gray-400 dark:text-gray-500">
            Step {currentStep + 1} form fields — implement me
          </div>
        </div>

        <div className="flex justify-between">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Back
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            {isLastStep ? 'Finish' : 'Next'}
            {!isLastStep && !isLoading && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}


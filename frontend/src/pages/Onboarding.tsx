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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 w-full max-w-lg">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-primary-600" />
          <h1 className="text-xl font-semibold text-gray-900">Welcome to AegisAI</h1>
        </div>

        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((step, index) => (
            <div key={step.label} className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  index < currentStep
                    ? 'bg-primary-600 text-white'
                    : index === currentStep
                      ? 'border-2 border-primary-600 text-primary-600'
                      : 'bg-gray-100 text-gray-400'
                }`}
              >
                {index + 1}
              </div>

              {index < STEPS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 ${
                    index < currentStep ? 'bg-primary-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <StepIcon className="w-6 h-6 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">
              {STEPS[currentStep].label}
            </h2>
          </div>

          <p className="text-gray-600 text-sm">{STEPS[currentStep].description}</p>

          {error && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {currentStep === 0 && (
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  AI System Name
                </label>
                <input
                  type="text"
                  value={systemForm.name}
                  onChange={(event) =>
                    setSystemForm((form) => ({
                      ...form,
                      name: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Example: Resume Screening AI"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  value={systemForm.description}
                  onChange={(event) =>
                    setSystemForm((form) => ({
                      ...form,
                      description: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Briefly describe your AI system"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Use Case
                </label>
                <input
                  type="text"
                  value={systemForm.use_case}
                  onChange={(event) =>
                    setSystemForm((form) => ({
                      ...form,
                      use_case: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Example: Hiring, healthcare, education"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Sector
                </label>
                <input
                  type="text"
                  value={systemForm.sector}
                  onChange={(event) =>
                    setSystemForm((form) => ({
                      ...form,
                      sector: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Example: HR Tech"
                />
              </div>
            </div>
          )}

          {currentStep === 1 && (
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Intended Purpose
                </label>
                <textarea
                  value={classificationForm.intended_purpose}
                  onChange={(event) =>
                    setClassificationForm((form) => ({
                      ...form,
                      intended_purpose: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="What is this AI system used for?"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Target Users
                </label>
                <input
                  type="text"
                  value={classificationForm.target_users}
                  onChange={(event) =>
                    setClassificationForm((form) => ({
                      ...form,
                      target_users: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Example: HR teams, compliance officers"
                />
              </div>

              <label className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={classificationForm.uses_personal_data}
                  onChange={(event) =>
                    setClassificationForm((form) => ({
                      ...form,
                      uses_personal_data: event.target.checked,
                    }))
                  }
                />
                Uses personal data
              </label>

              <label className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={classificationForm.affects_decision_making}
                  onChange={(event) =>
                    setClassificationForm((form) => ({
                      ...form,
                      affects_decision_making: event.target.checked,
                    }))
                  }
                />
                Affects decision-making about people
              </label>

              {riskLevel && (
                <div className="rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-700">
                  Risk classification: <span className="font-semibold">{riskLevel}</span>
                </div>
              )}
            </div>
          )}

          {currentStep === 2 && (
            <div className="mt-6 space-y-4">
              {riskLevel && (
                <div className="rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-700">
                  Your AI system was classified as:{' '}
                  <span className="font-semibold">{riskLevel}</span>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Document Type
                </label>
                <select
                  value={documentType}
                  onChange={(event) => setDocumentType(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="technical_documentation">
                    Technical Documentation
                  </option>
                  <option value="risk_assessment">Risk Assessment</option>
                  <option value="conformity_declaration">
                    Conformity Declaration
                  </option>
                </select>
              </div>

              <p className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                Click Finish to generate your first compliance document and complete
                onboarding.
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-between">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0 || isLoading}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
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


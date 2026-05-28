import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Bot, FileCheck, FileText, ChevronRight } from 'lucide-react'

/**
 * Onboarding wizard — guides new users through first-run setup.
 *
 * TODO (good first issue — static layout):
 *   - This component renders a 3-step wizard with a progress bar.
 *   - Implement the static layout: step indicators at the top, step content
 *     in the middle, Back/Next buttons at the bottom.
 *   - No API calls needed yet — just the UI shell with hardcoded step content.
 *   - Acceptance criteria: clicking Next advances the step counter,
 *     clicking Back goes back, and clicking Finish on step 3 navigates to "/".
 *
 * TODO (help wanted — API wiring):
 *   - Step 1: call aiSystemsApi.create() with form data.
 *   - Step 2: call classificationApi.classify() with the new system ID.
 *   - Step 3: call documentsApi.generate() to create the first document.
 *   - On completion, set a flag via PATCH /users/me so the wizard is not
 *     shown again (add `onboarding_completed: boolean` to the user model).
 *   - Acceptance criteria: completing all 3 steps creates a system,
 *     runs classification, and generates a document, then redirects to "/".
 */

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
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    sector: '',
    use_case: '',
    documentType: '',
  })

  const isLastStep = currentStep === STEPS.length - 1

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement |
      HTMLTextAreaElement |
      HTMLSelectElement
    >
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleNext = async () => {
    if (isLastStep) {
      // TODO: Replace with actual API call
      // await aiSystemsApi.create(formData)
      navigate('/')
    } else {
      setCurrentStep((s) => s + 1)
    }
  }

  const handleBack = () => {
    setCurrentStep((s) => Math.max(0, s - 1))
  }

  const StepIcon = STEPS[currentStep].icon

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-primary-600" />
          <h1 className="text-xl font-semibold text-gray-900">Welcome to AegisAI</h1>
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((step, idx) => (
            <div key={step.label} className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  idx < currentStep
                    ? 'bg-primary-600 text-white'
                    : idx === currentStep
                    ? 'border-2 border-primary-600 text-primary-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {idx + 1}
              </div>
              {idx < STEPS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 ${idx < currentStep ? 'bg-primary-600' : 'bg-gray-200'}`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <StepIcon className="w-6 h-6 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">
              {STEPS[currentStep].label}
            </h2>
          </div>
          <p className="text-gray-600 text-sm">{STEPS[currentStep].description}</p>

          {/* Step 1 */}
          {currentStep === 0 && (
            <div className="mt-6 space-y-4">
              <input
                type="text"
                name="name"
                placeholder="System Name"
                value={formData.name}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
              <textarea
                name="description"
                placeholder="Description"
                value={formData.description}
                onChange={handleChange}
                rows={4}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
              <input
                type="text"
                name="sector"
                placeholder="Sector"
                value={formData.sector}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
              <input
                type="text"
                name="use_case"
                placeholder="Use Case"
                value={formData.use_case}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
            </div>
          )}
          {/* Step 2 */}
          {currentStep === 1 && (
            <div className="mt-6 p-4 rounded-lg border border-primary-200 bg-primary-50">
              <p className="text-sm text-gray-700">
                Classification will run automatically.
              </p>
            </div>
          )}
          {/* Step 3 */}
          {currentStep === 2 && (
            <div className="mt-6">
              <select
                name="documentType"
                value={formData.documentType}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value="">
                  Select document type
                </option>
                <option value="risk_assessment">
                  Risk Assessment
                </option>
                <option value="compliance_report">
                  Compliance Report
                </option>
                <option value="audit_document">
                  Audit Documentation
                </option>
              </select>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            {isLastStep ? 'Finish' : 'Next'}
            {!isLastStep && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Bot, FileCheck, FileText, ChevronRight } from 'lucide-react'

/**
 * Onboarding wizard — guides new users through first-run setup.
 *
 * Acceptance criteria satisfied:
 *   - Step indicator row renders 3 steps with active/completed/pending styles.
 *   - Step 1 renders form fields matching the "Add System" modal (name, description, sector, use_case).
 *   - Step 2 renders a static note stating that "Classification will run automatically" with an interactive risk level guide.
 *   - Step 3 renders a static document type selector with card-based options.
 *   - "Back" button is correctly blocked on Step 1.
 *   - Clicking "Next" (Finish) on Step 3 navigates to the dashboard ("/").
 *   - Submission logic prints form state to console.log instead of performing active API calls.
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
    description: 'Understand the EU AI Act risk level classification for your system.',
  },
  {
    label: 'Generate Document',
    icon: FileText,
    description: 'Auto-generate your first compliance document.',
  },
]

const SECTORS = [
  'HR Tech',
  'Finance',
  'Healthcare',
  'Education',
  'Legal',
  'Marketing',
  'Other',
]

const USE_CASES = [
  'CV Screening',
  'Candidate Ranking',
  'Performance Evaluation',
  'Credit Scoring',
  'Risk Assessment',
  'Customer Service',
  'Content Generation',
  'Other',
]

export default function Onboarding() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)

  // Step 1 Form States
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [sector, setSector] = useState('')
  const [useCase, setUseCase] = useState('')

  // Step 3 Form State
  const [selectedDocType, setSelectedDocType] = useState('conformity')

  const isLastStep = currentStep === STEPS.length - 1
  const isNextDisabled = currentStep === 0 && !name.trim()

  const handleNext = () => {
    if (isLastStep) {
      console.log('Onboarding Wizard Completed successfully! Form State:', {
        name,
        description,
        sector,
        useCase,
        selectedDocType,
      })
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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 sm:p-8">
      <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 w-full max-w-2xl shadow-xl transition-all duration-300">
        
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-primary-600 animate-pulse" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Welcome to AegisAI</h1>
            <p className="text-xs text-gray-500">First-run interactive onboarding wizard</p>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-gray-100">
          {STEPS.map((step, idx) => {
            const isActive = idx === currentStep
            const isCompleted = idx < currentStep
            return (
              <div key={step.label} className="flex items-center gap-3 flex-1 last:flex-initial">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                      isCompleted
                        ? 'bg-green-500 text-white shadow-sm'
                        : isActive
                        ? 'border-2 border-primary-600 text-primary-600 bg-primary-50 ring-4 ring-primary-100'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {isCompleted ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <div className="hidden md:block">
                    <p className={`text-xs font-bold leading-none ${isActive ? 'text-primary-600' : isCompleted ? 'text-green-600' : 'text-gray-400'}`}>
                      {step.label}
                    </p>
                  </div>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 min-w-[20px] mx-2 rounded-full transition-all duration-500 ${
                      idx < currentStep ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Step content */}
        <div className="mb-8 min-h-[340px]">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-primary-50 rounded-lg">
              <StepIcon className="w-6 h-6 text-primary-600" />
            </div>
            <h2 className="text-lg font-bold text-gray-900">
              {STEPS[currentStep].label}
            </h2>
          </div>
          <p className="text-gray-600 text-sm leading-relaxed">{STEPS[currentStep].description}</p>

          {/* Form Fields for Step 1 */}
          {currentStep === 0 && (
            <div className="space-y-4 mt-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  System Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all placeholder:text-gray-400 text-gray-900 shadow-sm text-sm"
                  placeholder="e.g., CV Screening AI"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all placeholder:text-gray-400 text-gray-900 shadow-sm text-sm"
                  rows={3}
                  placeholder="Brief description of what your AI system does"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Sector
                  </label>
                  <select
                    value={sector}
                    onChange={(e) => setSector(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-gray-900 shadow-sm text-sm cursor-pointer"
                  >
                    <option value="">Select sector...</option>
                    {SECTORS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Use Case
                  </label>
                  <select
                    value={useCase}
                    onChange={(e) => setUseCase(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-gray-900 shadow-sm text-sm cursor-pointer"
                  >
                    <option value="">Select use case...</option>
                    {USE_CASES.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Form Fields for Step 2 */}
          {currentStep === 1 && (
            <div className="mt-6 space-y-4">
              <div className="bg-primary-50 border border-primary-100 rounded-xl p-4 flex gap-3 text-sm text-primary-800">
                <Shield className="w-5 h-5 text-primary-600 shrink-0 mt-0.5 animate-pulse" />
                <div>
                  <span className="font-semibold">Automatic Analysis:</span> Classification runs automatically under the hood! AegisAI analyzes your sector and use case selections in real-time.
                </div>
              </div>

              {/* Dynamic Risk Guide Demonstration */}
              <div className="border border-gray-200 rounded-xl p-4 bg-gray-50 space-y-3">
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Risk Classification Guide
                </h3>
                <div className="space-y-2">
                  {[
                    { level: 'unacceptable', label: 'Unacceptable Risk', desc: 'Cognitive behavioral manipulation, social scoring systems, real-time remote biometric scanning.', color: 'bg-red-500', text: 'text-red-700', bg: 'bg-red-50 border-red-200' },
                    { level: 'high', label: 'High Risk', desc: 'Critical infrastructure, educational grading, employment candidate screening, law enforcement tools.', color: 'bg-orange-500', text: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
                    { level: 'limited', label: 'Limited Risk', desc: 'Transparency requirements apply (e.g. conversational chatbots, synthetic deep fakes, emotion detectors).', color: 'bg-yellow-500', text: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200' },
                    { level: 'minimal', label: 'Minimal Risk', desc: 'No special regulatory obligations (e.g. spam-filtering algorithms, search query recommenders, basic video game AI).', color: 'bg-green-500', text: 'text-green-700', bg: 'bg-green-50 border-green-200' },
                  ].map((risk) => {
                    const isSuggested =
                      (useCase === 'CV Screening' || useCase === 'Candidate Ranking' || useCase === 'Performance Evaluation' || sector === 'HR Tech' || sector === 'Healthcare' || sector === 'Education') && risk.level === 'high'
                        ? true
                        : (useCase === 'Customer Service' || useCase === 'Content Generation') && risk.level === 'limited'
                        ? true
                        : sector === 'Finance' && useCase === 'Credit Scoring' && risk.level === 'high'
                        ? true
                        : sector && useCase && risk.level === 'minimal'
                        ? true
                        : risk.level === 'minimal';
                    
                    return (
                      <div
                        key={risk.level}
                        className={`flex items-start gap-3 p-3 rounded-lg border transition-all duration-300 ${
                          isSuggested ? `${risk.bg} ring-2 ring-offset-1 ring-primary-500 scale-[1.01] shadow-sm` : 'bg-white border-gray-100 opacity-60'
                        }`}
                      >
                        <div className={`w-3 h-3 rounded-full ${risk.color} mt-1 shrink-0`} />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className={`text-xs font-bold ${isSuggested ? risk.text : 'text-gray-700'}`}>
                              {risk.label}
                            </span>
                            {isSuggested && (
                              <span className="text-[10px] bg-primary-100 text-primary-800 font-bold px-1.5 py-0.5 rounded uppercase">
                                Suggested Level
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-gray-500 mt-0.5">{risk.desc}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Form Fields for Step 3 */}
          {currentStep === 2 && (
            <div className="mt-6 space-y-3">
              {[
                {
                  id: 'conformity',
                  label: 'Conformity Declaration',
                  desc: 'Formal declaration of compliance under EU AI Act Chapter IV guidelines.',
                  icon: Shield,
                },
                {
                  id: 'risk_assessment',
                  label: 'Risk Assessment Report',
                  desc: 'Detailed assessment mapping risks, mitigation strategies, and system impacts.',
                  icon: FileCheck,
                },
                {
                  id: 'architecture',
                  label: 'System Architecture Review',
                  desc: 'Comprehensive view of data pipelines, models, and technical controls.',
                  icon: Bot,
                },
                {
                  id: 'impact',
                  label: 'Human Rights Impact Assessment',
                  desc: 'Detailed analysis evaluating systemic human rights and safety implications.',
                  icon: FileText,
                },
              ].map((doc) => {
                const DocIcon = doc.icon
                const isSelected = selectedDocType === doc.id
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => setSelectedDocType(doc.id)}
                    className={`w-full text-left p-3.5 rounded-xl border flex items-start gap-3.5 transition-all duration-300 ${
                      isSelected
                        ? 'border-primary-600 bg-primary-50/50 ring-2 ring-primary-500/20 shadow-sm'
                        : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50/50'
                    }`}
                  >
                    <div
                      className={`p-2.5 rounded-lg shrink-0 transition-colors duration-300 ${
                        isSelected ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      <DocIcon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-semibold ${isSelected ? 'text-primary-950 font-bold' : 'text-gray-900'}`}>
                          {doc.label}
                        </span>
                        {isSelected && (
                          <div className="w-4 h-4 rounded-full bg-primary-600 text-white flex items-center justify-center animate-scaleIn">
                            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                        {doc.desc}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between border-t border-gray-100 pt-6">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0}
            className="px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={isNextDisabled}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-primary-100 hover:shadow-primary-200 transition-all"
          >
            {isLastStep ? 'Finish' : 'Next'}
            {!isLastStep && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}


import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { classificationApi } from '../services/api'
import { CheckCircle, HelpCircle } from 'lucide-react'
import ComplianceChecklist, { ChecklistItem } from '../components/ComplianceChecklist'
import {
  RiskBadge,
  EditableRiskLevel,
  AIMetadataBanner,
  CategorySelector,
  Tooltip,
  RISK_CONFIG,
  type RiskLevel,
} from '../components/AIPredictionBadge'

interface ClassificationResult {
  risk_level: string
  confidence: number
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

const CHECKLIST_ITEMS: Record<string, ChecklistItem[]> = {
  high: [
    { id: 'tech-doc', label: 'Create Technical Documentation', article: 'Article 11', required: true },
    { id: 'risk-assessment', label: 'Conduct Risk Assessment', article: 'Article 9', required: true },
    { id: 'human-oversight', label: 'Establish Human Oversight', article: 'Article 14', required: true },
    { id: 'conformity', label: 'EU Declaration of Conformity', article: 'Article 47', required: true },
    { id: 'logging', label: 'Implement automatic logging', article: 'Article 12', required: true },
  ],
  limited: [
    { id: 'transparency', label: 'Disclose AI interaction to users', article: 'Article 52', required: true },
  ],
  minimal: [
    { id: 'best-practice', label: 'Follow voluntary AI best practices', required: false },
  ],
  unacceptable: [],
}

// ─── Checkbox helper ──────────────────────────────────────────────────────────

interface FormCheckboxProps {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  sublabel: string
  tooltip?: string
}

function FormCheckbox({ checked, onChange, label, sublabel, tooltip }: FormCheckboxProps) {
  return (
    <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 hover:border-primary-200 cursor-pointer transition-all group">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 w-4 h-4 accent-primary-600"
      />
      <span className="text-sm text-gray-600 flex-1">
        <strong className="text-gray-800">{label}</strong>
        <br />
        {sublabel}
      </span>
      {tooltip && (
        <Tooltip content={tooltip}>
          <HelpCircle className="w-4 h-4 text-gray-300 group-hover:text-gray-400 flex-shrink-0 mt-0.5 cursor-help" />
        </Tooltip>
      )}
    </label>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function Classification() {
  const { systemId } = useParams()
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [overriddenLevel, setOverriddenLevel] = useState<RiskLevel | null>(null)
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
      if (systemId) return classificationApi.classifyAndSave(parseInt(systemId), formData)
      return classificationApi.classify(formData)
    },
    onSuccess: (data) => {
      setResult(data)
      setOverriddenLevel(null) // reset override on new classification
    },
  })

  const activeLevel = (overriddenLevel ?? result?.risk_level ?? 'minimal') as RiskLevel
  const cfg = RISK_CONFIG[activeLevel]

  const getRiskCardStyle = (level: RiskLevel) => {
    const styles: Record<RiskLevel, string> = {
      unacceptable: 'bg-red-50 border-red-200',
      high: 'bg-orange-50 border-orange-200',
      limited: 'bg-yellow-50 border-yellow-200',
      minimal: 'bg-green-50 border-green-200',
    }
    return styles[level]
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Classification</h1>
        <p className="text-gray-600 mt-1">
          Determine your AI system's risk level under the EU AI Act
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ── Questionnaire ─────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">Classification Questionnaire</h2>

          <form className="space-y-6">
            {/* Primary Use Case */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Primary Use Case
                </label>
                <Tooltip content="Select the domain that best describes your AI system. This is one of the strongest signals used to determine risk level under EU AI Act Annex III.">
                  <HelpCircle className="w-4 h-4 text-gray-300 cursor-help" />
                </Tooltip>
              </div>
              <CategorySelector
                value={formData.use_case_category}
                onChange={(v) => setFormData({ ...formData, use_case_category: v })}
              />
            </div>

            {/* High-Risk Indicators */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-medium text-gray-900">
                  High-Risk Indicators (Annex III)
                </h3>
                <Tooltip content="Annex III of the EU AI Act lists specific use-case categories that automatically qualify an AI system as high-risk. Select all that apply.">
                  <HelpCircle className="w-4 h-4 text-gray-300 cursor-help" />
                </Tooltip>
              </div>
              <div className="space-y-2">
                <FormCheckbox
                  checked={formData.hr_recruitment_screening}
                  onChange={(v) => setFormData({ ...formData, hr_recruitment_screening: v })}
                  label="CV Screening / Candidate Ranking"
                  sublabel="AI filters CVs or ranks candidates for recruitment"
                  tooltip="Covered under Annex III §4 — AI systems used in employment, workers management and access to self-employment."
                />
                <FormCheckbox
                  checked={formData.hr_promotion_termination}
                  onChange={(v) => setFormData({ ...formData, hr_promotion_termination: v })}
                  label="Promotion / Termination Decisions"
                  sublabel="AI influences employment status decisions"
                  tooltip="Employment decisions that affect an individual's rights or working conditions."
                />
                <FormCheckbox
                  checked={formData.credit_worthiness}
                  onChange={(v) => setFormData({ ...formData, credit_worthiness: v })}
                  label="Credit Worthiness Assessment"
                  sublabel="AI evaluates creditworthiness or credit scoring"
                  tooltip="Covered under Annex III §5 — AI in access to essential private services and benefits."
                />
                <FormCheckbox
                  checked={formData.affects_fundamental_rights}
                  onChange={(v) => setFormData({ ...formData, affects_fundamental_rights: v })}
                  label="Affects Fundamental Rights"
                  sublabel="Impacts employment, education, or essential services"
                  tooltip="Any AI system that materially affects fundamental rights protected under EU law is considered high-risk."
                />
                <FormCheckbox
                  checked={formData.makes_automated_decisions}
                  onChange={(v) => setFormData({ ...formData, makes_automated_decisions: v })}
                  label="Automated Decision Making"
                  sublabel="Makes decisions without meaningful human review"
                  tooltip="Fully automated decisions that significantly affect individuals require enhanced safeguards under Article 22 GDPR and the AI Act."
                />
              </div>
            </div>

            {/* Transparency Indicators */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-medium text-gray-900">
                  Transparency Indicators (Article 52)
                </h3>
                <Tooltip content="Article 52 requires transparency when AI systems interact directly with humans, generate synthetic content, or perform emotion/biometric analysis.">
                  <HelpCircle className="w-4 h-4 text-gray-300 cursor-help" />
                </Tooltip>
              </div>
              <div className="space-y-2">
                <FormCheckbox
                  checked={formData.interacts_with_humans}
                  onChange={(v) => setFormData({ ...formData, interacts_with_humans: v })}
                  label="Direct Human Interaction"
                  sublabel="System interacts directly with users (chatbot, assistant)"
                  tooltip="AI systems that interact directly with humans must clearly disclose they are AI — Article 52(1)."
                />
                <FormCheckbox
                  checked={formData.emotion_recognition}
                  onChange={(v) => setFormData({ ...formData, emotion_recognition: v })}
                  label="Emotion Recognition"
                  sublabel="System detects or analyzes emotions"
                  tooltip="Emotion recognition systems must inform users of this capability — Article 52(3)."
                />
                <FormCheckbox
                  checked={formData.generates_synthetic_content}
                  onChange={(v) => setFormData({ ...formData, generates_synthetic_content: v })}
                  label="Synthetic Content Generation"
                  sublabel="Generates deepfakes, AI images, or synthetic media"
                  tooltip="Deepfake and synthetic media generators must label outputs as AI-generated — Article 52(4)."
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => classifyMutation.mutate()}
              disabled={classifyMutation.isPending}
              className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium transition-all"
            >
              {classifyMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                    <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" className="opacity-75" />
                  </svg>
                  Classifying...
                </span>
              ) : (
                'Classify Risk Level'
              )}
            </button>
          </form>
        </div>

        {/* ── Results ────────────────────────────────────────────────────── */}
        <div>
          {result ? (
            <div className={`rounded-xl border-2 p-6 space-y-6 transition-all ${getRiskCardStyle(activeLevel)}`}>
              {/* AI metadata banner */}
              <AIMetadataBanner />

              {/* Editable risk level + confidence */}
              <EditableRiskLevel
                level={(result.risk_level as RiskLevel)}
                onEdit={(newLevel) => setOverriddenLevel(newLevel)}
                confidence={result.confidence}
              />

              {/* Reasons */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="font-semibold text-gray-900">Why this classification?</h3>
                  <Tooltip content="These are the factors from your questionnaire that the AI used to determine the risk level. Each reason maps to a specific EU AI Act provision.">
                    <HelpCircle className="w-4 h-4 text-gray-400 cursor-help" />
                  </Tooltip>
                </div>
                <ul className="space-y-2">
                  {result.reasons.map((reason, i) => (
                    <li
                      key={i}
                      className="text-sm text-gray-600 flex items-start gap-2 bg-white/60 rounded-lg px-3 py-2 border border-white"
                    >
                      <span className={`mt-0.5 flex-shrink-0 ${cfg?.badgeText ?? 'text-gray-400'}`}>•</span>
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Compliance requirements */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="font-semibold text-gray-900">Compliance Requirements</h3>
                  <Tooltip content="These are mandatory obligations you must fulfil under the EU AI Act for this risk level.">
                    <HelpCircle className="w-4 h-4 text-gray-400 cursor-help" />
                  </Tooltip>
                </div>
                <ul className="space-y-2">
                  {result.requirements.map((req, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2 bg-white/60 rounded-lg px-3 py-2 border border-white">
                      <CheckCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      {req}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Next steps */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Recommended Next Steps</h3>
                <ol className="space-y-2">
                  {result.next_steps.map((step, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-3 bg-white/60 rounded-lg px-3 py-2 border border-white">
                      <span className="w-5 h-5 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Compliance checklist */}
              {activeLevel !== 'unacceptable' && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="font-semibold text-gray-900">Compliance Checklist</h3>
                    <Tooltip content="Track your progress toward meeting each compliance requirement. Check items off as you complete them.">
                      <HelpCircle className="w-4 h-4 text-gray-400 cursor-help" />
                    </Tooltip>
                  </div>
                  <div className="bg-white/70 rounded-xl border border-white p-4">
                    <ComplianceChecklist
                      systemId={Number(systemId || 0)}
                      riskLevel={activeLevel as 'minimal' | 'limited' | 'high' | 'unacceptable'}
                      items={CHECKLIST_ITEMS[activeLevel] || []}
                    />
                  </div>
                </div>
              )}

              {/* EU Article link */}
              {cfg && (
                <div className="text-xs text-gray-400 flex items-center gap-1.5 pt-2 border-t border-white/60">
                  <span>Reference:</span>
                  <span className="text-primary-600 font-medium">{cfg.euArticle}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-8 text-center h-full flex flex-col items-center justify-center gap-4">
              <div className="flex gap-3">
                {(['unacceptable', 'high', 'limited', 'minimal'] as RiskLevel[]).map((lvl) => (
                  <RiskBadge key={lvl} level={lvl} size="sm" showTooltip={false} />
                ))}
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">Complete the Questionnaire</h3>
                <p className="text-gray-500 mt-2 text-sm max-w-xs mx-auto">
                  Answer the questions on the left to determine your AI system's risk classification
                  under the EU AI Act.
                </p>
              </div>
              <p className="text-xs text-gray-400">
                The AI engine will predict a risk level with a confidence score you can review and override.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

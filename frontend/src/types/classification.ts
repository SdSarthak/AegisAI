export type Tab = 'questionnaire' | 'results' | 'requirements'
export type RiskLevel = 'minimal' | 'limited' | 'high' | 'unacceptable'

export interface ClassificationResult {
  risk_level: string
  confidence: number
  reasoning?: string
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

export interface RequirementContent {
  title: string
  description: string
  obligations: string[]
}

export interface ClassificationFormData {
  use_case_category: string
  is_safety_component: boolean
  affects_fundamental_rights: boolean
  uses_biometric_data: boolean
  makes_automated_decisions: boolean
  hr_recruitment_screening: boolean
  hr_promotion_termination: boolean
  credit_worthiness: boolean
  insurance_risk_assessment: boolean
  law_enforcement: boolean
  border_control: boolean
  justice_system: boolean
  education_vocational_training: boolean
  interacts_with_humans: boolean
  generates_synthetic_content: boolean
  emotion_recognition: boolean
  biometric_categorization: boolean
}

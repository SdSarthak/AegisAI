export interface AISystem {
  id: number
  name: string
  description: string | null
  use_case: string | null
  sector: string | null
  risk_level: string | null
  compliance_status: string
  compliance_score: number
  updated_at: string
}

export interface AISystemFormData {
  name: string
  description: string
  use_case: string
  sector: string
}

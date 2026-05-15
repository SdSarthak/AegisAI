import { createElement } from 'react'
import { XCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react'

// ─── Risk level types ─────────────────────────────────────────────────────────

export type RiskLevel = 'unacceptable' | 'high' | 'limited' | 'minimal'

export interface RiskConfig {
  label: string
  shortLabel: string
  icon: React.ReactNode
  badgeBg: string
  badgeText: string
  borderColor: string
  ringColor: string
  description: string
  euArticle: string
}

// ─── Risk-level metadata ──────────────────────────────────────────────────────

export const RISK_CONFIG: Record<RiskLevel, RiskConfig> = {
  unacceptable: {
    label: 'Unacceptable Risk',
    shortLabel: 'Unacceptable',
    icon: createElement(XCircle, { className: 'w-4 h-4' }),
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    borderColor: 'border-red-300',
    ringColor: 'ring-red-200',
    description:
      'Prohibited under the EU AI Act. These AI practices pose an unacceptable risk to fundamental rights and safety.',
    euArticle: 'Article 5 — Prohibited AI Practices',
  },
  high: {
    label: 'High Risk',
    shortLabel: 'High',
    icon: createElement(AlertTriangle, { className: 'w-4 h-4' }),
    badgeBg: 'bg-orange-100',
    badgeText: 'text-orange-700',
    borderColor: 'border-orange-300',
    ringColor: 'ring-orange-200',
    description:
      'Significant compliance obligations apply — including technical documentation, human oversight, and conformity assessments.',
    euArticle: 'Annex III — High-Risk AI Systems',
  },
  limited: {
    label: 'Limited Risk',
    shortLabel: 'Limited',
    icon: createElement(Info, { className: 'w-4 h-4' }),
    badgeBg: 'bg-yellow-100',
    badgeText: 'text-yellow-700',
    borderColor: 'border-yellow-300',
    ringColor: 'ring-yellow-200',
    description:
      'Transparency obligations apply. Users must be informed when they are interacting with an AI system.',
    euArticle: 'Article 52 — Transparency Obligations',
  },
  minimal: {
    label: 'Minimal Risk',
    shortLabel: 'Minimal',
    icon: createElement(CheckCircle, { className: 'w-4 h-4' }),
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
    borderColor: 'border-green-300',
    ringColor: 'ring-green-200',
    description:
      'No mandatory obligations. Voluntary codes of conduct and best practices are recommended.',
    euArticle: 'Recital 48 — Minimal Risk AI',
  },
}

export const ALL_RISK_LEVELS: RiskLevel[] = ['unacceptable', 'high', 'limited', 'minimal']

// ─── Use-case categories ──────────────────────────────────────────────────────

export interface UseCaseCategory {
  value: string
  label: string
  description: string
}

export const USE_CASE_CATEGORIES: UseCaseCategory[] = [
  { value: 'hr_recruitment',  label: 'HR / Recruitment',   description: 'Screening CVs, candidate ranking, or employment decisions.' },
  { value: 'credit_scoring',  label: 'Credit Scoring',     description: 'Creditworthiness or insurance risk evaluation.' },
  { value: 'healthcare',      label: 'Healthcare',         description: 'Medical diagnosis, treatment recommendation, or patient management.' },
  { value: 'education',       label: 'Education',          description: 'Student evaluation, tutoring, or learning path management.' },
  { value: 'law_enforcement', label: 'Law Enforcement',    description: 'Predictive policing, facial recognition, or criminal risk assessment.' },
  { value: 'border_control',  label: 'Border Control',     description: 'Automated checks at borders, identity verification.' },
  { value: 'customer_service',label: 'Customer Service',   description: 'Chatbots, virtual assistants, or automated support.' },
  { value: 'other',           label: 'Other',              description: 'Any other use case not listed above.' },
]

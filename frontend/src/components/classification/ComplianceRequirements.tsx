import React from 'react'
import { ClassificationResult, RiskLevel, RequirementContent } from '../../types/classification'
import { ShieldCheck } from 'lucide-react'
import ComplianceChecklist, { ChecklistItem } from '../ComplianceChecklist'

interface ComplianceRequirementsProps {
  result: ClassificationResult | null
  systemId: string | undefined
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

export default function ComplianceRequirements({ result, systemId }: ComplianceRequirementsProps) {
  if (!result) return null;

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

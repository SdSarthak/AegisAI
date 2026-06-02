import React from 'react'
import { ClassificationFormData } from '../../types/classification'
import { UseMutationResult } from '@tanstack/react-query'

interface QuestionnaireFormProps {
  formData: ClassificationFormData
  setFormData: (data: ClassificationFormData) => void
  classifyMutation: UseMutationResult<any, Error, void, unknown>
}

export default function QuestionnaireForm({ formData, setFormData, classifyMutation }: QuestionnaireFormProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Classification Questionnaire
      </h2>

      <form className="space-y-6">
        {/* Use Case Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Primary Use Case
          </label>
          <select
            value={formData.use_case_category}
            onChange={(e) =>
              setFormData({ ...formData, use_case_category: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="hr_recruitment">HR / Recruitment</option>
            <option value="credit_scoring">Credit Scoring</option>
            <option value="healthcare">Healthcare</option>
            <option value="education">Education</option>
            <option value="customer_service">Customer Service</option>
            <option value="other">Other</option>
          </select>
        </div>

        {/* High-Risk Indicators */}
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            High-Risk Indicators (Annex III)
          </h3>
          <div className="space-y-3">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.hr_recruitment_screening}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    hr_recruitment_screening: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>CV Screening / Candidate Ranking</strong>
                <br />
                AI filters CVs or ranks candidates for recruitment
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.hr_promotion_termination}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    hr_promotion_termination: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Promotion/Termination Decisions</strong>
                <br />
                AI influences employment status decisions
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.credit_worthiness}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    credit_worthiness: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Credit Worthiness Assessment</strong>
                <br />
                AI evaluates creditworthiness or credit scoring
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.insurance_risk_assessment}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    insurance_risk_assessment: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Insurance Risk Assessment</strong>
                <br />
                AI evaluates risk for insurance pricing or eligibility
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.law_enforcement}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    law_enforcement: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Law Enforcement Use</strong>
                <br />
                Used by police or judicial authorities for decisions
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.border_control}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    border_control: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Border Control / Migration</strong>
                <br />
                Used for visa, asylum, or border management decisions
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.justice_system}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    justice_system: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Justice System / Legal Aid</strong>
                <br />
                Assists courts or legal processes with decisions
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.is_safety_component}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    is_safety_component: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Safety-Critical Component</strong>
                <br />
                Part of a product regulated under EU safety legislation
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.uses_biometric_data}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    uses_biometric_data: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Uses Biometric Data</strong>
                <br />
                Processes fingerprints, face scans, or other biometrics
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.biometric_categorization}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    biometric_categorization: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Biometric Categorization</strong>
                <br />
                Categorizes people by race, gender, or political views from biometrics
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.affects_fundamental_rights}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    affects_fundamental_rights: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Affects Fundamental Rights</strong>
                <br />
                Impacts employment, education, or essential services
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.makes_automated_decisions}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    makes_automated_decisions: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Automated Decision Making</strong>
                <br />
                Makes decisions without meaningful human review
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.education_vocational_training}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    education_vocational_training: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Education & Vocational Training</strong>
                <br />
                AI determines access to or assigns persons to educational institutions
              </span>
            </label>
          </div>
        </div>

        {/* Transparency Requirements */}
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Transparency Indicators (Article 52)
          </h3>
          <div className="space-y-3">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.interacts_with_humans}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    interacts_with_humans: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Direct Human Interaction</strong>
                <br />
                System interacts directly with users (chatbot, assistant)
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.emotion_recognition}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    emotion_recognition: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Emotion Recognition</strong>
                <br />
                System detects or analyzes emotions
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.generates_synthetic_content}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    generates_synthetic_content: e.target.checked,
                  })
                }
                className="mt-1"
              />
              <span className="text-sm text-gray-600">
                <strong>Synthetic Content Generation</strong>
                <br />
                Generates deepfakes, AI images, or synthetic media
              </span>
            </label>
          </div>
        </div>

        <button
          type="button"
          onClick={() => classifyMutation.mutate()}
          disabled={classifyMutation.isPending}
          className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          {classifyMutation.isPending ? 'Classifying...' : 'Classify Risk Level'}
        </button>

        {classifyMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {classifyMutation.error instanceof Error
              ? classifyMutation.error.message
              : 'Unable to classify this system right now.'}
          </div>
        )}
      </form>
    </div>
  )
}

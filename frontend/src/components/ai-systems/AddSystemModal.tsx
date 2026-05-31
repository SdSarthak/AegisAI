import React from 'react'
import { AISystemFormData } from '../../types/aiSystem'
import { UseMutationResult } from '@tanstack/react-query'

interface AddSystemModalProps {
  formData: AISystemFormData
  setFormData: (data: AISystemFormData) => void
  setShowModal: (show: boolean) => void
  createMutation: UseMutationResult<any, Error, AISystemFormData, unknown>
}

export default function AddSystemModal({
  formData,
  setFormData,
  setShowModal,
  createMutation
}: AddSystemModalProps) {
  const sectors = [
    'HR Tech',
    'Finance',
    'Healthcare',
    'Education',
    'Legal',
    'Marketing',
    'Other',
  ]

  const useCases = [
    'CV Screening',
    'Candidate Ranking',
    'Performance Evaluation',
    'Credit Scoring',
    'Risk Assessment',
    'Customer Service',
    'Content Generation',
    'Other',
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Add AI System
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              System Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              placeholder="e.g., CV Screening AI"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              rows={3}
              placeholder="Brief description of what your AI system does"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Sector
            </label>
            <select
              value={formData.sector}
              onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Select sector...</option>
              {sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Use Case
            </label>
            <select
              value={formData.use_case}
              onChange={(e) => setFormData({ ...formData, use_case: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Select use case...</option>
              {useCases.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => setShowModal(false)}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Adding...' : 'Add System'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

import React from 'react'
import { Bot, Edit, Trash2, Plus, Download } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { AISystem } from '../../types/aiSystem'

interface SystemListProps {
  systems: AISystem[]
  isLoading: boolean
  isError: boolean
  error: Error | null
  refetch: () => void
  searchTerm: string
  riskFilter: string
  complianceFilter: string
  handleExport: () => void
  exporting: boolean
  setShowModal: (show: boolean) => void
  setSystemToDelete: (system: AISystem) => void
}

export default function SystemList({
  systems,
  isLoading,
  isError,
  error,
  refetch,
  searchTerm,
  riskFilter,
  complianceFilter,
  handleExport,
  exporting,
  setShowModal,
  setSystemToDelete
}: SystemListProps) {
  const getRiskBadge = (riskLevel: string | null) => {
    switch (riskLevel) {
      case 'unacceptable':
        return { label: 'Unacceptable', className: 'bg-red-100 text-red-700' }
      case 'high':
        return { label: 'High', className: 'bg-orange-100 text-orange-700' }
      case 'limited':
        return { label: 'Limited', className: 'bg-yellow-100 text-yellow-700' }
      case 'minimal':
        return { label: 'Minimal', className: 'bg-green-100 text-green-700' }
      default:
        return { label: 'Unknown', className: 'bg-gray-100 text-gray-700' }
    }
  }

  if (isLoading) {
    return (
      <div className="grid gap-4">
        {[...Array(4)].map((_, index) => (
          <div key={index} className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
            <div className="flex justify-between items-start">
              <div className="space-y-3 flex-1">
                <div className="h-5 bg-gray-200 rounded w-1/3"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                <div className="flex gap-2">
                  <div className="h-5 w-20 bg-gray-200 rounded"></div>
                  <div className="h-5 w-24 bg-gray-200 rounded"></div>
                </div>
              </div>
              <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
        <Bot className="w-16 h-16 mx-auto mb-4 text-red-300" />
        <h3 className="text-lg font-medium text-gray-900">Unable to load AI systems</h3>
        <p className="text-gray-500 mt-1">
          {error?.message || 'Please try again.'}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (systems.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
        <Bot className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-900">
          {searchTerm || riskFilter || complianceFilter
            ? 'No matching AI systems'
            : 'No AI systems yet'}
        </h3>
        <p className="text-gray-500 mt-1">
          {searchTerm || riskFilter || complianceFilter
            ? 'Try adjusting your filters or search term'
            : 'Add your first AI system to start tracking compliance'}
        </p>
        {!searchTerm && !riskFilter && !complianceFilter && (
          <div className="flex items-center justify-center gap-3 mt-4">
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-5 h-5" />
              {exporting ? 'Exporting...' : 'Export CSV'}
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-5 h-5" />
              Add AI System
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      {systems.map((system: AISystem) => (
        <div key={system.id} className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-primary-50 rounded-lg">
                <Bot className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{system.name}</h3>
                {system.description && (
                  <p className="text-gray-600 text-sm mt-1">{system.description}</p>
                )}
                {system.updated_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Updated{' '}
                    {formatDistanceToNow(new Date(system.updated_at), { addSuffix: true })}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-2">
                  {system.sector && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      {system.sector}
                    </span>
                  )}
                  {system.use_case && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      {system.use_case}
                    </span>
                  )}
                  {system.risk_level && (
                    <span className={`text-xs px-2 py-1 rounded ${getRiskBadge(system.risk_level).className}`}>
                      {getRiskBadge(system.risk_level).label}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                <Edit className="w-5 h-5" />
              </button>
              <button
                onClick={() => setSystemToDelete(system)}
                className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Compliance Score</span>
              <span className="font-medium">{system.compliance_score}%</span>
            </div>
            <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  system.compliance_score >= 80
                    ? 'bg-green-500'
                    : system.compliance_score >= 50
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${system.compliance_score}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

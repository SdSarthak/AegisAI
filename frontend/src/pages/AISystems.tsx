import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi } from '../services/api'
import { Bot, Plus, Trash2, Edit, Search, Filter, ArrowUpDown, X, Download } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface AISystem {
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

export default function AISystems() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    use_case: '',
    sector: '',
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [complianceFilter, setComplianceFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [order, setOrder] = useState('desc')
  const [systemToDelete, setSystemToDelete] = useState<AISystem | null>(null)
  const [currentPage, setCurrentPage] = useState(1)

  const limit = 10

  const { data: systemsData, isLoading } = useQuery({
    queryKey: ['ai-systems', sortBy, order, currentPage],
    queryFn: () =>
      aiSystemsApi.list({
        sort_by: sortBy,
        order,
        page: currentPage,
        limit,
      }),
  })
  const systems = Array.isArray(systemsData) ? systemsData : (systemsData?.items ?? [])

  const createMutation = useMutation({
    mutationFn: aiSystemsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
      setShowModal(false)
      setFormData({ name: '', description: '', use_case: '', sector: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: aiSystemsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
      setSystemToDelete(null)
    },
  })

  const filteredSystems = systems.filter((system: AISystem) => {
    const matchesSearch =
      system.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (system.description?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false)

    const matchesRisk = !riskFilter || system.risk_level === riskFilter
    const matchesCompliance = !complianceFilter || system.compliance_status === complianceFilter

    return matchesSearch && matchesRisk && matchesCompliance
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

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

  // FIX 1: Use native fetch instead of aiSystemsApi.get() which doesn't exist.
  // FIX 2: Guard against null token before building the Authorization header.
  const handleExport = async () => {
    try {
      setIsExporting(true)

      const token = localStorage.getItem('token')
      if (!token) {
        console.error('No auth token found. Please log in again.')
        return
      }

      const params = new URLSearchParams()
      if (riskFilter) params.set('risk_level', riskFilter)

      const url = `/api/v1/ai-systems/export${params.toString() ? `?${params.toString()}` : ''}`

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'text/csv',
        },
      })

      if (!response.ok) {
        throw new Error(`Export failed with status ${response.status}`)
      }

      const blob = await response.blob()
      const objectUrl = window.URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = objectUrl
      link.setAttribute('download', 'ai_systems.csv')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(objectUrl)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setIsExporting(false)
    }
  }

  // FIX 3: Reset to page 1 whenever filters or sort options change,
  // so users never land on an empty page after narrowing results.
  const handleRiskFilterChange = (value: string) => {
    setRiskFilter(value)
    setCurrentPage(1)
  }

  const handleComplianceFilterChange = (value: string) => {
    setComplianceFilter(value)
    setCurrentPage(1)
  }

  const handleSortByChange = (value: string) => {
    setSortBy(value)
    setCurrentPage(1)
  }

  const handleOrderChange = (value: string) => {
    setOrder(value)
    setCurrentPage(1)
  }

  const handleClearFilters = () => {
    setSearchTerm('')
    setRiskFilter('')
    setComplianceFilter('')
    setCurrentPage(1)
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Systems</h1>
          <p className="text-gray-600">Manage your AI systems for compliance tracking</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 bg-white text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-5 h-5" />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>

          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-5 h-5" />
            Add AI System
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search AI systems..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1) // FIX 3 applied to search too
            }}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              value={riskFilter}
              onChange={(e) => handleRiskFilterChange(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="">All Risk Levels</option>
              <option value="unacceptable">Unacceptable Risk</option>
              <option value="high">High Risk</option>
              <option value="limited">Limited Risk</option>
              <option value="minimal">Minimal Risk</option>
            </select>
          </div>
          <div className="relative">
            <Bot className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              value={complianceFilter}
              onChange={(e) => handleComplianceFilterChange(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="not_started">Not Started</option>
              <option value="in_progress">In Progress</option>
              <option value="under_review">Under Review</option>
              <option value="compliant">Compliant</option>
              <option value="non_compliant">Non Compliant</option>
            </select>
          </div>
          <div className="relative">
            <ArrowUpDown className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              id="sort-by-select"
              value={sortBy}
              onChange={(e) => handleSortByChange(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="created_at">Sort by Date</option>
              <option value="name">Sort by Name</option>
              <option value="risk_level">Sort by Risk Level</option>
              <option value="compliance_score">Sort by Score</option>
            </select>
          </div>
          <div className="relative">
            <select
              id="sort-order-select"
              value={order}
              onChange={(e) => handleOrderChange(e.target.value)}
              className="px-3 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
          {(searchTerm || riskFilter || complianceFilter) && (
            <button
              onClick={handleClearFilters}
              className="flex items-center gap-1 px-3 py-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all text-sm font-medium"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4">
          {[...Array(4)].map((_, index) => (
            <div
              key={index}
              className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse"
            >
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
      ) : filteredSystems.length === 0 ? (
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
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Add AI System
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredSystems.map((system: AISystem) => (
            <div
              key={system.id}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
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
                        {formatDistanceToNow(new Date(system.updated_at), {
                          addSuffix: true,
                        })}
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
                        <span
                          className={`text-xs px-2 py-1 rounded ${getRiskBadge(system.risk_level).className}`}
                        >
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

              {/* Compliance Progress */}
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
      )}

      {/* FIX 3: Pagination uses filteredSystems.length for the Next button,
          so local filters correctly reflect whether more pages exist. */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
          disabled={currentPage === 1}
          className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Previous
        </button>

        <span className="text-sm font-medium text-gray-700">Page {currentPage}</span>

        <button
          onClick={() => setCurrentPage((prev) => prev + 1)}
          disabled={filteredSystems.length < limit}
          className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Next
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {systemToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Delete AI System</h2>
            <p className="text-gray-600">
              Are you sure you want to delete {systemToDelete.name}? This cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-6">
              <button
                type="button"
                onClick={() => setSystemToDelete(null)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(systemToDelete.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add AI System</h2>
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
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  rows={3}
                  placeholder="Brief description of what your AI system does"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Sector</label>
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
                <label className="block text-sm font-medium text-gray-700">Use Case</label>
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
      )}
    </div>
  )
}
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { Plus, Download } from 'lucide-react'
import ErrorBoundary from '../components/ErrorBoundary'
import { AISystem, AISystemFormData } from '../types/aiSystem'
import FilterBar from '../components/ai-systems/FilterBar'
import SystemList from '../components/ai-systems/SystemList'
import AddSystemModal from '../components/ai-systems/AddSystemModal'

export default function AISystems() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState<AISystemFormData>({
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
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const minDelay = new Promise((r) => setTimeout(r, 1000))
      const fetchExport = async () => {
        const token = useAuthStore.getState().token
        const response = await fetch('/api/v1/ai-systems/export', {
          headers: { Authorization: `Bearer ${token}` },
        })
        return response.blob()
      }
      const [blob] = await Promise.all([fetchExport(), minDelay])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ai_systems.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExporting(false)
    }
  }

  const limit = 10

  const {
    data: systemsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['ai-systems', sortBy, order, currentPage, riskFilter, complianceFilter],
    queryFn: () =>
      aiSystemsApi.list({
        sort_by: sortBy,
        order,
        skip: (currentPage - 1) * limit,
        limit,
      }),
  })
  const systems = (
    Array.isArray(systemsData) ? systemsData : (systemsData?.items ?? [])
  ) as AISystem[]

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
      </div>

      <ErrorBoundary>
        <FilterBar
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          riskFilter={riskFilter}
          setRiskFilter={setRiskFilter}
          complianceFilter={complianceFilter}
          setComplianceFilter={setComplianceFilter}
          sortBy={sortBy}
          setSortBy={setSortBy}
          order={order}
          setOrder={setOrder}
          setCurrentPage={setCurrentPage}
        />

        <SystemList
          systems={filteredSystems}
          isLoading={isLoading}
          isError={isError}
          error={error}
          refetch={refetch}
          searchTerm={searchTerm}
          riskFilter={riskFilter}
          complianceFilter={complianceFilter}
          handleExport={handleExport}
          exporting={exporting}
          setShowModal={setShowModal}
          setSystemToDelete={setSystemToDelete}
        />

        <div className="flex items-center justify-between pt-4">
          <button
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>

          <span className="text-sm font-medium text-gray-700">
            Page {currentPage}
          </span>

          <button
            onClick={() => setCurrentPage((prev) => prev + 1)}
            disabled={systems.length < limit}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
        </div>

        {systemToDelete && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Delete AI System
              </h2>
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

        {showModal && (
          <AddSystemModal
            formData={formData}
            setFormData={setFormData}
            setShowModal={setShowModal}
            createMutation={createMutation}
          />
        )}
      </ErrorBoundary>
    </div>
  )
}

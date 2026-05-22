import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi } from '../services/api'
import {
  Bot,
  Plus,
  Trash2,
  Edit,
  Search,
  Filter,
  ArrowUpDown,
  X,
} from 'lucide-react'

interface AISystem {
  id: number
  name: string
  description: string | null
  use_case: string | null
  sector: string | null
  risk_level: string | null
  compliance_status: string
  compliance_score: number
}

export default function AISystems() {
  const queryClient = useQueryClient()

  const [showModal, setShowModal] = useState(false)

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

  const { data: systems = [], isLoading } = useQuery({
    queryKey: ['ai-systems', sortBy, order],
    queryFn: () => aiSystemsApi.list({ sort_by: sortBy, order }),
  })

  const createMutation = useMutation({
    mutationFn: aiSystemsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems'] })

      setShowModal(false)

      setFormData({
        name: '',
        description: '',
        use_case: '',
        sector: '',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: aiSystemsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
    },
  })

  const filteredSystems = systems.filter((system: AISystem) => {
    const matchesSearch =
      system.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (system.description
        ?.toLowerCase()
        .includes(searchTerm.toLowerCase()) ?? false)

    const matchesRisk =
      !riskFilter || system.risk_level === riskFilter

    const matchesCompliance =
      !complianceFilter ||
      system.compliance_status === complianceFilter

    return (
      matchesSearch &&
      matchesRisk &&
      matchesCompliance
    )
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
        return {
          label: 'Unacceptable',
          className: 'bg-red-100 text-red-700',
        }

      case 'high':
        return {
          label: 'High',
          className: 'bg-orange-100 text-orange-700',
        }

      case 'limited':
        return {
          label: 'Limited',
          className: 'bg-yellow-100 text-yellow-700',
        }

      case 'minimal':
        return {
          label: 'Minimal',
          className: 'bg-green-100 text-green-700',
        }

      default:
        return {
          label: 'Unknown',
          className: 'bg-gray-100 text-gray-700',
        }
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Systems
          </h1>

          <p className="text-gray-600 dark:text-gray-400">
            Manage your AI systems for compliance tracking
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="
            flex items-center gap-2
            px-4 py-2
            bg-primary-600
            text-white
            rounded-lg
            hover:bg-primary-700
            transition-colors
          "
        >
          <Plus className="w-5 h-5" />
          Add AI System
        </button>
      </div>

      {/* Search + Filters */}
      <div
        className="
          flex flex-col md:flex-row gap-4
          bg-white dark:bg-gray-800
          p-4
          rounded-xl
          border border-gray-200 dark:border-gray-700
          shadow-sm
          transition-colors duration-200
        "
      >
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />

          <input
            type="text"
            placeholder="Search AI systems..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="
              w-full
              pl-10 pr-4 py-2
              border border-gray-200 dark:border-gray-700
              bg-white dark:bg-gray-900
              text-gray-900 dark:text-white
              rounded-lg
              focus:ring-2 focus:ring-primary-500
              focus:border-transparent
              outline-none
              transition-all
            "
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          {/* Risk Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />

            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="
                pl-9 pr-4 py-2
                bg-white dark:bg-gray-900
                text-gray-900 dark:text-white
                border border-gray-200 dark:border-gray-700
                rounded-lg
                focus:ring-2 focus:ring-primary-500
                outline-none
                transition-all
                appearance-none
                cursor-pointer
              "
            >
              <option value="">All Risk Levels</option>
              <option value="unacceptable">
                Unacceptable Risk
              </option>
              <option value="high">High Risk</option>
              <option value="limited">Limited Risk</option>
              <option value="minimal">Minimal Risk</option>
            </select>
          </div>

          {/* Compliance Filter */}
          <div className="relative">
            <Bot className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />

            <select
              value={complianceFilter}
              onChange={(e) =>
                setComplianceFilter(e.target.value)
              }
              className="
                pl-9 pr-4 py-2
                bg-white dark:bg-gray-900
                text-gray-900 dark:text-white
                border border-gray-200 dark:border-gray-700
                rounded-lg
                focus:ring-2 focus:ring-primary-500
                outline-none
                transition-all
                appearance-none
                cursor-pointer
              "
            >
              <option value="">All Statuses</option>
              <option value="not_started">
                Not Started
              </option>
              <option value="in_progress">
                In Progress
              </option>
              <option value="under_review">
                Under Review
              </option>
              <option value="compliant">
                Compliant
              </option>
              <option value="non_compliant">
                Non Compliant
              </option>
            </select>
          </div>

          {/* Sort */}
          <div className="relative">
            <ArrowUpDown className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />

            <select
              id="sort-by-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="
                pl-9 pr-4 py-2
                bg-white dark:bg-gray-900
                text-gray-900 dark:text-white
                border border-gray-200 dark:border-gray-700
                rounded-lg
                focus:ring-2 focus:ring-primary-500
                outline-none
                transition-all
                appearance-none
                cursor-pointer
              "
            >
              <option value="created_at">
                Sort by Date
              </option>
              <option value="name">
                Sort by Name
              </option>
              <option value="risk_level">
                Sort by Risk Level
              </option>
              <option value="compliance_score">
                Sort by Score
              </option>
            </select>
          </div>

          {/* Order */}
          <div className="relative">
            <select
              id="sort-order-select"
              value={order}
              onChange={(e) => setOrder(e.target.value)}
              className="
                px-3 py-2
                bg-white dark:bg-gray-900
                text-gray-900 dark:text-white
                border border-gray-200 dark:border-gray-700
                rounded-lg
                focus:ring-2 focus:ring-primary-500
                outline-none
                transition-all
                appearance-none
                cursor-pointer
              "
            >
              <option value="desc">
                Descending
              </option>
              <option value="asc">
                Ascending
              </option>
            </select>
          </div>

          {/* Clear */}
          {(searchTerm ||
            riskFilter ||
            complianceFilter) && (
            <button
              onClick={() => {
                setSearchTerm('')
                setRiskFilter('')
                setComplianceFilter('')
              }}
              className="
                flex items-center gap-1
                px-3 py-2
                text-gray-500 dark:text-gray-400
                hover:text-red-600
                hover:bg-red-50 dark:hover:bg-red-900/20
                rounded-lg
                transition-all
                text-sm font-medium
              "
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
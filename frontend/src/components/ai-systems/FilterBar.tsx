import React from 'react'
import { Search, Filter, Bot, ArrowUpDown, X } from 'lucide-react'

interface FilterBarProps {
  searchTerm: string
  setSearchTerm: (term: string) => void
  riskFilter: string
  setRiskFilter: (filter: string) => void
  complianceFilter: string
  setComplianceFilter: (filter: string) => void
  sortBy: string
  setSortBy: (sort: string) => void
  order: string
  setOrder: (order: string) => void
  setCurrentPage: (page: number) => void
}

export default function FilterBar({
  searchTerm,
  setSearchTerm,
  riskFilter,
  setRiskFilter,
  complianceFilter,
  setComplianceFilter,
  sortBy,
  setSortBy,
  order,
  setOrder,
  setCurrentPage
}: FilterBarProps) {
  return (
    <div className="flex flex-col md:flex-row gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search AI systems..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setCurrentPage(1)
          }}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
        />
      </div>
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value)
              setCurrentPage(1)
            }}
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
            onChange={(e) => {
              setComplianceFilter(e.target.value)
              setCurrentPage(1)
            }}
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
            onChange={(e) => setSortBy(e.target.value)}
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
            onChange={(e) => setOrder(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none transition-all appearance-none cursor-pointer"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
        {(searchTerm || riskFilter || complianceFilter) && (
          <button
            onClick={() => {
              setSearchTerm('')
              setRiskFilter('')
              setComplianceFilter('')
              setCurrentPage(1)
            }}
            className="flex items-center gap-1 px-3 py-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all text-sm font-medium"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        )}
      </div>
    </div>
  )
}

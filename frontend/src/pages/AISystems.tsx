import { useState } from 'react'

import {
  useQuery,
} from '@tanstack/react-query'

import {
  Search,
  Plus,
  Edit,
  Trash2,
  Bot,
} from 'lucide-react'

import { aiSystemsApi } from '../services/api'

interface AISystem {
  id: number
  name: string
  description?: string
  risk_level?: string
  compliance_status?: string
}

export default function AISystems() {
  const [searchQuery, setSearchQuery] =
    useState('')

  const [sortBy] =
    useState('created_at')

  const {
    data: systemsData,
    isLoading,
  } = useQuery({
    queryKey: ['ai-systems', sortBy],

    queryFn: () =>
      aiSystemsApi.list({
        sort_by: sortBy,
        order: 'desc',
      }),
  })

  const systems = Array.isArray(systemsData)
    ? systemsData
    : systemsData?.items || []

  const filteredSystems = systems.filter(
    (system: AISystem) =>
      system.name
        .toLowerCase()
        .includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Systems
          </h1>

          <p className="text-gray-600 dark:text-gray-400">
            Manage your AI systems for
            compliance tracking
          </p>
        </div>

        <button
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

      {/* Search */}
      <div
        className="
          bg-white dark:bg-gray-800
          rounded-xl
          border border-gray-200 dark:border-gray-700
          p-4
        "
      >
        <div className="relative">
          <Search
            className="
              absolute left-3 top-1/2
              -translate-y-1/2
              w-5 h-5
              text-gray-400
            "
          />

          <input
            type="text"
            placeholder="Search AI systems..."
            value={searchQuery}
            onChange={(e) =>
              setSearchQuery(e.target.value)
            }
            className="
              w-full pl-10 pr-4 py-3
              bg-white dark:bg-gray-900
              border border-gray-300 dark:border-gray-700
              rounded-lg
              text-gray-900 dark:text-white
              placeholder:text-gray-400
              focus:outline-none
              focus:ring-2
              focus:ring-primary-500
            "
          />
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          Loading...
        </div>
      ) : filteredSystems.length === 0 ? (
        <div
          className="
            text-center py-16
            bg-white dark:bg-gray-800
            rounded-xl
            border border-gray-200 dark:border-gray-700
          "
        >
          <Bot className="w-14 h-14 mx-auto text-gray-300 dark:text-gray-600 mb-4" />

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            No AI systems yet
          </h3>

          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Add your first AI system to
            start tracking compliance
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredSystems.map(
            (system: AISystem) => (
              <div
                key={system.id}
                className="
                  bg-white dark:bg-gray-800
                  rounded-xl
                  border border-gray-200 dark:border-gray-700
                  p-6
                  transition-colors duration-200
                "
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {system.name}
                    </h3>

                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                      {system.description ||
                        'No description available'}
                    </p>

                    <div className="flex items-center gap-2 mt-3">
                      {system.risk_level && (
                        <span
                          className="
                            text-xs px-2 py-1
                            rounded-full
                            bg-red-100
                            text-red-700
                          "
                        >
                          {system.risk_level}
                        </span>
                      )}

                      {system.compliance_status && (
                        <span
                          className="
                            text-xs px-2 py-1
                            rounded-full
                            bg-blue-100
                            text-blue-700
                          "
                        >
                          {
                            system.compliance_status
                          }
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      className="
                        p-2 rounded-lg
                        hover:bg-gray-100
                        dark:hover:bg-gray-700
                      "
                    >
                      <Edit className="w-5 h-5 text-gray-500 dark:text-gray-300" />
                    </button>

                    <button
                      className="
                        p-2 rounded-lg
                        hover:bg-red-100
                        dark:hover:bg-red-900/20
                      "
                    >
                      <Trash2 className="w-5 h-5 text-red-500" />
                    </button>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}
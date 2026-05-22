import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi, documentsApi } from '../services/api'
import {
  FileText,
  Download,
  Trash2,
  Plus,
  Edit,
} from 'lucide-react'

import DocumentEditor from '../components/DocumentEditor'

interface Document {
  id: number
  title: string
  document_type: string
  status: string
  content: string | null
  created_at: string
  ai_system_id: number | null
}

interface AISystem {
  id: number
  name: string
}

export default function Documents() {
  const queryClient = useQueryClient()

  const [showModal, setShowModal] = useState(false)
  const [selectedSystem, setSelectedSystem] =
    useState<number | null>(null)

  const [selectedType, setSelectedType] =
    useState('technical_documentation')

  const [editingDoc, setEditingDoc] =
    useState<Document | null>(null)

  const { data: documents = [], isLoading } =
  useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list(),
  })

const { data: systems = [] } =
  useQuery<AISystem[]>({
    queryKey: ['ai-systems'],
    queryFn: () => aiSystemsApi.list(),
  })

const generateMutation = useMutation<
  any,
  Error,
  {
    document_type: string
    ai_system_id: number
  }
>({
  mutationFn: documentsApi.generate,

  onSuccess: () => {
    queryClient.invalidateQueries({
      queryKey: ['documents'],
    })

    setShowModal(false)
  },
})

const deleteMutation = useMutation<
  any,
  Error,
  number
>({
  mutationFn: documentsApi.delete,

  onSuccess: () => {
    queryClient.invalidateQueries({
      queryKey: ['documents'],
    })
  },
})

  const documentTypes = [
    {
      value: 'technical_documentation',
      label: 'Technical Documentation',
    },
    {
      value: 'risk_assessment',
      label: 'Risk Assessment Report',
    },
    {
      value: 'conformity_declaration',
      label: 'Declaration of Conformity',
    },
    {
      value: 'data_governance',
      label: 'Data Governance Policy',
    },
    {
      value: 'transparency_notice',
      label: 'Transparency Notice',
    },
    {
      value: 'human_oversight_plan',
      label: 'Human Oversight Plan',
    },
  ]

  const handleGenerate = () => {
    if (!selectedSystem) return

    generateMutation.mutate({
      document_type: selectedType,
      ai_system_id: selectedSystem,
    })
  }

  const handleSaveDocument = async (
    content: string
  ) => {
    if (!editingDoc) return

    try {
      const response = await fetch(
        `/api/v1/documents/${editingDoc.id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content }),
        }
      )

      if (response.ok) {
        queryClient.invalidateQueries({
          queryKey: ['documents'],
        })
      }
    } catch (error) {
      console.error('Save failed:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-700'

      case 'reviewed':
        return 'bg-blue-100 text-blue-700'

      case 'generated':
        return 'bg-yellow-100 text-yellow-700'

      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Documents
          </h1>

          <p className="text-gray-600 dark:text-gray-400">
            Generate and manage compliance documentation
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          disabled={systems.length === 0}
          className="
            flex items-center gap-2
            px-4 py-2
            bg-primary-600
            text-white
            rounded-lg
            hover:bg-primary-700
            disabled:opacity-50
            transition-colors
          "
        >
          <Plus className="w-5 h-5" />
          Generate Document
        </button>
      </div>

      {/* Warning */}
      {systems.length === 0 && (
        <div
          className="
            bg-yellow-50 dark:bg-yellow-900/20
            border border-yellow-200 dark:border-yellow-700
            rounded-lg
            p-4
            text-yellow-800 dark:text-yellow-300
            text-sm
          "
        >
          You need to add an AI system first before
          generating documents.
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          Loading...
        </div>
      ) : documents.length === 0 ? (
        /* Empty State */
        <div
          className="
            text-center py-12
            bg-white dark:bg-gray-800
            rounded-xl
            border border-gray-200 dark:border-gray-700
            transition-colors duration-200
          "
        >
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />

          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            No documents yet
          </h3>

          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Generate your first compliance document
          </p>
        </div>
      ) : (
        /* Documents List */
        <div className="grid gap-4">
          {documents.map((doc: Document) => (
            <div
              key={doc.id}
              className="
                bg-white dark:bg-gray-800
                rounded-xl
                border border-gray-200 dark:border-gray-700
                p-6
                transition-colors duration-200
              "
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>

                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {doc.title}
                    </h3>

                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded">
                        {doc.document_type.replace(
                          /_/g,
                          ' '
                        )}
                      </span>

                      <span
                        className={`text-xs px-2 py-1 rounded ${getStatusColor(
                          doc.status
                        )}`}
                      >
                        {doc.status}
                      </span>

                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(
                          doc.created_at
                        ).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditingDoc(doc)}
                    className="
                      p-2
                      text-gray-400 dark:text-gray-300
                      hover:text-blue-600
                      rounded-lg
                      hover:bg-blue-50 dark:hover:bg-blue-900/20
                    "
                    title="Edit"
                  >
                    <Edit className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() => {
                      const blob = new Blob(
                        [doc.content || ''],
                        {
                          type: 'text/markdown',
                        }
                      )

                      const url =
                        URL.createObjectURL(blob)

                      const a =
                        document.createElement('a')

                      a.href = url
                      a.download = `${doc.title}.md`
                      a.click()
                    }}
                    className="
                      p-2
                      text-gray-400 dark:text-gray-300
                      hover:text-gray-600 dark:hover:text-white
                      rounded-lg
                      hover:bg-gray-100 dark:hover:bg-gray-700
                    "
                  >
                    <Download className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() =>
                      deleteMutation.mutate(doc.id)
                    }
                    className="
                      p-2
                      text-gray-400 dark:text-gray-300
                      hover:text-red-600
                      rounded-lg
                      hover:bg-red-50 dark:hover:bg-red-900/20
                    "
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Preview */}
              {doc.content && (
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                  <pre
                    className="
                      text-xs
                      text-gray-600 dark:text-gray-300
                      bg-gray-50 dark:bg-gray-900
                      p-3
                      rounded-lg
                      overflow-auto
                      max-h-32
                    "
                  >
                    {doc.content.slice(0, 500)}...
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
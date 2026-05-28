import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi, documentsApi } from '../services/api'


import { FileText, Download, Trash2, Plus, Edit, Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import DocumentEditor from '../components/DocumentEditor'
import CopyButton from '../components/CopyButton'


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
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null)
  const [selectedType, setSelectedType] = useState('technical_documentation')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [editingDoc, setEditingDoc] = useState<Document | null>(null)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const handleCopy = async (docId: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content)

      setCopiedDocId(docId)

      setTimeout(() => {
        setCopiedDocId(null)
      }, 2000)
    } catch (error) {
      console.error('Failed to copy content:', error)
    }
  }

  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['documents', currentPage],
    queryFn: () => documentsApi.list({ skip: (currentPage - 1) * limit, limit }),
  })
  const documents = Array.isArray(documentsData) ? documentsData : (documentsData?.items ?? [])
  const filteredDocuments = documents.filter((doc: Document) => {
  const matchesSearch =
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (doc.content || '').toLowerCase().includes(searchQuery.toLowerCase())

  const matchesType =
    filterType === 'all' || doc.document_type === filterType

  const matchesStatus =
    filterStatus === 'all' || doc.status === filterStatus

  return matchesSearch && matchesType && matchesStatus
})

  const { data: systemsData } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: () => aiSystemsApi.list(),
  })
  const systems = Array.isArray(systemsData) ? systemsData : (systemsData?.items ?? [])
  
  const generateMutation = useMutation({
    mutationFn: documentsApi.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setShowModal(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setDocumentToDelete(null)
    },
  })

  const documentTypes = [
    { value: 'technical_documentation', label: 'Technical Documentation' },
    { value: 'risk_assessment', label: 'Risk Assessment Report' },
    { value: 'conformity_declaration', label: 'Declaration of Conformity' },
    { value: 'data_governance', label: 'Data Governance Policy' },
    { value: 'transparency_notice', label: 'Transparency Notice' },
    { value: 'human_oversight_plan', label: 'Human Oversight Plan' },
  ]

  const handleGenerate = () => {
    if (!selectedSystem) return
    generateMutation.mutate({
      document_type: selectedType,
      ai_system_id: selectedSystem,
    })
  }

  const handleSaveDocument = async (content: string) => {
    if (!editingDoc) return

    try {
      const response = await fetch(`/api/v1/documents/${editingDoc.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content })
      })

      if (response.ok) {
        queryClient.invalidateQueries({ queryKey: ['documents'] })
      }
    } catch (error) {
      console.error('Save failed:', error)
    }
  }


  const handleCopy = async (doc: Document) => {
  if (!doc.content) return

  try {
    await navigator.clipboard.writeText(doc.content)

    setCopiedId(doc.id)
    toast.success('Copied to clipboard')

    setTimeout(() => {
      setCopiedId(null)
    }, 2000)

  } catch (error) {
    console.error('Copy failed:', error)
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-600">
            Generate and manage compliance documentation
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          disabled={systems.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          Generate Document
        </button>
        
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="all">All Types</option>

            {documentTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="all">All Statuses</option>
            <option value="generated">Generated</option>
            <option value="reviewed">Reviewed</option>
            <option value="approved">Approved</option>
          </select>
        </div>
      </div>


      {systems.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800 text-sm">
          You need to add an AI system first before generating documents.
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4">
          {[...Array(3)].map((_, index) => (
            <div
              key={index}
              className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>

                  <div className="flex-1 space-y-3">
                    <div className="h-5 bg-gray-200 rounded w-1/3"></div>

                    <div className="flex gap-2">
                      <div className="h-5 bg-gray-200 rounded w-20"></div>
                      <div className="h-5 bg-gray-200 rounded w-16"></div>
                      <div className="h-5 bg-gray-200 rounded w-24"></div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <div className="w-9 h-9 bg-gray-200 rounded-lg"></div>
                  <div className="w-9 h-9 bg-gray-200 rounded-lg"></div>
                  <div className="w-9 h-9 bg-gray-200 rounded-lg"></div>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
                <div className="h-3 bg-gray-200 rounded w-full"></div>
                <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                <div className="h-3 bg-gray-200 rounded w-4/6"></div>
              </div>
            </div>
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No documents yet</h3>
          <p className="text-gray-500 mt-1">
            Generate your first compliance document
          </p>
        </div>
      ) : (
        filteredDocuments.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            No matching documents
          </h3>
          <p className="text-gray-500 mt-1">
            Try adjusting your search or filters
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredDocuments.map((doc: Document) => (
            <div
              key={doc.id}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-primary-50 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{doc.title}</h3>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded ${getStatusColor(
                          doc.status
                        )}`}
                      >
                        {doc.status}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  
                  <button
                    onClick={() => setEditingDoc(doc)}
                    className="p-2 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50"
                    title="Edit"
                  >
                    <Edit className="w-5 h-5" />
                  </button>
                  
                   

                  <button
                   onClick={() => handleCopy(doc)}

                  className="p-2 text-gray-400 hover:text-green-600 rounded-lg hover:bg-green-50"
                  title="Copy"
                >
                  {copiedId === doc.id ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <Copy className="w-5 h-5" />
                  )}
                </button>
                  <button
                    onClick={() => {
                      // Download as text file
                      const blob = new Blob([doc.content || ''], {
                        type: 'text/markdown',
                      })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `${doc.title}.md`
                      a.click()
                    }}
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                  >
                    <Download className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() => setDocumentToDelete(doc)}
                    className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Preview */}
              {doc.content && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded-lg overflow-auto max-h-32">
                    {doc.content.slice(0, 500)}...
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      ))}

      {/* Pagination Controls */}
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
          disabled={documents.length < limit}
          className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Next
        </button>
      </div>


      {/* Delete Confirmation Modal */}
      {documentToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Delete Document
            </h2>
            <p className="text-gray-600">
              Are you sure you want to delete {documentToDelete.title}? This cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-6">
              <button
                type="button"
                onClick={() => setDocumentToDelete(null)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(documentToDelete.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Generate Document
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  AI System
                </label>
                <select
                  value={selectedSystem || ''}
                  onChange={(e) => setSelectedSystem(parseInt(e.target.value))}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Select AI system...</option>
                  {systems.map((system: AISystem) => (
                    <option key={system.id} value={system.id}>
                      {system.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Document Type
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {documentTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
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
                  onClick={handleGenerate}
                  disabled={!selectedSystem || generateMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {generateMutation.isPending ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Editor Modal */}
      {editingDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-6xl h-[90vh]">
            <DocumentEditor
              documentId={editingDoc.id}
              initialContent={editingDoc.content || ''}
              onSave={handleSaveDocument}
              onClose={() => setEditingDoc(null)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
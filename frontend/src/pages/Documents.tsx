import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Check,
  ChevronDown,
  FileText,
  Loader2,
  Pencil,
  Plus,
  RefreshCcw,
  Trash2,
} from 'lucide-react'

import { documentsApi } from '../services/api'
import DocumentEditor from '../components/DocumentEditor'

type DocumentItem = {
  id: number
  title: string
  created_at: string
  updated_at: string
}

type DocumentVersion = {
  id: number
  document_id: number
  version_number: string
  created_at: string
}

export default function Documents() {
  const navigate = useNavigate()

  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null)
  const [selectedDocumentTitle, setSelectedDocumentTitle] = useState<string>('')
  const [selectedDocumentContent, setSelectedDocumentContent] = useState<string>('')

  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [versionsError, setVersionsError] = useState<string | null>(null)

  const refreshDocuments = async () => {
    const list = await documentsApi.list()
    setDocuments(list as DocumentItem[])
  }

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)

    documentsApi
      .list()
      .then((data) => {
        if (!mounted) return
        setDocuments(data as DocumentItem[])
      })
      .catch(() => {
        if (!mounted) return
        setError('Failed to load documents')
      })
      .finally(() => {
        if (!mounted) return
        setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!selectedDocumentId) return

    setVersionsLoading(true)
    setVersionsError(null)

    documentsApi
      .getVersions(selectedDocumentId)
      .then((data) => setVersions(data as DocumentVersion[]))
      .catch(() => setVersionsError('Failed to load versions'))
      .finally(() => setVersionsLoading(false))
  }, [selectedDocumentId])

  useEffect(() => {
    if (!selectedDocumentId) return

    documentsApi
      .get(selectedDocumentId)
      .then((doc: any) => {
        setSelectedDocumentContent(doc?.content ?? '')
      })
      .catch(() => {
        // keep existing content
      })
  }, [selectedDocumentId])

  const handleSelectDocument = (doc: DocumentItem) => {
    setSelectedDocumentId(doc.id)
    setSelectedDocumentTitle(doc.title)
  }

  const handleCreateDocument = async () => {
    setError(null)
    try {
      // Backend expects: { document_type, ai_system_id }
      await documentsApi.generate({
        document_type: 'regulatory',
        ai_system_id: 1,
      })
      await refreshDocuments()
    } catch {
      setError('Failed to generate document')
    }
  }

  const handleRegenerate = async (documentId: number) => {
    setError(null)
    try {
      // The current API does not expose a regenerate-by-id endpoint on the frontend API wrapper.
      // Use generate to create a new document for the configured backend.
      await documentsApi.generate({
        document_type: 'regulatory',
        ai_system_id: 1,
      })
      await refreshDocuments()
    } catch {
      setError('Failed to regenerate document')
    }
  }

  const handleDelete = async (documentId: number) => {
    if (!confirm('Delete this document?')) return
    setError(null)
    try {
      await documentsApi.delete(documentId)
      await refreshDocuments()
      if (selectedDocumentId === documentId) {
        setSelectedDocumentId(null)
        setSelectedDocumentTitle('')
        setSelectedDocumentContent('')
        setVersions([])
      }
    } catch {
      setError('Failed to delete document')
    }
  }

  const handleBackToList = () => {
    setSelectedDocumentId(null)
    setSelectedDocumentTitle('')
    setSelectedDocumentContent('')
    setVersions([])
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading documents...
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500">Generate, edit, delete, and compare compliance documents.</p>
        </div>
        <button
          type="button"
          onClick={handleCreateDocument}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
        >
          <Plus className="w-4 h-4" />
          Generate
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-5">
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-gray-200 font-medium text-gray-900">Your documents</div>
          <div className="p-2 max-h-[62vh] overflow-y-auto">
            {documents.length === 0 ? (
              <div className="p-6 text-center text-gray-500">No documents yet</div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => {
                  const isActive = doc.id === selectedDocumentId
                  return (
                    <button
                      key={doc.id}
                      type="button"
                      onClick={() => handleSelectDocument(doc)}
                      className={`w-full text-left px-3 py-2 rounded-lg border transition-colors ${
                        isActive
                          ? 'bg-primary-50 border-primary-200'
                          : 'bg-white border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 truncate">{doc.title}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            Updated {new Date(doc.updated_at).toLocaleDateString()}
                          </p>
                        </div>
                        <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {!selectedDocumentId ? (
            <div className="p-8 text-gray-500">Select a document to edit.</div>
          ) : (
            <div>
              <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-gray-900 truncate">{selectedDocumentTitle}</h2>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => navigate(`/documents/${selectedDocumentId}`)}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
                  >
                    <ChevronDown className="w-4 h-4" />
                    Versions
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRegenerate(selectedDocumentId)}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
                  >
                    <RefreshCcw className="w-4 h-4" />
                    Regenerate
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(selectedDocumentId)}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-red-200 text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                  <button
                    type="button"
                    onClick={handleBackToList}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
                  >
                    <Check className="w-4 h-4" />
                    Close
                  </button>
                </div>
              </div>

              {versionsError && (
                <div className="px-4 py-3 text-sm text-red-700 bg-red-50 border-b border-red-200">{versionsError}</div>
              )}

              <div className="p-4">
                {versionsLoading ? (
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading versions...
                  </div>
                ) : (
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-gray-900">History</p>
                      <p className="text-xs text-gray-500">{versions.length} version(s)</p>
                    </div>
                    <div className="space-y-2">
                      {versions
                        .slice()
                        .reverse()
                        .map((v) => (
                          <div
                            key={v.id}
                            className="flex items-center justify-between gap-3 p-3 rounded-lg border border-gray-200 bg-gray-50"
                          >
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-900">Version {v.version_number}</p>
                              <p className="text-xs text-gray-500 mt-1">{new Date(v.created_at).toLocaleString()}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => navigate(`/documents/${v.document_id}/diff`)}
                              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 text-sm"
                            >
                              <FileText className="w-4 h-4 text-gray-400" />
                              Compare
                            </button>
                          </div>
                        ))}
                      {versions.length === 0 && (
                        <div className="text-sm text-gray-500 p-4 border border-gray-200 rounded-lg bg-white">
                          No versions found.
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="mb-4 flex items-center gap-2 text-sm text-gray-600">
                  <Pencil className="w-4 h-4" />
                  Editor
                </div>

                <DocumentEditor
                  documentId={selectedDocumentId}
                  initialContent={selectedDocumentContent}
                  onSave={async () => {
                    // refresh content + documents list
                    try {
                      const doc: any = await documentsApi.get(selectedDocumentId)
                      setSelectedDocumentContent(doc?.content ?? selectedDocumentContent)
                      await refreshDocuments()
                    } catch {
                      // ignore
                    }
                  }}
                  onClose={handleBackToList}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


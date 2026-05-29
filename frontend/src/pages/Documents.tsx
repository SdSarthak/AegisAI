import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { aiSystemsApi, documentsApi } from '../services/api'
import { FileText, Download, Trash2, Plus, Edit, Copy, Check } from 'lucide-react'
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
  const [documentToDelete, setDocumentToDelete] =
    useState<Document | null>(null)
  const [copiedDocId, setCopiedDocId] = useState<number | null>(null)

  const handleCopy = async (docId: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedDocId(docId)

      setTimeout(() => {
        setCopiedDocId(null)
      }, 2000)
    } catch (error) {
      console.error('Failed to copy content:', error)
      toast.error('Failed to copy document')
    }
  }

  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  })

  const documents = (
    Array.isArray(documentsData)
      ? documentsData
      : (documentsData?.items ?? [])
  ) as Document[]

  const filteredDocuments = documents.filter((doc: Document) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.content || '')
        .toLowerCase()
        .includes(searchQuery.toLowerCase())

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

  const systems = (
    Array.isArray(systemsData)
      ? systemsData
      : (systemsData?.items ?? [])
  ) as AISystem[]

  const generateMutation = useMutation({
    mutationFn: documentsApi.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setShowModal(false)
      toast.success('Document generated successfully')
    },
    onError: (error) => {
      console.error('Generate failed:', error)
      toast.error('Failed to generate document')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setDocumentToDelete(null)
      toast.success('Document deleted successfully')
    },
    onError: (error) => {
      console.error('Delete failed:', error)
      toast.error('Failed to delete document')
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({
      id,
      content,
    }: {
      id: number
      content: string
    }) => documentsApi.update(id, { content }),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setEditingDoc(null)
      toast.success('Document saved successfully')
    },

    onError: (error) => {
      console.error('Save failed:', error)
      toast.error('Failed to save document')
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

  const handleSaveDocument = (content: string) => {
    if (!editingDoc || saveMutation.isPending) return

    saveMutation.mutate({
      id: editingDoc.id,
      content,
    })
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
      {/* keep rest of your existing JSX unchanged */}

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
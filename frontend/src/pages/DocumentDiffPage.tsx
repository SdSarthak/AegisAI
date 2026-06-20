'use client';

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, GitCompare, AlertCircle } from 'lucide-react'
import ReactDiffViewer from 'react-diff-viewer-continued'
import { documentsApi } from '../services/api'

interface Version {
  id: number
  document_id: number
  version_number: string
  created_at: string
  regeneration_reason: string | null
}

interface VersionWithContent extends Version {
  content: string
}

interface DiffData {
  v1: VersionWithContent
  v2: VersionWithContent
  hunks: Array<{
    old_start: number
    old_count: number
    new_start: number
    new_count: number
    lines: Array<{ type: string; content: string }>
  }>
}

export default function DocumentDiffPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [versions, setVersions] = useState<Version[]>([])
  const [v1, setV1] = useState<number | null>(null)
  const [v2, setV2] = useState<number | null>(null)
  const [diffData, setDiffData] = useState<DiffData | null>(null)
  const [viewType, setViewType] = useState<'split' | 'unified'>('split')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    documentsApi.getVersions(Number(id))
      .then((data: Version[]) => {
        setVersions(data)
        if (data.length >= 2) {
          setV1(data[data.length - 2].id)
          setV2(data[data.length - 1].id)
        }
      })
      .catch(() => setError('Failed to load document versions'))
  }, [id])

  useEffect(() => {
    if (!v1 || !v2 || !id) return
    setLoading(true)
    setError(null)
    documentsApi.getDiff(Number(id), v1, v2)
      .then((data: DiffData) => setDiffData(data))
      .catch(() => setError('Failed to load diff'))
      .finally(() => setLoading(false))
  }, [v1, v2, id])

  if (error && versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <AlertCircle className="w-12 h-12 mb-4 text-red-400" />
        <p className="text-lg font-medium text-gray-700">{error}</p>
        <Link to="/documents" className="mt-4 text-primary-600 hover:underline">
          Back to Documents
        </Link>
      </div>
    )
  }

  if (versions.length > 0 && versions.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <GitCompare className="w-12 h-12 mb-4 text-gray-300" />
        <p className="text-lg font-medium text-gray-700">
          Need at least 2 versions to compare
        </p>
        <Link to="/documents" className="mt-4 text-primary-600 hover:underline">
          Back to Documents
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/documents')}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compare Versions</h1>
          <p className="text-sm text-gray-500">
            Select two versions to see what changed
          </p>
        </div>
      </div>

      {versions.length >= 2 && (
        <>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 w-full sm:w-auto">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 w-8">v1:</label>
                <select
                  value={v1 ?? ''}
                  onChange={(e) => setV1(Number(e.target.value))}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      Version {v.version_number} — {new Date(v.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 w-8">v2:</label>
                <select
                  value={v2 ?? ''}
                  onChange={(e) => setV2(Number(e.target.value))}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      Version {v.version_number} — {new Date(v.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewType('split')}
                className={`px-3 py-1.5 text-sm rounded-lg border ${
                  viewType === 'split'
                    ? 'bg-primary-50 text-primary-700 border-primary-300'
                    : 'text-gray-600 border-gray-300 hover:bg-gray-50'
                }`}
              >
                Split View
              </button>
              <button
                onClick={() => setViewType('unified')}
                className={`px-3 py-1.5 text-sm rounded-lg border ${
                  viewType === 'unified'
                    ? 'bg-primary-50 text-primary-700 border-primary-300'
                    : 'text-gray-600 border-gray-300 hover:bg-gray-50'
                }`}
              >
                Unified View
              </button>
            </div>
          </div>

          {diffData && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border text-sm">
                <p className="font-semibold text-gray-900">
                  Version {diffData.v1.version_number}
                </p>
                <p className="text-gray-500 text-xs mt-0.5">
                  {new Date(diffData.v1.created_at).toLocaleString()}
                </p>
                {diffData.v1.regeneration_reason && (
                  <p className="text-gray-400 text-xs mt-1">
                    Reason: {diffData.v1.regeneration_reason}
                  </p>
                )}
              </div>
              <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border text-sm">
                <p className="font-semibold text-gray-900">
                  Version {diffData.v2.version_number}
                </p>
                <p className="text-gray-500 text-xs mt-0.5">
                  {new Date(diffData.v2.created_at).toLocaleString()}
                </p>
                {diffData.v2.regeneration_reason && (
                  <p className="text-gray-400 text-xs mt-1">
                    Reason: {diffData.v2.regeneration_reason}
                  </p>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="animate-pulse space-y-2 bg-white rounded-xl border border-gray-200 p-6">
              {Array.from({ length: 15 }).map((_, i) => (
                <div
                  key={i}
                  className="h-4 bg-gray-200 rounded"
                  style={{ width: `${60 + Math.random() * 40}%` }}
                />
              ))}
            </div>
          ) : diffData ? (
            <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
              <ReactDiffViewer
                oldValue={diffData.v1.content}
                newValue={diffData.v2.content}
                splitView={viewType === 'split'}
                leftTitle={`v${diffData.v1.version_number}`}
                rightTitle={`v${diffData.v2.version_number}`}
                showDiffOnly={false}
                extraLinesSurroundingDiff={3}
              />
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

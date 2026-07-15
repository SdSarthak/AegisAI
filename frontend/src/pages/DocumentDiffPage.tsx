import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, GitCompare, AlertCircle } from 'lucide-react'
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

interface DiffHunkLine {
  type: 'context' | 'added' | 'removed'
  content: string
}

interface DiffHunk {
  old_start: number
  old_count: number
  new_start: number
  new_count: number
  lines: DiffHunkLine[]
}

interface DiffData {
  v1: VersionWithContent
  v2: VersionWithContent
  hunks: DiffHunk[]
}

function HunkViewer({ hunks, viewType }: { hunks: DiffHunk[]; viewType: 'split' | 'unified' }) {
  if (viewType === 'unified') {
    return (
      <div className="font-mono text-sm leading-6 overflow-x-auto">
        {hunks.map((hunk, hi) => (
          <div key={hi}>
            <div className="bg-gray-100 px-4 py-1 text-xs text-gray-500 font-semibold border-y">
              @@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@
            </div>
            {hunk.lines.map((line, li) => (
              <div
                key={li}
                className={`flex px-4 ${
                  line.type === 'added'
                    ? 'bg-green-50 text-green-800'
                    : line.type === 'removed'
                    ? 'bg-red-50 text-red-800'
                    : ''
                }`}
              >
                <span className="w-8 text-gray-400 select-none shrink-0 text-right mr-2">
                  {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                </span>
                <span className="whitespace-pre-wrap break-all min-w-0">{line.content}</span>
              </div>
            ))}
          </div>
        ))}
        {hunks.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-400 text-sm">
            No differences — the two versions are identical
          </div>
        )}
      </div>
    )
  }

  const oldLines: { lineNum: number | null; content: string; type: string }[] = []
  const newLines: { lineNum: number | null; content: string; type: string }[] = []
  let oldLineNum = 0
  let newLineNum = 0

  for (const hunk of hunks) {
    if (oldLines.length > 0 || newLines.length > 0) {
      oldLines.push({ lineNum: null, content: '⋯', type: 'context' })
      newLines.push({ lineNum: null, content: '⋯', type: 'context' })
    }
    oldLineNum = hunk.old_start
    newLineNum = hunk.new_start
    for (const line of hunk.lines) {
      if (line.type === 'added') {
        oldLines.push({ lineNum: null, content: '', type: 'empty' })
        newLines.push({ lineNum: newLineNum++, content: line.content, type: 'added' })
      } else if (line.type === 'removed') {
        oldLines.push({ lineNum: oldLineNum++, content: line.content, type: 'removed' })
        newLines.push({ lineNum: null, content: '', type: 'empty' })
      } else {
        oldLines.push({ lineNum: oldLineNum++, content: line.content, type: 'context' })
        newLines.push({ lineNum: newLineNum++, content: line.content, type: 'context' })
      }
    }
  }

  if (hunks.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-gray-400 text-sm">
        No differences — the two versions are identical
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 font-mono text-sm leading-6">
      <div className="border-r border-gray-200">
        <div className="bg-gray-100 px-3 py-1 text-xs text-gray-500 font-semibold border-b text-center">
          v1 (older)
        </div>
        {oldLines.map((line, i) => (
          <div
            key={i}
            className={`flex ${
              line.type === 'removed'
                ? 'bg-red-50 text-red-800'
                : line.type === 'empty'
                ? 'bg-gray-50'
                : ''
            }`}
          >
            <span className="w-10 text-gray-400 select-none shrink-0 text-right px-1 border-r border-gray-100">
              {line.lineNum ?? ''}
            </span>
            <span className="whitespace-pre-wrap break-all min-w-0 px-2">
              {line.content}
            </span>
          </div>
        ))}
      </div>
      <div>
        <div className="bg-gray-100 px-3 py-1 text-xs text-gray-500 font-semibold border-b text-center">
          v2 (newer)
        </div>
        {newLines.map((line, i) => (
          <div
            key={i}
            className={`flex ${
              line.type === 'added'
                ? 'bg-green-50 text-green-800'
                : line.type === 'empty'
                ? 'bg-gray-50'
                : ''
            }`}
          >
            <span className="w-10 text-gray-400 select-none shrink-0 text-right px-1 border-r border-gray-100">
              {line.lineNum ?? ''}
            </span>
            <span className="whitespace-pre-wrap break-all min-w-0 px-2">
              {line.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
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
              <HunkViewer hunks={diffData.hunks} viewType={viewType} />
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

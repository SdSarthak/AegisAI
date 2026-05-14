import { useState, useRef } from 'react'
import { AlertTriangle, Plus, Upload, X, Trash2, MapPin, Calendar } from 'lucide-react'

interface ImagePreview {
  id: string
  file: File
  url: string
}

interface CivicIssue {
  id: number
  title: string
  description: string
  category: string
  location: string
  images: ImagePreview[]
  createdAt: string
}

export default function CivicIssues() {
  const [showModal, setShowModal] = useState(false)
  const [issues, setIssues] = useState<CivicIssue[]>([])
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    location: '',
  })
  const [imagePreviews, setImagePreviews] = useState<ImagePreview[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const categories = [
    'Road Damage',
    'Garbage Disposal',
    'Street Lighting',
    'Water Supply',
    'Public Safety',
    'Other',
  ]

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach((file) => {
      if (!file.type.startsWith('image/')) return

      const reader = new FileReader()
      reader.onload = (event) => {
        if (event.target?.result) {
          const newPreview: ImagePreview = {
            id: `${Date.now()}-${Math.random()}`,
            file,
            url: event.target.result as string,
          }
          setImagePreviews((prev) => [...prev, newPreview])
        }
      }
      reader.readAsDataURL(file)
    })

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeImage = (id: string) => {
    setImagePreviews((prev) => prev.filter((img) => img.id !== id))
  }

  const resetForm = () => {
    setFormData({ title: '', description: '', category: '', location: '' })
    setImagePreviews([])
    setShowModal(false)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const newIssue: CivicIssue = {
      id: Date.now(),
      title: formData.title,
      description: formData.description,
      category: formData.category,
      location: formData.location,
      images: imagePreviews,
      createdAt: new Date().toLocaleDateString(),
    }
    setIssues((prev) => [newIssue, ...prev])
    resetForm()
  }

  const deleteIssue = (id: number) => {
    setIssues((prev) => prev.filter((issue) => issue.id !== id))
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Civic Issues</h1>
          <p className="text-gray-600">Report and track civic issues in your area</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-5 h-5" />
          Report Issue
        </button>
      </div>

      {issues.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No civic issues reported yet</h3>
          <p className="text-gray-500 mt-1">Report your first civic issue to get started</p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Report Issue
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {issues.map((issue) => (
            <div key={issue.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-gray-900">{issue.title}</h3>
                    <span className="text-xs bg-primary-50 text-primary-700 px-2 py-1 rounded">
                      {issue.category}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">{issue.description}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {issue.location}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {issue.createdAt}
                    </span>
                  </div>
                  {issue.images.length > 0 && (
                    <div className="flex gap-2 mt-3 flex-wrap">
                      {issue.images.map((img) => (
                        <img
                          key={img.id}
                          src={img.url}
                          alt="Issue"
                          className="w-20 h-20 object-cover rounded-lg border border-gray-200"
                        />
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => deleteIssue(issue.id)}
                  className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Report Civic Issue</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Title *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., Pothole on Main Street"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Description *</label>
                <textarea
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  rows={3}
                  placeholder="Describe the issue in detail"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Category *</label>
                <select
                  required
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select category...</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Location *</label>
                <input
                  type="text"
                  required
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., 5th Avenue, Downtown"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Attach Images</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageChange}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-1 flex items-center justify-center gap-2 w-full px-3 py-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-gray-600 hover:text-primary-700"
                >
                   <Upload className="w-5 h-5" />
                  <span className="text-sm">Click to upload images</span>
                </button>
                {imagePreviews.length > 0 && (
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {imagePreviews.map((preview) => (
                      <div key={preview.id} className="relative group">
                        <img
                          src={preview.url}
                          alt="Preview"
                          className="w-full h-24 object-cover rounded-lg border border-gray-200"
                        />
                        <button
                          type="button"
                          onClick={() => removeImage(preview.id)}
                          className="absolute top-1 right-1 p-1 bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-700"
                          aria-label="Remove image"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )} 
                {imagePreviews.length > 0 && (
                  <p className="mt-2 text-xs text-gray-500">
                    {imagePreviews.length} image{imagePreviews.length > 1 ? 's' : ''} attached
                  </p>
                )}
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Submit Report
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

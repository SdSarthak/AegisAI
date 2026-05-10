import { useState, useEffect, useRef } from 'react'
import { Bell } from 'lucide-react'
import { Link } from 'react-router-dom'

interface NotificationPreview {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string
}

const DUMMY_PREVIEWS: NotificationPreview[] = [
  {
    id: 1,
    title: 'High Risk Classification',
    message: 'CV Screening AI has been classified as High Risk under the EU AI Act and requires immediate review.',
    is_read: false,
    created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    title: 'Document Generated',
    message: 'Technical Documentation has been successfully generated for Medical Diagnosis AI.',
    is_read: false,
    created_at: new Date(Date.now() - 17 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    title: 'Reassessment Due Soon',
    message: 'Reassessment is due in 7 days for Loan Approval System. Please review compliance status.',
    is_read: true,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
]

function getRelativeTime(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const unreadCount = DUMMY_PREVIEWS.filter((n) => !n.is_read).length

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return

    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [isOpen])

  return (
    <div className="relative" ref={containerRef}>
      {/* Bell button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 bg-white rounded-xl border border-gray-200 shadow-lg z-50">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900 text-sm">Notifications</h3>
          </div>

          {DUMMY_PREVIEWS.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-400">
              No notifications yet
            </div>
          ) : (
            <ul>
              {DUMMY_PREVIEWS.map((n) => (
                <li
                  key={n.id}
                  className={`px-4 py-3 border-b border-gray-50 last:border-b-0 hover:bg-gray-50 transition-colors ${
                    !n.is_read ? 'bg-blue-50/40' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {!n.is_read && (
                        <span className="mt-1 shrink-0 w-2 h-2 rounded-full bg-blue-500" />
                      )}
                      <p className="text-sm font-medium text-gray-900 truncate">{n.title}</p>
                    </div>
                    <span className="shrink-0 text-xs text-gray-400 whitespace-nowrap">
                      {getRelativeTime(n.created_at)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 line-clamp-2 pl-3.5">
                    {n.message}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <div className="p-3 border-t border-gray-100">
            <Link
              to="/notifications"
              className="block text-center text-sm text-primary-600 hover:text-primary-700"
              onClick={() => setIsOpen(false)}
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

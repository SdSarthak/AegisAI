import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Shield, AlertTriangle, Home, LayoutDashboard } from 'lucide-react'

export default function NotFound() {
  useEffect(() => {
    document.title = '404 - Page Not Found | AegisAI'
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center space-y-6 p-8">
        <div className="flex justify-center">
          <div className="relative">
            <Shield className="w-20 h-20 text-primary-200 dark:text-primary-800" />
            <AlertTriangle className="w-8 h-8 text-primary-600 dark:text-primary-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
        </div>

        <meta name="robots" content="noindex" />

        <div className="space-y-2">
          <h1 className="text-6xl font-bold text-gray-900 dark:text-white">404</h1>
          <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300">Page Not Found</h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            The page you are looking for does not exist or has been moved.
          </p>
        </div>

        <div className="flex items-center justify-center gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <LayoutDashboard className="w-5 h-5" />
            Go to Dashboard
          </Link>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors font-medium"
          >
            <Home className="w-5 h-5" />
            Go to Home
          </Link>
        </div>
      </div>
    </div>
  )
}

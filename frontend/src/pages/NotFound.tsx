import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="max-w-xl text-center">
        <h1 className="text-4xl font-bold mb-4">404 — Page Not Found</h1>
        <p className="text-gray-300 mb-6">Sorry, we couldn't find the page you're looking for.</p>
        <Link to="/" className="inline-block bg-slate-700 text-white px-4 py-2 rounded hover:bg-slate-600">
          Go to Dashboard
        </Link>
      </div>
    </div>
  )
}

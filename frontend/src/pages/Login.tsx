import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../services/api'
import { Shield } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // 1. Login → get token
      const tokenData = await authApi.login(email, password)
      console.log('LOGIN SUCCESS:', tokenData)

      // 2. Store token immediately (NO user yet)
      setAuth(tokenData.access_token, null)

      // 3. Small delay ensures interceptor + store sync
      await new Promise((r) => setTimeout(r, 50))

      // 4. Fetch user safely with token now active
      const user = await authApi.getMe()
      console.log('USER:', user)

      // 5. Update full auth state
      setAuth(tokenData.access_token, user)

      // 6. Redirect
      navigate('/')
    } catch (err: any) {
      console.log('LOGIN ERROR:', err.response?.data || err.message)

      setError(
        err.response?.data?.detail ||
        err.response?.data ||
        'Login failed'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-lg">

        <div className="text-center">
          <div className="flex justify-center">
            <Shield className="w-12 h-12 text-primary-600" />
          </div>
          <h2 className="mt-4 text-3xl font-bold text-gray-900">
            EU AI Act Compliance
          </h2>
          <p className="mt-2 text-gray-600">Sign in to your account</p>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 rounded-lg text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600">
            Sign up
          </Link>
        </p>

      </div>
    </div>
  )
}
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../services/api'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'

interface ValidationError {
  field: string
  message: string
}

interface PydanticValidationError {
  loc?: Array<string | number>
  msg?: string
}

export default function Login() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<ValidationError[]>([])
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors([])

    const trimmedEmail = email.trim()
    const validationErrors: ValidationError[] = []

    if (!trimmedEmail) {
      validationErrors.push({ field: 'email', message: 'Email is required.' })
    }

    if (!password) {
      validationErrors.push({ field: 'password', message: 'Password is required.' })
    }

    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)

    try {
      const tokenData = await authApi.login(trimmedEmail, password)
      setAuth(tokenData.access_token, null)
      const user = await authApi.getMe(tokenData.access_token)
      setAuth(tokenData.access_token, user)
      navigate('/')
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail
        if (detail) {
          if (typeof detail === 'object' && detail.field && detail.message) {
            // Authentication failure (always field: 'general')
            setErrors([{ field: detail.field, message: detail.message }])
          } else if (Array.isArray(detail)) {
            // Pydantic 422 errors — login uses OAuth2PasswordRequestForm so
            // the server field name is 'username'; map it to 'email' for the UI.
            const parsed = detail.map((error: PydanticValidationError) => {
              const rawField = String(error.loc?.[error.loc.length - 1] ?? 'general')
              const field = rawField === 'username' ? 'email' : rawField
              return { field, message: error.msg || 'Invalid input' }
            })
            setErrors(parsed)
          } else {
            setErrors([{ field: 'general', message: String(detail) }])
          }
        } else if (err.code === 'ERR_NETWORK') {
          setErrors([
            {
              field: 'general',
              message: 'Network error. Please check your connection and try again.',
            },
          ])
        } else {
          setErrors([{ field: 'general', message: 'Invalid email or password' }])
        }
      } else {
        setErrors([{ field: 'general', message: 'An unexpected error occurred. Please try again.' }])
      }
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
          {errors.some((e: ValidationError) => e.field === 'general') && (
            <div className="p-3 flex items-start gap-3 text-sm bg-red-50 rounded-lg border border-red-200">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="text-red-700">
                {errors.find((e: ValidationError) => e.field === 'general')?.message}
              </div>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e: ValidationError) => e.field === 'email')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e: ValidationError) => e.field === 'email') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e: ValidationError) => e.field === 'email')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <div className="relative mt-1">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`block w-full pl-3 pr-10 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                  errors.some((e: ValidationError) => e.field === 'password')
                    ? 'border-red-300 bg-red-50'
                    : 'border-gray-300'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {errors.some((e: ValidationError) => e.field === 'password') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e: ValidationError) => e.field === 'password')?.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 border border-transparent rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600 hover:text-primary-500">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}

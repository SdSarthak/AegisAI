import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { authApi } from '../services/api'
import { Shield, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

interface ValidationError {
  field: string
  message: string
}

interface PydanticValidationError {
  loc?: Array<string | number>
  msg?: string
}

interface ErrorResponseData {
  detail?: string | PydanticValidationError[]
}

function isErrorResponseData(value: unknown): value is ErrorResponseData {
  return typeof value === 'object' && value !== null && 'detail' in value
}

function parsePydanticErrors(errorData: unknown): ValidationError[] {
  if (!isErrorResponseData(errorData)) return []

  if (Array.isArray(errorData.detail)) {
    return errorData.detail.map((error) => ({
      field: String(error.loc?.[error.loc.length - 1] ?? 'unknown'),
      message: error.msg || 'Invalid input',
    }))
  }

  if (typeof errorData.detail === 'string') {
    return [{ field: 'general', message: errorData.detail }]
  }

  return []
}

function checkPasswordStrength(password: string) {
  return {
    hasMinLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasDigit: /\d/.test(password),
    hasSpecialChar: /[!@#$%^&*]/.test(password),
  }
}

function isPasswordValid(password: string): boolean {
  const strength = checkPasswordStrength(password)
  return (
    strength.hasMinLength &&
    strength.hasUppercase &&
    strength.hasDigit &&
    strength.hasSpecialChar
  )
}

export default function Register() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    company_name: '',
  })
  const [errors, setErrors] = useState<ValidationError[]>([])
  const [loading, setLoading] = useState(false)
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false)

  const passwordStrength = checkPasswordStrength(formData.password)
  const isPasswordFieldValid = isPasswordValid(formData.password)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors([])
    setLoading(true)

    // Frontend validation
    if (!isPasswordValid(formData.password)) {
      setErrors([
        {
          field: 'password',
          message:
            'Password must contain: at least 8 characters, at least one uppercase letter, at least one digit, at least one special character (!@#$%^&*)',
        },
      ])
      setLoading(false)
      return
    }

    try {
      await authApi.register(formData)
      navigate('/login')
    } catch (err) {
      if (axios.isAxiosError(err)) {
        // Try to parse Pydantic validation errors (422)
        const parsedErrors = parsePydanticErrors(err.response?.data)

        if (parsedErrors.length > 0) {
          setErrors(parsedErrors)
        } else if (err.response?.data?.detail) {
          // Handle custom error messages (400, etc.)
          setErrors([
            { field: 'general', message: err.response.data.detail },
          ])
        } else if (err.code === 'ERR_NETWORK') {
          setErrors([
            {
              field: 'general',
              message:
                'Network error. Please check your connection and try again.',
            },
          ])
        } else {
          setErrors([
            {
              field: 'general',
              message: 'Registration failed. Please try again.',
            },
          ])
        }
      } else {
        setErrors([
          {
            field: 'general',
            message: 'An unexpected error occurred. Please try again.',
          },
        ])
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-transparent dark:border-gray-700">
        <div className="text-center">
          <div className="flex justify-center">
            <Shield className="w-12 h-12 text-primary-600 dark:text-primary-400" />
          </div>
          <h2 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">
            Create Account
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Start your compliance journey</p>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="p-3 text-sm text-red-650 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 rounded-lg">
              {error}
          {/* General error message */}
          {errors.some((e) => e.field === 'general') && (
            <div className="p-3 flex items-start gap-3 text-sm bg-red-50 rounded-lg border border-red-200">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="text-red-700">
                {errors.find((e) => e.field === 'general')?.message}
              </div>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 outline-none"
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e) => e.field === 'email')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e) => e.field === 'email') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e) => e.field === 'email')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 outline-none"
              onFocus={() => setShowPasswordRequirements(true)}
              onBlur={() => setShowPasswordRequirements(false)}
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                formData.password && !isPasswordFieldValid
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />

            {/* Password strength requirements feedback */}
            {(showPasswordRequirements || formData.password) && (
              <div className="mt-3 space-y-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-xs font-semibold text-gray-700">
                  Password requirements:
                </p>
                <div className="space-y-1">
                  <PasswordRequirement
                    met={passwordStrength.hasMinLength}
                    text="At least 8 characters"
                  />
                  <PasswordRequirement
                    met={passwordStrength.hasUppercase}
                    text="At least one uppercase letter (A-Z)"
                  />
                  <PasswordRequirement
                    met={passwordStrength.hasDigit}
                    text="At least one digit (0-9)"
                  />
                  <PasswordRequirement
                    met={passwordStrength.hasSpecialChar}
                    text="At least one special character (!@#$%^&*)"
                  />
                </div>
              </div>
            )}

            {errors.some((e) => e.field === 'password') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e) => e.field === 'password')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Full Name
            </label>
            <input
              id="full_name"
              type="text"
              required
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 outline-none"
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e) => e.field === 'full_name')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e) => e.field === 'full_name') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e) => e.field === 'full_name')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="company_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Company Name
            </label>
            <input
              id="company_name"
              type="text"
              required
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 outline-none"
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e) => e.field === 'company_name')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e) => e.field === 'company_name') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e) => e.field === 'company_name')?.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !isPasswordFieldValid}
            className="w-full py-2 px-4 border border-transparent rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600 dark:text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

/**
 * Component to display individual password requirement with checkmark or X.
 */
function PasswordRequirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {met ? (
        <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
      ) : (
        <XCircle className="w-4 h-4 text-gray-300 flex-shrink-0" />
      )}
      <span className={met ? 'text-green-700' : 'text-gray-600'}>{text}</span>
    </div>
  )
}

import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { authApi } from '../services/api'
import { Shield, AlertCircle, CheckCircle, XCircle, Eye, EyeOff } from 'lucide-react'

interface ValidationError {
  field: string
  message: string
}

interface PydanticValidationError {
  loc?: Array<string | number>
  msg?: string
}

interface ErrorResponseData {
  detail?: string | PydanticValidationError[] | { field: string; message: string }
}

function isErrorResponseData(value: unknown): value is ErrorResponseData {
  return typeof value === 'object' && value !== null && 'detail' in value
}

const USER_FRIENDLY_ERROR_MAP: Record<string, string> = {
  'value is not a valid email address': 'Please enter a valid email address',
  'field required': 'This field is required',
}

function toUserFriendlyMessage(msg: string): string {
  return USER_FRIENDLY_ERROR_MAP[msg] || msg
}

function parsePydanticErrors(errorData: unknown): ValidationError[] {
  if (!isErrorResponseData(errorData)) return []

  if (Array.isArray(errorData.detail)) {
    return errorData.detail.map((error) => ({
      field: String(error.loc?.[error.loc.length - 1] ?? 'unknown'),
      message: toUserFriendlyMessage(error.msg || 'Invalid input'),
    }))
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

function isPasswordStrong(strength: ReturnType<typeof checkPasswordStrength>) {
  return Object.values(strength).every(Boolean)
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
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false)

  const passwordStrength = checkPasswordStrength(formData.password)
  const passwordIsStrong = isPasswordStrong(passwordStrength)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors([])

    const trimmedEmail = formData.email.trim()
    const trimmedFullName = formData.full_name.trim()
    const trimmedCompanyName = formData.company_name.trim()

    const validationErrors: ValidationError[] = []
    if (!trimmedEmail) validationErrors.push({ field: 'email', message: 'Email is required.' })
    if (!formData.password) validationErrors.push({ field: 'password', message: 'Password is required.' })
    if (formData.password && !passwordIsStrong) validationErrors.push({ field: 'password', message: 'Password does not meet strength requirements.' })
    if (!trimmedFullName) validationErrors.push({ field: 'full_name', message: 'Full name is required.' })
    if (!trimmedCompanyName) validationErrors.push({ field: 'company_name', message: 'Company name is required.' })

    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)

    try {
      await authApi.register({
        email: trimmedEmail,
        password: formData.password,
        full_name: trimmedFullName,
        company_name: trimmedCompanyName,
      })
      navigate('/login')
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const parsedErrors = parsePydanticErrors(err.response?.data)
        const detail = err.response?.data?.detail

        if (parsedErrors.length > 0) {
          setErrors(parsedErrors)
        } else if (detail) {
          if (typeof detail === 'object' && detail.field && detail.message) {
            setErrors([{ field: detail.field, message: detail.message }])
          } else {
            setErrors([{ field: 'general', message: String(detail) }])
          }
        } else if (err.code === 'ERR_NETWORK') {
          setErrors([
            {
              field: 'general',
              message:
                'Network error. Please check your connection and try again.',
            },
          ])
        } else if (err.code === 'ECONNABORTED') {
          setErrors([
            {
              field: 'general',
              message: 'Request timed out. Please try again.',
            },
          ])
        } else {
          setErrors([{ field: 'general', message: 'Registration failed. Please try again.' }])
        }
      } else {
        setErrors([{ field: 'general', message: 'An unexpected error occurred. Please try again.' }])
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg">
        <div className="text-center">
          <div className="flex justify-center">
            <Shield className="w-12 h-12 text-primary-600" />
          </div>
          <h2 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">
            Create Account
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Start your compliance journey</p>
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
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={formData.email}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, email: e.target.value })}
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
                value={formData.password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, password: e.target.value })}
                onFocus={() => setShowPasswordRequirements(true)}
                onBlur={() => setShowPasswordRequirements(false)}
                className={`block w-full pl-3 pr-10 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                  errors.some((e: ValidationError) => e.field === 'password')
                    ? 'border-red-300 bg-red-50'
                    : 'border-gray-300'
                }`}
              />
              <button
                type="button"
                onMouseDown={(e: React.MouseEvent) => e.preventDefault()}
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>

            {formData.password && <PasswordStrengthBar strength={passwordStrength} />}

            {(showPasswordRequirements || formData.password) && (
              <div className="mt-3 space-y-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
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

            {errors.some((e: ValidationError) => e.field === 'password') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e: ValidationError) => e.field === 'password')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
              Full Name
            </label>
            <input
              id="full_name"
              type="text"
              required
              value={formData.full_name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, full_name: e.target.value })}
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e: ValidationError) => e.field === 'full_name')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e: ValidationError) => e.field === 'full_name') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e: ValidationError) => e.field === 'full_name')?.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="company_name" className="block text-sm font-medium text-gray-700">
              Company Name
            </label>
            <input
              id="company_name"
              type="text"
              required
              value={formData.company_name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, company_name: e.target.value })}
              className={`mt-1 block w-full px-3 py-2 border rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 ${
                errors.some((e: ValidationError) => e.field === 'company_name')
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
            />
            {errors.some((e: ValidationError) => e.field === 'company_name') && (
              <p className="mt-1 text-sm text-red-600">
                {errors.find((e: ValidationError) => e.field === 'company_name')?.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || (formData.password.length > 0 && !passwordIsStrong)}
            className="w-full py-2 px-4 border border-transparent rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600 dark:text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 hover:text-primary-500">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

function getPasswordStrengthLevel(strength: ReturnType<typeof checkPasswordStrength>) {
  const metCount = Object.values(strength).filter(Boolean).length
  if (metCount <= 2) return { level: 'Weak', color: 'bg-red-500', width: '33%' }
  if (metCount === 3) return { level: 'Medium', color: 'bg-yellow-500', width: '66%' }
  return { level: 'Strong', color: 'bg-green-500', width: '100%' }
}

function PasswordStrengthBar({ strength }: { strength: ReturnType<typeof checkPasswordStrength> }) {
  const { level, color, width } = getPasswordStrengthLevel(strength)
  return (
    <div className="mt-2">
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width }}
        />
      </div>
      <p className="text-xs mt-1 text-gray-600">{level} password</p>
    </div>
  )
}

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
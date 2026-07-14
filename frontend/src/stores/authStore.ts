import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { buildApiUrl } from '../utils/apiUrl'

interface User {
  id: number
  email: string
  full_name: string | null
  company_name: string | null
  subscription_tier: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isRevalidating: boolean
  setAuth: (token: string, user: User | null) => void
  logout: () => void
  revalidateSession: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isRevalidating: false,
      setAuth: (token: string, user: User | null) =>
        set({ token, user, isAuthenticated: true }),
      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),
      revalidateSession: async () => {
        const { token } = get()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }
        set({ isRevalidating: true })
        try {
          const response = await fetch(buildApiUrl('/auth/me'), {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })
          if (response.ok) {
            const user = await response.json()
            set({ user, isAuthenticated: true })
          } else {
            set({ token: null, user: null, isAuthenticated: false })
          }
        } catch {
          set({ isAuthenticated: true })
        } finally {
          set({ isRevalidating: false })
        }
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)

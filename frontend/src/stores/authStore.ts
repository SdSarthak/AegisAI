import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  email: string
  full_name: string | null
  company_name: string | null
  subscription_tier: string
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean
  isRevalidating: boolean

  setAuth: (
    token: string,
    refreshToken: string,
    user: User | null
  ) => void

  updateTokens: (
    token: string,
    refreshToken: string
  ) => void

  logout: () => void
  revalidateSession: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isRevalidating: false,

      setAuth: (
        token: string,
        refreshToken: string,
        user: User | null
      ) =>
        set({
          token,
          refreshToken,
          user,
          isAuthenticated: true,
        }),

      updateTokens: (
        token: string,
        refreshToken: string
      ) =>
        set({
          token,
          refreshToken,
          isAuthenticated: true,
        }),

      logout: () =>
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
        }),

      revalidateSession: async () => {
        const { token } = get()
        if (!token) {
          set({
            refreshToken: null,
            isAuthenticated: false,
            user: null,
          })
          return
        }

        set({ isRevalidating: true })
        try {
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          if (response.ok) {
            const user = await response.json()
            set({ user, isAuthenticated: true })
          } else {
            set({
              token: null,
              refreshToken: null,
              user: null,
              isAuthenticated: false,
            })
          }
        } catch {
          set({
            token: null,
            refreshToken: null,
            user: null,
            isAuthenticated: false,
          })
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

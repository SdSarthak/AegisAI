import { Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense, useEffect, type ReactNode } from 'react'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import NotFound from './pages/NotFound'
import { Toaster } from 'react-hot-toast'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Analytics = lazy(() => import('./pages/Analytics'))
const AISystems = lazy(() => import('./pages/AISystems'))
const Classification = lazy(() => import('./pages/Classification'))
const Documents = lazy(() => import('./pages/Documents'))
const GuardConsole = lazy(() => import('./pages/GuardConsole'))
const RagChat = lazy(() => import('./pages/RagChat'))
const Notifications = lazy(() => import('./pages/Notifications'))

function PrivateRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function RouteFallback() {
  return (
    <div
      className="flex min-h-[40vh] items-center justify-center text-sm text-gray-500 dark:text-gray-400"
      role="status"
      aria-live="polite"
    >
      Loading...
    </div>
  )
}

function App() {
  // ✅ Sync with system theme (only if no manual preference)
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)")

    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem("theme")) {
        document.documentElement.classList.toggle("dark", e.matches)
      }
    }

    media.addEventListener("change", handler)
    return () => media.removeEventListener("change", handler)
  }, [])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          success: {
            style: {
              background: '#f0fdf4',
              color: '#166534',
              border: '1px solid #bbf7d0',
            },
          },
          error: {
            style: {
              background: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #fecaca',
            },
          },
        }}
      />

      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="ai-systems" element={<AISystems />} />
            <Route path="classification/:systemId?" element={<Classification />} />
            <Route path="documents" element={<Documents />} />
            <Route path="guard" element={<GuardConsole />} />
            <Route path="rag-chat" element={<RagChat />} />
            <Route path="notifications" element={<Notifications />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </>
  )
}

export default App

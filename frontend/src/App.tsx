import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AISystems from './pages/AISystems'
import Classification from './pages/Classification'
import Documents from './pages/Documents'
import DocumentDiffPage from './pages/DocumentDiffPage'
import Notifications from './pages/Notifications'
import Analytics from './pages/Analytics'
import GuardConsole from './pages/GuardConsole'
import NotFound from './pages/NotFound'
import { Toaster } from 'react-hot-toast'
import RagChat from './pages/RagChat'
import AuditDashboard from "./pages/AuditDashboard";
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isRevalidating } = useAuthStore()

  if (isRevalidating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Verifying session...</p>
        </div>
      </div>
    )
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  const { revalidateSession } = useAuthStore()

  // Revalidate session on app startup to ensure token is still valid
  useEffect(() => {
    revalidateSession()
  }, [revalidateSession])

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

      <Routes>
        <Route path="/audit" element={<AuditDashboard />} />
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
          <Route path="documents/:id/diff" element={<DocumentDiffPage />} />
          <Route path="guard" element={<GuardConsole />} />
          <Route path="rag-chat" element={<RagChat />} />
          <Route path="notifications" element={<Notifications />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  )
}

export default App
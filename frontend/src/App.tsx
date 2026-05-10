import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AISystems from './pages/AISystems'
import Classification from './pages/Classification'
import Onboarding from './pages/Onboarding'
import Documents from './pages/Documents'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Onboarding Route */}
      <Route path="/onboarding" element={<Onboarding />} />

      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="ai-systems" element={<AISystems />} />
        <Route path="classification/:systemId?" element={<Classification />} />
        <Route path="documents" element={<Documents />} />
      </Route>
    </Routes>
  )
}

export default App

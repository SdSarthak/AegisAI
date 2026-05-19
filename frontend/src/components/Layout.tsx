import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import {
  LayoutDashboard,
  Bot,
  FileCheck,
  FileText,
  LogOut,
  Shield,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import ThemeToggle from './ThemeToggle'

const navigation = [
  { name: 'Dashboard',           href: '/',               icon: LayoutDashboard },
  { name: 'AI Systems',          href: '/ai-systems',     icon: Bot             },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck       },
  { name: 'Documents',           href: '/documents',      icon: FileText        },
]

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const displayName = user?.full_name || user?.email || 'Demo User'
  const companyName = user?.company_name || 'Free Plan'
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-200">

      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <div
        className={`fixed inset-y-0 left-0 flex flex-col
                    bg-white border-r border-gray-200
                    dark:bg-gray-900 dark:border-gray-700
                    transition-[width] duration-200
                    ${isCollapsed ? 'w-20' : 'w-64'}`}
      >
        {/* Logo + ThemeToggle + collapse */}
        <div className="flex items-center justify-between gap-2 px-4 py-4
                        border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 min-w-0">
            <Shield className="w-8 h-8 shrink-0 text-primary-600 dark:text-primary-400" />
            {!isCollapsed && (
              <span className="text-lg font-semibold truncate
                               text-gray-900 dark:text-white">
                AI Compliance
              </span>
            )}
          </div>

          {/* ThemeToggle sits right beside the collapse button */}
          <div className="flex items-center gap-0.5 shrink-0">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setIsCollapsed((c) => !c)}
              className="p-2 rounded-lg transition-colors duration-200
                         text-gray-500 hover:text-gray-700 hover:bg-gray-100
                         dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-700
                         focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed
                ? <ChevronRight className="w-5 h-5" />
                : <ChevronLeft  className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto flex flex-col gap-1 p-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                title={item.name}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg
                            transition-colors duration-150
                            ${isCollapsed ? 'justify-center' : ''}
                            ${isActive
                              ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white'
                            }`}
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {!isCollapsed && <span>{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className={`flex items-center
                          ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
            {!isCollapsed && (
              <div className="truncate">
                <p className="text-sm font-medium truncate
                               text-gray-900 dark:text-white">
                  {displayName}
                </p>
                <p className="text-xs truncate text-gray-500 dark:text-gray-400">
                  {companyName}
                </p>
              </div>
            )}
            <button
              onClick={logout}
              className="p-2 rounded-lg transition-colors duration-200
                         text-gray-400 hover:text-gray-600 hover:bg-gray-100
                         dark:text-gray-500 dark:hover:text-white dark:hover:bg-gray-700
                         focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <div className={`transition-[padding] duration-200
                      ${isCollapsed ? 'pl-20' : 'pl-64'}`}>
        <main className="p-8 min-h-screen
                         text-gray-900 dark:text-white
                         transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
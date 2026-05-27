import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import NotificationBell from './NotificationBell'
import ThemeToggle from './ThemeToggle'
import {
  LayoutDashboard,
  Bot,
  FileCheck,
  FileText,
  MessageSquareText,
  LogOut,
  Shield,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  BarChart,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Analytics', href: '/analytics', icon: BarChart },
  { name: 'AI Systems', href: '/ai-systems', icon: Bot },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'LLM Guard', href: '/guard', icon: ShieldCheck },
  { name: 'Chatbot', href: '/rag-chat', icon: MessageSquareText },
]

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const displayName = user?.full_name || user?.email || 'Demo User'
  const companyName = user?.company_name || 'Free Plan'
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 transition-colors duration-200 dark:bg-gray-950 dark:text-gray-100">
      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-40 border-r border-gray-200 bg-white transition-[width,background-color,border-color] duration-200 dark:border-gray-800 dark:bg-gray-900 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between gap-3 border-b border-gray-200 px-4 py-4 dark:border-gray-800">
          <div className="flex min-w-0 items-center gap-2">
            <Shield className="w-8 h-8 text-primary-600" />

            <span
              className={`truncate text-lg font-semibold text-gray-900 dark:text-gray-100 ${
                isCollapsed ? 'sr-only' : ''
              }`}
            >
              AI Compliance
            </span>
          </div>

          <div className="flex items-center gap-1">
            <ThemeToggle />

            <button
              type="button"
              onClick={() => setIsCollapsed((prev) => !prev)}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="w-5 h-5" />
              ) : (
                <ChevronLeft className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 p-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href

            return (
              <Link
                key={item.name}
                to={item.href}
                title={item.name}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-white'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                } ${isCollapsed ? 'justify-center' : ''}`}
              >
                <item.icon className="w-5 h-5" />

                <span className={isCollapsed ? 'sr-only' : ''}>
                  {item.name}
                </span>
              </Link>
            )
          })}
        </nav>

        {/* User section */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-gray-200 p-4 dark:border-gray-800">
          <div
            className={`flex items-center ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
            <div className={isCollapsed ? 'sr-only' : 'truncate'}>
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                {displayName}
              </p>
              <p className="text-xs text-gray-500 truncate dark:text-gray-400">
                {companyName}
              </p>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={logout}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
                aria-label="Log out"
                title="Log out"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content area (right of sidebar) */}
      <div
        className={`transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >
        <header className="sticky top-0 z-30 flex items-center justify-end gap-1 border-b border-gray-200/60 bg-white/80 px-8 py-3 backdrop-blur-md transition-colors dark:border-gray-800/80 dark:bg-gray-950/80">
          <NotificationBell />
        </header>

        <main className="min-h-screen bg-gray-50 p-8 transition-colors duration-200 dark:bg-gray-950">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

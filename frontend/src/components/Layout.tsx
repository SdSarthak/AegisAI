import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import ThemeToggle from './ThemeToggle'
import NotificationBell from './NotificationBell'

import {
  LayoutDashboard,
  Bot,
  FileCheck,
  FileText,
  MessageSquareText,
  LogOut,
  Shield,
  ChevronLeft,
  ChevronRight,
  BarChart,
} from 'lucide-react'
import NotificationBell from './NotificationBell'
// ThemeToggle imported above



const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Analytics', href: '/analytics', icon: BarChart },
  { name: 'AI Systems', href: '/ai-systems', icon: Bot },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Chatbot', href: '/rag-chat', icon: MessageSquareText },
]

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const displayName = user?.full_name || user?.email || 'Demo User'
  const companyName = user?.company_name || 'Free Plan'

  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-black dark:text-white transition-colors duration-200">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 transition-[width] duration-200 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Logo + Controls */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-4">
          <div className="flex items-center gap-3 overflow-hidden">
            <Shield className="h-8 w-8 text-primary-600 shrink-0" />

            {!isCollapsed && (
              <span className="truncate text-lg font-semibold text-gray-900 dark:text-white">
                AegisAI
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />

            <button
              type="button"
              onClick={() => setIsCollapsed((prev) => !prev)}
              className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
              aria-label={
                isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'
              }
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="h-5 w-5" />
              ) : (
                <ChevronLeft className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 overflow-y-auto p-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href

            return (
              <Link
                key={item.name}
                to={item.href}
                title={item.name}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-white'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                } ${isCollapsed ? 'justify-center' : ''}`}
              >
                <item.icon className="h-5 w-5 shrink-0" />

                {!isCollapsed && <span>{item.name}</span>}
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
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

        {/* User Section */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-gray-200 dark:border-gray-700 p-4">
          <div
            className={`flex items-center ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
            {!isCollapsed && (
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-900 dark:text-white">
                  {displayName}
                </p>

                <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                  {companyName}
                </p>
              </div>
            )}

            <button
              onClick={logout}
              className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="h-5 w-5" />
            </button>
            <div className={isCollapsed ? 'sr-only' : 'truncate'}>
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {displayName}
              </p>
              <p className="text-xs text-gray-500 truncate dark:text-gray-400">
  {companyName}
</p>
</div>

<div className="flex items-center gap-1">
  <button
    onClick={logout}
    className="p-2 text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
    aria-label="Log out"
    title="Log out"
  >
    <LogOut className="w-5 h-5" />
  </button>
</div>

          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div
        className={`transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center justify-end gap-2 border-b border-gray-200/60 bg-white/80 px-8 py-3 backdrop-blur-md dark:border-gray-700 dark:bg-gray-800/80">
          <NotificationBell />
          <ThemeToggle />
        </header>

      {/* Main content area (right of sidebar) */}
      <div
        className={`transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >

        <header className="sticky top-0 z-30 flex items-center justify-end gap-1 px-8 py-3 bg-white/80 backdrop-blur-md border-b border-gray-200/60">
          <NotificationBell />
          <ThemeToggle />
        </header>

        <main className="p-8 min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
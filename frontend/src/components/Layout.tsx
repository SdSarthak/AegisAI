import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import ThemeToggle from './ThemeToggle'

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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-black dark:text-white">
      {/* Sidebar */}
    <div
     className={`fixed inset-y-0 left-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-r border-white/10 shadow-xl transition-all duration-300 ease-in-out z-40 ${
     isCollapsed ? 'w-20' : 'w-72'
    }`}
>
        {/* Logo */}
        <div className="flex items-center justify-between gap-2 px-4 py-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary-600" />
            <ThemeToggle />

            <span
              className={`text-lg font-semibold text-gray-900 dark:text-white ${
                isCollapsed ? 'sr-only' : ''
              }`}
            >
              AI Compliance
            </span>
          </div>

          <button
            type="button"
            onClick={() => setIsCollapsed((prev) => !prev)}
            className="p-2 text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
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
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-primary-100 dark:hover:bg-primary-800 hover:scale-[1.02] transition-all duration-300'
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
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div
            className={`flex items-center rounded-xl bg-white/40 dark:bg-gray-800/40 backdrop-blur-md p-2 ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
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
      </div>

      {/* Main content area (right of sidebar) */}
      <div
        className={`transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >

        <header className="sticky top-0 z-30 flex items-center justify-end gap-2 px-4 md:px-8 py-3 bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl border-b border-white/10 shadow-sm">
          <NotificationBell />
          <ThemeToggle />
        </header>

        <main className="p-4 md:p-8 min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
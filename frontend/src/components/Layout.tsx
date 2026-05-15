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
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'AI Systems', href: '/ai-systems', icon: Bot },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck },
  { name: 'Documents', href: '/documents', icon: FileText },
]

const sidebarBase = [
  'fixed inset-y-0 left-0 z-30 flex flex-col',
  'bg-white dark:bg-gray-900',
  'border-r border-gray-200 dark:border-gray-700',
  'transition-[width] duration-200 overflow-hidden',
].join(' ')

const controlBtnClass = [
  'p-2 rounded-lg transition-colors duration-150',
  'text-gray-500 hover:text-gray-700 hover:bg-gray-100',
  'dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
].join(' ')

const logoutBtnClass = [
  'p-2 rounded-lg transition-colors duration-150 shrink-0',
  'text-gray-400 hover:text-gray-600 hover:bg-gray-100',
  'dark:text-gray-500 dark:hover:text-gray-200 dark:hover:bg-gray-700',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
].join(' ')

function navLinkClass(isActive: boolean, isCollapsed: boolean): string {
  const base =
    'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500'

  const active =
    'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'

  const inactive =
    'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200'

  const collapsed = isCollapsed ? 'justify-center' : ''

  return [base, isActive ? active : inactive, collapsed].join(' ')
}

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const displayName = user?.full_name || user?.email || 'Demo User'
  const companyName = user?.company_name || 'Free Plan'

  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-950 transition-colors duration-200">

      {/* Sidebar */}
      <aside
        aria-label="Sidebar navigation"
        className={`${sidebarBase} ${isCollapsed ? 'w-20' : 'w-64'}`}
      >

        {/* Logo + Controls */}
        <div className="flex items-center justify-between gap-2 px-4 py-4 border-b border-gray-200 dark:border-gray-700 shrink-0">

          <div className="flex items-center gap-2 min-w-0">
            <Shield
              className="w-8 h-8 text-primary-600 dark:text-primary-400 shrink-0"
              aria-hidden="true"
            />

            {!isCollapsed && (
              <span className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                AI Compliance
              </span>
            )}
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <ThemeToggle />

            <button
              type="button"
              onClick={() => setIsCollapsed((prev) => !prev)}
              aria-expanded={!isCollapsed}
              aria-controls="sidebar-nav"
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className={controlBtnClass}
            >
              {isCollapsed ? (
                <ChevronRight className="w-5 h-5" aria-hidden="true" />
              ) : (
                <ChevronLeft className="w-5 h-5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav
          id="sidebar-nav"
          className="flex flex-col gap-1 p-4 flex-1 overflow-y-auto"
        >
          {navigation.map(({ name, href, icon: Icon }) => {
            const isActive = location.pathname === href

            return (
              <Link
                key={name}
                to={href}
                title={isCollapsed ? name : undefined}
                aria-current={isActive ? 'page' : undefined}
                className={navLinkClass(isActive, isCollapsed)}
              >
                <Icon
                  className="w-5 h-5 shrink-0"
                  aria-hidden="true"
                />

                <span className={isCollapsed ? 'sr-only' : 'truncate'}>
                  {name}
                </span>
              </Link>
            )
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
          <div
            className={`flex items-center gap-2 ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >

            {!isCollapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {displayName}
                </p>

                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {companyName}
                </p>
              </div>
            )}

            <button
              type="button"
              onClick={logout}
              aria-label="Log out"
              title="Log out"
              className={logoutBtnClass}
            >
              <LogOut className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div
        className={`flex-1 transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >
        <main className="p-8 min-h-screen text-gray-900 dark:text-gray-100">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
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
import NotificationBell from './NotificationBell'
import ThemeToggle from './ThemeToggle'

/*──────────────────────────────────────────────────────────────────────────────
  Layout — app shell with collapsible sidebar + sticky top bar.

  WHAT CHANGED (Issue #113):
    • Added a sticky header bar between the sidebar padding wrapper and the
      <main> content area.  This bar hosts the NotificationBell and
      ThemeToggle components.
    • The header uses `sticky top-0 z-30` so it stays visible while the
      user scrolls page content.  `bg-white/80 backdrop-blur-md` gives a
      frosted-glass effect that lets underlying content peek through.

  WHY A TOP BAR AND NOT THE SIDEBAR?
    Notification bells are conventionally top-right in SaaS dashboards
    because:
      1. They sit in the user's natural reading scan path (top → right).
      2. Dropdown panels need horizontal space; a sidebar placement would
         overlap the nav links or push outside the viewport.
      3. The sidebar is already dense with navigation — adding more icons
         there hurts scannability.
──────────────────────────────────────────────────────────────────────────────*/

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'AI Systems', href: '/ai-systems', icon: Bot },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck },
  { name: 'Documents', href: '/documents', icon: FileText },
]

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const displayName = user?.full_name || user?.email || 'Demo User'
  const companyName = user?.company_name || 'Free Plan'
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 bg-white border-r border-gray-200 transition-[width] duration-200 z-40 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between gap-2 px-4 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary-600" />
            <span
              className={`text-lg font-semibold text-gray-900 ${
                isCollapsed ? 'sr-only' : ''
              }`}
            >
              AI Compliance
            </span>
          </div>
          <button
            type="button"
            onClick={() => setIsCollapsed((prev) => !prev)}
            className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
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
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
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
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div
            className={`flex items-center ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
            <div className={isCollapsed ? 'sr-only' : 'truncate'}>
              <p className="text-sm font-medium text-gray-900 truncate">
                {displayName}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {companyName}
              </p>
            </div>
            <button
              onClick={logout}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main content area (right of sidebar) */}
      <div
        className={`transition-[padding] duration-200 ${
          isCollapsed ? 'pl-20' : 'pl-64'
        }`}
      >
        {/*
         * ── Sticky header bar ──────────────────────────────────────────
         *
         * STYLING RATIONALE:
         *   sticky top-0     → sticks to viewport top while scrolling
         *   z-30             → above page content, below sidebar (z-40)
         *                      and below notification dropdown (z-50)
         *   bg-white/80      → 80 % white opacity
         *   backdrop-blur-md → frosted-glass blur behind the bar
         *   border-b         → subtle separator from page content
         *
         * The flex container pushes the controls to the right edge via
         * justify-end.  gap-1 keeps icons tight together — they're small
         * interactive controls, not navigation items.
         */}
        <header className="sticky top-0 z-30 flex items-center justify-end gap-1 px-8 py-3 bg-white/80 backdrop-blur-md border-b border-gray-200/60">
          <NotificationBell />
          <ThemeToggle />
        </header>

        <main className="p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

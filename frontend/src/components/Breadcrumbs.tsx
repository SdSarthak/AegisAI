import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { aiSystemsApi } from '../services/api'
import { ChevronRight, LayoutDashboard, Bot, FileText, BarChart, FileCheck, MessageSquareText, Bell } from 'lucide-react'

export default function Breadcrumbs() {
  const location = useLocation()
  const pathnames = location.pathname.split('/').filter((x) => x)

  // Determine if we have a system ID from the classification route
  const isClassificationRoute = pathnames[0] === 'classification'
  const systemIdStr = isClassificationRoute ? pathnames[1] : null
  const systemId = systemIdStr ? parseInt(systemIdStr, 10) : null

  // Fetch the AI system name if on classification/:id
  const { data: system, isLoading } = useQuery({
    queryKey: ['ai-system', systemId],
    queryFn: () => aiSystemsApi.get(systemId!),
    enabled: !!systemId && !isNaN(systemId),
  })

  // Define breadcrumb items list based on current path
  const items = []

  // Always start with Dashboard as the home breadcrumb unless we are already on the root Dashboard page
  if (pathnames.length > 0) {
    items.push({
      label: 'Dashboard',
      href: '/',
      icon: LayoutDashboard,
    })
  }

  // Parse path segments to build breadcrumbs
  if (pathnames.length > 0) {
    const primarySegment = pathnames[0]

    switch (primarySegment) {
      case 'analytics':
        items.push({
          label: 'Analytics',
          href: null,
          icon: BarChart,
        })
        break

      case 'ai-systems':
        items.push({
          label: 'AI Systems',
          href: null,
          icon: Bot,
        })
        break

      case 'classification':
        if (!systemId) {
          items.push({
            label: 'Risk Classification',
            href: null,
            icon: FileCheck,
          })
        } else {
          // If viewing a specific system's classification, nest under AI Systems
          items.push({
            label: 'AI Systems',
            href: '/ai-systems',
            icon: Bot,
          })
          items.push({
            label: isLoading ? 'Loading...' : system?.name || 'AI System',
            href: null,
            icon: Bot,
            isHighlight: true,
          })
          items.push({
            label: 'Risk Classification',
            href: null,
            icon: FileCheck,
          })
        }
        break

      case 'documents':
        items.push({
          label: 'Documents',
          href: null,
          icon: FileText,
        })
        break

      case 'rag-chat':
        items.push({
          label: 'Chatbot',
          href: null,
          icon: MessageSquareText,
        })
        break

      case 'notifications':
        items.push({
          label: 'Notifications',
          href: null,
          icon: Bell,
        })
        break

      default:
        // Generic fallback for any other pathnames
        items.push({
          label: primarySegment.charAt(0).toUpperCase() + primarySegment.slice(1).replace('-', ' '),
          href: null,
          icon: null,
        })
    }
  }

  // If we are at the dashboard root, show a single static label or icon
  if (pathnames.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 font-medium">
        <LayoutDashboard className="w-4 h-4 text-primary-500 dark:text-primary-400" />
        <span className="text-gray-900 dark:text-white font-semibold">Dashboard</span>
      </div>
    )
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center flex-wrap gap-1 text-sm md:text-base font-medium">
      {items.map((item, index) => {
        const isLast = index === items.length - 1
        const Icon = item.icon

        return (
          <div key={index} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="w-4 h-4 mx-1.5 text-gray-400 dark:text-gray-600 flex-shrink-0" />
            )}

            {isLast ? (
              <span
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-gray-900 dark:text-white font-semibold select-none ${
                  item.isHighlight
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-950/40 dark:text-primary-400 border border-primary-100 dark:border-primary-900/60'
                    : ''
                }`}
              >
                {Icon && <Icon className={`w-4 h-4 ${item.isHighlight ? 'text-primary-500' : 'text-gray-400 dark:text-gray-500'}`} />}
                <span>{item.label}</span>
              </span>
            ) : item.href ? (
              <Link
                to={item.href}
                className="flex items-center gap-1.5 px-2 py-1 rounded-md text-gray-500 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-150 ease-in-out font-medium"
              >
                {Icon && <Icon className="w-4 h-4 text-gray-400 dark:text-gray-500" />}
                <span>{item.label}</span>
              </Link>
            ) : (
              <span className="flex items-center gap-1.5 px-2 py-1 text-gray-500 dark:text-gray-400">
                {Icon && <Icon className="w-4 h-4 text-gray-400 dark:text-gray-500" />}
                <span>{item.label}</span>
              </span>
            )}
          </div>
        )
      })}
    </nav>
  )
}

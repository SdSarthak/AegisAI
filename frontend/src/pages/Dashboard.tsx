import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { aiSystemsApi, documentsApi } from '../services/api'
import { Bot, FileText, AlertTriangle, CheckCircle, Clock } from 'lucide-react'

export default function Dashboard() {
  const { data: systems = [] } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: () => aiSystemsApi.list(),
  })

  const { data: documents = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  })

  const stats = [
    {
      name: 'AI Systems',
      value: systems.length,
      icon: Bot,
      color: 'bg-blue-500',
    },
    {
      name: 'Documents',
      value: documents.length,
      icon: FileText,
      color: 'bg-green-500',
    },
    {
      name: 'High Risk',
      value: systems.filter((s: { risk_level: string }) => s.risk_level === 'high').length,
      icon: AlertTriangle,
      color: 'bg-red-500',
    },
    {
      name: 'Compliant',
      value: systems.filter((s: { compliance_status: string }) => s.compliance_status === 'compliant').length,
      icon: CheckCircle,
      color: 'bg-emerald-500',
    },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your EU AI Act compliance status</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/ai-systems"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <Bot className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Add AI System</span>
          </Link>
          <Link
            to="/classification"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <AlertTriangle className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Risk Classification</span>
          </Link>
          <Link
            to="/documents"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <FileText className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Generate Documents</span>
          </Link>
        </div>
      </div>

      {/* Recent AI Systems */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your AI Systems</h2>
        {systems.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Bot className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No AI systems registered yet</p>
            <Link
              to="/ai-systems"
              className="text-primary-600 hover:text-primary-500 mt-2 inline-block"
            >
              Add your first AI system →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {systems.slice(0, 5).map((system: {
              id: number
              name: string
              risk_level: string | null
              compliance_status: string
            }) => (
              <div
                key={system.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-200"
              >
                <div>
                  <p className="font-medium text-gray-900">{system.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {system.risk_level && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          system.risk_level === 'high'
                            ? 'bg-red-100 text-red-700'
                            : system.risk_level === 'limited'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-green-100 text-green-700'
                        }`}
                      >
                        {system.risk_level} risk
                      </span>
                    )}
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {system.compliance_status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
                <Link
                  to={`/classification/${system.id}`}
                  className="text-sm text-primary-600 hover:text-primary-500"
                >
                  View →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

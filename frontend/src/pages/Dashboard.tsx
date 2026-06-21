import BackendStatus from '../components/BackendStatus'
import DashboardGrid from '../components/dashboard/DashboardGrid'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end">
        <BackendStatus />
      </div>
      <DashboardGrid />
    </div>
  )
}

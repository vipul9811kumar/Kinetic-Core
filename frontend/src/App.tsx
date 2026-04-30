import { Routes, Route, NavLink } from 'react-router-dom'
import { Activity, ClipboardList, Zap, BarChart3, Shield } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Incidents from './pages/Incidents'
import WorkOrders from './pages/WorkOrders'
import TelemetryView from './pages/TelemetryView'
import AgentTrace from './pages/AgentTrace'

const navItems = [
  { to: '/', label: 'Dashboard', icon: Activity },
  { to: '/incidents', label: 'Incidents', icon: Zap },
  { to: '/work-orders', label: 'Work Orders', icon: ClipboardList },
  { to: '/telemetry', label: 'Telemetry', icon: BarChart3 },
]

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-blue-400" />
            <div>
              <div className="font-bold text-white text-lg leading-tight">Kinetic-Core</div>
              <div className="text-xs text-gray-400">Autonomous Reliability</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <div className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
            All agents online
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:id" element={<AgentTrace />} />
          <Route path="/work-orders" element={<WorkOrders />} />
          <Route path="/telemetry" element={<TelemetryView />} />
        </Routes>
      </main>
    </div>
  )
}

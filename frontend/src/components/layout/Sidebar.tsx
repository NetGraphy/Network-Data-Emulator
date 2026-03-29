import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Topology', icon: '⬡' },
  { path: '/devices', label: 'Devices', icon: '▦' },
  { path: '/cli-modeling', label: 'CLI Modeling', icon: '⌨' },
  { path: '/scenarios', label: 'Scenarios', icon: '⚡' },
  { path: '/custom-filters', label: 'Filters (Code)', icon: '{f}' },
  { path: '/query-explorer', label: 'Query Explorer', icon: '>' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-lg font-bold text-cyan-400 tracking-wide">SNEP</h1>
        <p className="text-xs text-gray-500 mt-0.5">Network Emulator</p>
      </div>
      <nav className="flex-1 p-2">
        {navItems.map(item => {
          const active = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors mb-0.5 ${
                active
                  ? 'bg-cyan-500/10 text-cyan-400'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>
      <div className="p-3 border-t border-gray-800">
        <p className="text-xs text-gray-600">v0.1.0</p>
      </div>
    </aside>
  )
}

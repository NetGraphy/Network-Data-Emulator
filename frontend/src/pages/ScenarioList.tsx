import { useQuery } from '@tanstack/react-query'
import { fetchScenarios } from '../api/client'

export default function ScenarioList() {
  const { data: scenarios, isLoading } = useQuery({
    queryKey: ['scenarios'],
    queryFn: fetchScenarios,
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">Scenarios</h2>
          <p className="text-sm text-gray-400">Fault injection and state change scenarios</p>
        </div>
        <button className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm transition-colors">
          New Scenario
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : scenarios && scenarios.length > 0 ? (
        <div className="grid gap-4">
          {scenarios.map(s => (
            <div key={s.id} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{s.name}</h3>
                  {s.description && <p className="text-sm text-gray-400 mt-1">{s.description}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{s.event_count} events</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    s.status === 'ready' ? 'bg-green-500/10 text-green-400' :
                    s.status === 'running' ? 'bg-cyan-500/10 text-cyan-400' :
                    s.status === 'completed' ? 'bg-gray-500/10 text-gray-400' :
                    'bg-yellow-500/10 text-yellow-400'
                  }`}>
                    {s.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center text-gray-500">
          No scenarios yet. Create one to simulate network faults and events.
        </div>
      )}
    </div>
  )
}

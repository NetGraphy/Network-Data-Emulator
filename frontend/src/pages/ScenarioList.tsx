import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchScenarios, fetchScenario, startScenario, pauseScenario, resumeScenario, resetScenario, getScenarioExecution } from '../api/client'

export default function ScenarioList() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: scenarios, isLoading } = useQuery({ queryKey: ['scenarios'], queryFn: fetchScenarios })
  const { data: detail } = useQuery({
    queryKey: ['scenario', selectedId],
    queryFn: () => fetchScenario(selectedId!),
    enabled: !!selectedId,
  })
  const { data: execution, refetch: refetchExec } = useQuery({
    queryKey: ['scenario-exec', selectedId],
    queryFn: () => getScenarioExecution(selectedId!),
    enabled: !!selectedId,
    refetchInterval: selectedId ? 3000 : false,
  })

  const startMut = useMutation({
    mutationFn: (id: string) => startScenario(id),
    onSuccess: () => { refetchExec(); queryClient.invalidateQueries({ queryKey: ['scenarios'] }); },
  })
  const pauseMut = useMutation({ mutationFn: (id: string) => pauseScenario(id), onSuccess: () => refetchExec() })
  const resumeMut = useMutation({ mutationFn: (id: string) => resumeScenario(id), onSuccess: () => refetchExec() })
  const resetMut = useMutation({
    mutationFn: (id: string) => resetScenario(id),
    onSuccess: () => { refetchExec(); queryClient.invalidateQueries({ queryKey: ['scenarios'] }); },
  })

  const progress = execution?.progress || {}
  const logs = execution?.recent_logs || []

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: Scenario list */}
      <div className="w-1/3 flex flex-col gap-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold">Scenarios</h2>
        </div>

        {isLoading ? <p className="text-gray-500">Loading...</p> : (
          <div className="space-y-2">
            {scenarios?.map((s: any) => (
              <button
                key={s.id}
                onClick={() => setSelectedId(s.id)}
                className={`w-full text-left p-4 rounded-xl border transition-colors ${
                  selectedId === s.id ? 'border-cyan-500 bg-cyan-500/5' : 'border-gray-800 bg-gray-900 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{s.name}</span>
                  <StatusBadge status={s.status} />
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{s.description}</p>
                <span className="text-[10px] text-gray-600 mt-1 block">{s.event_count} events</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Detail + Execution */}
      <div className="flex-1 flex flex-col gap-4 overflow-auto">
        {selectedId && detail ? (
          <>
            {/* Header + Controls */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-lg">{detail.name}</h3>
                <StatusBadge status={detail.status} />
              </div>
              <p className="text-sm text-gray-400 mb-4">{detail.description}</p>

              <div className="flex gap-2">
                {(detail.status === 'ready' || detail.status === 'completed') && (
                  <button onClick={() => startMut.mutate(selectedId)} disabled={startMut.isPending}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg text-sm font-medium">
                    {startMut.isPending ? 'Starting...' : 'Start Scenario'}
                  </button>
                )}
                {detail.status === 'running' && (
                  <button onClick={() => pauseMut.mutate(selectedId)}
                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm font-medium">Pause</button>
                )}
                {progress.status === 'paused' && (
                  <button onClick={() => resumeMut.mutate(selectedId)}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm font-medium">Resume</button>
                )}
                {(detail.status === 'completed' || detail.status === 'running') && (
                  <button onClick={() => resetMut.mutate(selectedId)} disabled={resetMut.isPending}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
                    {resetMut.isPending ? 'Resetting...' : 'Reset'}
                  </button>
                )}
              </div>
            </div>

            {/* Progress */}
            {progress.status && progress.status !== 'not_started' && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-200">Execution Progress</h4>
                  <span className="text-xs text-gray-400">
                    {progress.current_event || 0} / {progress.total_events || 0} events
                  </span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 mb-3">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      progress.status === 'completed' ? 'bg-green-500' :
                      progress.status === 'failed' ? 'bg-red-500' : 'bg-cyan-500'
                    }`}
                    style={{ width: `${progress.total_events ? (progress.current_event / progress.total_events * 100) : 0}%` }}
                  />
                </div>
                <div className="text-xs text-gray-400">
                  Status: <span className="text-gray-200">{progress.status}</span>
                  {' '} | Logs generated: <span className="text-gray-200">{progress.logs_generated || 0}</span>
                </div>
              </div>
            )}

            {/* Events */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h4 className="text-sm font-medium text-gray-200 mb-3">Events</h4>
              <div className="space-y-2">
                {detail.events?.map((e: any, i: number) => {
                  const completed = progress.completed_events?.find((c: any) => c.event_id === e.id)
                  return (
                    <div key={e.id} className={`flex items-center gap-3 p-3 rounded-lg ${
                      completed ? 'bg-green-500/5 border border-green-500/20' : 'bg-gray-800/50'
                    }`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        completed ? 'bg-green-600 text-white' :
                        progress.current_event === i + 1 ? 'bg-cyan-600 text-white animate-pulse' :
                        'bg-gray-700 text-gray-400'
                      }`}>{i + 1}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-200">{e.action_type}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                            e.trigger_type === 'immediate' ? 'bg-gray-700 text-gray-300' :
                            e.trigger_type === 'delay' ? 'bg-blue-900/30 text-blue-400' :
                            'bg-purple-900/30 text-purple-400'
                          }`}>{e.trigger_type}{e.trigger_config?.delay_seconds ? ` (${e.trigger_config.delay_seconds}s)` : ''}</span>
                        </div>
                        {completed && (
                          <span className="text-[10px] text-green-400">{completed.logs_generated} logs generated</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Generated Logs */}
            {logs.length > 0 && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h4 className="text-sm font-medium text-gray-200 mb-3">
                  Generated Syslog ({execution?.total_logs || 0} total)
                </h4>
                <div className="space-y-0.5 max-h-[400px] overflow-auto">
                  {logs.map((log: any, i: number) => (
                    <div key={i} className={`font-mono text-[11px] py-0.5 ${
                      log.severity <= 2 ? 'text-red-400' :
                      log.severity <= 4 ? 'text-yellow-400' :
                      'text-green-400'
                    }`}>
                      {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Select a scenario to view details and run it
          </div>
        )}
      </div>
    </div>
  )
}


function StatusBadge({ status }: { status: string }) {
  const c: Record<string, string> = {
    ready: 'bg-green-500/10 text-green-400',
    running: 'bg-cyan-500/10 text-cyan-400',
    paused: 'bg-yellow-500/10 text-yellow-400',
    completed: 'bg-gray-500/10 text-gray-400',
    draft: 'bg-gray-500/10 text-gray-500',
    failed: 'bg-red-500/10 text-red-400',
  }
  return <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${c[status] || c.draft}`}>{status}</span>
}

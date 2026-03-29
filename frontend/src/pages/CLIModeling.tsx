import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDevices, fetchDevice, fetchCLIMappings, createCLIMapping, parseNeighbors, createLink, fetchInterfaces } from '../api/client'
import type { CLIMapping, NeighborParseResult, Device } from '../types'

const COMMON_COMMANDS = [
  'show version',
  'show interfaces',
  'show ip interface brief',
  'show cdp neighbors',
  'show cdp neighbors detail',
  'show lldp neighbors',
  'show running-config',
  'show inventory',
  'show logging',
]

export default function CLIModeling() {
  const { id: paramDeviceId } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const [selectedDeviceId, setSelectedDeviceId] = useState(paramDeviceId || '')
  const [command, setCommand] = useState('')
  const [rawOutput, setRawOutput] = useState('')
  const [mode, setMode] = useState<'paste' | 'neighbor-map'>('paste')
  const [neighborResults, setNeighborResults] = useState<NeighborParseResult[]>([])
  const [saving, setSaving] = useState(false)

  const { data: devices } = useQuery({ queryKey: ['devices'], queryFn: fetchDevices })
  const { data: mappings, refetch: refetchMappings } = useQuery({
    queryKey: ['cli-mappings', selectedDeviceId],
    queryFn: () => fetchCLIMappings(selectedDeviceId || undefined),
    enabled: !!selectedDeviceId,
  })

  const deviceId = selectedDeviceId || paramDeviceId

  const saveMutation = useMutation({
    mutationFn: (data: any) => createCLIMapping(data),
    onSuccess: () => {
      refetchMappings()
      setRawOutput('')
      setCommand('')
    },
  })

  const handleSaveStatic = async () => {
    if (!deviceId || !command || !rawOutput) return
    setSaving(true)
    await saveMutation.mutateAsync({
      device_id: deviceId,
      command,
      raw_output: rawOutput,
      mode: 'static',
    })
    setSaving(false)
  }

  const handleParseNeighbors = async () => {
    if (!rawOutput) return
    const cmdType = command.toLowerCase().includes('lldp') ? 'lldp' : 'cdp'
    const results = await parseNeighbors({ raw_output: rawOutput, command_type: cmdType })
    setNeighborResults(results)
    setMode('neighbor-map')
  }

  const handleCreateLink = async (entry: NeighborParseResult) => {
    if (!deviceId || !entry.matched_device_id) return
    // Find local and remote interface IDs
    const localInterfaces = await fetchInterfaces(deviceId)
    const remoteInterfaces = await fetchInterfaces(entry.matched_device_id)

    const localIface = localInterfaces.find(i =>
      i.name === entry.local_interface || i.short_name === entry.local_interface
    )
    const remoteIface = remoteInterfaces.find(i =>
      i.name === entry.remote_interface || i.short_name === entry.remote_interface
    )

    if (localIface && remoteIface) {
      await createLink({
        interface_a_id: localIface.id,
        interface_b_id: remoteIface.id,
        link_type: 'physical',
        discovery_protocol: command.toLowerCase().includes('lldp') ? 'lldp' : 'cdp',
      })
      queryClient.invalidateQueries({ queryKey: ['topology'] })
      // Re-parse to update match status
      handleParseNeighbors()
    }
  }

  const isNeighborCommand = command.toLowerCase().includes('cdp neighbor') || command.toLowerCase().includes('lldp neighbor')

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">CLI Output Modeling</h2>
          <p className="text-sm text-gray-400">Paste real device output and map to emulated devices</p>
        </div>
      </div>

      <div className="flex gap-6 flex-1 min-h-0">
        {/* Left: Input Panel */}
        <div className="w-1/2 flex flex-col gap-4">
          {/* Device selector */}
          <div className="flex gap-3">
            <select
              value={selectedDeviceId}
              onChange={e => setSelectedDeviceId(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
            >
              <option value="">Select device...</option>
              {devices?.map(d => (
                <option key={d.id} value={d.id}>{d.hostname}</option>
              ))}
            </select>

            <select
              value={command}
              onChange={e => setCommand(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
            >
              <option value="">Select command...</option>
              {COMMON_COMMANDS.map(cmd => (
                <option key={cmd} value={cmd}>{cmd}</option>
              ))}
            </select>
            <input
              type="text"
              value={command}
              onChange={e => setCommand(e.target.value)}
              placeholder="Or type custom command"
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>

          {/* Raw output textarea */}
          <div className="flex-1 flex flex-col">
            <label className="text-xs text-gray-400 mb-1">Paste CLI output from real device:</label>
            <textarea
              value={rawOutput}
              onChange={e => setRawOutput(e.target.value)}
              placeholder={`Paste the output of "${command || 'show ...'}" here...`}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-4 text-sm font-mono text-green-400 focus:border-cyan-500 focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleSaveStatic}
              disabled={!deviceId || !command || !rawOutput || saving}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 disabled:hover:bg-cyan-600 rounded-lg text-sm transition-colors"
            >
              {saving ? 'Saving...' : 'Save as Static Replay'}
            </button>

            {isNeighborCommand && (
              <button
                onClick={handleParseNeighbors}
                disabled={!rawOutput}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
              >
                Parse & Map Neighbors
              </button>
            )}
          </div>
        </div>

        {/* Right: Results Panel */}
        <div className="w-1/2 flex flex-col gap-4">
          {mode === 'paste' && (
            <>
              <h3 className="text-sm font-medium text-gray-300">Existing CLI Mappings</h3>
              <div className="flex-1 overflow-auto bg-gray-900 rounded-xl border border-gray-800">
                {mappings && mappings.length > 0 ? (
                  <div className="divide-y divide-gray-800">
                    {mappings.map((m: CLIMapping) => (
                      <div key={m.id} className="p-3 hover:bg-gray-800/30">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-sm text-cyan-400">{m.command}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            m.mode === 'static' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'
                          }`}>
                            {m.mode}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1 truncate font-mono">
                          {m.raw_output.substring(0, 120)}...
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                    No CLI mappings yet. Paste output on the left to create one.
                  </div>
                )}
              </div>
            </>
          )}

          {mode === 'neighbor-map' && (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-300">Detected Neighbors ({neighborResults.length})</h3>
                <button
                  onClick={() => setMode('paste')}
                  className="text-xs text-gray-400 hover:text-gray-200"
                >
                  Back to Mappings
                </button>
              </div>
              <div className="flex-1 overflow-auto space-y-3">
                {neighborResults.map((entry, i) => (
                  <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500 text-xs">Device ID</span>
                        <p className="font-mono font-medium">{entry.device_id}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Local Interface</span>
                        <p className="font-mono">{entry.local_interface}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Remote Interface</span>
                        <p className="font-mono">{entry.remote_interface}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Match Status</span>
                        <p className={`font-medium ${
                          entry.match_status === 'matched' ? 'text-green-400' :
                          entry.match_status === 'partial_match' ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {entry.match_status === 'matched' && '✓ Matched'}
                          {entry.match_status === 'partial_match' && `~ Partial: ${entry.matched_hostname}`}
                          {entry.match_status === 'unmatched' && '✗ No match'}
                        </p>
                      </div>
                    </div>

                    {entry.matched_device_id && (
                      <div className="mt-3 pt-3 border-t border-gray-800">
                        <button
                          onClick={() => handleCreateLink(entry)}
                          className="px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded text-xs transition-colors"
                        >
                          Create Link
                        </button>
                      </div>
                    )}
                  </div>
                ))}

                {neighborResults.length === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    No neighbors detected. Check the output format.
                  </div>
                )}
              </div>

              {neighborResults.some(e => e.matched_device_id) && (
                <button
                  onClick={() => neighborResults.filter(e => e.matched_device_id).forEach(handleCreateLink)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm transition-colors"
                >
                  Create All Matched Links ({neighborResults.filter(e => e.matched_device_id).length})
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

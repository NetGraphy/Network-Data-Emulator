import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDevice, fetchInterfaces, fetchDeviceNeighbors, updateInterface, executeCommand } from '../api/client'

type Tab = 'interfaces' | 'neighbors' | 'cli' | 'snmp' | 'connection'

export default function DeviceDetail() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('interfaces')
  const [command, setCommand] = useState('')
  const [output, setOutput] = useState('')
  const queryClient = useQueryClient()

  const { data: device } = useQuery({ queryKey: ['device', id], queryFn: () => fetchDevice(id!) })
  const { data: interfaces } = useQuery({ queryKey: ['interfaces', id], queryFn: () => fetchInterfaces(id!) })
  const { data: neighbors } = useQuery({ queryKey: ['neighbors', id], queryFn: () => fetchDeviceNeighbors(id!) })

  const toggleInterface = useMutation({
    mutationFn: ({ ifaceId, status }: { ifaceId: string; status: string }) =>
      updateInterface(ifaceId, { oper_status: status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interfaces', id] }),
  })

  const runCommand = async () => {
    if (!command.trim() || !id) return
    const result = await executeCommand(id, command)
    setOutput(result.output)
  }

  if (!device) return <div className="p-6 text-gray-500">Loading...</div>

  const tabs: { key: Tab; label: string }[] = [
    { key: 'interfaces', label: `Interfaces (${interfaces?.length || 0})` },
    { key: 'neighbors', label: `Neighbors (${neighbors?.length || 0})` },
    { key: 'cli', label: 'CLI Preview' },
    { key: 'snmp', label: 'SNMP' },
    { key: 'connection', label: 'Connection Info' },
  ]

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold">{device.hostname}</h2>
          <p className="text-sm text-gray-400">
            {device.platform?.name} / {device.device_model?.display_name} / {device.serial_number}
          </p>
        </div>
        <span className={`ml-auto px-3 py-1 rounded-full text-xs font-medium ${
          device.admin_state === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
        }`}>
          {device.admin_state}
        </span>
        <Link to={`/devices/${id}/cli`} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm">
          CLI Modeling
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-800">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm transition-colors border-b-2 -mb-px ${
              tab === t.key ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'interfaces' && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left p-3 font-medium">Name</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">IP Address</th>
                <th className="text-left p-3 font-medium">Speed</th>
                <th className="text-left p-3 font-medium">Description</th>
                <th className="text-left p-3 font-medium">In/Out (bps)</th>
                <th className="text-left p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {interfaces?.map(iface => (
                <tr key={iface.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-3 font-mono text-gray-200">{iface.name}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1 text-xs ${
                      iface.oper_status === 'up' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        iface.oper_status === 'up' ? 'bg-green-400' : 'bg-red-400'
                      }`} />
                      {iface.admin_status}/{iface.oper_status}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-gray-300 text-xs">{iface.ip_address || '-'}</td>
                  <td className="p-3 text-gray-400">{iface.speed_mbps >= 1000 ? `${iface.speed_mbps/1000}G` : `${iface.speed_mbps}M`}</td>
                  <td className="p-3 text-gray-500 text-xs">{iface.description || '-'}</td>
                  <td className="p-3 text-gray-400 text-xs font-mono">
                    {iface.counters ? `${(iface.counters.rate_in_bps / 1e6).toFixed(0)}M / ${(iface.counters.rate_out_bps / 1e6).toFixed(0)}M` : '-'}
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => toggleInterface.mutate({
                        ifaceId: iface.id,
                        status: iface.oper_status === 'up' ? 'down' : 'up',
                      })}
                      className={`px-2 py-1 rounded text-xs ${
                        iface.oper_status === 'up'
                          ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                          : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                      }`}
                    >
                      {iface.oper_status === 'up' ? 'Shut' : 'No Shut'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'neighbors' && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left p-3 font-medium">Local Interface</th>
                <th className="text-left p-3 font-medium">Remote Device</th>
                <th className="text-left p-3 font-medium">Remote Interface</th>
                <th className="text-left p-3 font-medium">Platform</th>
                <th className="text-left p-3 font-medium">Protocol</th>
              </tr>
            </thead>
            <tbody>
              {neighbors?.map((n, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-3 font-mono">{n.local_interface}</td>
                  <td className="p-3 text-cyan-400">{n.remote_hostname}</td>
                  <td className="p-3 font-mono">{n.remote_interface}</td>
                  <td className="p-3 text-gray-400">{n.remote_platform}</td>
                  <td className="p-3 text-gray-500 uppercase text-xs">{n.discovery_protocol}</td>
                </tr>
              ))}
              {(!neighbors || neighbors.length === 0) && (
                <tr><td colSpan={5} className="p-6 text-center text-gray-500">No neighbors found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'cli' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={command}
              onChange={e => setCommand(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runCommand()}
              placeholder="Enter command (e.g., show ip interface brief)"
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none"
            />
            <button onClick={runCommand} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm">
              Execute
            </button>
          </div>
          {output && (
            <pre className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-sm font-mono text-green-400 overflow-auto max-h-[600px] whitespace-pre">
              {output}
            </pre>
          )}
        </div>
      )}

      {tab === 'snmp' && device.snmp_profile && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3 text-sm">
          <div><span className="text-gray-400 w-32 inline-block">SNMPv2:</span> {device.snmp_profile.v2_enabled ? 'Enabled' : 'Disabled'}</div>
          <div><span className="text-gray-400 w-32 inline-block">Community:</span> <span className="font-mono">{device.snmp_profile.v2_community}</span></div>
          <div><span className="text-gray-400 w-32 inline-block">SNMPv3:</span> {device.snmp_profile.v3_enabled ? 'Enabled' : 'Disabled'}</div>
        </div>
      )}

      {tab === 'connection' && device.connection_info && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4 text-sm">
          {device.connection_info.ssh && (
            <div>
              <h4 className="text-gray-300 font-medium mb-2">SSH</h4>
              <code className="bg-gray-800 px-3 py-2 rounded-lg block font-mono text-cyan-400">
                ssh admin@{device.connection_info.ssh.host} -p {device.connection_info.ssh.port}
              </code>
            </div>
          )}
          {device.connection_info.snmp && (
            <div>
              <h4 className="text-gray-300 font-medium mb-2">SNMP</h4>
              <code className="bg-gray-800 px-3 py-2 rounded-lg block font-mono text-cyan-400">
                snmpwalk -v2c -c public {device.connection_info.snmp.host}:{device.connection_info.snmp.port} 1.3.6.1.2.1.1
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

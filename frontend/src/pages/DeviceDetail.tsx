import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDevice, fetchInterfaces, fetchDeviceNeighbors, updateInterface, executeCommand, snmpWalk } from '../api/client'

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

  const [executing, setExecuting] = useState(false)

  const runCommand = async () => {
    if (!command.trim() || !id) return
    setExecuting(true)
    setOutput('')
    try {
      const result = await executeCommand(id, command)
      setOutput(result.output)
    } catch (e: any) {
      setOutput(`Error: ${e?.response?.data?.detail || e?.message || 'Command execution failed'}`)
    } finally {
      setExecuting(false)
    }
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
          {/* Command selector + execute */}
          <div className="flex gap-2">
            <select
              value={command}
              onChange={e => { setCommand(e.target.value); setOutput(''); }}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm font-mono focus:border-cyan-500 focus:outline-none"
            >
              <option value="">Select a command...</option>
              <optgroup label="Common">
                <option value="show version">show version</option>
                <option value="show ip interface brief">show ip interface brief</option>
                <option value="show interfaces">show interfaces</option>
                <option value="show cdp neighbors">show cdp neighbors</option>
                <option value="show cdp neighbors detail">show cdp neighbors detail</option>
                <option value="show lldp neighbors">show lldp neighbors</option>
                <option value="show inventory">show inventory</option>
              </optgroup>
              <optgroup label="Configuration">
                <option value="show running-config">show running-config</option>
                <option value="show startup-config">show startup-config</option>
              </optgroup>
              <optgroup label="Routing & Switching">
                <option value="show ip route">show ip route</option>
                <option value="show ip bgp summary">show ip bgp summary</option>
                <option value="show ip ospf neighbor">show ip ospf neighbor</option>
                <option value="show mac address-table">show mac address-table</option>
                <option value="show vlan brief">show vlan brief</option>
                <option value="show spanning-tree">show spanning-tree</option>
              </optgroup>
              <optgroup label="System">
                <option value="show logging">show logging</option>
                <option value="show processes cpu">show processes cpu</option>
                <option value="show environment">show environment</option>
              </optgroup>
            </select>
            <button
              onClick={runCommand}
              disabled={!command || executing}
              className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            >
              {executing ? 'Running...' : 'Execute'}
            </button>
          </div>

          {/* Output */}
          {output && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-mono">{device.hostname}# {command}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(output)}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-sm font-mono text-green-400 overflow-auto max-h-[600px] whitespace-pre">
                {output}
              </pre>
            </div>
          )}

          {!output && command && !executing && (
            <div className="text-center text-gray-500 text-sm py-12">
              Click Execute to run <span className="font-mono text-cyan-400">{command}</span> on {device.hostname}
            </div>
          )}
        </div>
      )}

      {tab === 'snmp' && <SNMPTab device={device} deviceId={id!} />}

      {tab === 'connection' && device.connection_info && (
        <div className="space-y-4">
          {/* Connect commands */}
          {/* Warning if not reachable */}
          {device.connection_info.ssh?.host === 'NOT_REACHABLE' && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-sm">
              <h3 className="font-medium text-yellow-400 mb-1">SSH/SNMP Not Reachable from Cloud</h3>
              <p className="text-yellow-300/70 text-xs leading-relaxed">
                This SNEP instance is running on Railway which only proxies HTTP traffic.
                SSH and SNMP ports are not exposed externally.
              </p>
              <p className="text-yellow-300/70 text-xs mt-2 leading-relaxed">
                <strong>To connect with tools:</strong> Clone the repo and run <code className="bg-yellow-900/30 px-1 rounded">docker compose up</code> locally.
                SSH/SNMP will be available on <code className="bg-yellow-900/30 px-1 rounded">127.0.0.1</code> with port-per-device mapping.
              </p>
              <div className="mt-3 space-y-1.5">
                <code className="bg-gray-800 px-3 py-2 rounded-lg block font-mono text-cyan-400 text-xs">
                  ssh admin@127.0.0.1 -p {device.connection_info.ssh?.port || 10000}
                </code>
                <code className="bg-gray-800 px-3 py-2 rounded-lg block font-mono text-cyan-400 text-xs">
                  snmpwalk -v2c -c {device.snmp_profile?.v2_community || 'public'} 127.0.0.1:{device.connection_info.snmp?.port || 20000} 1.3.6.1.2.1.1
                </code>
              </div>
            </div>
          )}

          {device.connection_info.ssh?.host !== 'NOT_REACHABLE' && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4 text-sm">
            <h3 className="font-medium text-gray-200">Connection Commands</h3>
            {device.connection_info.ssh && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-gray-400">SSH</span>
                  <button onClick={() => navigator.clipboard.writeText(`ssh admin@${device.connection_info.ssh.host} -p ${device.connection_info.ssh.port}`)} className="text-xs text-gray-500 hover:text-gray-300">Copy</button>
                </div>
                <code className="bg-gray-800 px-3 py-2.5 rounded-lg block font-mono text-cyan-400 text-xs">
                  ssh admin@{device.connection_info.ssh.host} -p {device.connection_info.ssh.port}
                </code>
              </div>
            )}
            {device.connection_info.snmp && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-gray-400">SNMP Walk</span>
                  <button onClick={() => navigator.clipboard.writeText(`snmpwalk -v2c -c ${device.snmp_profile?.v2_community || 'public'} ${device.connection_info.snmp.host}:${device.connection_info.snmp.port} 1.3.6.1.2.1.1`)} className="text-xs text-gray-500 hover:text-gray-300">Copy</button>
                </div>
                <code className="bg-gray-800 px-3 py-2.5 rounded-lg block font-mono text-cyan-400 text-xs">
                  snmpwalk -v2c -c {device.snmp_profile?.v2_community || 'public'} {device.connection_info.snmp.host}:{device.connection_info.snmp.port} 1.3.6.1.2.1.1
                </code>
              </div>
            )}
          </div>
          )}

          {/* Nornir inventory entry */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-200">Nornir Inventory Entry</h3>
              <button onClick={() => {
                const entry = `${device.hostname}:\n  hostname: "${device.connection_info.ssh?.host}"\n  port: ${device.connection_info.ssh?.port}\n  username: "admin"\n  password: "cisco123"\n  platform: "${device.platform?.name || 'cisco_ios'}"`
                navigator.clipboard.writeText(entry)
              }} className="text-xs text-gray-500 hover:text-gray-300">Copy YAML</button>
            </div>
            <pre className="bg-gray-800 px-3 py-2.5 rounded-lg font-mono text-xs text-yellow-300 whitespace-pre">{`${device.hostname}:
  hostname: "${device.connection_info.ssh?.host}"
  port: ${device.connection_info.ssh?.port}
  username: "admin"
  password: "cisco123"
  platform: "${device.platform?.name || 'cisco_ios'}"${device.connection_info.snmp ? `
  data:
    snmp_host: "${device.connection_info.snmp.host}"
    snmp_port: ${device.connection_info.snmp.port}
    snmp_community: "${device.snmp_profile?.v2_community || 'public'}"` : ''}`}</pre>
          </div>

          {/* Network details */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-sm">
            <h3 className="font-medium text-gray-200 mb-3">Network Details</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              {device.connection_info.ssh && (
                <>
                  <div>
                    <span className="text-gray-500 block">SSH Connect Address</span>
                    <span className="font-mono text-gray-200">{device.connection_info.ssh.host}:{device.connection_info.ssh.port}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">SSH Listen Address</span>
                    <span className="font-mono text-gray-400">{device.connection_info.ssh.listen_host}:{device.connection_info.ssh.listen_port}</span>
                  </div>
                </>
              )}
              {device.connection_info.snmp && (
                <>
                  <div>
                    <span className="text-gray-500 block">SNMP Connect Address</span>
                    <span className="font-mono text-gray-200">{device.connection_info.snmp.host}:{device.connection_info.snmp.port}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">SNMP Listen Address</span>
                    <span className="font-mono text-gray-400">{device.connection_info.snmp.listen_host}:{device.connection_info.snmp.listen_port}</span>
                  </div>
                </>
              )}
              <div>
                <span className="text-gray-500 block">Management IP</span>
                <span className="font-mono text-gray-200">{device.management_ip || 'unassigned'}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Platform</span>
                <span className="text-gray-200">{device.platform?.name}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


function SNMPTab({ device, deviceId }: { device: any; deviceId: string }) {
  const [subtree, setSubtree] = useState('system')
  const [outputFormat, setOutputFormat] = useState('named')
  const [walkOutput, setWalkOutput] = useState('')
  const [walking, setWalking] = useState(false)
  const [lineCount, setLineCount] = useState(0)

  const doWalk = async () => {
    setWalking(true)
    setWalkOutput('')
    try {
      const result = await snmpWalk(deviceId, subtree, outputFormat)
      setWalkOutput(result.output)
      setLineCount(result.line_count)
    } catch (e: any) {
      setWalkOutput(`Error: ${e?.response?.data?.detail || e?.message || 'SNMP walk failed'}`)
    } finally {
      setWalking(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* SNMP Profile info */}
      {device.snmp_profile && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-sm grid grid-cols-3 gap-4">
          <div>
            <span className="text-gray-500 text-xs block">SNMPv2</span>
            <span className={device.snmp_profile.v2_enabled ? 'text-green-400' : 'text-gray-500'}>
              {device.snmp_profile.v2_enabled ? 'Enabled' : 'Disabled'}
            </span>
            {device.snmp_profile.v2_community && (
              <span className="text-gray-400 ml-2 font-mono text-xs">({device.snmp_profile.v2_community})</span>
            )}
          </div>
          <div>
            <span className="text-gray-500 text-xs block">SNMPv3</span>
            <span className={device.snmp_profile.v3_enabled ? 'text-green-400' : 'text-gray-500'}>
              {device.snmp_profile.v3_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div>
            <span className="text-gray-500 text-xs block">Connection</span>
            {device.connection_info?.snmp && (
              <span className="font-mono text-xs text-gray-300">
                {device.connection_info.snmp.host}:{device.connection_info.snmp.port}
              </span>
            )}
          </div>
        </div>
      )}

      {/* SNMP Walk controls */}
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <label className="text-xs text-gray-400 block mb-1">MIB Subtree</label>
          <select
            value={subtree}
            onChange={e => { setSubtree(e.target.value); setWalkOutput(''); }}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-sm font-mono focus:border-cyan-500 focus:outline-none"
          >
            <optgroup label="Common Walks">
              <option value="system">system (sysDescr, sysName, sysUpTime, ...)</option>
              <option value="ifTable">IF-MIB::ifTable (ifIndex, ifDescr, ifType, ifSpeed, ifStatus, counters)</option>
              <option value="ifXTable">IF-MIB::ifXTable (ifName, ifHCInOctets, ifHighSpeed, ifAlias)</option>
              <option value="interfaces">interfaces (ifNumber + ifTable)</option>
            </optgroup>
            <optgroup label="Full Walk">
              <option value="all">All MIBs (system + IF-MIB)</option>
            </optgroup>
            <optgroup label="Numeric OID">
              <option value="1.3.6.1.2.1.1">1.3.6.1.2.1.1 (system)</option>
              <option value="1.3.6.1.2.1.2.2">1.3.6.1.2.1.2.2 (ifTable)</option>
              <option value="1.3.6.1.2.1.31.1.1">1.3.6.1.2.1.31.1.1 (ifXTable)</option>
            </optgroup>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Format</label>
          <select
            value={outputFormat}
            onChange={e => setOutputFormat(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none"
          >
            <option value="named">MIB Names</option>
            <option value="numeric">Numeric OIDs</option>
          </select>
        </div>
        <button
          onClick={doWalk}
          disabled={walking}
          className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
        >
          {walking ? 'Walking...' : 'SNMP Walk'}
        </button>
      </div>

      {/* Walk output */}
      {walkOutput && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400 font-mono">
              $ snmpwalk -v2c -c {device.snmp_profile?.v2_community || 'public'} {device.hostname} {subtree}
              <span className="text-gray-600 ml-2">({lineCount} OIDs)</span>
            </span>
            <button
              onClick={() => navigator.clipboard.writeText(walkOutput)}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Copy
            </button>
          </div>
          <pre className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs font-mono text-green-400 overflow-auto max-h-[600px] whitespace-pre leading-relaxed">
            {walkOutput}
          </pre>
        </div>
      )}

      {!walkOutput && !walking && (
        <div className="text-center text-gray-500 text-sm py-12">
          Select a MIB subtree and click SNMP Walk to preview the OID output
        </div>
      )}
    </div>
  )
}

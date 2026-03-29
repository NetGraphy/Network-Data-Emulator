import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchNetworkingSettings, updateConnectAddress } from '../api/client'

export default function Settings() {
  const queryClient = useQueryClient()
  const [addressInput, setAddressInput] = useState('')
  const { data: settings, isLoading } = useQuery({
    queryKey: ['networking-settings'],
    queryFn: fetchNetworkingSettings,
  })

  const updateMutation = useMutation({
    mutationFn: (addr: string) => updateConnectAddress(addr),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networking-settings'] })
    },
  })

  const env = settings?.detected_environment
  const config = settings?.current_config
  const methods = settings?.connection_methods || []

  if (isLoading) return <div className="p-6 text-gray-500">Loading...</div>

  return (
    <div className="p-6 max-w-5xl">
      <h2 className="text-xl font-semibold mb-1">Settings</h2>
      <p className="text-sm text-gray-400 mb-6">Configure how external tools connect to emulated devices</p>

      {/* Environment Detection */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-200">Detected Environment</h3>
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
            env?.type?.includes('docker') ? 'bg-blue-500/10 text-blue-400' :
            env?.type?.includes('railway') ? 'bg-purple-500/10 text-purple-400' :
            env?.type?.includes('native') ? 'bg-green-500/10 text-green-400' :
            'bg-gray-500/10 text-gray-400'
          }`}>
            {env?.type?.replace(/_/g, ' ')}
          </span>
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">{env?.note}</p>

        <div className="grid grid-cols-3 gap-4 mt-4 text-xs">
          <div>
            <span className="text-gray-500 block">Listen Address</span>
            <span className="font-mono text-gray-300">{env?.listen_address}</span>
          </div>
          <div>
            <span className="text-gray-500 block">Connect Address</span>
            <span className="font-mono text-gray-300">{config?.connect_address}</span>
          </div>
          <div>
            <span className="text-gray-500 block">Devices</span>
            <span className="text-gray-300">{config?.device_count}</span>
          </div>
        </div>
      </div>

      {/* Connect Address Configuration */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mb-6">
        <h3 className="font-medium text-gray-200 mb-1">Connect Address</h3>
        <p className="text-xs text-gray-400 mb-4">
          This is the IP or hostname that external tools (Nornir, Ansible, snmpwalk) use to reach the emulated devices.
          Leave empty to auto-detect, or enter your machine's public/lab IP.
        </p>

        <div className="flex gap-3 mb-4">
          <input
            type="text"
            value={addressInput}
            onChange={e => setAddressInput(e.target.value)}
            placeholder={config?.connect_address === 'NOT_REACHABLE' ? '192.168.1.100 or lab.example.com' : config?.connect_address}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm font-mono focus:border-cyan-500 focus:outline-none"
          />
          <button
            onClick={() => updateMutation.mutate(addressInput)}
            disabled={updateMutation.isPending}
            className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            {updateMutation.isPending ? 'Saving...' : 'Apply'}
          </button>
          <button
            onClick={() => { setAddressInput(''); updateMutation.mutate(''); }}
            className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-400 transition-colors"
          >
            Auto-detect
          </button>
        </div>

        {updateMutation.isSuccess && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-xs text-green-400">
            Updated. All devices now connectable at: <span className="font-mono font-bold">{(updateMutation.data as any)?.connect_address}</span>
          </div>
        )}

        {/* Quick presets */}
        <div className="flex flex-wrap gap-2 mt-3">
          <span className="text-xs text-gray-500 py-1">Quick set:</span>
          {['127.0.0.1', '192.168.1.100', '10.0.0.100', 'localhost'].map(addr => (
            <button
              key={addr}
              onClick={() => { setAddressInput(addr); updateMutation.mutate(addr); }}
              className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs font-mono text-gray-400 hover:text-gray-200 transition-colors"
            >
              {addr}
            </button>
          ))}
        </div>
      </div>

      {/* Connection Methods Documentation */}
      <div className="mb-6">
        <h3 className="font-medium text-gray-200 mb-4">Connection Methods</h3>
        <div className="grid gap-4">
          {methods.map((method: any) => (
            <div key={method.id} className={`bg-gray-900 rounded-xl border p-5 ${
              method.available ? 'border-gray-800' : 'border-gray-800/50 opacity-60'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-200">{method.name}</h4>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  method.available ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-500'
                }`}>
                  {method.available ? 'Available' : 'Not available'}
                </span>
              </div>
              <p className="text-xs text-gray-400 mb-3">{method.description}</p>
              <p className="text-[10px] text-gray-500 mb-3">Best for: {method.when_to_use}</p>

              {/* Example commands */}
              <div className="space-y-2 mb-3">
                <div>
                  <span className="text-[10px] text-gray-500 block mb-1">SSH command:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-gray-800 px-3 py-1.5 rounded flex-1 font-mono text-xs text-cyan-400">
                      {method.example_ssh}
                    </code>
                    <button
                      onClick={() => navigator.clipboard.writeText(method.example_ssh)}
                      className="text-[10px] text-gray-500 hover:text-gray-300 shrink-0"
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block mb-1">Nornir inventory:</span>
                  <pre className="bg-gray-800 px-3 py-2 rounded font-mono text-[11px] text-yellow-300 whitespace-pre">{Object.entries(method.example_nornir || {}).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('\n')}</pre>
                </div>
                {method.setup_required && (
                  <div className="bg-yellow-500/5 border border-yellow-500/10 rounded p-2">
                    <span className="text-[10px] text-yellow-400">Setup required: </span>
                    <code className="text-[10px] font-mono text-yellow-300">{method.setup_required}</code>
                  </div>
                )}
              </div>

              {/* Pros / Cons */}
              <div className="grid grid-cols-2 gap-3 text-[10px]">
                <div>
                  {method.pros?.map((p: string, i: number) => (
                    <div key={i} className="text-green-400/70 flex gap-1"><span>+</span> {p}</div>
                  ))}
                </div>
                <div>
                  {method.cons?.map((c: string, i: number) => (
                    <div key={i} className="text-red-400/50 flex gap-1"><span>-</span> {c}</div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Setup Guide */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 className="font-medium text-gray-200 mb-4">Setup Guide</h3>
        <div className="space-y-4 text-sm">
          <Step n={1} title="Clone and start">
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300 mb-1">git clone git@github.com:NetGraphy/Network-Data-Emulator.git</code>
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300 mb-1">cd Network-Data-Emulator && cp .env.example .env</code>
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300">docker compose up -d</code>
          </Step>
          <Step n={2} title="Initialize database">
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300">make migrate && make seed</code>
            <p className="text-xs text-gray-500 mt-1">Creates 5 Cisco IOS devices with interfaces, links, and SNMP profiles.</p>
          </Step>
          <Step n={3} title="Configure connect address">
            <p className="text-xs text-gray-400">
              Open <span className="text-cyan-400">http://localhost:3000/settings</span> and set your connect address.
              For local testing: <span className="font-mono text-gray-300">127.0.0.1</span>.
              For lab access from other machines: your machine's IP (e.g., <span className="font-mono text-gray-300">192.168.1.100</span>).
            </p>
          </Step>
          <Step n={4} title="Test SSH connectivity">
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300 mb-1">ssh admin@127.0.0.1 -p 10000</code>
            <p className="text-xs text-gray-500 mt-1">Password: <span className="font-mono text-gray-300">cisco123</span>. Try: show version, show ip interface brief, show cdp neighbors</p>
          </Step>
          <Step n={5} title="Test SNMP">
            <code className="block bg-gray-800 px-3 py-2 rounded font-mono text-xs text-gray-300">snmpwalk -v2c -c public 127.0.0.1:20000 1.3.6.1.2.1.1</code>
          </Step>
          <Step n={6} title="Run Nornir against it">
            <p className="text-xs text-gray-400">
              Export inventory from <span className="text-cyan-400">/api/v1/export/nornir</span>, save as hosts.yaml, and run your Nornir scripts.
            </p>
          </Step>
        </div>
      </div>
    </div>
  )
}


function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <div className="w-6 h-6 rounded-full bg-cyan-600/20 text-cyan-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
        {n}
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-medium text-gray-200 mb-1.5">{title}</h4>
        {children}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchConfigSources, createConfigSource, deleteConfigSource, syncConfigSource } from '../api/client'

const PATH_PRESETS = [
  { label: 'Oxidized', template: 'configs/{{ device.hostname }}', ext: '' },
  { label: 'RANCID', template: 'configs/router/{{ device.hostname }}', ext: '' },
  { label: 'Flat (.cfg)', template: '{{ device.hostname }}.cfg', ext: '.cfg' },
  { label: 'Flat (.conf)', template: '{{ device.hostname }}.conf', ext: '.conf' },
  { label: 'By site', template: '{{ device.tags.site }}/{{ device.hostname }}.cfg', ext: '.cfg' },
  { label: 'By platform', template: '{{ platform.name }}/{{ device.hostname }}.cfg', ext: '.cfg' },
]

export default function ConfigSources() {
  const queryClient = useQueryClient()
  const { data: sources, isLoading } = useQuery({ queryKey: ['config-sources'], queryFn: fetchConfigSources })

  const [form, setForm] = useState({
    name: '', repo_url: '', branch: 'main', auth_token: '',
    path_template: '{{ device.hostname }}.cfg', file_extension: '.cfg', description: '',
  })
  const [syncResult, setSyncResult] = useState<any>(null)

  const createMut = useMutation({
    mutationFn: () => createConfigSource(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-sources'] })
      setForm({ ...form, name: '', repo_url: '', auth_token: '', description: '' })
    },
  })
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteConfigSource(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config-sources'] }),
  })
  const syncMut = useMutation({
    mutationFn: (id: string) => syncConfigSource(id),
    onSuccess: (data) => {
      setSyncResult(data)
      queryClient.invalidateQueries({ queryKey: ['config-sources'] })
    },
  })

  return (
    <div className="p-6 max-w-4xl">
      <h2 className="text-xl font-semibold mb-1">Config Sources</h2>
      <p className="text-sm text-gray-400 mb-6">
        Import device configs from Git repos. Matched configs power <code className="text-cyan-400">show running-config</code> in SSH sessions.
      </p>

      {/* Existing sources */}
      <div className="space-y-3 mb-6">
        {sources?.map((s: any) => (
          <div key={s.id} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{s.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{s.source_type}</span>
                {s.has_auth && <span className="text-[10px] text-green-400">auth</span>}
                {s.last_sync_status && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    s.last_sync_status === 'success' ? 'bg-green-500/10 text-green-400' :
                    s.last_sync_status === 'failed' ? 'bg-red-500/10 text-red-400' : 'bg-yellow-500/10 text-yellow-400'
                  }`}>{s.last_sync_status}</span>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={() => syncMut.mutate(s.id)} disabled={syncMut.isPending}
                  className="px-3 py-1 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded text-xs font-medium">
                  {syncMut.isPending ? 'Syncing...' : 'Sync Now'}
                </button>
                <button onClick={() => deleteMut.mutate(s.id)} className="px-3 py-1 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded text-xs">
                  Delete
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-500 space-y-0.5">
              <div className="font-mono">{s.repo_url} ({s.branch || 'main'})</div>
              <div>Path template: <code className="text-cyan-400">{s.path_template}</code></div>
              {s.last_sync_message && <div className="text-gray-400">{s.last_sync_message}</div>}
              {s.last_sync_at && <div>Last sync: {new Date(s.last_sync_at).toLocaleString()}</div>}
            </div>
          </div>
        ))}
        {!isLoading && (!sources || sources.length === 0) && (
          <div className="text-gray-500 text-sm">No config sources configured. Add one below.</div>
        )}
      </div>

      {/* Sync result */}
      {syncResult && (
        <div className={`mb-6 p-4 rounded-xl border text-sm ${syncResult.error ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
          {syncResult.error ? <span>Sync failed: {syncResult.error}</span> : (
            <div>
              <div className="font-medium">Sync Complete</div>
              <div>Files found: {syncResult.files_found} | Matched: {syncResult.matched} | Updated: {syncResult.updated} | Unmatched: {syncResult.unmatched}</div>
              {syncResult.errors?.length > 0 && <div className="text-yellow-400 mt-1">Errors: {syncResult.errors.join(', ')}</div>}
            </div>
          )}
        </div>
      )}

      {/* Add new source */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-4">
        <h3 className="font-medium text-gray-200">Add Config Source</h3>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Name</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Production Backups"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Branch</label>
            <input value={form.branch} onChange={e => setForm({ ...form, branch: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Git Repository URL</label>
          <input value={form.repo_url} onChange={e => setForm({ ...form, repo_url: e.target.value })} placeholder="https://github.com/org/network-configs.git"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none" />
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Auth Token (for private repos)</label>
          <input type="password" value={form.auth_token} onChange={e => setForm({ ...form, auth_token: e.target.value })} placeholder="ghp_..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">
            Path Template <span className="text-gray-600">(Jinja2 — how to find each device's config file)</span>
          </label>
          <input value={form.path_template} onChange={e => setForm({ ...form, path_template: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none" />
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className="text-[10px] text-gray-500 py-1">Presets:</span>
            {PATH_PRESETS.map(p => (
              <button key={p.label} onClick={() => setForm({ ...form, path_template: p.template, file_extension: p.ext })}
                className="text-[10px] px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200 font-mono">
                {p.label}: {p.template}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Production config backups from Oxidized"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
        </div>

        <button onClick={() => createMut.mutate()} disabled={!form.name || !form.repo_url}
          className="px-5 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium">
          Add Config Source
        </button>
      </div>

      {/* Documentation */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mt-6">
        <h3 className="font-medium text-gray-200 mb-3">How It Works</h3>
        <div className="text-xs text-gray-400 space-y-2 leading-relaxed">
          <p>1. Add a Git repo containing device config files (Oxidized, RANCID, or any backup system).</p>
          <p>2. Configure the <strong>path template</strong> to match your repo's file naming convention. Available variables:</p>
          <div className="grid grid-cols-2 gap-1 ml-4 font-mono text-[10px] text-cyan-400/70">
            <span>{'{{ device.hostname }}'}</span><span className="text-gray-500">core-rtr-01</span>
            <span>{'{{ device.management_ip }}'}</span><span className="text-gray-500">10.1.1.1</span>
            <span>{'{{ device.tags.site }}'}</span><span className="text-gray-500">dc-east</span>
            <span>{'{{ device.tags.role }}'}</span><span className="text-gray-500">core</span>
            <span>{'{{ platform.name }}'}</span><span className="text-gray-500">cisco_ios</span>
            <span>{'{{ model.name }}'}</span><span className="text-gray-500">catalyst_9300_48t</span>
          </div>
          <p>3. Click <strong>Sync</strong> — SNEP clones the repo, renders the path for each device, and matches files.</p>
          <p>4. SSH into any matched device and run <code className="text-cyan-400">show running-config</code> — returns the real config.</p>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { importNetBox, importNautobot, importNetGraphy } from '../api/client'

type Source = 'netbox' | 'nautobot' | 'netgraphy'

export default function ImportWizard() {
  const [source, setSource] = useState<Source>('netbox')
  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  const [siteFilter, setSiteFilter] = useState('')
  const [neo4jUri, setNeo4jUri] = useState('bolt://localhost:7687')
  const [neo4jUser, setNeo4jUser] = useState('neo4j')
  const [neo4jPassword, setNeo4jPassword] = useState('netgraphy')
  const [hostnameFilter, setHostnameFilter] = useState('')
  const [result, setResult] = useState<any>(null)

  const importMutation = useMutation({
    mutationFn: async () => {
      if (source === 'netbox') {
        return importNetBox({ url, token, site_filter: siteFilter || null })
      } else if (source === 'nautobot') {
        return importNautobot({ url, token, site_filter: siteFilter || null })
      } else {
        return importNetGraphy({
          neo4j_uri: neo4jUri,
          neo4j_user: neo4jUser,
          neo4j_password: neo4jPassword,
          hostname_filter: hostnameFilter || null,
        })
      }
    },
    onSuccess: (data) => setResult(data),
  })

  const sources: { key: Source; label: string; description: string }[] = [
    { key: 'netbox', label: 'NetBox', description: 'Import via GraphQL API' },
    { key: 'nautobot', label: 'Nautobot', description: 'Import via GraphQL API' },
    { key: 'netgraphy', label: 'NetGraphy', description: 'Import directly from Neo4j' },
  ]

  return (
    <div className="p-6 max-w-3xl">
      <h2 className="text-xl font-semibold mb-2">Import Devices</h2>
      <p className="text-sm text-gray-400 mb-6">
        Pull devices, interfaces, and cable connections from an external source.
      </p>

      {/* Source selector */}
      <div className="flex gap-3 mb-6">
        {sources.map(s => (
          <button
            key={s.key}
            onClick={() => { setSource(s.key); setResult(null) }}
            className={`flex-1 p-4 rounded-xl border text-left transition-colors ${
              source === s.key
                ? 'border-cyan-500 bg-cyan-500/5'
                : 'border-gray-800 bg-gray-900 hover:border-gray-700'
            }`}
          >
            <div className="font-medium text-sm">{s.label}</div>
            <div className="text-xs text-gray-500 mt-1">{s.description}</div>
          </button>
        ))}
      </div>

      {/* Config form */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4 mb-6">
        {(source === 'netbox' || source === 'nautobot') && (
          <>
            <div>
              <label className="text-xs text-gray-400 block mb-1">URL</label>
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder={source === 'netbox' ? 'https://netbox.example.com' : 'https://nautobot.example.com'}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">API Token</label>
              <input
                type="password"
                value={token}
                onChange={e => setToken(e.target.value)}
                placeholder="Enter API token"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Site Filter (optional)</label>
              <input
                type="text"
                value={siteFilter}
                onChange={e => setSiteFilter(e.target.value)}
                placeholder="e.g., dc-east"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </>
        )}

        {source === 'netgraphy' && (
          <>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Neo4j URI</label>
              <input
                type="text"
                value={neo4jUri}
                onChange={e => setNeo4jUri(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Username</label>
                <input
                  type="text"
                  value={neo4jUser}
                  onChange={e => setNeo4jUser(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Password</label>
                <input
                  type="password"
                  value={neo4jPassword}
                  onChange={e => setNeo4jPassword(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Hostname Filter (optional)</label>
              <input
                type="text"
                value={hostnameFilter}
                onChange={e => setHostnameFilter(e.target.value)}
                placeholder="e.g., nyc (matches all hostnames containing 'nyc')"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </>
        )}
      </div>

      {/* Import button */}
      <button
        onClick={() => importMutation.mutate()}
        disabled={importMutation.isPending}
        className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
      >
        {importMutation.isPending ? 'Importing...' : `Import from ${sources.find(s => s.key === source)?.label}`}
      </button>

      {/* Result */}
      {importMutation.isError && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
          Import failed: {(importMutation.error as any)?.response?.data?.detail || 'Unknown error'}
        </div>
      )}

      {result && (
        <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-xl text-sm text-green-400">
          <div className="font-medium mb-2">Import Complete</div>
          <div>Devices: {result.imported_devices}</div>
          <div>Interfaces: {result.imported_interfaces}</div>
          <div>Links: {result.imported_links}</div>
          {result.skipped?.length > 0 && (
            <div className="mt-2 text-yellow-400">Skipped: {result.skipped.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  )
}

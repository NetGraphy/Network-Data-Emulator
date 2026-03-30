import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import {
  fetchDataSources, createDataSource, deleteDataSource,
  fetchQueryMappings, fetchQueryMapping,
  executeQueryAPI, previewImportMapping, runQueryImport,
} from '../api/client'

type Tab = 'query' | 'sources' | 'mappings'

export default function QueryExplorer() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('query')
  const [sourceId, setSourceId] = useState('')
  const [query, setQuery] = useState('')
  const [mappingId, setMappingId] = useState('')
  const [results, setResults] = useState<any>(null)
  const [preview, setPreview] = useState<any>(null)
  const [importResult, setImportResult] = useState<any>(null)
  const [running, setRunning] = useState(false)

  const { data: sources } = useQuery({ queryKey: ['data-sources'], queryFn: fetchDataSources })
  const { data: mappings } = useQuery({ queryKey: ['query-mappings'], queryFn: fetchQueryMappings })
  const { data: selectedMapping } = useQuery({
    queryKey: ['query-mapping', mappingId],
    queryFn: () => fetchQueryMapping(mappingId),
    enabled: !!mappingId,
  })

  const selectedSource = sources?.find((s: any) => s.id === sourceId)
  const editorLanguage = selectedSource?.query_language === 'cypher' ? 'plaintext' : 'graphql'

  // Load query from mapping
  const handleMappingSelect = (id: string) => {
    setMappingId(id)
    const m = mappings?.find((mm: any) => mm.id === id)
    if (m && !query) {
      // Load mapping to get query
      fetchQueryMapping(id).then((detail: any) => {
        if (detail.query) setQuery(detail.query)
      })
    }
  }

  const handleRunQuery = async () => {
    if (!sourceId || !query) return
    setRunning(true)
    setResults(null)
    setPreview(null)
    setImportResult(null)
    try {
      const r = await executeQueryAPI(sourceId, query)
      setResults(r)
    } catch (e: any) {
      setResults({ status: 'error', error: e?.response?.data?.detail || e?.message || 'Query failed' })
    } finally {
      setRunning(false)
    }
  }

  const handlePreview = async () => {
    if (!results?.data || !selectedMapping) return
    try {
      const p = await previewImportMapping({
        results: results.data,
        mapping_id: mappingId,
        result_path: selectedMapping.result_path,
      })
      setPreview(p)
    } catch (e: any) {
      setPreview({ error: e?.message || 'Preview failed' })
    }
  }

  const handleImport = async () => {
    if (!sourceId || !query || !mappingId) return
    setRunning(true)
    try {
      const r = await runQueryImport({
        source_id: sourceId,
        query,
        mapping_id: mappingId,
      })
      setImportResult(r)
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      queryClient.invalidateQueries({ queryKey: ['topology'] })
    } catch (e: any) {
      setImportResult({ error: e?.response?.data?.detail || e?.message })
    } finally {
      setRunning(false)
    }
  }

  const tabs: { key: Tab; label: string; desc: string }[] = [
    { key: 'query', label: 'Query & Import', desc: 'Write queries, preview, and import inventory' },
    { key: 'sources', label: 'Data Sources', desc: 'Configure NetBox, Nautobot, or NetGraphy connections' },
    { key: 'mappings', label: 'Field Mappings', desc: 'Jinja2 templates that transform results into SNEP devices' },
  ]

  return (
    <div className="p-6 h-full flex flex-col">
      <h2 className="text-xl font-semibold mb-4">Query Explorer</h2>

      {/* Prominent horizontal tabs */}
      <div className="flex gap-2 mb-5">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex-1 p-3 rounded-xl border text-left transition-colors ${
              tab === t.key ? 'border-cyan-500 bg-cyan-500/10' : 'border-gray-800 bg-gray-900 hover:border-gray-700'
            }`}>
            <div className={`text-sm font-medium ${tab === t.key ? 'text-cyan-400' : 'text-gray-300'}`}>{t.label}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">{t.desc}</div>
          </button>
        ))}
      </div>

      {tab === 'query' && (
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Left: Query */}
          <div className="w-1/2 flex flex-col gap-3">
            <div className="flex gap-2">
              <select value={sourceId} onChange={e => setSourceId(e.target.value)}
                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                <option value="">Select data source...</option>
                {sources?.map((s: any) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.source_type})</option>
                ))}
              </select>
              <select value={mappingId} onChange={e => handleMappingSelect(e.target.value)}
                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                <option value="">Select mapping...</option>
                {mappings?.filter((m: any) => !sourceId || !selectedSource || m.source_type === selectedSource.source_type || m.source_type === 'generic')
                  .map((m: any) => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
              </select>
            </div>

            <div className="flex-1 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden flex flex-col min-h-[200px]">
              <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {selectedSource ? `${selectedSource.query_language.toUpperCase()} Query` : 'Select a data source'}
                </span>
                <button onClick={handleRunQuery} disabled={!sourceId || !query || running}
                  className="px-4 py-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-xs font-medium">
                  {running ? 'Running...' : 'Run Query'}
                </button>
              </div>
              <div className="flex-1">
                <Editor height="100%" language={editorLanguage} theme="vs-dark"
                  value={query} onChange={v => setQuery(v || '')}
                  options={{ minimap: { enabled: false }, fontSize: 12, lineNumbers: 'on', scrollBeyondLastLine: false, wordWrap: 'on', automaticLayout: true }} />
              </div>
            </div>

            {/* Action buttons */}
            {results?.status === 'success' && (
              <div className="flex gap-2">
                {mappingId && (
                  <>
                    <button onClick={handlePreview} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-medium">
                      Preview Mapping
                    </button>
                    <button onClick={handleImport} disabled={running}
                      className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-xs font-medium">
                      {running ? 'Importing...' : 'Import to SNEP'}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Right: Results */}
          <div className="w-1/2 flex flex-col gap-3 overflow-auto">
            {importResult && (
              <div className={`p-4 rounded-xl border text-sm ${importResult.error ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
                {importResult.error ? (
                  <span>Import failed: {importResult.error}</span>
                ) : (
                  <div>
                    <div className="font-medium mb-1">Import Complete</div>
                    <div>Devices: {importResult.imported_devices} | Interfaces: {importResult.imported_interfaces}</div>
                    {importResult.skipped?.length > 0 && <div className="text-yellow-400 mt-1">Skipped: {importResult.skipped.join(', ')}</div>}
                  </div>
                )}
              </div>
            )}

            {preview && !preview.error && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h3 className="text-sm font-medium text-gray-200 mb-2">Mapping Preview ({preview.count} devices)</h3>
                <pre className="text-xs font-mono text-yellow-300 overflow-auto max-h-[300px] whitespace-pre-wrap">
                  {JSON.stringify(preview.preview?.slice(0, 3), null, 2)}
                </pre>
                {preview.count > 3 && <p className="text-[10px] text-gray-500 mt-2">...and {preview.count - 3} more</p>}
              </div>
            )}

            {results && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex-1 overflow-auto">
                <h3 className="text-sm font-medium text-gray-200 mb-2">
                  {results.status === 'success' ? 'Query Results' : 'Error'}
                </h3>
                {results.status === 'error' ? (
                  <p className="text-red-400 text-xs">{results.error}</p>
                ) : (
                  <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap max-h-[500px] overflow-auto">
                    {JSON.stringify(results.data, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {!results && (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-sm text-center px-8">
                Select a data source and run a query.
                <br />Use a mapping template to transform results into SNEP devices.
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'sources' && <DataSourcesPanel />}
      {tab === 'mappings' && <MappingsPanel />}
    </div>
  )
}


function DataSourcesPanel() {
  const queryClient = useQueryClient()
  const { data: sources } = useQuery({ queryKey: ['data-sources'], queryFn: fetchDataSources })
  const [form, setForm] = useState({ name: '', source_type: 'netbox', url: '', auth_token: '', graphql_path: '/graphql/', query_language: 'graphql', description: '' })

  const createMut = useMutation({
    mutationFn: () => createDataSource(form),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['data-sources'] }); setForm({ ...form, name: '', url: '', auth_token: '' }); },
  })
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteDataSource(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-sources'] }),
  })

  const handleTypeChange = (type: string) => {
    const defaults: Record<string, any> = {
      netbox: { query_language: 'graphql', graphql_path: '/graphql/' },
      nautobot: { query_language: 'graphql', graphql_path: '/api/graphql/' },
      netgraphy: { query_language: 'cypher', graphql_path: '/api/v1/query/cypher' },
    }
    setForm({ ...form, source_type: type, ...(defaults[type] || {}) })
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h3 className="text-sm font-medium text-gray-200">Data Sources</h3>

      {/* Existing */}
      <div className="space-y-2">
        {sources?.map((s: any) => (
          <div key={s.id} className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{s.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{s.source_type}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{s.query_language}</span>
                {s.has_auth && <span className="text-[10px] text-green-400">authenticated</span>}
              </div>
              <p className="text-xs text-gray-500 font-mono mt-0.5">{s.url}</p>
            </div>
            <button onClick={() => deleteMut.mutate(s.id)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
          </div>
        ))}
      </div>

      {/* Add new */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
        <h4 className="text-xs font-medium text-gray-300">Add Data Source</h4>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-gray-500 block mb-0.5">Name</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Production NetBox"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs focus:border-cyan-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 block mb-0.5">Type</label>
            <select value={form.source_type} onChange={e => handleTypeChange(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs focus:border-cyan-500 focus:outline-none">
              <option value="netbox">NetBox</option>
              <option value="nautobot">Nautobot</option>
              <option value="netgraphy">NetGraphy</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-gray-500 block mb-0.5">URL</label>
            <input value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} placeholder="https://netbox.example.com"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs font-mono focus:border-cyan-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 block mb-0.5">API Token</label>
            <input type="password" value={form.auth_token} onChange={e => setForm({ ...form, auth_token: e.target.value })} placeholder="Token / JWT"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs focus:border-cyan-500 focus:outline-none" />
          </div>
        </div>
        <button onClick={() => createMut.mutate()} disabled={!form.name || !form.url}
          className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded text-xs font-medium">Add Source</button>
      </div>
    </div>
  )
}


function MappingsPanel() {
  const { data: mappings } = useQuery({ queryKey: ['query-mappings'], queryFn: fetchQueryMappings })
  const [selectedId, setSelectedId] = useState('')
  const { data: detail } = useQuery({
    queryKey: ['query-mapping', selectedId], queryFn: () => fetchQueryMapping(selectedId), enabled: !!selectedId,
  })

  return (
    <div className="flex gap-4 flex-1 min-h-0">
      <div className="w-64 space-y-1.5 overflow-auto">
        <h3 className="text-sm font-medium text-gray-200 mb-2">Import Mappings</h3>
        {mappings?.map((m: any) => (
          <button key={m.id} onClick={() => setSelectedId(m.id)}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${selectedId === m.id ? 'border-cyan-500 bg-cyan-500/5' : 'border-gray-800 bg-gray-900 hover:border-gray-700'}`}>
            <div className="flex items-center gap-1.5">
              <span className="text-sm">{m.name}</span>
              {m.is_builtin && <span className="text-[9px] text-blue-400">built-in</span>}
            </div>
            <span className="text-[10px] text-gray-500">{m.source_type}</span>
          </button>
        ))}
      </div>

      {detail ? (
        <div className="flex-1 overflow-auto space-y-3">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <h3 className="font-medium text-sm mb-1">{detail.name}</h3>
            <p className="text-xs text-gray-400">{detail.description}</p>
            <span className="text-[10px] text-gray-500">Result path: <code className="text-gray-300">{detail.result_path}</code></span>
          </div>
          {detail.query && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-3 py-1.5 border-b border-gray-800 text-xs text-gray-400">Default Query</div>
              <div className="h-[200px]">
                <Editor height="100%" language={detail.source_type === 'netgraphy' ? 'plaintext' : 'graphql'} theme="vs-dark"
                  value={detail.query} options={{ readOnly: true, minimap: { enabled: false }, fontSize: 11, automaticLayout: true }} />
              </div>
            </div>
          )}
          {detail.device_template && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-3 py-1.5 border-b border-gray-800 text-xs text-gray-400">Device Mapping Template (Jinja2 → YAML)</div>
              <div className="h-[250px]">
                <Editor height="100%" language="yaml" theme="vs-dark"
                  value={detail.device_template} options={{ readOnly: detail.is_builtin, minimap: { enabled: false }, fontSize: 11, automaticLayout: true }} />
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
          Select a mapping to view its query and field templates
        </div>
      )}
    </div>
  )
}

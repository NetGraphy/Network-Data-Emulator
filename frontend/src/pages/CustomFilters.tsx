import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import {
  fetchCustomFilters, createCustomFilter, updateCustomFilter,
  deleteCustomFilter, testCustomFilter, fetchAllowedModules,
  addAllowedModule, fetchRegisteredFilters,
} from '../api/client'

const CATEGORIES = ['formatting', 'calculation', 'network', 'conversion', 'general']

export default function CustomFilters() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isNew, setIsNew] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [code, setCode] = useState('return str(value)')
  const [signature, setSignature] = useState('value')
  const [testInput, setTestInput] = useState('[100]')
  const [testExpected, setTestExpected] = useState('')
  const [category, setCategory] = useState('general')

  // Test result
  const [testResult, setTestResult] = useState<any>(null)

  const { data: filters } = useQuery({ queryKey: ['custom-filters'], queryFn: fetchCustomFilters })
  const { data: modules } = useQuery({ queryKey: ['allowed-modules'], queryFn: fetchAllowedModules })
  const { data: registered } = useQuery({ queryKey: ['registered-filters'], queryFn: fetchRegisteredFilters })
  const [newModule, setNewModule] = useState('')

  const selectFilter = (f: any) => {
    setSelectedId(f.id)
    setIsNew(false)
    setName(f.name)
    setDescription(f.description)
    setCode(f.code)
    setSignature(f.signature)
    setTestInput(f.test_input || '[100]')
    setTestExpected(f.test_expected || '')
    setCategory(f.category)
    setTestResult(null)
  }

  const startNew = () => {
    setSelectedId(null)
    setIsNew(true)
    setName('')
    setDescription('')
    setCode('return str(value)')
    setSignature('value')
    setTestInput('[100]')
    setTestExpected('')
    setCategory('general')
    setTestResult(null)
  }

  const saveMutation = useMutation({
    mutationFn: (data: any) => isNew ? createCustomFilter(data) : updateCustomFilter(selectedId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-filters'] })
      queryClient.invalidateQueries({ queryKey: ['registered-filters'] })
      if (isNew) setIsNew(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteCustomFilter(selectedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-filters'] })
      setSelectedId(null)
    },
  })

  const addModuleMutation = useMutation({
    mutationFn: (mod: string) => addAllowedModule(mod),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['allowed-modules'] }); setNewModule(''); },
  })

  const handleSave = () => {
    saveMutation.mutate({ name, description, code, signature, test_input: testInput, test_expected: testExpected, category })
  }

  const handleTest = async () => {
    try {
      const args = JSON.parse(testInput)
      const result = await testCustomFilter({ name: name || 'test', code, signature, test_args: args })
      setTestResult(result)
    } catch (e: any) {
      setTestResult({ output: null, error: `Invalid test input JSON: ${e.message}`, execution_time_ms: 0 })
    }
  }

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: Filter list */}
      <div className="w-72 flex flex-col shrink-0">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Custom Filters</h2>
          <button onClick={startNew} className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-700 rounded text-xs font-medium">+ New</button>
        </div>

        <div className="space-y-1.5 overflow-auto flex-1">
          {filters?.map((f: any) => (
            <button key={f.id} onClick={() => selectFilter(f)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedId === f.id ? 'border-cyan-500 bg-cyan-500/5' : 'border-gray-800 bg-gray-900 hover:border-gray-700'
              }`}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-cyan-400">{f.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{f.category}</span>
              </div>
              <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-1">{f.description}</p>
              <div className="flex items-center gap-2 mt-1">
                {f.is_builtin && <span className="text-[9px] text-blue-400">built-in</span>}
                <span className="text-[9px] text-gray-600 font-mono">({f.signature})</span>
              </div>
            </button>
          ))}
        </div>

        {/* Allowed Modules */}
        <div className="mt-4 pt-4 border-t border-gray-800">
          <h3 className="text-xs font-medium text-gray-400 mb-2">Allowed Python Modules</h3>
          <div className="flex flex-wrap gap-1 mb-2">
            {modules?.allowed?.map((m: string) => (
              <span key={m} className="text-[10px] px-1.5 py-0.5 bg-gray-800 rounded font-mono text-gray-300">{m}</span>
            ))}
          </div>
          <div className="flex gap-1">
            <input value={newModule} onChange={e => setNewModule(e.target.value)} placeholder="module name"
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-[10px] font-mono focus:border-cyan-500 focus:outline-none" />
            <button onClick={() => newModule && addModuleMutation.mutate(newModule)}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-[10px]">Add</button>
          </div>
        </div>
      </div>

      {/* Right: Editor */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {(selectedId || isNew) ? (
          <>
            {/* Metadata */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Filter Name</label>
                  <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., bits_to_human"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Parameters</label>
                  <input value={signature} onChange={e => setSignature(e.target.value)} placeholder="value, precision=2"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Category</label>
                  <select value={category} onChange={e => setCategory(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="mt-3">
                <label className="text-xs text-gray-400 block mb-1">Description</label>
                <input value={description} onChange={e => setDescription(e.target.value)}
                  placeholder="What this filter does..."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
              </div>
            </div>

            {/* Code Editor */}
            <div className="flex-1 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden flex flex-col min-h-[300px]">
              <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  <span className="text-gray-500">def</span> <span className="text-cyan-400">{name || 'filter_name'}</span>(<span className="text-yellow-300">{signature}</span>):
                </span>
                <div className="flex gap-2">
                  <button onClick={handleSave} disabled={!name || saveMutation.isPending}
                    className="px-3 py-1 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded text-xs font-medium">
                    {saveMutation.isPending ? 'Saving...' : 'Save'}
                  </button>
                  {selectedId && (
                    <button onClick={() => deleteMutation.mutate()} className="px-3 py-1 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded text-xs">
                      Delete
                    </button>
                  )}
                </div>
              </div>
              <div className="flex-1">
                <Editor
                  height="100%"
                  language="python"
                  theme="vs-dark"
                  value={code}
                  onChange={v => setCode(v || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    tabSize: 4,
                    insertSpaces: true,
                    automaticLayout: true,
                    padding: { top: 8 },
                  }}
                />
              </div>
            </div>

            {/* Test Runner */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-xs font-medium text-gray-200 mb-2">Test Runner</h3>
              <div className="flex gap-2 mb-2">
                <div className="flex-1">
                  <label className="text-[10px] text-gray-500 block mb-0.5">Test Args (JSON array)</label>
                  <input value={testInput} onChange={e => setTestInput(e.target.value)} placeholder='[450000000]'
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
                <div className="w-40">
                  <label className="text-[10px] text-gray-500 block mb-0.5">Expected</label>
                  <input value={testExpected} onChange={e => setTestExpected(e.target.value)} placeholder='450.0 Mbps'
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
                <button onClick={handleTest} className="px-4 py-1.5 bg-green-600 hover:bg-green-700 rounded text-xs font-medium self-end">
                  Run Test
                </button>
              </div>

              {testResult && (
                <div className={`p-2 rounded text-xs font-mono ${
                  testResult.error ? 'bg-red-500/10 text-red-400' :
                  testExpected && testResult.output === testExpected ? 'bg-green-500/10 text-green-400' :
                  'bg-blue-500/10 text-blue-400'
                }`}>
                  {testResult.error ? (
                    <span>{testResult.error}</span>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span>Output: <strong>{testResult.output}</strong></span>
                      <span className="text-gray-500">{testResult.execution_time_ms}ms</span>
                    </div>
                  )}
                  {testExpected && testResult.output && testResult.output !== testExpected && (
                    <div className="text-yellow-400 mt-1">Expected: {testExpected}</div>
                  )}
                </div>
              )}

              {/* Usage hint */}
              <div className="mt-3 text-[10px] text-gray-500">
                <strong>Usage in templates:</strong>{' '}
                <code className="text-cyan-400/70">{'{{ value | ' + (name || 'filter_name') + ' }}'}</code>
                {signature.includes(',') && (
                  <span> or <code className="text-cyan-400/70">{'{{ value | ' + (name || 'filter_name') + '(' + signature.split(',').slice(1).map(s => s.trim().split('=')[0]).join(', ') + ') }}'}</code></span>
                )}
              </div>
            </div>

            {/* Documentation */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-xs font-medium text-gray-200 mb-2">Filter Development Guide</h3>
              <div className="grid grid-cols-2 gap-4 text-[10px] text-gray-400">
                <div>
                  <h4 className="text-gray-300 font-medium mb-1">How it works</h4>
                  <p>Your code is the body of a Python function. The first parameter receives the piped value in Jinja2 templates.</p>
                  <p className="mt-1">Template: <code className="text-cyan-400">{'{{ 450000000 | bits_to_human }}'}</code></p>
                  <p>Calls: <code className="text-cyan-400">bits_to_human(450000000)</code></p>
                  <p className="mt-1">With args: <code className="text-cyan-400">{'{{ 45.6 | pct(2) }}'}</code></p>
                  <p>Calls: <code className="text-cyan-400">pct(45.6, 2)</code></p>
                </div>
                <div>
                  <h4 className="text-gray-300 font-medium mb-1">Available modules</h4>
                  <p className="font-mono">{modules?.allowed?.join(', ')}</p>
                  <h4 className="text-gray-300 font-medium mt-2 mb-1">Security</h4>
                  <p>Code runs in a sandbox. No file I/O, no network, no dangerous imports. Admin can add modules via the sidebar.</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Select a filter to edit or click "+ New" to create one.
            <br />Filters are usable in all Jinja2 templates and custom syslog messages.
          </div>
        )}
      </div>
    </div>
  )
}

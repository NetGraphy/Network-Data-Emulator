import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchPlatforms,
  fetchDeviceModels,
  fetchSoftwareVersions,
  fetchCLILibrary,
  fetchCLILibraryVersions,
  createCLILibraryEntry,
} from '../api/client'

const COMMON_COMMANDS = [
  'show version', 'show interfaces', 'show ip interface brief',
  'show cdp neighbors', 'show cdp neighbors detail', 'show lldp neighbors',
  'show running-config', 'show inventory', 'show ip route',
  'show ip bgp summary', 'show mac address-table', 'show vlan brief', 'show logging',
]

export default function CLIModeling() {
  const queryClient = useQueryClient()

  const [platformId, setPlatformId] = useState('')
  const [modelId, setModelId] = useState('')
  const [versionId, setVersionId] = useState('')
  const [command, setCommand] = useState('')
  const [rawOutput, setRawOutput] = useState('')
  const [submitResult, setSubmitResult] = useState<any>(null)

  // Cascading data queries
  const { data: platforms } = useQuery({ queryKey: ['platforms'], queryFn: fetchPlatforms })
  const { data: models } = useQuery({
    queryKey: ['device-models', platformId],
    queryFn: () => fetchDeviceModels(platformId),
    enabled: !!platformId,
  })
  const { data: versions } = useQuery({
    queryKey: ['software-versions', platformId],
    queryFn: () => fetchSoftwareVersions(platformId),
    enabled: !!platformId,
  })
  const { data: libraryEntries, refetch: refetchLibrary } = useQuery({
    queryKey: ['cli-library', platformId, command],
    queryFn: () => fetchCLILibrary({
      ...(platformId ? { platform_id: platformId } : {}),
      ...(command ? { command } : {}),
    }),
    enabled: !!platformId || !!command,
  })
  const { data: existingVersions } = useQuery({
    queryKey: ['cli-versions', platformId, command],
    queryFn: () => fetchCLILibraryVersions(platformId, command),
    enabled: !!platformId && !!command,
  })

  const selectedPlatform = platforms?.find((p: any) => p.id === platformId)
  const selectedModel = models?.find((m: any) => m.id === modelId)
  const selectedVersion = versions?.find((v: any) => v.id === versionId)

  const handlePlatformChange = (id: string) => {
    setPlatformId(id)
    setModelId('')
    setVersionId('')
    setSubmitResult(null)
  }

  const submitMutation = useMutation({
    mutationFn: (data: any) => createCLILibraryEntry(data),
    onSuccess: (result) => {
      setSubmitResult(result)
      refetchLibrary()
      queryClient.invalidateQueries({ queryKey: ['cli-versions'] })
    },
  })

  const handleSubmit = () => {
    if (!platformId || !versionId || !command || !rawOutput) return
    submitMutation.mutate({
      platform_id: platformId,
      device_model_id: modelId || null,
      software_version: selectedVersion?.version_string || '',
      command,
      raw_output: rawOutput,
      auto_validate: true,
    })
  }

  const canSubmit = platformId && versionId && command && rawOutput && !submitMutation.isPending

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">CLI Output Library</h2>
        <p className="text-sm text-gray-400">
          Versioned CLI output management with automatic parser validation
        </p>
      </div>

      <div className="flex gap-6 flex-1 min-h-0">
        {/* Left: Input */}
        <div className="w-1/2 flex flex-col gap-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
            {/* Platform */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Platform</label>
              <select
                value={platformId}
                onChange={e => handlePlatformChange(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="">Select platform...</option>
                {platforms?.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.display_name} ({p.vendor})</option>
                ))}
              </select>
            </div>

            {/* Model + Version (cascaded) */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Hardware Model
                  {!platformId && <span className="text-gray-600 ml-1">(select platform)</span>}
                </label>
                <select
                  value={modelId}
                  onChange={e => setModelId(e.target.value)}
                  disabled={!platformId}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none disabled:opacity-40"
                >
                  <option value="">Any model</option>
                  {models?.map((m: any) => (
                    <option key={m.id} value={m.id}>
                      {m.display_name}{m.vendor_name ? ` (${m.vendor_name})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Software Version
                  {!platformId && <span className="text-gray-600 ml-1">(select platform)</span>}
                </label>
                <select
                  value={versionId}
                  onChange={e => setVersionId(e.target.value)}
                  disabled={!platformId}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none disabled:opacity-40"
                >
                  <option value="">Select version...</option>
                  {versions?.map((v: any) => (
                    <option key={v.id} value={v.id}>
                      {v.version_string}{v.status !== 'current' ? ` (${v.status})` : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Command */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Command</label>
              <select
                value={command}
                onChange={e => setCommand(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="">Select command...</option>
                {COMMON_COMMANDS.map(cmd => (
                  <option key={cmd} value={cmd}>{cmd}</option>
                ))}
              </select>
            </div>

            {/* Selection summary */}
            {(platformId || modelId || versionId) && (
              <div className="bg-gray-800/50 rounded-lg px-3 py-2 text-xs text-gray-400 flex flex-wrap gap-1.5">
                {selectedPlatform && <span className="bg-gray-700 px-2 py-0.5 rounded">{selectedPlatform.display_name}</span>}
                {selectedModel && <span className="bg-indigo-900/30 text-indigo-300 px-2 py-0.5 rounded">{selectedModel.display_name}</span>}
                {selectedVersion && <span className="bg-teal-900/30 text-teal-300 px-2 py-0.5 rounded font-mono">v{selectedVersion.version_string}</span>}
                {command && <span className="bg-cyan-900/30 text-cyan-300 px-2 py-0.5 rounded font-mono">{command}</span>}
              </div>
            )}
          </div>

          {/* Output paste */}
          <div className="flex-1 flex flex-col">
            <label className="text-xs text-gray-400 mb-1">Paste CLI output from real device:</label>
            <textarea
              value={rawOutput}
              onChange={e => setRawOutput(e.target.value)}
              placeholder={`Paste the output of "${command || 'show ...'}" from a ${selectedPlatform?.display_name || '...'} ${selectedModel?.display_name || ''} running ${selectedVersion?.version_string || '...'}`}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-4 text-sm font-mono text-green-400 focus:border-cyan-500 focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            {submitMutation.isPending ? 'Validating & Saving...' : 'Validate & Save to Library'}
          </button>
        </div>

        {/* Right: Results */}
        <div className="w-1/2 flex flex-col gap-4 overflow-auto">
          {submitResult && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
              <h3 className="text-sm font-medium text-gray-200">Validation Results</h3>
              {submitResult.parser_results && (
                <div className="space-y-2">
                  <ParserBadge label="TextFSM / NTC-Templates" result={submitResult.parser_results.textfsm} />
                  <ParserBadge label="Regex Field Extraction" result={submitResult.parser_results.regex_extract} />
                </div>
              )}
              {submitResult.diff_from_parent && (
                <div className="pt-3 border-t border-gray-800">
                  <DiffDisplay diff={submitResult.diff_from_parent} />
                </div>
              )}
              {submitResult.version_matches?.length > 0 && (
                <div className="pt-3 border-t border-gray-800">
                  <h4 className="text-xs text-gray-400 mb-2">Matching Versions</h4>
                  {submitResult.version_matches.slice(0, 5).map((m: any, i: number) => (
                    <div key={i} className="flex items-center justify-between text-xs py-1">
                      <span className="font-mono">{m.version}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-400">{(m.similarity * 100).toFixed(0)}%</span>
                        <RecPill rec={m.recommendation} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {submitResult.recommendation && (
                <p className="text-xs text-cyan-400 pt-3 border-t border-gray-800">{submitResult.recommendation}</p>
              )}
            </div>
          )}

          {existingVersions?.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">
                Existing Versions — <span className="font-mono text-cyan-400">{command}</span>
              </h3>
              {existingVersions.map((v: any) => (
                <div key={v.entry_id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-800/50">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm">{v.version}</span>
                    {v.is_reference && <span className="text-[10px] px-1.5 py-0.5 bg-cyan-500/10 text-cyan-400 rounded">REF</span>}
                  </div>
                  <StatusPill status={v.parser_status} />
                </div>
              ))}
            </div>
          )}

          {libraryEntries?.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">Library Entries</h3>
              <div className="divide-y divide-gray-800">
                {libraryEntries.map((e: any) => (
                  <div key={e.id} className="py-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-sm text-cyan-400">{e.command}</span>
                        <span className="text-gray-500 text-xs">{e.platform_name}</span>
                        <span className="text-xs font-mono bg-teal-900/20 text-teal-400 px-1.5 py-0.5 rounded">v{e.software_version}</span>
                        {e.device_model_name && (
                          <span className="text-xs bg-indigo-900/20 text-indigo-400 px-1.5 py-0.5 rounded">{e.device_model_name}</span>
                        )}
                      </div>
                      <StatusPill status={getParserStatus(e.parser_results)} />
                    </div>
                    <p className="text-xs text-gray-600 font-mono mt-1 truncate">{e.raw_output}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!libraryEntries?.length && !submitResult && (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-sm text-center px-8 leading-relaxed">
              Select a platform and command to browse the library.
              <br />
              Models and versions are imported from NetBox, Nautobot, or NetGraphy via the Import page.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ParserBadge({ label, result }: { label: string; result: any }) {
  if (!result) return null
  const c: Record<string, string> = {
    pass: 'bg-green-500/10 text-green-400 border-green-500/20',
    fail: 'bg-red-500/10 text-red-400 border-red-500/20',
    no_library: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  }
  return (
    <div className={`rounded-lg border p-3 ${c[result.status] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{label}</span>
        <span className="text-xs font-bold uppercase">{result.status}</span>
      </div>
      {result.parsed_fields?.length > 0 && <p className="text-[10px] font-mono mt-1">Fields: {result.parsed_fields.join(', ')}</p>}
      {result.detected_fields && Object.keys(result.detected_fields).length > 0 && (
        <p className="text-[10px] font-mono mt-1">{Object.entries(result.detected_fields).map(([k, v]) => `${k}=${typeof v === 'string' ? v : '...'}`).join(', ')}</p>
      )}
      {result.error && <p className="text-[10px] mt-1 opacity-60">{result.error}</p>}
    </div>
  )
}

function DiffDisplay({ diff }: { diff: any }) {
  const c: Record<string, string> = { identical: 'text-green-400', compatible: 'text-green-400', minor_change: 'text-yellow-400', new_parser_needed: 'text-red-400' }
  return (
    <div className="space-y-1">
      <span className={`text-xs font-medium ${c[diff.parser_compatibility] || 'text-gray-400'}`}>
        {diff.parser_compatibility === 'identical' ? 'Identical' : diff.parser_compatibility === 'compatible' ? 'Compatible — use existing parser' : diff.parser_compatibility === 'minor_change' ? 'Minor change — review parser' : 'Significant change — new parser needed'}
      </span>
      <p className="text-[10px] text-gray-400">{diff.diff_summary}</p>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const c: Record<string, string> = { pass: 'bg-green-500/10 text-green-400', fail: 'bg-red-500/10 text-red-400', untested: 'bg-gray-500/10 text-gray-400', regex_only: 'bg-blue-500/10 text-blue-400' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${c[status] || c.untested}`}>{status}</span>
}

function RecPill({ rec }: { rec: string }) {
  const c: Record<string, string> = { use_existing_parser: 'bg-green-500/10 text-green-400', review_parser: 'bg-yellow-500/10 text-yellow-400', new_parser_likely: 'bg-red-500/10 text-red-400' }
  const l: Record<string, string> = { use_existing_parser: 'Use Existing', review_parser: 'Review', new_parser_likely: 'New Parser' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${c[rec] || ''}`}>{l[rec] || rec}</span>
}

function getParserStatus(r: any): string {
  if (!r) return 'untested'
  if (r.textfsm?.status === 'pass') return 'pass'
  if (r.textfsm?.status === 'fail') return 'fail'
  if (r.regex_extract?.detected_fields) return 'regex_only'
  return 'untested'
}

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchPlatforms,
  fetchCLILibrary,
  fetchCLILibraryVersions,
  createCLILibraryEntry,
} from '../api/client'

const COMMON_COMMANDS = [
  'show version',
  'show interfaces',
  'show ip interface brief',
  'show cdp neighbors',
  'show cdp neighbors detail',
  'show lldp neighbors',
  'show running-config',
  'show inventory',
  'show ip route',
  'show ip bgp summary',
  'show mac address-table',
  'show vlan brief',
  'show logging',
]

type ParserStatus = 'pass' | 'fail' | 'untested' | 'regex_only' | 'no_library'

export default function CLIModeling() {
  const queryClient = useQueryClient()

  // Selectors
  const [platformId, setPlatformId] = useState('')
  const [softwareVersion, setSoftwareVersion] = useState('')
  const [modelId, setModelId] = useState('')
  const [command, setCommand] = useState('')
  const [rawOutput, setRawOutput] = useState('')

  // Results
  const [submitResult, setSubmitResult] = useState<any>(null)

  // Data
  const { data: platforms } = useQuery({ queryKey: ['platforms'], queryFn: fetchPlatforms })
  const { data: libraryEntries, refetch: refetchLibrary } = useQuery({
    queryKey: ['cli-library', platformId, command],
    queryFn: () => fetchCLILibrary({ ...(platformId ? { platform_id: platformId } : {}), ...(command ? { command } : {}) }),
    enabled: !!platformId || !!command,
  })
  const { data: versions } = useQuery({
    queryKey: ['cli-versions', platformId, command],
    queryFn: () => fetchCLILibraryVersions(platformId, command),
    enabled: !!platformId && !!command,
  })

  const selectedPlatform = platforms?.find((p: any) => p.id === platformId)

  const submitMutation = useMutation({
    mutationFn: (data: any) => createCLILibraryEntry(data),
    onSuccess: (result) => {
      setSubmitResult(result)
      refetchLibrary()
      queryClient.invalidateQueries({ queryKey: ['cli-versions'] })
    },
  })

  const handleSubmit = async () => {
    if (!platformId || !softwareVersion || !command || !rawOutput) return
    submitMutation.mutate({
      platform_id: platformId,
      device_model_id: modelId || null,
      software_version: softwareVersion,
      command,
      raw_output: rawOutput,
      auto_validate: true,
    })
  }

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
          {/* Platform / Version / Model / Command selectors */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Platform</label>
                <select
                  value={platformId}
                  onChange={e => setPlatformId(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select platform...</option>
                  {platforms?.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.display_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Software Version</label>
                <input
                  type="text"
                  value={softwareVersion}
                  onChange={e => setSoftwareVersion(e.target.value)}
                  placeholder="e.g., 15.4.23, 17.06.05"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Model (optional)</label>
                <input
                  type="text"
                  value={modelId}
                  onChange={e => setModelId(e.target.value)}
                  placeholder="e.g., ISR-4311"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Command</label>
                <select
                  value={command}
                  onChange={e => setCommand(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select command...</option>
                  {COMMON_COMMANDS.map(cmd => (
                    <option key={cmd} value={cmd}>{cmd}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Output paste area */}
          <div className="flex-1 flex flex-col">
            <label className="text-xs text-gray-400 mb-1">
              Paste CLI output from real device:
            </label>
            <textarea
              value={rawOutput}
              onChange={e => setRawOutput(e.target.value)}
              placeholder={`Paste the output of "${command || 'show ...'}" from a ${selectedPlatform?.display_name || ''} device running version ${softwareVersion || '...'}`}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-4 text-sm font-mono text-green-400 focus:border-cyan-500 focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!platformId || !softwareVersion || !command || !rawOutput || submitMutation.isPending}
            className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            {submitMutation.isPending ? 'Validating & Saving...' : 'Validate & Save to Library'}
          </button>
        </div>

        {/* Right: Results & Library */}
        <div className="w-1/2 flex flex-col gap-4 overflow-auto">
          {/* Submit result */}
          {submitResult && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
              <h3 className="text-sm font-medium text-gray-200">Validation Results</h3>

              {/* Parser status */}
              {submitResult.parser_results && (
                <div className="space-y-2">
                  <ParserResultBadge
                    label="TextFSM / NTC-Templates"
                    result={submitResult.parser_results.textfsm}
                  />
                  <ParserResultBadge
                    label="Regex Field Extraction"
                    result={submitResult.parser_results.regex_extract}
                  />
                </div>
              )}

              {/* Diff from parent */}
              {submitResult.diff_from_parent && (
                <div className="mt-3 pt-3 border-t border-gray-800">
                  <h4 className="text-xs text-gray-400 mb-2">Version Comparison</h4>
                  <DiffDisplay diff={submitResult.diff_from_parent} />
                </div>
              )}

              {/* Version matches */}
              {submitResult.version_matches && submitResult.version_matches.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-800">
                  <h4 className="text-xs text-gray-400 mb-2">Matching Versions</h4>
                  <div className="space-y-1">
                    {submitResult.version_matches.slice(0, 5).map((m: any, i: number) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="font-mono">{m.version}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-400">{(m.similarity * 100).toFixed(0)}% match</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            m.recommendation === 'use_existing_parser'
                              ? 'bg-green-500/10 text-green-400'
                              : m.recommendation === 'review_parser'
                              ? 'bg-yellow-500/10 text-yellow-400'
                              : 'bg-red-500/10 text-red-400'
                          }`}>
                            {m.recommendation === 'use_existing_parser' ? 'Use Existing' :
                             m.recommendation === 'review_parser' ? 'Review Needed' : 'New Parser'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendation */}
              {submitResult.recommendation && (
                <div className="mt-3 pt-3 border-t border-gray-800">
                  <p className="text-xs text-cyan-400">{submitResult.recommendation}</p>
                </div>
              )}
            </div>
          )}

          {/* Existing versions for this command */}
          {versions && versions.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">
                Existing Versions — {command}
              </h3>
              <div className="space-y-1">
                {versions.map((v: any) => (
                  <div key={v.entry_id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-800/50">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{v.version}</span>
                      {v.is_reference && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-cyan-500/10 text-cyan-400 rounded">REF</span>
                      )}
                    </div>
                    <ParserStatusPill status={v.parser_status} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full library browse */}
          {libraryEntries && libraryEntries.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">Library Entries</h3>
              <div className="divide-y divide-gray-800">
                {libraryEntries.map((e: any) => (
                  <div key={e.id} className="py-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-mono text-sm text-cyan-400">{e.command}</span>
                        <span className="text-gray-500 text-xs ml-2">{e.platform_name}</span>
                        <span className="text-gray-500 text-xs ml-1">v{e.software_version}</span>
                        {e.device_model_name && (
                          <span className="text-gray-600 text-xs ml-1">({e.device_model_name})</span>
                        )}
                      </div>
                      <ParserStatusPill status={_getParserStatus(e.parser_results)} />
                    </div>
                    <p className="text-xs text-gray-600 font-mono mt-1 truncate">{e.raw_output}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!libraryEntries || libraryEntries.length === 0) && !submitResult && (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
              Select a platform and command to browse the library, or paste output to add a new entry.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


function ParserResultBadge({ label, result }: { label: string; result: any }) {
  if (!result) return null

  const statusColors: Record<string, string> = {
    pass: 'bg-green-500/10 text-green-400 border-green-500/20',
    fail: 'bg-red-500/10 text-red-400 border-red-500/20',
    no_template: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    no_library: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  }

  const color = statusColors[result.status] || statusColors.no_template

  return (
    <div className={`rounded-lg border p-3 ${color}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{label}</span>
        <span className="text-xs font-bold uppercase">{result.status}</span>
      </div>
      {result.status === 'pass' && result.parsed_fields && (
        <div className="mt-2">
          <span className="text-[10px] text-gray-400">Parsed fields: </span>
          <span className="text-[10px] font-mono">
            {result.parsed_fields.join(', ')}
          </span>
          {result.row_count && (
            <span className="text-[10px] text-gray-500 ml-2">({result.row_count} rows)</span>
          )}
        </div>
      )}
      {result.status === 'pass' && result.detected_fields && (
        <div className="mt-2">
          <span className="text-[10px] text-gray-400">Detected: </span>
          <span className="text-[10px] font-mono">
            {Object.entries(result.detected_fields)
              .filter(([k]) => !k.startsWith('_'))
              .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v).slice(0, 30)}`)
              .join(', ')}
          </span>
        </div>
      )}
      {result.error && (
        <p className="text-[10px] mt-1 opacity-75">{result.error}</p>
      )}
      {result.template && (
        <p className="text-[10px] mt-1 opacity-50">Template: {result.template}</p>
      )}
    </div>
  )
}


function DiffDisplay({ diff }: { diff: any }) {
  const compatColors: Record<string, string> = {
    identical: 'text-green-400',
    compatible: 'text-green-400',
    minor_change: 'text-yellow-400',
    new_parser_needed: 'text-red-400',
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className={`text-xs font-medium ${compatColors[diff.parser_compatibility] || 'text-gray-400'}`}>
          {diff.parser_compatibility === 'identical' && 'Identical to previous version'}
          {diff.parser_compatibility === 'compatible' && 'Compatible — existing parser works'}
          {diff.parser_compatibility === 'minor_change' && 'Minor structural change — review parser'}
          {diff.parser_compatibility === 'new_parser_needed' && 'Significant change — new parser recommended'}
        </span>
      </div>
      <p className="text-[10px] text-gray-400">{diff.diff_summary}</p>
      {diff.added_fields?.length > 0 && (
        <div className="text-[10px]">
          <span className="text-green-400">+ New fields: </span>
          <span className="font-mono text-green-300">{diff.added_fields.join(', ')}</span>
        </div>
      )}
      {diff.removed_fields?.length > 0 && (
        <div className="text-[10px]">
          <span className="text-red-400">- Removed fields: </span>
          <span className="font-mono text-red-300">{diff.removed_fields.join(', ')}</span>
        </div>
      )}
      {diff.field_changes?.length > 0 && (
        <div className="text-[10px] text-yellow-400">
          ~ {diff.field_changes.length} field value(s) changed
        </div>
      )}
    </div>
  )
}


function ParserStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pass: 'bg-green-500/10 text-green-400',
    fail: 'bg-red-500/10 text-red-400',
    untested: 'bg-gray-500/10 text-gray-400',
    regex_only: 'bg-blue-500/10 text-blue-400',
  }

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${colors[status] || colors.untested}`}>
      {status}
    </span>
  )
}


function _getParserStatus(parserResults: any): string {
  if (!parserResults) return 'untested'
  const textfsm = parserResults.textfsm
  if (textfsm?.status === 'pass') return 'pass'
  if (textfsm?.status === 'fail') return 'fail'
  if (parserResults.regex_extract?.detected_fields) return 'regex_only'
  return 'untested'
}

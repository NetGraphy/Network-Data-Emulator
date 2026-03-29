import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchScenarios, fetchScenario, startScenario, pauseScenario,
  resumeScenario, resetScenario, getScenarioExecution,
  createScenario, fetchDevices, fetchInterfaces, fetchLinks,
  fetchDeviceVariables,
} from '../api/client'

const ACTION_TYPES = [
  { value: 'interface_state_change', label: 'Interface State Change' },
  { value: 'interface_admin_change', label: 'Interface Admin Change' },
  { value: 'device_state_change', label: 'Device State Change' },
  { value: 'counter_set', label: 'Counter Set' },
  { value: 'counter_rate_change', label: 'Counter Rate Change' },
  { value: 'link_state_change', label: 'Link State Change' },
  { value: 'log_event', label: 'Custom Log Event' },
]

const SYSLOG_FACILITIES = ['SYS', 'LINK', 'LINEPROTO', 'BGP', 'OSPF', 'CDP', 'HSRP', 'SPANTREE', 'SEC', 'PLATFORM_ENV']
const SYSLOG_SEVERITIES = [
  { value: 0, label: '0 - Emergency' }, { value: 1, label: '1 - Alert' },
  { value: 2, label: '2 - Critical' }, { value: 3, label: '3 - Error' },
  { value: 4, label: '4 - Warning' }, { value: 5, label: '5 - Notification' },
  { value: 6, label: '6 - Informational' }, { value: 7, label: '7 - Debug' },
]

const TRIGGER_TYPES = [
  { value: 'immediate', label: 'Immediate' },
  { value: 'delay', label: 'Delay (seconds)' },
  { value: 'manual', label: 'Manual Trigger' },
]

type View = 'list' | 'create'

export default function ScenarioList() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<View>('list')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: scenarios, isLoading } = useQuery({ queryKey: ['scenarios'], queryFn: fetchScenarios })
  const { data: detail } = useQuery({
    queryKey: ['scenario', selectedId], queryFn: () => fetchScenario(selectedId!), enabled: !!selectedId,
  })
  const { data: execution, refetch: refetchExec } = useQuery({
    queryKey: ['scenario-exec', selectedId], queryFn: () => getScenarioExecution(selectedId!),
    enabled: !!selectedId, refetchInterval: selectedId ? 3000 : false,
  })

  const startMut = useMutation({
    mutationFn: (id: string) => startScenario(id),
    onSuccess: () => { refetchExec(); queryClient.invalidateQueries({ queryKey: ['scenarios'] }); },
  })
  const resetMut = useMutation({
    mutationFn: (id: string) => resetScenario(id),
    onSuccess: () => { refetchExec(); queryClient.invalidateQueries({ queryKey: ['scenarios'] }); },
  })

  const progress = execution?.progress || {}
  const logs = execution?.recent_logs || []

  if (view === 'create') {
    return <ScenarioBuilder onBack={() => { setView('list'); queryClient.invalidateQueries({ queryKey: ['scenarios'] }); }} />
  }

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: Scenario list */}
      <div className="w-1/3 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Scenarios</h2>
          <button onClick={() => setView('create')} className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-xs font-medium">
            + New Scenario
          </button>
        </div>

        {isLoading ? <p className="text-gray-500">Loading...</p> : (
          <div className="space-y-2 overflow-auto">
            {scenarios?.map((s: any) => (
              <button
                key={s.id} onClick={() => setSelectedId(s.id)}
                className={`w-full text-left p-4 rounded-xl border transition-colors ${
                  selectedId === s.id ? 'border-cyan-500 bg-cyan-500/5' : 'border-gray-800 bg-gray-900 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{s.name}</span>
                  <StatusBadge status={s.status} />
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{s.description}</p>
                <div className="flex gap-3 mt-1 text-[10px] text-gray-600">
                  <span>{s.event_count} events</span>
                  {s.log_count > 0 && <span>{s.log_count} logs</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Detail + Execution */}
      <div className="flex-1 flex flex-col gap-4 overflow-auto">
        {selectedId && detail ? (
          <>
            {/* Header + Controls */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-lg">{detail.name}</h3>
                <StatusBadge status={detail.status} />
              </div>
              <p className="text-sm text-gray-400 mb-4">{detail.description}</p>
              <div className="flex gap-2">
                {(detail.status === 'ready' || detail.status === 'completed') && (
                  <button onClick={() => startMut.mutate(selectedId)} disabled={startMut.isPending}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg text-sm font-medium">
                    {startMut.isPending ? 'Starting...' : 'Start'}
                  </button>
                )}
                {(detail.status === 'completed' || detail.status === 'running') && (
                  <button onClick={() => resetMut.mutate(selectedId)} disabled={resetMut.isPending}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
                    {resetMut.isPending ? 'Resetting...' : 'Reset'}
                  </button>
                )}
              </div>
            </div>

            {/* Progress */}
            {progress.status && progress.status !== 'not_started' && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium">Execution Progress</h4>
                  <span className="text-xs text-gray-400">{progress.current_event || 0} / {progress.total_events || 0} events</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 mb-2">
                  <div className={`h-2 rounded-full ${progress.status === 'completed' ? 'bg-green-500' : 'bg-cyan-500'}`}
                    style={{ width: `${progress.total_events ? (progress.current_event / progress.total_events * 100) : 0}%` }} />
                </div>
                <span className="text-xs text-gray-400">
                  {progress.status} | {progress.logs_generated || 0} logs
                </span>
              </div>
            )}

            {/* Events */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <h4 className="text-sm font-medium mb-3">Events ({detail.events?.length})</h4>
              <div className="space-y-2">
                {detail.events?.map((e: any, i: number) => {
                  const completed = progress.completed_events?.find((c: any) => c.event_id === e.id)
                  return (
                    <div key={e.id} className={`flex items-center gap-3 p-3 rounded-lg ${completed ? 'bg-green-500/5 border border-green-500/20' : 'bg-gray-800/50'}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                        completed ? 'bg-green-600' : progress.current_event === i + 1 ? 'bg-cyan-600 animate-pulse' : 'bg-gray-700 text-gray-400'
                      }`}>{i + 1}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-mono">{e.action_type}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                            e.trigger_type === 'delay' ? 'bg-blue-900/30 text-blue-400' : 'bg-gray-700 text-gray-300'
                          }`}>{e.trigger_type}{e.trigger_config?.delay_seconds ? ` (${e.trigger_config.delay_seconds}s)` : ''}</span>
                        </div>
                        <p className="text-[10px] text-gray-500 truncate mt-0.5">{JSON.stringify(e.action_config)}</p>
                        {completed && <span className="text-[10px] text-green-400">{completed.logs_generated} logs</span>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Logs */}
            {logs.length > 0 && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h4 className="text-sm font-medium mb-3">Generated Syslog ({execution?.total_logs})</h4>
                <div className="space-y-0.5 max-h-[400px] overflow-auto">
                  {logs.map((log: any, i: number) => (
                    <div key={i} className={`font-mono text-[11px] py-0.5 ${log.severity <= 2 ? 'text-red-400' : log.severity <= 4 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Select a scenario or create a new one
          </div>
        )}
      </div>
    </div>
  )
}


// === Scenario Builder ===

function ScenarioBuilder({ onBack }: { onBack: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [events, setEvents] = useState<any[]>([])
  const [saving, setSaving] = useState(false)

  // Load devices and interfaces for pickers
  const { data: devices } = useQuery({ queryKey: ['devices'], queryFn: fetchDevices })
  const [selectedDeviceId, setSelectedDeviceId] = useState('')
  const { data: interfaces } = useQuery({
    queryKey: ['interfaces', selectedDeviceId],
    queryFn: () => fetchInterfaces(selectedDeviceId),
    enabled: !!selectedDeviceId,
  })

  const addEvent = () => {
    setEvents([...events, {
      sequence_order: events.length + 1,
      trigger_type: 'immediate',
      trigger_config: {},
      action_type: 'interface_state_change',
      action_config: {},
      rollback_action: null,
    }])
  }

  const updateEvent = (index: number, field: string, value: any) => {
    const updated = [...events]
    if (field.startsWith('action_config.')) {
      const key = field.split('.')[1]
      updated[index].action_config = { ...updated[index].action_config, [key]: value }
    } else if (field.startsWith('trigger_config.')) {
      const key = field.split('.')[1]
      updated[index].trigger_config = { ...updated[index].trigger_config, [key]: value }
    } else {
      updated[index][field] = value
    }
    setEvents(updated)
  }

  const removeEvent = (index: number) => {
    setEvents(events.filter((_, i) => i !== index).map((e, i) => ({ ...e, sequence_order: i + 1 })))
  }

  const handleSave = async () => {
    if (!name || events.length === 0) return
    setSaving(true)
    try {
      // Build rollback actions
      const eventsWithRollback = events.map(e => {
        let rollback = null
        if (e.action_type === 'interface_state_change') {
          const opposite = e.action_config.oper_status === 'down' ? 'up' : 'down'
          rollback = { action_type: 'interface_state_change', action_config: { interface_id: e.action_config.interface_id, oper_status: opposite } }
        } else if (e.action_type === 'device_state_change') {
          const opposite = e.action_config.admin_state === 'maintenance' ? 'active' : 'maintenance'
          rollback = { action_type: 'device_state_change', action_config: { device_id: e.action_config.device_id, admin_state: opposite } }
        } else if (e.action_type === 'counter_set') {
          rollback = { action_type: 'counter_set', action_config: { interface_id: e.action_config.interface_id, counter_name: e.action_config.counter_name, value: 0 } }
        }
        return { ...e, rollback_action: rollback }
      })

      await createScenario({ name, description, events: eventsWithRollback })
      onBack()
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack} className="text-gray-400 hover:text-gray-200 text-sm">Back</button>
        <h2 className="text-xl font-semibold">New Scenario</h2>
      </div>

      {/* Name + Description */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mb-4 space-y-3">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Scenario Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Core Router Failure"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
            placeholder="What this scenario simulates..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:border-cyan-500 focus:outline-none resize-none" />
        </div>
      </div>

      {/* Device/Interface Picker (shared context) */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 mb-4">
        <label className="text-xs text-gray-400 block mb-1">Target Device (for interface picker)</label>
        <select value={selectedDeviceId} onChange={e => setSelectedDeviceId(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
          <option value="">Select device...</option>
          {devices?.map((d: any) => <option key={d.id} value={d.id}>{d.hostname} ({d.platform_name})</option>)}
        </select>
      </div>

      {/* Events */}
      <div className="space-y-3 mb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-200">Events ({events.length})</h3>
          <button onClick={addEvent} className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-xs font-medium">
            + Add Event
          </button>
        </div>

        {events.map((event, i) => (
          <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-cyan-600 flex items-center justify-center text-xs font-bold">{i + 1}</span>
                <span className="text-sm font-medium">Event {i + 1}</span>
              </div>
              <button onClick={() => removeEvent(i)} className="text-xs text-red-400 hover:text-red-300">Remove</button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Trigger */}
              <div>
                <label className="text-xs text-gray-400 block mb-1">Trigger</label>
                <select value={event.trigger_type} onChange={e => updateEvent(i, 'trigger_type', e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                  {TRIGGER_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              {event.trigger_type === 'delay' && (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Delay (seconds)</label>
                  <input type="number" value={event.trigger_config.delay_seconds || ''} onChange={e => updateEvent(i, 'trigger_config.delay_seconds', parseInt(e.target.value) || 0)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
                </div>
              )}

              {/* Action Type */}
              <div>
                <label className="text-xs text-gray-400 block mb-1">Action</label>
                <select value={event.action_type} onChange={e => updateEvent(i, 'action_type', e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                  {ACTION_TYPES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </div>

              {/* Action-specific fields */}
              {(event.action_type === 'interface_state_change' || event.action_type === 'interface_admin_change' || event.action_type === 'counter_set' || event.action_type === 'counter_rate_change') && (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Interface</label>
                  <select value={event.action_config.interface_id || ''} onChange={e => updateEvent(i, 'action_config.interface_id', e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none">
                    <option value="">Select interface...</option>
                    {interfaces?.map((iface: any) => <option key={iface.id} value={iface.id}>{iface.name} ({iface.oper_status})</option>)}
                  </select>
                </div>
              )}

              {event.action_type === 'interface_state_change' && (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Oper Status</label>
                  <select value={event.action_config.oper_status || ''} onChange={e => updateEvent(i, 'action_config.oper_status', e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                    <option value="">Select...</option>
                    <option value="down">down</option>
                    <option value="up">up</option>
                  </select>
                </div>
              )}

              {event.action_type === 'device_state_change' && (
                <>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Device</label>
                    <select value={event.action_config.device_id || ''} onChange={e => updateEvent(i, 'action_config.device_id', e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      <option value="">Select device...</option>
                      {devices?.map((d: any) => <option key={d.id} value={d.id}>{d.hostname}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Admin State</label>
                    <select value={event.action_config.admin_state || ''} onChange={e => updateEvent(i, 'action_config.admin_state', e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      <option value="">Select...</option>
                      <option value="maintenance">maintenance</option>
                      <option value="active">active</option>
                      <option value="decommissioned">decommissioned</option>
                    </select>
                  </div>
                </>
              )}

              {event.action_type === 'counter_set' && (
                <>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Counter</label>
                    <select value={event.action_config.counter_name || ''} onChange={e => updateEvent(i, 'action_config.counter_name', e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      <option value="">Select...</option>
                      <option value="in_errors">in_errors</option>
                      <option value="out_errors">out_errors</option>
                      <option value="crc_errors">crc_errors</option>
                      <option value="in_discards">in_discards</option>
                      <option value="collisions">collisions</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Value</label>
                    <input type="number" value={event.action_config.value || ''} onChange={e => updateEvent(i, 'action_config.value', parseInt(e.target.value) || 0)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
                  </div>
                </>
              )}

              {/* Custom Log Event */}
              {event.action_type === 'log_event' && (
                <>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Device</label>
                    <select value={event.action_config.device_id || ''} onChange={e => updateEvent(i, 'action_config.device_id', e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      <option value="">Select device...</option>
                      {devices?.map((d: any) => <option key={d.id} value={d.id}>{d.hostname}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Severity</label>
                    <select value={event.action_config.severity ?? ''} onChange={e => updateEvent(i, 'action_config.severity', parseInt(e.target.value))}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      {SYSLOG_SEVERITIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Facility</label>
                    <select value={event.action_config.facility || ''} onChange={e => updateEvent(i, 'action_config.facility', e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
                      {SYSLOG_FACILITIES.map(f => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Mnemonic</label>
                    <input value={event.action_config.mnemonic || ''} onChange={e => updateEvent(i, 'action_config.mnemonic', e.target.value)}
                      placeholder="e.g., UPDOWN, CONFIG_I"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs text-gray-400 block mb-1">Message (supports {'{{ variables }}'})</label>
                    <textarea value={event.action_config.custom_message || ''} onChange={e => updateEvent(i, 'action_config.custom_message', e.target.value)}
                      rows={2} placeholder="e.g., Interface {{ interface.GigabitEthernet1/0/1.name }} on {{ device.hostname }} experienced a fault"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none resize-none" />
                    {/* Variable picker */}
                    {event.action_config.device_id && (
                      <VariablePicker deviceId={event.action_config.device_id} onInsert={(v: string) => {
                        const cur = event.action_config.custom_message || ''
                        updateEvent(i, 'action_config.custom_message', cur + `{{ ${v} }}`)
                      }} />
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        ))}

        {events.length === 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center text-gray-500 text-sm">
            Click "+ Add Event" to build your scenario. Events execute in order.
          </div>
        )}
      </div>

      {/* Help: Template Variables Documentation */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 className="font-medium text-gray-200 mb-3">Template Variables Guide</h3>
        <p className="text-xs text-gray-400 mb-3">
          Use <code className="bg-gray-800 px-1 rounded text-cyan-400">{'{{ variable.path }}'}</code> in custom log messages to insert device state dynamically.
          Variables are resolved at execution time from the target device's current state.
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px]">
          <div className="font-mono text-cyan-400">{'{{ device.hostname }}'}</div><div className="text-gray-500">Device hostname</div>
          <div className="font-mono text-cyan-400">{'{{ device.management_ip }}'}</div><div className="text-gray-500">Management IP</div>
          <div className="font-mono text-cyan-400">{'{{ device.serial_number }}'}</div><div className="text-gray-500">Serial number</div>
          <div className="font-mono text-cyan-400">{'{{ device.software_version }}'}</div><div className="text-gray-500">Software version</div>
          <div className="font-mono text-cyan-400">{'{{ device.uptime }}'}</div><div className="text-gray-500">Current uptime</div>
          <div className="font-mono text-cyan-400">{'{{ model.display_name }}'}</div><div className="text-gray-500">Hardware model</div>
          <div className="font-mono text-cyan-400">{'{{ platform.name }}'}</div><div className="text-gray-500">Platform (cisco_ios, arista_eos)</div>
          <div className="font-mono text-cyan-400">{'{{ interface.<name>.name }}'}</div><div className="text-gray-500">Interface full name</div>
          <div className="font-mono text-cyan-400">{'{{ interface.<name>.oper_status }}'}</div><div className="text-gray-500">Operational status</div>
          <div className="font-mono text-cyan-400">{'{{ interface.<name>.ip_address }}'}</div><div className="text-gray-500">IP address</div>
          <div className="font-mono text-cyan-400">{'{{ counter.<name>.in_errors }}'}</div><div className="text-gray-500">Error counter</div>
          <div className="font-mono text-cyan-400">{'{{ snmp.community }}'}</div><div className="text-gray-500">SNMP community</div>
          <div className="font-mono text-cyan-400">{'{{ now.cisco_timestamp }}'}</div><div className="text-gray-500">Cisco syslog timestamp</div>
        </div>
        <p className="text-[10px] text-gray-600 mt-3">
          Replace <code className="text-gray-500">{'<name>'}</code> with the actual interface name, e.g.,
          <code className="text-cyan-400/50 ml-1">{'{{ interface.GigabitEthernet1/0/1.oper_status }}'}</code>.
          Select a device first to use the variable picker which shows all available variables with their current values.
        </p>
      </div>

      {/* Save */}
      <div className="flex gap-3">
        <button onClick={handleSave} disabled={!name || events.length === 0 || saving}
          className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium">
          {saving ? 'Saving...' : 'Create Scenario'}
        </button>
        <button onClick={onBack} className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-400">
          Cancel
        </button>
      </div>
    </div>
  )
}


// === Variable Picker ===

function VariablePicker({ deviceId, onInsert }: { deviceId: string; onInsert: (v: string) => void }) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const { data: variables } = useQuery({
    queryKey: ['device-variables', deviceId],
    queryFn: () => fetchDeviceVariables(deviceId),
    enabled: open && !!deviceId,
  })

  const filtered = (variables || []).filter((v: any) =>
    v.path.toLowerCase().includes(filter.toLowerCase()) || v.value.toLowerCase().includes(filter.toLowerCase())
  )

  // Group by category
  const grouped: Record<string, any[]> = {}
  for (const v of filtered) {
    const cat = v.category || 'Other'
    ;(grouped[cat] = grouped[cat] || []).push(v)
  }

  return (
    <div className="mt-1.5">
      <button onClick={() => setOpen(!open)} className="text-[10px] text-cyan-400 hover:text-cyan-300">
        {open ? 'Close variable picker' : 'Insert variable from device state...'}
      </button>
      {open && (
        <div className="mt-2 bg-gray-800 rounded-lg border border-gray-700 max-h-60 overflow-auto">
          <div className="sticky top-0 bg-gray-800 p-2 border-b border-gray-700">
            <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter variables..."
              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs focus:border-cyan-500 focus:outline-none" />
          </div>
          {Object.entries(grouped).map(([cat, vars]) => (
            <div key={cat}>
              <div className="px-2 py-1 text-[10px] font-medium text-gray-500 bg-gray-800/80 sticky top-[41px]">{cat}</div>
              {(vars as any[]).map((v: any) => (
                <button key={v.path} onClick={() => { onInsert(v.path); setOpen(false); }}
                  className="w-full text-left px-2 py-1 hover:bg-gray-700/50 flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] text-cyan-400 truncate">{v.path}</span>
                  <span className="text-[10px] text-gray-500 truncate max-w-[150px]">{v.value}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


function StatusBadge({ status }: { status: string }) {
  const c: Record<string, string> = {
    ready: 'bg-green-500/10 text-green-400', running: 'bg-cyan-500/10 text-cyan-400',
    paused: 'bg-yellow-500/10 text-yellow-400', completed: 'bg-gray-500/10 text-gray-400',
    draft: 'bg-gray-500/10 text-gray-500', failed: 'bg-red-500/10 text-red-400',
  }
  return <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${c[status] || c.draft}`}>{status}</span>
}

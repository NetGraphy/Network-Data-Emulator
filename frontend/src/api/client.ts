import axios from 'axios'
import type { CLIMapping, Device, InterfaceData, Link, Topology, Scenario, Neighbor, NeighborParseResult } from '../types'

const apiBase = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

const api = axios.create({ baseURL: apiBase })

// Devices
export const fetchDevices = () => api.get<Device[]>('/devices').then(r => r.data)
export const fetchDevice = (id: string) => api.get(`/devices/${id}`).then(r => r.data)
export const createDevice = (data: any) => api.post('/devices', data).then(r => r.data)
export const updateDevice = (id: string, data: any) => api.patch(`/devices/${id}`, data).then(r => r.data)
export const deleteDevice = (id: string) => api.delete(`/devices/${id}`)
export const fetchDeviceNeighbors = (id: string) => api.get<Neighbor[]>(`/devices/${id}/neighbors`).then(r => r.data)

// Interfaces
export const fetchInterfaces = (deviceId?: string) => {
  const params = deviceId ? { device_id: deviceId } : {}
  return api.get<InterfaceData[]>('/interfaces', { params }).then(r => r.data)
}
export const updateInterface = (id: string, data: any) => api.patch(`/interfaces/${id}`, data).then(r => r.data)

// Links
export const fetchLinks = () => api.get<Link[]>('/links').then(r => r.data)
export const createLink = (data: any) => api.post('/links', data).then(r => r.data)
export const deleteLink = (id: string) => api.delete(`/links/${id}`)

// Topology
export const fetchTopology = () => api.get<Topology>('/topology').then(r => r.data)

// CLI Mappings
export const fetchCLIMappings = (deviceId?: string) => {
  const params = deviceId ? { device_id: deviceId } : {}
  return api.get<CLIMapping[]>('/cli-mappings', { params }).then(r => r.data)
}
export const createCLIMapping = (data: any) => api.post('/cli-mappings', data).then(r => r.data)
export const updateCLIMapping = (id: string, data: any) => api.put(`/cli-mappings/${id}`, data).then(r => r.data)
export const deleteCLIMapping = (id: string) => api.delete(`/cli-mappings/${id}`)
export const parseNeighbors = (data: { raw_output: string; command_type: string }) =>
  api.post<NeighborParseResult[]>('/cli-mappings/parse-neighbors', data).then(r => r.data)

// Scenarios
export const fetchScenarios = () => api.get<Scenario[]>('/scenarios').then(r => r.data)
export const fetchScenario = (id: string) => api.get(`/scenarios/${id}`).then(r => r.data)
export const createScenario = (data: any) => api.post('/scenarios', data).then(r => r.data)
export const startScenario = (id: string) => api.post(`/scenarios/${id}/start`).then(r => r.data)
export const pauseScenario = (id: string) => api.post(`/scenarios/${id}/pause`).then(r => r.data)
export const resumeScenario = (id: string) => api.post(`/scenarios/${id}/resume`).then(r => r.data)
export const resetScenario = (id: string) => api.post(`/scenarios/${id}/reset`).then(r => r.data)
export const getScenarioExecution = (id: string) => api.get(`/scenarios/${id}/execution`).then(r => r.data)
export const fetchDeviceLogs = (deviceId: string) => api.get(`/scenarios/logs/${deviceId}`).then(r => r.data)

// Execute
export const executeCommand = (deviceId: string, command: string) =>
  api.post(`/devices/${deviceId}/execute`, { command }).then(r => r.data)

// SNMP Walk / Get
export const snmpWalk = (deviceId: string, subtree: string = 'all', outputFormat: string = 'named') =>
  api.post(`/devices/${deviceId}/snmp-walk`, { subtree, output_format: outputFormat }).then(r => r.data)
export const snmpGet = (deviceId: string, oid: string, outputFormat: string = 'named') =>
  api.post(`/devices/${deviceId}/snmp-get`, { oid, output_format: outputFormat }).then(r => r.data)

// Export
export const exportNornir = () => api.get('/export/nornir').then(r => r.data)
export const exportAnsible = () => api.get('/export/ansible').then(r => r.data)

// Import
export const importNetBox = (data: any) => api.post('/import/netbox', data).then(r => r.data)
export const importNautobot = (data: any) => api.post('/import/nautobot', data).then(r => r.data)
export const importNetGraphy = (data: any) => api.post('/import/netgraphy', data).then(r => r.data)

// CLI Library (platform/version/model-based)
export const fetchCLILibrary = (params?: Record<string, string>) =>
  api.get('/cli-library', { params }).then(r => r.data)
export const fetchCLILibraryEntry = (id: string) => api.get(`/cli-library/${id}`).then(r => r.data)
export const createCLILibraryEntry = (data: any) => api.post('/cli-library', data).then(r => r.data)
export const fetchCLILibraryVersions = (platformId: string, command: string) =>
  api.get('/cli-library/versions', { params: { platform_id: platformId, command } }).then(r => r.data)
export const fetchCLILibraryCommands = () => api.get('/cli-library/commands').then(r => r.data)
export const diffCLIEntries = (id1: string, id2: string) => api.post(`/cli-library/${id1}/diff/${id2}`).then(r => r.data)

// Platforms (for selectors)
export const fetchPlatforms = () => api.get('/platforms').then(r => r.data)

// Device Models (for selectors — cascades from platform)
export const fetchDeviceModels = (platformId?: string) => {
  const params = platformId ? { platform_id: platformId } : {}
  return api.get('/device-models', { params }).then(r => r.data)
}

// Software Versions (for selectors — cascades from platform)
export const fetchSoftwareVersions = (platformId?: string) => {
  const params = platformId ? { platform_id: platformId } : {}
  return api.get('/software-versions', { params }).then(r => r.data)
}

// Vendors
export const fetchVendors = () => api.get('/vendors').then(r => r.data)

// Template Variables
export const fetchDeviceVariables = (deviceId: string) => api.get(`/devices/${deviceId}/variables`).then(r => r.data)
export const fetchVariableCatalog = () => api.get('/template-variables/catalog').then(r => r.data)
export const resolveTemplate = (deviceId: string, template: string) =>
  api.post(`/devices/${deviceId}/resolve-template`, { template }).then(r => r.data)

// Settings
export const fetchNetworkingSettings = () => api.get('/settings/networking').then(r => r.data)
export const updateConnectAddress = (connectAddress: string) =>
  api.post('/settings/networking/connect-address', { connect_address: connectAddress }).then(r => r.data)

// Custom Filters
export const fetchCustomFilters = () => api.get('/custom-filters').then(r => r.data)
export const fetchCustomFilter = (id: string) => api.get(`/custom-filters/${id}`).then(r => r.data)
export const createCustomFilter = (data: any) => api.post('/custom-filters', data).then(r => r.data)
export const updateCustomFilter = (id: string, data: any) => api.put(`/custom-filters/${id}`, data).then(r => r.data)
export const deleteCustomFilter = (id: string) => api.delete(`/custom-filters/${id}`)
export const testCustomFilter = (data: any) => api.post('/custom-filters/test', data).then(r => r.data)
export const reloadCustomFilters = () => api.post('/custom-filters/reload').then(r => r.data)
export const fetchAllowedModules = () => api.get('/custom-filters/modules/allowed').then(r => r.data)
export const addAllowedModule = (module: string) => api.post('/custom-filters/modules/add', { module }).then(r => r.data)
export const fetchRegisteredFilters = () => api.get('/custom-filters/registered').then(r => r.data)

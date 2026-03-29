export interface Device {
  id: string
  hostname: string
  management_ip: string | null
  serial_number: string
  software_version: string | null
  admin_state: string
  tags: Record<string, string> | null
  platform_name?: string
  model_name?: string
  interface_count?: number
  connection_info?: Record<string, { host: string; port: number }>
}

export interface InterfaceData {
  id: string
  device_id: string
  name: string
  short_name: string
  if_index: number
  interface_type: string
  admin_status: string
  oper_status: string
  speed_mbps: number
  mtu: number
  mac_address: string
  ip_address: string | null
  description: string | null
  counters: Record<string, number> | null
}

export interface Link {
  id: string
  interface_a_id: string
  interface_b_id: string
  link_type: string
  discovery_protocol: string
  admin_state: string
}

export interface TopologyNode {
  id: string
  hostname: string
  platform: string | null
  model: string | null
  admin_state: string
  interface_count: number
  management_ip: string | null
  tags: Record<string, string> | null
}

export interface TopologyEdge {
  id: string
  source_device_id: string
  source_interface: string
  target_device_id: string
  target_interface: string
  link_type: string
  admin_state: string
  oper_state: string
}

export interface Topology {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}

export interface CLIMapping {
  id: string
  device_id: string
  command: string
  raw_output: string
  mode: string
  field_annotations: any[] | null
  is_active: boolean
  source_description: string | null
}

export interface Scenario {
  id: string
  name: string
  description: string | null
  status: string
  is_repeatable: boolean
  event_count: number
}

export interface Neighbor {
  local_interface: string
  remote_hostname: string
  remote_interface: string
  remote_platform: string
  remote_ip: string | null
  discovery_protocol: string
}

export interface NeighborParseResult {
  device_id: string
  local_interface: string
  remote_interface: string
  matched_device_id: string | null
  match_status: string
  matched_hostname?: string
}

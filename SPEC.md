# Synthetic Network Emulator Platform - Complete Specification

**Version:** 1.0.0-draft
**Date:** 2026-03-28
**Status:** DRAFT - Awaiting Review
**Authors:** Architecture Team

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Logical Data Model](#3-logical-data-model)
4. [State Model vs Output Model](#4-state-model-vs-output-model)
5. [Protocol Emulation Specifications](#5-protocol-emulation-specifications)
6. [Scale & Networking Model](#6-scale--networking-model)
7. [CLI Output Modeling System](#7-cli-output-modeling-system)
8. [Rendering Engine](#8-rendering-engine)
9. [Scenario & Fault Engine](#9-scenario--fault-engine)
10. [API Specification](#10-api-specification)
11. [UI/UX Specification](#11-uiux-specification)
12. [Storage Strategy](#12-storage-strategy)
13. [Performance & Scalability](#13-performance--scalability)
14. [Security Model](#14-security-model)
15. [MVP Definition](#15-mvp-definition)
16. [Phased Roadmap](#16-phased-roadmap)
17. [Risks & Tradeoffs](#17-risks--tradeoffs)
18. [Testing Strategy](#18-testing-strategy)

---

# 1. Executive Summary

## 1.1 What We Are Building

The Synthetic Network Emulator Platform (SNEP) is a software system that emulates enterprise network devices at the **protocol interaction layer** -- SSH CLI and SNMP -- without simulating actual packet forwarding, routing protocols, or control plane behavior.

SNEP presents itself to external tools as a fleet of real network devices. An automation framework like Nornir can SSH into an emulated Cisco IOS switch, run `show interfaces`, and receive output that is structurally identical to what a real device would produce. An SNMP polling system can walk IF-MIB on that same device and receive counters consistent with the CLI output. The system maintains a single internal state model from which all protocol responses are derived, ensuring cross-protocol consistency.

The platform operates in two complementary modes:

- **Static Replay Mode:** Users paste real CLI output captured from production devices. The system replays that output verbatim when the corresponding command is issued over SSH.
- **Structured Rendering Mode:** The system maintains structured state (interfaces, counters, neighbors) and generates CLI/SNMP output dynamically from that state using platform-specific templates.

Both modes can coexist on the same device -- some commands may replay static output while others render from state.

## 1.2 Why It Matters

Network automation development today faces a fundamental tooling gap:

1. **Real hardware labs** are expensive, slow to provision, and impossible to share across distributed teams.
2. **Simulation platforms** (GNS3, EVE-NG) run actual device images, consuming enormous resources -- a 50-device lab can require 100+ GB of RAM and licensed firmware images.
3. **Mock tools** are ad hoc, fragile, and cannot emulate protocol behavior realistically enough to validate parsers or automation workflows.

SNEP fills the gap by providing:

- **Lightweight emulation** -- thousands of devices on a single machine with no vendor firmware required.
- **Protocol fidelity** -- outputs that pass through TextFSM, Genie, and NTC-Templates parsers without modification.
- **Cross-protocol consistency** -- a state change propagates to CLI, SNMP, and topology simultaneously.
- **Scenario simulation** -- inject faults, degrade counters, drop neighbors, and observe how automation handles it.
- **Zero licensing** -- no vendor images, no EULA compliance, fully open-source.

## 1.3 Key Differentiators

| Dimension | GNS3 / EVE-NG | Real Hardware Labs | Mock CLI Tools | SNEP |
|---|---|---|---|---|
| Resource cost per device | ~2 GB RAM | Physical hardware | ~0 | ~2-5 MB RAM |
| Max practical devices | 20-50 | Limited by budget | Unlimited (no protocol) | 5,000-10,000 |
| Requires vendor firmware | Yes | Yes | No | No |
| SSH protocol fidelity | Full (real OS) | Full | Partial | High (emulated) |
| SNMP support | Full (real OS) | Full | Rarely | High (emulated) |
| Cross-protocol consistency | Inherent (real OS) | Inherent | None | Enforced by state model |
| Scenario/fault injection | Manual/limited | Manual | None | Built-in engine |
| Parser compatibility | Full | Full | Variable | Designed for it |
| Multi-tenant cloud hosting | No | No | N/A | Yes |
| Setup time for 100 devices | Hours | Days/weeks | Minutes (no protocol) | Minutes |
| Licensing concerns | Yes (IOS images) | Yes (SmartNet) | None | None |

## 1.4 Target Users

1. **Network automation engineers** developing and testing Nornir, Ansible, or custom automation against realistic device fleets.
2. **Parser developers** building or validating TextFSM, Genie, or TTP templates against diverse output samples.
3. **Platform teams** building network source-of-truth or incident management systems that consume CLI/SNMP data.
4. **AI/ML researchers** training network-aware agents that interact with devices via SSH or SNMP.
5. **Training and certification** programs that need safe, disposable lab environments.

---

# 2. System Architecture

## 2.1 Architecture Overview

SNEP follows a **shared-service, state-driven architecture**. There are no per-device processes or containers. All devices exist as rows in a database and lightweight in-memory state objects. Protocol services (SSH, SNMP) are shared daemons that multiplex thousands of logical devices over a small number of listeners.

```
                    +------------------+
                    |   Web UI / CLI   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    API Gateway    |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
+---------v------+  +--------v-------+  +-------v--------+
| Inventory &    |  | Scenario       |  | CLI Modeling    |
| State Service  |  | Engine         |  | Service         |
+-------+--------+  +--------+-------+  +-------+--------+
        |                     |                  |
        +----------+----------+------------------+
                   |
          +--------v---------+
          | Rendering Engine  |
          +--------+---------+
                   |
        +----------+----------+
        |                     |
+-------v--------+   +-------v--------+
| SSH Emulation  |   | SNMP Emulation |
| Service        |   | Service        |
+----------------+   +----------------+
```

## 2.2 Core Services

### 2.2.1 Inventory & State Service

**Responsibility:** Owns the canonical state of all devices, interfaces, neighbors, counters, and topology. This is the single source of truth.

**Key behaviors:**
- CRUD operations for all state entities (devices, interfaces, links, etc.)
- Publishes state-change events when any entity is modified
- Maintains counter progression (bytes in/out, packets, errors) via configurable rate models
- Provides snapshot reads for rendering (point-in-time consistent views)
- Enforces referential integrity (deleting a device cascades to its interfaces, links, etc.)

**Interfaces:**
- Internal gRPC API consumed by other services
- Exposes state via the REST/GraphQL API Gateway for external consumers

**State ownership boundaries:**

| Entity | Owned by Inventory & State Service |
|---|---|
| Platform definitions | Yes |
| Device models | Yes |
| Devices | Yes |
| Interfaces | Yes |
| Links / Neighbors | Yes |
| Counter values | Yes |
| SNMP profiles | Yes |
| Command templates | No (Rendering Engine) |
| CLI output mappings | No (CLI Modeling Service) |
| Scenarios | No (Scenario Engine) |

### 2.2.2 SSH Emulation Service

**Responsibility:** Accepts inbound SSH connections, authenticates users, identifies the target device, and manages interactive CLI sessions.

**Key behaviors:**
- Listens on configured IP:port combinations (see Section 6 for networking model)
- Maps incoming connections to a device identity based on destination IP/port
- Authenticates using per-device or global credentials
- Presents platform-appropriate prompts (e.g., `Router1#` for Cisco IOS)
- Parses entered commands and routes them to the Rendering Engine
- Returns rendered output to the SSH session
- Emulates terminal behavior: paging, line width, `terminal length 0`
- Supports session modes: user exec, privileged exec, global config
- Handles unknown commands with platform-appropriate error messages

**Concurrency model:** Single async process handling all SSH sessions via an event loop. Each session is a lightweight coroutine, not a thread or process.

### 2.2.3 SNMP Emulation Service

**Responsibility:** Accepts inbound SNMP requests (GET, GETNEXT, GETBULK) and returns OID values derived from device state.

**Key behaviors:**
- Listens on configured UDP IP:port combinations
- Maps incoming requests to a device identity based on destination IP/port and community string or SNMPv3 context
- Resolves OIDs against the device's SNMP profile and current state
- Returns values with correct ASN.1 types (Integer32, Counter32, Counter64, OctetString, etc.)
- Supports SNMP WALK by correctly implementing GETNEXT traversal order
- Supports GETBULK with configurable max-repetitions
- Counters are derived from the state model and advance based on configured rates

**Concurrency model:** Single async process handling all SNMP UDP packets.

### 2.2.4 Rendering Engine

**Responsibility:** Transforms structured device state into protocol-specific output (CLI text, SNMP values).

**Key behaviors:**
- Maintains a library of command templates per platform
- Resolves templates by (platform, command) lookup
- Substitutes state variables into templates
- Handles conditional sections (e.g., omit LLDP neighbor block if no neighbors exist)
- Produces platform-authentic formatting (column alignment, whitespace, header/footer)
- For SNMP: maps state fields to OID values with correct types
- Falls back to static replay output when no template exists for a command

**Template resolution order:**
1. Device-specific override (if exists)
2. Device-model-specific template
3. Platform-level template
4. Static CLI output mapping (verbatim replay)
5. Unknown command error response

### 2.2.5 Scenario Engine

**Responsibility:** Orchestrates state changes over time to simulate network events, faults, and incidents.

**Key behaviors:**
- Executes named scenarios composed of ordered events
- Events modify state via the Inventory & State Service
- Supports time-based triggers (at T+30s, set interface GigabitEthernet0/1 to down)
- Supports manual triggers (user clicks "execute" or calls API)
- Supports conditional triggers (when counter X exceeds threshold, fire event Y)
- Scenarios can be paused, resumed, and rewound
- All state changes are applied through the same path as manual edits, ensuring rendering consistency

**Event types:**
- `interface_state_change` -- toggle admin/oper status
- `counter_spike` -- inject abnormal counter values
- `neighbor_change` -- add or remove a neighbor relationship
- `log_event` -- generate a syslog-style message
- `device_state_change` -- toggle device reachability
- `bulk_update` -- apply multiple changes atomically

### 2.2.6 CLI Modeling Service

**Responsibility:** Manages the import, annotation, and storage of real CLI output samples and their field mappings.

**Key behaviors:**
- Accepts raw CLI text pasted by users
- Provides annotation tooling metadata (field boundaries, types, entity mappings)
- Stores annotated mappings: which substrings correspond to which state fields
- Supports both "static replay" (return verbatim) and "structured extraction" (parse into state)
- Validates that annotated fields are consistent with the data model

### 2.2.7 API Gateway

**Responsibility:** Exposes a unified REST API for all external interactions -- UI, CI/CD, scripting.

**Key behaviors:**
- Routes requests to appropriate internal services
- Handles authentication and authorization
- Rate limiting and request validation
- OpenAPI 3.1 schema published and versioned

## 2.3 Data Flow

### 2.3.1 SSH Command Flow

```
SSH Client
  |
  v
SSH Emulation Service
  |-- identifies device from connection mapping
  |-- authenticates session
  |-- parses command string
  |
  v
Rendering Engine
  |-- looks up template for (platform, command)
  |-- fetches current state from Inventory & State Service
  |-- renders output
  |
  v
SSH Emulation Service
  |-- applies paging / terminal formatting
  |-- sends output to client
```

### 2.3.2 SNMP Request Flow

```
SNMP Client
  |
  v
SNMP Emulation Service
  |-- identifies device from connection mapping + community/context
  |-- resolves OID
  |
  v
Rendering Engine
  |-- maps OID to state field(s)
  |-- fetches current state from Inventory & State Service
  |-- computes value with correct ASN.1 type
  |
  v
SNMP Emulation Service
  |-- encodes SNMP response PDU
  |-- sends UDP response
```

### 2.3.3 Scenario Execution Flow

```
User / API / Timer
  |
  v
Scenario Engine
  |-- loads scenario definition
  |-- for each event at trigger time:
  |     |
  |     v
  |   Inventory & State Service
  |     |-- applies state mutation
  |     |-- publishes state-change event
  |
  v
(next SSH/SNMP request sees updated state)
```

## 2.4 Deployment Models

### 2.4.1 Local Development Mode

All services run in a single Docker Compose stack on one machine.

**Containers:**
- `postgres` -- database
- `snep-core` -- runs Inventory & State Service, Rendering Engine, CLI Modeling Service, Scenario Engine as a single process with internal module boundaries
- `snep-ssh` -- SSH Emulation Service (needs to bind many ports)
- `snep-snmp` -- SNMP Emulation Service (needs to bind UDP ports)
- `snep-api` -- API Gateway + Web UI (static assets served by the API process)

**Why separate SSH and SNMP containers:** These services bind to potentially thousands of IP:port combinations and benefit from independent resource allocation and restart isolation. The core logic remains in `snep-core`.

**Resource profile:** A 100-device deployment should run comfortably on a laptop with 4 GB RAM allocated to Docker.

### 2.4.2 Distributed Cloud Mode

For multi-tenant SaaS deployment:

**Additions to local mode:**
- PostgreSQL replaced with managed database (e.g., RDS, Cloud SQL)
- Redis added for cross-service event bus and session state caching
- API Gateway placed behind a load balancer with TLS termination
- SSH Emulation Service runs in a dedicated instance pool (SSH is long-lived and CPU-light but connection-heavy)
- SNMP Emulation Service runs in a dedicated instance pool (UDP, stateless)
- Tenant isolation at the database level (schema-per-tenant or row-level security)
- Object storage (S3/GCS) for bulk import/export of inventories and CLI samples

**Container orchestration:** Kubernetes with:
- SSH service as a DaemonSet or StatefulSet (stable network identity for IP mappings)
- SNMP service as a Deployment (stateless UDP)
- Core service as a Deployment
- API as a Deployment behind an Ingress

---

# 3. Logical Data Model

## 3.1 Entity Relationship Overview

```
Platform
  |
  +-- has many --> DeviceModel
                     |
                     +-- has many --> Device
                                       |
                                       +-- has many --> Interface
                                       |                  |
                                       |                  +-- has many --> InterfaceCounter
                                       |
                                       +-- has one --> SNMPProfile
                                       |
                                       +-- has many --> DeviceCredential
                                       |
                                       +-- participates in --> Link (via interfaces)

Platform
  |
  +-- has many --> CommandTemplate

Device
  |
  +-- has many --> CLIOutputMapping

Scenario
  |
  +-- has many --> ScenarioEvent
                     |
                     +-- targets --> Device / Interface / Link
```

## 3.2 Entity Definitions

### 3.2.1 Platform

Represents a network operating system family (e.g., Cisco IOS, Arista EOS, Juniper Junos).

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `name` | String(64) | Yes | Unique display name (e.g., "cisco_ios") |
| `display_name` | String(128) | Yes | Human-readable name (e.g., "Cisco IOS") |
| `vendor` | String(64) | Yes | Vendor name |
| `prompt_template` | String(256) | Yes | Template for CLI prompt (e.g., `{hostname}#`) |
| `error_template` | String(512) | Yes | Template for unknown command error |
| `cli_modes` | JSONB | Yes | Definition of supported CLI modes and transitions |
| `default_credentials` | JSONB | No | Default SSH username/password for this platform |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `name` must be unique
- `name` must match pattern `[a-z][a-z0-9_]*` (used as identifier in templates and API)

**Example:**

```yaml
id: "a1b2c3d4-0001-0001-0001-000000000001"
name: "cisco_ios"
display_name: "Cisco IOS"
vendor: "Cisco"
prompt_template: "{hostname}{mode_char}"
error_template: "% Invalid input detected at '^' marker.\n\n{hostname}{mode_char}"
cli_modes:
  user_exec:
    prompt_char: ">"
    transitions:
      enable: privileged_exec
  privileged_exec:
    prompt_char: "#"
    transitions:
      configure terminal: global_config
      disable: user_exec
  global_config:
    prompt_char: "(config)#"
    transitions:
      exit: privileged_exec
      end: privileged_exec
      interface: interface_config
  interface_config:
    prompt_char: "(config-if)#"
    transitions:
      exit: global_config
      end: privileged_exec
default_credentials:
  username: "admin"
  password: "admin"
```

### 3.2.2 DeviceModel

Represents a specific hardware model within a platform (e.g., Cisco Catalyst 9300, Arista 7050X3).

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `platform_id` | UUID (FK) | Yes | References Platform |
| `name` | String(128) | Yes | Model identifier (e.g., "catalyst_9300") |
| `display_name` | String(256) | Yes | Human-readable (e.g., "Cisco Catalyst 9300-48T") |
| `default_interface_pattern` | JSONB | Yes | Default interfaces this model ships with |
| `software_version` | String(64) | Yes | Default OS version string |
| `hardware_details` | JSONB | No | Chassis, serial format, memory, flash, etc. |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(platform_id, name)` must be unique

**Example:**

```yaml
id: "b2c3d4e5-0002-0002-0002-000000000001"
platform_id: "a1b2c3d4-0001-0001-0001-000000000001"  # cisco_ios
name: "catalyst_9300_48t"
display_name: "Cisco Catalyst 9300-48T"
software_version: "17.06.05"
default_interface_pattern:
  - prefix: "GigabitEthernet1/0/"
    range: [1, 48]
    type: "ethernet"
    speed: 1000
  - prefix: "TenGigabitEthernet1/1/"
    range: [1, 4]
    type: "ethernet"
    speed: 10000
  - prefix: "Loopback"
    range: [0, 0]
    type: "loopback"
    speed: 0
  - prefix: "Vlan"
    range: [1, 1]
    type: "vlan"
    speed: 0
hardware_details:
  chassis: "C9300-48T"
  serial_prefix: "FCW"
  serial_length: 11
  memory_mb: 8192
  flash_mb: 16384
  uptime_base: "2 years, 14 weeks, 3 days, 7 hours, 22 minutes"
```

### 3.2.3 Device

An individual emulated network device.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_model_id` | UUID (FK) | Yes | References DeviceModel |
| `hostname` | String(64) | Yes | Device hostname (used in prompts) |
| `management_ip` | INET | No | Emulated management IP for display in outputs |
| `serial_number` | String(32) | Yes | Emulated serial number |
| `software_version` | String(64) | No | Override of model default |
| `uptime_seconds` | BigInt | Yes | Current emulated uptime, advances in real time |
| `uptime_reference` | Timestamp | Yes | Real-world timestamp when uptime_seconds was set |
| `admin_state` | Enum | Yes | `active`, `maintenance`, `decommissioned` |
| `tags` | JSONB | No | Arbitrary key-value metadata |
| `emulation_config` | JSONB | No | Per-device overrides (SSH port, etc.) |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `hostname` must be unique within a tenant/environment
- `serial_number` must be unique within a tenant/environment
- `admin_state` defaults to `active`

**Derived fields (computed, not stored):**
- `current_uptime`: `uptime_seconds + (now() - uptime_reference)` in seconds
- `platform`: resolved via `device_model.platform`
- `platform_name`: resolved via `device_model.platform.name`

**Example:**

```yaml
id: "c3d4e5f6-0003-0003-0003-000000000001"
device_model_id: "b2c3d4e5-0002-0002-0002-000000000001"  # catalyst_9300_48t
hostname: "core-rtr-01"
management_ip: "10.1.1.1"
serial_number: "FCW2145L0RN"
software_version: null  # uses model default "17.06.05"
uptime_seconds: 7776000  # 90 days
uptime_reference: "2026-03-28T00:00:00Z"
admin_state: "active"
tags:
  site: "dc-east"
  role: "core"
  environment: "production"
emulation_config:
  ssh_port_override: null
  snmp_port_override: null
```

### 3.2.4 Interface

A network interface on a device. Interfaces are the primary state-bearing entity.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_id` | UUID (FK) | Yes | References Device |
| `name` | String(128) | Yes | Full interface name (e.g., "GigabitEthernet1/0/1") |
| `short_name` | String(64) | Yes | Abbreviated name (e.g., "Gi1/0/1") |
| `if_index` | Integer | Yes | SNMP ifIndex value |
| `interface_type` | Enum | Yes | `ethernet`, `loopback`, `vlan`, `port_channel`, `tunnel`, `management` |
| `admin_status` | Enum | Yes | `up`, `down` |
| `oper_status` | Enum | Yes | `up`, `down`, `dormant`, `notPresent`, `lowerLayerDown` |
| `speed_mbps` | Integer | Yes | Interface speed in Mbps |
| `duplex` | Enum | No | `full`, `half`, `auto` |
| `mtu` | Integer | Yes | MTU in bytes (default 1500) |
| `mac_address` | String(17) | Yes | MAC address (format: "aabb.ccdd.eeff") |
| `ip_address` | INET | No | Primary IPv4 address with prefix |
| `ipv6_address` | INET | No | Primary IPv6 address with prefix |
| `description` | String(256) | No | Interface description |
| `vlan_id` | Integer | No | Access VLAN if applicable |
| `is_trunk` | Boolean | No | Whether interface is a trunk port |
| `allowed_vlans` | String(512) | No | Allowed VLAN list for trunk |
| `last_input` | Interval | No | Time since last input (for show interface) |
| `last_output` | Interval | No | Time since last output |
| `last_state_change` | Timestamp | Yes | When oper_status last changed |
| `sort_order` | Integer | Yes | For deterministic ordering in outputs |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(device_id, name)` must be unique
- `(device_id, if_index)` must be unique
- `if_index` must be > 0
- `mac_address` must be valid MAC format
- `speed_mbps` must be >= 0

**Example:**

```yaml
id: "d4e5f6a7-0004-0004-0004-000000000001"
device_id: "c3d4e5f6-0003-0003-0003-000000000001"  # core-rtr-01
name: "GigabitEthernet1/0/1"
short_name: "Gi1/0/1"
if_index: 1
interface_type: "ethernet"
admin_status: "up"
oper_status: "up"
speed_mbps: 1000
duplex: "full"
mtu: 1500
mac_address: "aabb.cc01.0001"
ip_address: "10.0.1.1/30"
description: "Uplink to dist-sw-01 Gi1/0/49"
vlan_id: null
is_trunk: false
allowed_vlans: null
last_input: "00:00:03"
last_output: "00:00:01"
last_state_change: "2026-01-15T10:30:00Z"
sort_order: 1
```

### 3.2.5 InterfaceCounter

Counters for an interface. Stored separately to enable efficient counter progression.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `interface_id` | UUID (FK) | Yes | References Interface |
| `in_octets` | BigInt | Yes | Input bytes (maps to ifInOctets / ifHCInOctets) |
| `out_octets` | BigInt | Yes | Output bytes |
| `in_unicast_pkts` | BigInt | Yes | Input unicast packets |
| `out_unicast_pkts` | BigInt | Yes | Output unicast packets |
| `in_multicast_pkts` | BigInt | Yes | Input multicast packets |
| `out_multicast_pkts` | BigInt | Yes | Output multicast packets |
| `in_broadcast_pkts` | BigInt | Yes | Input broadcast packets |
| `out_broadcast_pkts` | BigInt | Yes | Output broadcast packets |
| `in_errors` | BigInt | Yes | Input errors |
| `out_errors` | BigInt | Yes | Output errors |
| `in_discards` | BigInt | Yes | Input discards |
| `out_discards` | BigInt | Yes | Output discards |
| `crc_errors` | BigInt | Yes | CRC errors |
| `collisions` | BigInt | Yes | Collisions |
| `rate_in_bps` | BigInt | Yes | Current configured input rate (bits/sec) for progression |
| `rate_out_bps` | BigInt | Yes | Current configured output rate (bits/sec) for progression |
| `rate_reference` | Timestamp | Yes | When the rates were last set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Counter progression model:**
- `current_in_octets = in_octets + ((now() - rate_reference) * rate_in_bps / 8)`
- Rates are configurable per-interface; default rates are derived from interface utilization targets
- When `oper_status` goes to `down`, rates are set to 0 and base counters are frozen
- Counter wrapping follows SNMP standards: Counter32 wraps at 2^32, Counter64 wraps at 2^64

**Constraints:**
- One-to-one with Interface
- All counter values must be >= 0

**Example:**

```yaml
id: "e5f6a7b8-0005-0005-0005-000000000001"
interface_id: "d4e5f6a7-0004-0004-0004-000000000001"  # Gi1/0/1
in_octets: 584792031847
out_octets: 291034958271
in_unicast_pkts: 4839201748
out_unicast_pkts: 2419384751
in_multicast_pkts: 12847291
out_multicast_pkts: 8471023
in_broadcast_pkts: 847102
out_broadcast_pkts: 423551
in_errors: 0
out_errors: 0
in_discards: 142
out_discards: 0
crc_errors: 0
collisions: 0
rate_in_bps: 450000000    # ~450 Mbps
rate_out_bps: 225000000   # ~225 Mbps
rate_reference: "2026-03-28T00:00:00Z"
```

### 3.2.6 Link

Represents a physical or logical connection between two interfaces on different devices. Links establish neighbor relationships.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `interface_a_id` | UUID (FK) | Yes | References Interface (side A) |
| `interface_b_id` | UUID (FK) | Yes | References Interface (side B) |
| `link_type` | Enum | Yes | `physical`, `logical`, `virtual` |
| `discovery_protocol` | Enum | Yes | `cdp`, `lldp`, `both`, `none` |
| `admin_state` | Enum | Yes | `up`, `down` |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(interface_a_id, interface_b_id)` must be unique (unordered -- the pair is stored with the lower UUID first to prevent duplicates)
- Both interfaces must be on different devices
- A link being `down` or either interface being operationally `down` means the neighbor relationship is not visible in CDP/LLDP output

**Derived neighbor data (computed from link + device + interface state):**
- For device A looking at a CDP neighbor:
  - `device_id` = device owning interface_b
  - `remote_hostname` = that device's hostname
  - `remote_interface` = interface_b name
  - `remote_platform` = that device's model display_name
  - `remote_ip` = interface_b IP address

**Example:**

```yaml
id: "f6a7b8c9-0006-0006-0006-000000000001"
interface_a_id: "d4e5f6a7-0004-0004-0004-000000000001"  # core-rtr-01 Gi1/0/1
interface_b_id: "d4e5f6a7-0004-0004-0004-000000000099"  # dist-sw-01 Gi1/0/49
link_type: "physical"
discovery_protocol: "cdp"
admin_state: "up"
```

### 3.2.7 CommandTemplate

Defines how to render a specific command's output for a given platform.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `platform_id` | UUID (FK) | Yes | References Platform |
| `device_model_id` | UUID (FK) | No | Optional: model-specific override |
| `command_pattern` | String(256) | Yes | Regex or exact match for the command string |
| `command_canonical` | String(256) | Yes | Canonical form (e.g., "show interfaces") |
| `template_body` | Text | Yes | Jinja2-style template text |
| `required_state` | JSONB | Yes | Lists state fields the template needs |
| `output_type` | Enum | Yes | `tabular`, `freeform`, `structured` |
| `platform_version_min` | String(32) | No | Minimum software version |
| `platform_version_max` | String(32) | No | Maximum software version |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(platform_id, device_model_id, command_canonical)` must be unique
- `command_pattern` must be a valid regex

**Example:**

```yaml
id: "a7b8c9d0-0007-0007-0007-000000000001"
platform_id: "a1b2c3d4-0001-0001-0001-000000000001"  # cisco_ios
device_model_id: null  # applies to all Cisco IOS devices
command_pattern: "^show ip interface brief$"
command_canonical: "show ip interface brief"
template_body: |
  Interface                  IP-Address      OK? Method Status                Protocol
  {% for iface in interfaces | sort(attribute='sort_order') %}
  {{ iface.name | ljust(27) }}{{ (iface.ip_address | default('unassigned')) | ljust(16) }}YES {{ 'manual' | ljust(7) }}{{ iface.admin_status | ljust(22) }}{{ iface.oper_status }}
  {% endfor %}
required_state:
  - "interfaces.name"
  - "interfaces.ip_address"
  - "interfaces.admin_status"
  - "interfaces.oper_status"
output_type: "tabular"
```

### 3.2.8 SNMPProfile

SNMP configuration for a device.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_id` | UUID (FK) | Yes | References Device (one-to-one) |
| `v2_enabled` | Boolean | Yes | Whether SNMPv2 is enabled |
| `v2_community` | String(64) | No | SNMPv2 community string |
| `v3_enabled` | Boolean | Yes | Whether SNMPv3 is enabled |
| `v3_username` | String(64) | No | SNMPv3 username |
| `v3_auth_protocol` | Enum | No | `md5`, `sha`, `sha256`, `sha512` |
| `v3_auth_password` | String(128) | No | SNMPv3 auth password |
| `v3_priv_protocol` | Enum | No | `des`, `aes128`, `aes256` |
| `v3_priv_password` | String(128) | No | SNMPv3 priv password |
| `v3_context` | String(64) | No | SNMPv3 context name |
| `sys_descr` | String(512) | No | Override for sysDescr.0 |
| `sys_contact` | String(256) | No | sysContact.0 value |
| `sys_name` | String(256) | No | sysName.0 (defaults to device hostname) |
| `sys_location` | String(256) | No | sysLocation.0 |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- One-to-one with Device
- If `v2_enabled`, `v2_community` is required
- If `v3_enabled`, `v3_username` is required
- If `v3_auth_protocol` is set, `v3_auth_password` is required
- If `v3_priv_protocol` is set, `v3_priv_password` and `v3_auth_protocol` are both required

**Example:**

```yaml
id: "b8c9d0e1-0008-0008-0008-000000000001"
device_id: "c3d4e5f6-0003-0003-0003-000000000001"  # core-rtr-01
v2_enabled: true
v2_community: "public"
v3_enabled: true
v3_username: "snmpuser"
v3_auth_protocol: "sha256"
v3_auth_password: "authpass123"
v3_priv_protocol: "aes128"
v3_priv_password: "privpass456"
v3_context: null
sys_descr: null  # derived from platform + model + version
sys_contact: "noc@example.com"
sys_name: null   # defaults to device hostname
sys_location: "DC-East Rack A14 U22"
```

### 3.2.9 DeviceCredential

SSH/CLI credentials for a device.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_id` | UUID (FK) | Yes | References Device |
| `username` | String(64) | Yes | SSH username |
| `password` | String(128) | Yes | SSH password (stored encrypted at rest) |
| `enable_password` | String(128) | No | Enable mode password |
| `privilege_level` | Integer | Yes | Initial privilege level (0-15, default 1) |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(device_id, username)` must be unique
- `privilege_level` must be between 0 and 15

**Example:**

```yaml
id: "c9d0e1f2-0009-0009-0009-000000000001"
device_id: "c3d4e5f6-0003-0003-0003-000000000001"
username: "admin"
password: "cisco123"
enable_password: "enable456"
privilege_level: 1
```

### 3.2.10 CLIOutputMapping

Stores a pasted CLI output sample and its field annotations for a specific command on a specific device.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_id` | UUID (FK) | Yes | References Device |
| `command` | String(256) | Yes | Exact command string |
| `raw_output` | Text | Yes | Original pasted CLI output |
| `mode` | Enum | Yes | `static` (replay verbatim) or `mapped` (fields extracted) |
| `field_annotations` | JSONB | No | Array of field mappings (see below) |
| `is_active` | Boolean | Yes | Whether this mapping is currently used |
| `source_description` | String(256) | No | Where this output came from |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Field annotation structure:**

```yaml
field_annotations:
  - field_name: "hostname"
    start_offset: 142      # character offset in raw_output
    end_offset: 153
    value: "core-rtr-01"
    maps_to: "device.hostname"
    data_type: "string"

  - field_name: "interface_name"
    start_offset: 312
    end_offset: 332
    value: "GigabitEthernet1/0/1"
    maps_to: "interface.name"
    data_type: "string"
    context:
      interface_match: "GigabitEthernet1/0/1"

  - field_name: "in_octets"
    start_offset: 487
    end_offset: 502
    value: "584792031847"
    maps_to: "interface_counter.in_octets"
    data_type: "integer"
    context:
      interface_match: "GigabitEthernet1/0/1"
```

**Constraints:**
- `(device_id, command, is_active)` -- only one active mapping per device+command
- If `mode` is `mapped`, `field_annotations` must not be empty
- If `mode` is `static`, `field_annotations` may be null

**Example:**

```yaml
id: "d0e1f2a3-0010-0010-0010-000000000001"
device_id: "c3d4e5f6-0003-0003-0003-000000000001"
command: "show version"
raw_output: |
  Cisco IOS XE Software, Version 17.06.05
  Cisco IOS Software [Bengaluru], Catalyst L3 Switch Software (CAT9K_IOSXE), Version 17.06.05, RELEASE SOFTWARE (fc2)
  Technical Support: http://www.cisco.com/techsupport
  ...
mode: "static"
field_annotations: null
is_active: true
source_description: "Captured from lab device core-rtr-01 on 2026-03-15"
```

### 3.2.11 Scenario

A named collection of events that simulate a network incident or change.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `name` | String(128) | Yes | Unique scenario name |
| `description` | Text | No | What this scenario simulates |
| `status` | Enum | Yes | `draft`, `ready`, `running`, `paused`, `completed` |
| `is_repeatable` | Boolean | Yes | Whether scenario can be run multiple times |
| `created_at` | Timestamp | Yes | Auto-set |
| `updated_at` | Timestamp | Yes | Auto-set |

**Example:**

```yaml
id: "e1f2a3b4-0011-0011-0011-000000000001"
name: "uplink-failure-dc-east"
description: "Simulates a fiber cut on the DC-East core uplink, causing interface down, neighbor loss, and traffic reroute."
status: "ready"
is_repeatable: true
```

### 3.2.12 ScenarioEvent

An individual state mutation within a scenario.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `scenario_id` | UUID (FK) | Yes | References Scenario |
| `sequence_order` | Integer | Yes | Execution order within the scenario |
| `trigger_type` | Enum | Yes | `immediate`, `delay`, `manual`, `conditional` |
| `trigger_config` | JSONB | Yes | Trigger parameters (see below) |
| `action_type` | Enum | Yes | See action types below |
| `action_config` | JSONB | Yes | Action parameters |
| `rollback_action` | JSONB | No | How to undo this event (for scenario reset) |
| `created_at` | Timestamp | Yes | Auto-set |

**Trigger types:**
- `immediate` -- fires as soon as the previous event completes
- `delay` -- fires after a specified duration: `{ "delay_seconds": 30 }`
- `manual` -- waits for user/API trigger
- `conditional` -- fires when a condition is met: `{ "field": "interface.in_errors", "operator": "gt", "value": 1000, "check_interval_seconds": 5 }`

**Action types:**
- `interface_state_change` -- `{ "interface_id": "...", "oper_status": "down" }`
- `interface_admin_change` -- `{ "interface_id": "...", "admin_status": "down" }`
- `counter_set` -- `{ "interface_id": "...", "counter_name": "in_errors", "value": 5000 }`
- `counter_rate_change` -- `{ "interface_id": "...", "rate_in_bps": 950000000 }`
- `link_state_change` -- `{ "link_id": "...", "admin_state": "down" }`
- `device_state_change` -- `{ "device_id": "...", "admin_state": "maintenance" }`
- `log_event` -- `{ "device_id": "...", "severity": "warning", "message": "..." }`
- `bulk_update` -- `{ "updates": [ ... ] }` (array of any of the above)

**Example:**

```yaml
# Event 1: Interface goes down immediately
- id: "f2a3b4c5-0012-0012-0012-000000000001"
  scenario_id: "e1f2a3b4-0011-0011-0011-000000000001"
  sequence_order: 1
  trigger_type: "immediate"
  trigger_config: {}
  action_type: "interface_state_change"
  action_config:
    interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
    oper_status: "down"
  rollback_action:
    action_type: "interface_state_change"
    action_config:
      interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
      oper_status: "up"

# Event 2: Errors spike 30 seconds later
- id: "f2a3b4c5-0012-0012-0012-000000000002"
  scenario_id: "e1f2a3b4-0011-0011-0011-000000000001"
  sequence_order: 2
  trigger_type: "delay"
  trigger_config:
    delay_seconds: 30
  action_type: "counter_set"
  action_config:
    interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
    counter_name: "in_errors"
    value: 15847
  rollback_action:
    action_type: "counter_set"
    action_config:
      interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
      counter_name: "in_errors"
      value: 0

# Event 3: Log message generated
- id: "f2a3b4c5-0012-0012-0012-000000000003"
  scenario_id: "e1f2a3b4-0011-0011-0011-000000000001"
  sequence_order: 3
  trigger_type: "immediate"
  trigger_config: {}
  action_type: "log_event"
  action_config:
    device_id: "c3d4e5f6-0003-0003-0003-000000000001"
    severity: "critical"
    message: "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down"
  rollback_action: null  # logs are not rolled back
```

### 3.2.13 ConnectionMapping

Maps inbound network connections to device identities. This is how the SSH/SNMP services know which device a connection is targeting.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `device_id` | UUID (FK) | Yes | References Device |
| `protocol` | Enum | Yes | `ssh`, `snmp` |
| `listen_address` | INET | Yes | IP address to listen on |
| `listen_port` | Integer | Yes | Port to listen on |
| `created_at` | Timestamp | Yes | Auto-set |

**Constraints:**
- `(protocol, listen_address, listen_port)` must be unique
- `listen_port` must be in valid range (1-65535)

**Example:**

```yaml
# Loopback alias model: each device gets its own IP on standard ports
- id: "a3b4c5d6-0013-0013-0013-000000000001"
  device_id: "c3d4e5f6-0003-0003-0003-000000000001"  # core-rtr-01
  protocol: "ssh"
  listen_address: "127.0.0.1"
  listen_port: 10022

- id: "a3b4c5d6-0013-0013-0013-000000000002"
  device_id: "c3d4e5f6-0003-0003-0003-000000000001"  # core-rtr-01
  protocol: "snmp"
  listen_address: "127.0.0.1"
  listen_port: 10161
```

---

# 4. State Model vs Output Model

## 4.1 Fundamental Principle

The system maintains a **single canonical state** from which all outputs are **derived**. There is no separate "CLI state" or "SNMP state." The state model described in Section 3 is the only source of truth.

```
+-------------------+
|   Canonical       |
|   State Model     |
|   (DB + Memory)   |
+--------+----------+
         |
    +----+----+----+----+
    |         |         |
    v         v         v
  CLI      SNMP     Topology
 Output   Response   View
```

## 4.2 State-to-Output Derivation Rules

Every output the system produces must be traceable to one or more state fields. The following table defines how key state fields map to outputs across protocols:

### Interface State Mapping

| State Field | CLI: `show interfaces` | CLI: `show ip int brief` | SNMP: IF-MIB | Topology View |
|---|---|---|---|---|
| `interface.name` | Full interface header | Interface column | `ifDescr` (1.3.6.1.2.1.2.2.1.2) | Node port label |
| `interface.admin_status` | "administratively down" or absent | Status column | `ifAdminStatus` (1.3.6.1.2.1.2.2.1.7) | Port color |
| `interface.oper_status` | "up" / "down" in line protocol | Protocol column | `ifOperStatus` (1.3.6.1.2.1.2.2.1.8) | Port color |
| `interface.speed_mbps` | "BW \<x> Kbit" line | -- | `ifSpeed` / `ifHighSpeed` | Tooltip |
| `interface.mtu` | "MTU \<x> bytes" line | -- | `ifMtu` (1.3.6.1.2.1.2.2.1.4) | -- |
| `interface.mac_address` | "Hardware is ... address is" line | -- | `ifPhysAddress` (1.3.6.1.2.1.2.2.1.6) | -- |
| `interface.ip_address` | "Internet address is" line | IP-Address column | ipAddrTable | Tooltip |
| `interface.description` | "Description:" line | -- | `ifAlias` (1.3.6.1.2.1.31.1.1.1.18) | Tooltip |
| `counter.in_octets` | "input" bytes line | -- | `ifInOctets` / `ifHCInOctets` | -- |
| `counter.out_octets` | "output" bytes line | -- | `ifOutOctets` / `ifHCOutOctets` | -- |
| `counter.in_errors` | "input errors" line | -- | `ifInErrors` | -- |
| `counter.in_unicast_pkts` | "packets input" line | -- | `ifInUcastPkts` / `ifHCInUcastPkts` | -- |

### Device State Mapping

| State Field | CLI: `show version` | SNMP: system MIB | Topology View |
|---|---|---|---|
| `device.hostname` | Hostname in output | `sysName.0` | Node label |
| `device.serial_number` | "System serial number" line | Entity MIB (future) | -- |
| `device.current_uptime` | "uptime is" line | `sysUpTime.0` (in timeticks) | Tooltip |
| `device_model.display_name` | Hardware line | `sysDescr.0` | Node icon/type |
| `device_model.software_version` | Software version line | `sysDescr.0` | Tooltip |

### Neighbor/Link State Mapping

| State Field | CLI: `show cdp neighbors` | CLI: `show lldp neighbors` | Topology View |
|---|---|---|---|
| `link` exists + both interfaces up | Row appears in output | Row appears in output | Edge drawn |
| Remote `device.hostname` | Device ID column | System Name | Edge label |
| Remote `interface.name` | Port ID column | Port ID | Edge endpoint |
| Local `interface.name` | Local Intrfce column | Local Intf | Edge endpoint |
| Remote `device_model.display_name` | Platform column | System Description | -- |

## 4.3 Consistency Enforcement Example: Interface Goes Down

When `interface.oper_status` changes from `up` to `down`, the following outputs are affected **simultaneously** without any additional action:

### Step 1: State Mutation
```yaml
# State change applied to Inventory & State Service
interface:
  id: "d4e5f6a7-0004-0004-0004-000000000001"
  oper_status: "down"          # changed from "up"
  last_state_change: "2026-03-28T14:30:00Z"  # updated

interface_counter:
  rate_in_bps: 0               # frozen
  rate_out_bps: 0              # frozen
  rate_reference: "2026-03-28T14:30:00Z"  # reset
```

### Step 2: Derived CLI Output Changes

**`show interfaces GigabitEthernet1/0/1` -- BEFORE:**
```
GigabitEthernet1/0/1 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is aabb.cc01.0001
  Description: Uplink to dist-sw-01 Gi1/0/49
  Internet address is 10.0.1.1/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 115/255, rxload 230/255
  ...
     584792031847 bytes input, 4839201748 packets input, 0 input errors
```

**`show interfaces GigabitEthernet1/0/1` -- AFTER:**
```
GigabitEthernet1/0/1 is up, line protocol is down
  Hardware is Gigabit Ethernet, address is aabb.cc01.0001
  Description: Uplink to dist-sw-01 Gi1/0/49
  Internet address is 10.0.1.1/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 0/255, rxload 0/255
  ...
     584792031847 bytes input, 4839201748 packets input, 0 input errors
```

**`show ip interface brief` -- interface row changes:**
```
GigabitEthernet1/0/1      10.0.1.1        YES manual up                    down
```

**`show cdp neighbors` -- neighbor row DISAPPEARS** because link is no longer viable.

### Step 3: Derived SNMP Changes

| OID | Before | After |
|---|---|---|
| `ifOperStatus.1` (1.3.6.1.2.1.2.2.1.8.1) | `1` (up) | `2` (down) |
| `ifInOctets.1` (1.3.6.1.2.1.2.2.1.10.1) | Advancing | Frozen at last value |
| `ifOutOctets.1` (1.3.6.1.2.1.2.2.1.16.1) | Advancing | Frozen at last value |
| `ifLastChange.1` (1.3.6.1.2.1.2.2.1.9.1) | Previous value | Updated to current sysUpTime |

### Step 4: Topology View Changes

- Edge between `core-rtr-01:Gi1/0/1` and `dist-sw-01:Gi1/0/49` changes to red/dashed
- Port indicator on both devices changes to red

### Step 5: Log Generation (if configured)

```
*Mar 28 14:30:00.000: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down
*Mar 28 14:30:01.000: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/0/1, changed state to down
```

All of these changes are **automatic consequences** of the single state mutation. No separate update is needed for CLI, SNMP, or topology -- the rendering engine reads the current state at the time of each request.

## 4.4 Static Replay Interaction with State

When a command has a CLIOutputMapping in `static` mode, the raw output is returned verbatim. This means:

- Static outputs **do not reflect state changes**
- This is intentional for the use case of parser testing with known-good output
- The UI must clearly indicate which commands are in static vs structured mode
- A command can be transitioned from static to structured by creating a CommandTemplate and removing the static mapping

**Resolution priority (repeated from Section 2.2.4 for emphasis):**
1. Device-specific CommandTemplate override
2. DeviceModel-specific CommandTemplate
3. Platform-level CommandTemplate
4. Active CLIOutputMapping (static replay)
5. Unknown command error response

---

# 5. Protocol Emulation Specifications

## 5.1 SSH CLI Emulation

### 5.1.1 Session Lifecycle

```
Client connects (TCP)
  |
  v
SSH handshake (key exchange, encryption)
  |
  v
Authentication (username/password)
  |-- fail --> disconnect after 3 attempts
  |
  v (success)
Banner display (optional, per-device)
  |
  v
Initial mode (user_exec or privileged_exec based on privilege_level)
  |
  v
Command loop:
  |-- display prompt
  |-- read input line
  |-- parse command
  |-- route to rendering engine
  |-- display output
  |-- repeat
  |
  v (on "exit" from top mode, or disconnect)
Session teardown
```

### 5.1.2 Authentication Model

- SSH password authentication is the primary method
- Credentials are checked against DeviceCredential records for the target device
- If no device-specific credentials exist, fall back to Platform.default_credentials
- Failed authentication returns "% Access denied" and allows up to 3 retries before disconnect
- SSH public key authentication is NOT supported in MVP (password only)
- The SSH host key is generated per-installation (not per-device) -- automation tools typically skip host key verification against lab environments

### 5.1.3 Prompt Behavior

The prompt is derived from:
- `device.hostname`
- `platform.prompt_template`
- Current CLI mode's `prompt_char`

**Examples by platform:**

| Platform | User Exec | Privileged Exec | Global Config | Interface Config |
|---|---|---|---|---|
| cisco_ios | `Router>` | `Router#` | `Router(config)#` | `Router(config-if)#` |
| arista_eos | `Router>` | `Router#` | `Router(config)#` | `Router(config-if-Gi1)#` |
| juniper_junos | `user@Router>` | `user@Router>` | `user@Router#` | `user@Router# ` (edit mode) |

The prompt must include:
- No trailing space after the mode character for Cisco/Arista style
- One trailing space after the mode character for Junos style
- Platform definition controls this via `prompt_template`

### 5.1.4 Command Parsing

When the user enters a line of text:

1. **Trim** leading/trailing whitespace
2. **Empty line** -- redisplay prompt, no output
3. **Mode transition commands** (e.g., `enable`, `configure terminal`, `exit`, `end`):
   - Change session mode
   - Display appropriate response (e.g., no output for `enable` if no password, or password prompt if enable_password is set)
4. **Show commands** (e.g., `show interfaces`):
   - Route to Rendering Engine with `(device_id, platform, command_string)`
   - Return rendered output
5. **Configuration commands** (in config mode):
   - In MVP: return acceptance response (next-line prompt) but do NOT actually modify state
   - Post-MVP: parse config commands and modify state (e.g., `shutdown` sets admin_status to down)
6. **Unknown commands**:
   - Return platform-appropriate error from `platform.error_template`
   - Cisco IOS: `% Invalid input detected at '^' marker.`
   - Arista EOS: `% Invalid input (privileged mode required)`

**Command abbreviation:** Cisco IOS and Arista EOS support abbreviated commands. The command parser must support prefix matching:
- `sh int` matches `show interfaces`
- `sh ip int br` matches `show ip interface brief`
- Ambiguous abbreviations return: `% Ambiguous command: "sh i"`

### 5.1.5 Command Routing

The SSH service does NOT render output itself. It sends the parsed command to the Rendering Engine and receives text back. The routing follows the priority order defined in Section 2.2.4 (template resolution order).

If the Rendering Engine returns no match, the SSH service returns the platform's error template.

### 5.1.6 Error Handling

| Error Condition | Behavior |
|---|---|
| Unknown command | Platform error template |
| Command in wrong mode | Platform-specific mode error (e.g., "% Invalid input detected" in user exec for config commands) |
| Command requires arguments | Platform-specific incomplete command error |
| Device in maintenance state | Connection accepted, banner shows "Device is in maintenance mode" |
| Device decommissioned | Connection refused (TCP RST) |

### 5.1.7 Paging Behavior

- Default terminal length: 24 lines (configurable per-session)
- When output exceeds terminal length, display `--More--` prompt
- At `--More--`:
  - Space: next page
  - Enter: next line
  - `q`: abort output
- `terminal length 0` disables paging for the session
- Automation tools typically send `terminal length 0` as their first command -- this must work

### 5.1.8 Mode Handling

Modes are defined per-platform in `Platform.cli_modes`. The SSH service tracks the current mode per-session.

**Mode transitions are platform-specific:**

**Cisco IOS mode tree:**
```
user_exec (>)
  └── enable --> privileged_exec (#)
                   ├── configure terminal --> global_config ((config)#)
                   │     ├── interface X --> interface_config ((config-if)#)
                   │     │     └── exit --> global_config
                   │     ├── router ospf X --> router_config ((config-router)#)
                   │     │     └── exit --> global_config
                   │     └── exit --> privileged_exec
                   └── disable --> user_exec
```

Each mode defines:
- Which commands are valid in that mode
- Which commands trigger mode transitions
- What prompt character to use

Show commands are valid in both `user_exec` and `privileged_exec` modes on Cisco IOS.

### 5.1.9 Minimum Supported Commands (MVP)

| Command | Rendering Mode | Output Source |
|---|---|---|
| `show version` | Structured or Static | Device + DeviceModel state |
| `show interfaces` | Structured | Interface + Counter state |
| `show interfaces <name>` | Structured | Single interface state |
| `show ip interface brief` | Structured | Interface state (tabular) |
| `show cdp neighbors` | Structured | Link + remote Device/Interface state |
| `show cdp neighbors detail` | Structured | Same as above, verbose |
| `show running-config` | Static only (MVP) | CLIOutputMapping |
| `show inventory` | Structured or Static | Device + DeviceModel state |
| `terminal length <n>` | Session control | Modifies paging |
| `enable` | Mode transition | Changes to privileged_exec |
| `disable` | Mode transition | Changes to user_exec |
| `configure terminal` | Mode transition | Changes to global_config |
| `exit` | Mode transition | Returns to parent mode |
| `end` | Mode transition | Returns to privileged_exec |

## 5.2 SNMP Emulation

### 5.2.1 Protocol Support

**SNMPv2c:**
- Community string authentication
- Community string is matched against `SNMPProfile.v2_community` for the target device
- Mismatched community: no response (silent drop, per RFC 3584 behavior)

**SNMPv3:**
- User Security Model (USM) with:
  - `noAuthNoPriv` -- username only
  - `authNoPriv` -- username + authentication (MD5, SHA, SHA-256, SHA-512)
  - `authPriv` -- username + authentication + encryption (DES, AES-128, AES-256)
- Engine ID is derived per-device: `0x80000000` + device UUID hash (first 8 bytes)
- Context name support for device selection (alternative to IP-based mapping)

### 5.2.2 OID Mapping Strategy

OIDs are mapped to state fields through a two-level system:

**Level 1: Static OID Registry**
A built-in registry maps well-known OIDs to state field paths:

| OID | MIB Object | State Field Path | ASN.1 Type |
|---|---|---|---|
| 1.3.6.1.2.1.1.1.0 | sysDescr | device_model.platform.display_name + version | OctetString |
| 1.3.6.1.2.1.1.2.0 | sysObjectID | platform-specific OID | ObjectIdentifier |
| 1.3.6.1.2.1.1.3.0 | sysUpTime | device.current_uptime * 100 (timeticks) | TimeTicks |
| 1.3.6.1.2.1.1.4.0 | sysContact | snmp_profile.sys_contact | OctetString |
| 1.3.6.1.2.1.1.5.0 | sysName | device.hostname | OctetString |
| 1.3.6.1.2.1.1.6.0 | sysLocation | snmp_profile.sys_location | OctetString |
| 1.3.6.1.2.1.2.1.0 | ifNumber | count(device.interfaces) | Integer32 |
| 1.3.6.1.2.1.2.2.1.1.{ifIndex} | ifIndex | interface.if_index | Integer32 |
| 1.3.6.1.2.1.2.2.1.2.{ifIndex} | ifDescr | interface.name | OctetString |
| 1.3.6.1.2.1.2.2.1.3.{ifIndex} | ifType | derived from interface.interface_type | Integer32 |
| 1.3.6.1.2.1.2.2.1.4.{ifIndex} | ifMtu | interface.mtu | Integer32 |
| 1.3.6.1.2.1.2.2.1.5.{ifIndex} | ifSpeed | interface.speed_mbps * 1000000 | Gauge32 |
| 1.3.6.1.2.1.2.2.1.6.{ifIndex} | ifPhysAddress | interface.mac_address | OctetString |
| 1.3.6.1.2.1.2.2.1.7.{ifIndex} | ifAdminStatus | interface.admin_status mapped | Integer32 |
| 1.3.6.1.2.1.2.2.1.8.{ifIndex} | ifOperStatus | interface.oper_status mapped | Integer32 |
| 1.3.6.1.2.1.2.2.1.9.{ifIndex} | ifLastChange | interface.last_state_change as timeticks | TimeTicks |
| 1.3.6.1.2.1.2.2.1.10.{ifIndex} | ifInOctets | counter.current_in_octets mod 2^32 | Counter32 |
| 1.3.6.1.2.1.2.2.1.11.{ifIndex} | ifInUcastPkts | counter.in_unicast_pkts mod 2^32 | Counter32 |
| 1.3.6.1.2.1.2.2.1.13.{ifIndex} | ifInDiscards | counter.in_discards | Counter32 |
| 1.3.6.1.2.1.2.2.1.14.{ifIndex} | ifInErrors | counter.in_errors | Counter32 |
| 1.3.6.1.2.1.2.2.1.16.{ifIndex} | ifOutOctets | counter.current_out_octets mod 2^32 | Counter32 |
| 1.3.6.1.2.1.2.2.1.17.{ifIndex} | ifOutUcastPkts | counter.out_unicast_pkts mod 2^32 | Counter32 |
| 1.3.6.1.2.1.2.2.1.19.{ifIndex} | ifOutDiscards | counter.out_discards | Counter32 |
| 1.3.6.1.2.1.2.2.1.20.{ifIndex} | ifOutErrors | counter.out_errors | Counter32 |
| 1.3.6.1.2.1.31.1.1.1.1.{ifIndex} | ifName | interface.short_name | OctetString |
| 1.3.6.1.2.1.31.1.1.1.6.{ifIndex} | ifHCInOctets | counter.current_in_octets | Counter64 |
| 1.3.6.1.2.1.31.1.1.1.10.{ifIndex} | ifHCOutOctets | counter.current_out_octets | Counter64 |
| 1.3.6.1.2.1.31.1.1.1.15.{ifIndex} | ifHighSpeed | interface.speed_mbps | Gauge32 |
| 1.3.6.1.2.1.31.1.1.1.18.{ifIndex} | ifAlias | interface.description | OctetString |

**Level 2: Extensible OID Plugins (Post-MVP)**
Allow users to register custom OID-to-state mappings for vendor-specific MIBs.

**ifType mapping:**

| interface_type | ifType value | ifType name |
|---|---|---|
| ethernet | 6 | ethernetCsmacd |
| loopback | 24 | softwareLoopback |
| vlan | 136 | l3ipvlan |
| port_channel | 161 | ieee8023adLag |
| tunnel | 131 | tunnel |
| management | 6 | ethernetCsmacd |

**ifAdminStatus / ifOperStatus mapping:**

| State value | SNMP integer |
|---|---|
| up | 1 |
| down | 2 |
| dormant | 5 |
| notPresent | 6 |
| lowerLayerDown | 7 |

### 5.2.3 SNMP Operations

**GET:**
- Client requests a specific OID
- Service resolves OID to state field
- Returns value with correct type
- If OID not found: return `noSuchObject` or `noSuchInstance` per SNMPv2 convention

**GETNEXT (WALK):**
- Client requests OID; service returns the *next* OID in lexicographic order
- The service must maintain a sorted OID tree per device
- OID tree is built dynamically from the device's current state (interfaces present, etc.)
- Walk terminates when the next OID falls outside the requested subtree

**GETBULK:**
- Client requests starting OID with `max-repetitions`
- Service returns up to `max-repetitions` successive OID-value pairs
- Non-repeaters field is respected
- Default max-repetitions cap: 100 (configurable)

### 5.2.4 Counter Evolution

Counters are not static. They must advance over time to appear realistic to polling systems.

**Counter progression model:**
- Each InterfaceCounter has `rate_in_bps` and `rate_out_bps` fields
- At any point in time, the effective counter value is:
  ```
  effective_value = base_value + (elapsed_seconds * rate_bps / 8)
  ```
  where `elapsed_seconds = now() - rate_reference`
- Packet counters are derived from byte counters assuming an average packet size (configurable, default 512 bytes)
- When oper_status is `down`, rates are 0 (counters frozen)
- Counter wrapping:
  - Counter32 OIDs: `effective_value mod 4294967296`
  - Counter64 OIDs: `effective_value mod 18446744073709551616`
- `sysUpTime` advances in real time: `device.current_uptime * 100` (centiseconds)

**Rate defaults by interface type:**

| interface_type | Default rate_in_bps | Default rate_out_bps |
|---|---|---|
| ethernet (1G) | 300,000,000 | 150,000,000 |
| ethernet (10G) | 3,000,000,000 | 1,500,000,000 |
| loopback | 0 | 0 |
| vlan | 100,000,000 | 50,000,000 |
| management | 10,000,000 | 5,000,000 |

These are configurable per-interface.

---

# 6. Scale & Networking Model

## 6.1 The Core Challenge

Automation tools like Nornir connect to devices by IP address (and optionally port). Each emulated device needs to be addressable as a distinct network endpoint. With thousands of devices, we cannot allocate thousands of real IPs on a physical network.

SNEP supports three networking models. Deployments choose one (or combine them) based on their scale and environment.

## 6.2 Model A: Port Multiplexing (Recommended for MVP)

**How it works:**
- All devices share a single IP address (e.g., `127.0.0.1` or the host's IP)
- Each device is assigned unique SSH and SNMP port numbers
- SSH: base port 10000 + offset (e.g., device 1 = 10022, device 2 = 10023, ...)
- SNMP: base port 20000 + offset (e.g., device 1 = 20161, device 2 = 20162, ...)

**Pros:**
- Works on any machine with no OS-level configuration
- Works inside Docker containers with simple port mapping
- Trivial to implement

**Cons:**
- Nornir inventory must specify non-standard ports
- Less realistic (real devices use port 22/161)
- Port exhaustion at ~55,000 devices per IP

**Nornir inventory example:**
```yaml
# hosts.yaml
core-rtr-01:
  hostname: 127.0.0.1
  port: 10022
  platform: cisco_ios
  data:
    snmp_port: 20161

core-rtr-02:
  hostname: 127.0.0.1
  port: 10023
  platform: cisco_ios
  data:
    snmp_port: 20162
```

**ConnectionMapping assignment:** Automatic. When a device is created, the system assigns the next available port pair from the configured ranges.

**Port range configuration (system-level):**

```yaml
networking:
  model: "port_multiplex"
  bind_address: "0.0.0.0"
  ssh_port_range:
    start: 10000
    end: 19999
  snmp_port_range:
    start: 20000
    end: 29999
```

## 6.3 Model B: Loopback Alias IPs (Recommended for Production)

**How it works:**
- The host machine creates loopback aliases in a private IP range (e.g., `127.0.0.0/8` on Linux/macOS, or `10.x.x.x` aliases)
- Each device gets its own IP address
- SSH listens on port 22, SNMP on port 161 (standard ports)
- From the client's perspective, each device appears to be a separate host

**Pros:**
- Standard ports -- tools work without port configuration
- Most realistic from the client's perspective
- Compatible with all automation frameworks out of the box

**Cons:**
- Requires OS-level configuration (creating loopback aliases)
- On Linux: `ip addr add 127.0.0.2/32 dev lo` for each device
- On macOS: `sudo ifconfig lo0 alias 127.0.0.2`
- Requires elevated privileges to set up aliases
- Limit of ~16 million on `127.0.0.0/8` (more than enough)

**Nornir inventory example:**
```yaml
# hosts.yaml
core-rtr-01:
  hostname: 127.0.0.2
  port: 22
  platform: cisco_ios

core-rtr-02:
  hostname: 127.0.0.3
  port: 22
  platform: cisco_ios
```

**Setup automation:** SNEP provides a helper script that reads the device inventory and creates/removes loopback aliases. This script runs at startup and teardown.

**ConnectionMapping assignment:** Automatic. Each device is assigned the next IP in the configured range.

**IP range configuration:**

```yaml
networking:
  model: "loopback_alias"
  ip_range: "127.0.0.2/16"    # 127.0.0.2 through 127.0.255.254
  ssh_port: 22
  snmp_port: 161
  setup_script: "auto"         # auto-create aliases on startup
```

## 6.4 Model C: Proxy Routing (Recommended for Cloud/Multi-Tenant)

**How it works:**
- A single SSH/SNMP proxy listens on one IP:port
- Device identity is determined by:
  - For SSH: a lookup header or username prefix (e.g., `admin@core-rtr-01`)
  - For SNMP: the community string or SNMPv3 context encodes the device name
- The proxy routes the request to the appropriate device's state

**Pros:**
- Single IP:port for all devices
- Works behind load balancers and NAT
- Ideal for cloud/SaaS deployment

**Cons:**
- Requires non-standard client configuration (username prefix for SSH)
- SNMP community string encoding is non-standard
- Less transparent to automation tools

**SSH proxy model -- username encoding:**
```
ssh admin%core-rtr-01@emulator.example.com
```
The SSH service splits the username on `%`:
- `admin` = credential username
- `core-rtr-01` = target device hostname

**SNMP proxy model -- community string encoding:**
```
snmpwalk -v2c -c "public@core-rtr-01" emulator.example.com
```
The SNMP service splits the community on `@`:
- `public` = actual community string
- `core-rtr-01` = target device hostname

**SNMPv3 proxy model:**
- Use SNMPv3 context name as device identifier
- `snmpwalk -v3 -n core-rtr-01 ...` where `-n` sets the context name

**Nornir inventory example (proxy model):**
```yaml
# hosts.yaml
core-rtr-01:
  hostname: emulator.example.com
  port: 22
  username: "admin%core-rtr-01"
  platform: cisco_ios
```

## 6.5 Connection-to-Device Resolution

Regardless of the networking model, the SSH and SNMP services must resolve an incoming connection to a device identity. The resolution chain:

**SSH:**
1. Check ConnectionMapping for `(listen_address, listen_port, protocol=ssh)`
2. If proxy model: parse username for device identifier
3. Look up Device by resolved identifier
4. If device not found or `admin_state != active`: reject connection

**SNMP:**
1. Check ConnectionMapping for `(listen_address, listen_port, protocol=snmp)`
2. If proxy model: parse community string or SNMPv3 context for device identifier
3. Validate community/credentials against device's SNMPProfile
4. If device not found or `admin_state != active`: silent drop (no response)

## 6.6 Nornir Compatibility

SNEP must work with Nornir without requiring custom plugins or platform modifications. This means:

- **Connection plugins:** `netmiko` (SSH) and `napalm` (SSH + some SNMP) must work. These use standard SSH libraries internally.
- **Inventory:** Nornir's SimpleInventory (YAML files) or any inventory plugin that produces host objects with `hostname`, `port`, `username`, `password`, `platform`.
- **Platform mapping:** SNEP platforms must match Nornir/Netmiko platform names (e.g., `cisco_ios`, `arista_eos`, `juniper_junos`).

**SNEP must provide inventory export:** Given a set of devices, generate a Nornir-compatible inventory (hosts.yaml, groups.yaml, defaults.yaml) with correct hostnames, ports, and credentials for the chosen networking model.

---

# 7. CLI Output Modeling System

## 7.1 Overview

The CLI Output Modeling system allows users to work with real CLI output in two ways:

1. **Import and replay** -- paste real output, replay it verbatim when the command is issued
2. **Import, annotate, and templatize** -- paste real output, tag fields that correspond to state variables, and convert the output into a template that renders dynamically

This system bridges the gap between "I have real device output" and "I need synthetic output that adapts to state changes."

## 7.2 Import Workflow

### Step 1: Paste Raw Output

The user provides:
- The command that was run (e.g., `show interfaces GigabitEthernet0/1`)
- The raw text output from a real device
- The platform (e.g., `cisco_ios`)
- Optionally, the device this output came from

The system stores this as a CLIOutputMapping with `mode: static`.

### Step 2: Annotate Fields (Optional)

In the UI, the user can highlight portions of the raw output and tag them:

**Annotation types:**

| Tag Type | Description | Maps To |
|---|---|---|
| `device_field` | A field from the device entity | `device.<field>` |
| `interface_field` | A field from an interface | `interface.<field>` |
| `counter_field` | A counter value | `counter.<field>` |
| `neighbor_field` | A neighbor/link field | `link.<field>` |
| `literal` | Static text that should remain as-is | (not mapped) |
| `computed` | A derived value (e.g., formatted uptime) | Expression |

**Example annotation of `show interfaces` output:**

```
[interface.name] is [interface.admin_status_text], line protocol is [interface.oper_status_text]
  Hardware is [interface.hardware_type], address is [interface.mac_address]
  Description: [interface.description]
  Internet address is [interface.ip_address]
  MTU [interface.mtu] bytes, BW [computed:interface.speed_mbps*1000] Kbit/sec, DLY 10 usec,
     reliability 255/255, txload [computed:txload_fraction], rxload [computed:rxload_fraction]
  ...
     [counter.in_octets] bytes input, [counter.in_unicast_pkts] packets input, [counter.in_errors] input errors
```

### Step 3: Validate Mapping

The system validates that:
- All tagged fields exist in the data model
- All required fields for the command template are tagged
- No orphaned tags (tags that reference nonexistent fields)
- The tagged output, when rendered with current state, produces reasonable output

### Step 4: Convert to Template

If the user has annotated all dynamic fields, the system can auto-generate a CommandTemplate from the annotated output. This moves the command from static replay to structured rendering.

## 7.3 Field Annotation Schema

Each annotation in the `field_annotations` array:

```yaml
- field_name: "interface_name"           # Human-readable label
  start_offset: 0                        # Character offset in raw_output (inclusive)
  end_offset: 20                         # Character offset (exclusive)
  value: "GigabitEthernet0/1"           # The actual text at this position
  maps_to: "interface.name"              # State field path
  data_type: "string"                    # string, integer, float, mac, ip, duration
  format_spec: null                      # Optional: formatting instructions
  context:                               # Optional: disambiguation
    interface_match: "GigabitEthernet0/1"  # Which interface this belongs to
```

## 7.4 Dual-Mode Operation

A device can have a mix of static and structured commands:

| Command | Mode | Source |
|---|---|---|
| `show version` | Static | CLIOutputMapping (pasted from real device) |
| `show interfaces` | Structured | CommandTemplate (renders from state) |
| `show ip interface brief` | Structured | CommandTemplate |
| `show running-config` | Static | CLIOutputMapping |
| `show cdp neighbors` | Structured | CommandTemplate (derived from links) |
| `show logging` | Static | CLIOutputMapping |

This allows gradual migration: users start by pasting static outputs and progressively convert them to structured templates as needed.

## 7.5 Bulk Import

For setting up large environments, support bulk import via:

**CSV/YAML bulk format:**
```yaml
imports:
  - device_hostname: "core-rtr-01"
    command: "show version"
    mode: "static"
    output_file: "outputs/core-rtr-01/show_version.txt"

  - device_hostname: "core-rtr-01"
    command: "show interfaces"
    mode: "static"
    output_file: "outputs/core-rtr-01/show_interfaces.txt"
```

**Directory convention:**
```
import/
  core-rtr-01/
    show_version.txt
    show_interfaces.txt
    show_ip_interface_brief.txt
  dist-sw-01/
    show_version.txt
    show_interfaces.txt
```

The import system reads the directory structure, matches filenames to commands (configurable mapping), and creates CLIOutputMapping records.

---

# 8. Rendering Engine

## 8.1 Template System

The Rendering Engine uses a Jinja2-compatible template language to produce CLI output from device state. Templates are stored as CommandTemplate records in the database.

### 8.1.1 Template Variables

Templates receive a context object with the following top-level variables:

| Variable | Type | Description |
|---|---|---|
| `device` | Object | The Device entity with all fields |
| `model` | Object | The DeviceModel entity |
| `platform` | Object | The Platform entity |
| `interfaces` | List | All Interface entities for the device, sorted by sort_order |
| `interface` | Object | Single interface (when command targets a specific interface) |
| `counters` | Dict | Map of interface_id to InterfaceCounter |
| `neighbors` | List | Resolved neighbor records (from Links) |
| `snmp_profile` | Object | The SNMPProfile for this device |
| `timestamp` | DateTime | Current time |
| `uptime` | Duration | Current device uptime |

### 8.1.2 Template Filters

Custom filters available in templates:

| Filter | Description | Example |
|---|---|---|
| `ljust(width)` | Left-justify in field of given width | `{{ name \| ljust(30) }}` |
| `rjust(width)` | Right-justify | `{{ value \| rjust(10) }}` |
| `mac_cisco` | Format MAC as Cisco style (aabb.ccdd.eeff) | `{{ mac \| mac_cisco }}` |
| `mac_colon` | Format MAC as colon style (aa:bb:cc:dd:ee:ff) | `{{ mac \| mac_colon }}` |
| `uptime_ios` | Format duration as IOS uptime string | `{{ uptime \| uptime_ios }}` |
| `uptime_eos` | Format duration as EOS uptime string | `{{ uptime \| uptime_eos }}` |
| `speed_human` | Convert Mbps to human-readable | `{{ 1000 \| speed_human }}` -> `"1 Gbit"` |
| `counter_human` | Format large counter values | `{{ 584792031847 \| counter_human }}` |
| `default(val)` | Default value if None | `{{ ip \| default("unassigned") }}` |
| `admin_status_text` | Convert enum to display text | `{{ "down" \| admin_status_text }}` -> `"administratively down"` |
| `oper_status_text` | Convert enum to display text | `{{ "up" \| oper_status_text }}` -> `"up"` |
| `txload(rate_bps, speed_mbps)` | Calculate txload/255 fraction | `{{ rate \| txload(1000) }}` |

### 8.1.3 Conditional Sections

Templates support conditional rendering for sections that depend on state:

```
{% if interface.ip_address %}
  Internet address is {{ interface.ip_address }}
{% endif %}
{% if interface.description %}
  Description: {{ interface.description }}
{% endif %}
```

### 8.1.4 Loop Constructs

For commands that list multiple items (interfaces, neighbors):

```
{% for iface in interfaces %}
{{ iface.name | ljust(27) }}{{ iface.ip_address | default("unassigned") | ljust(16) }}...
{% endfor %}
```

## 8.2 Platform-Specific Examples

### 8.2.1 Cisco IOS: `show ip interface brief`

**Template:**

```
Interface                  IP-Address      OK? Method Status                Protocol
{% for iface in interfaces | sort(attribute='sort_order') %}
{{ iface.name | ljust(27) }}{{ (iface.ip_address | ip_only | default('unassigned')) | ljust(16) }}YES {{ 'manual' | ljust(7) }}{{ iface.admin_status | admin_status_display_brief | ljust(22) }}{{ iface.oper_status | oper_status_display_brief }}
{% endfor %}
```

**Rendered output (3 interfaces):**

```
Interface                  IP-Address      OK? Method Status                Protocol
GigabitEthernet1/0/1       10.0.1.1        YES manual up                    up
GigabitEthernet1/0/2       10.0.2.1        YES manual up                    up
Loopback0                  10.255.0.1      YES manual up                    up
```

### 8.2.2 Cisco IOS: `show version`

**Template (abbreviated):**

```
Cisco IOS XE Software, Version {{ device.software_version | default(model.software_version) }}
Cisco IOS Software [{{ model.train_name | default("Bengaluru") }}], {{ model.software_family | default("Catalyst L3 Switch Software") }} ({{ model.image_name | default("CAT9K_IOSXE") }}), Version {{ device.software_version | default(model.software_version) }}, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2024 by Cisco Systems, Inc.
Compiled {{ model.compile_date | default("Sat 17-Jun-24 07:03") }} by {{ model.compile_user | default("mcpre") }}

{{ device.hostname }} uptime is {{ uptime | uptime_ios }}
System returned to ROM by PowerOn

System image file is "flash:packages.conf"

Last reload reason: PowerOn

cisco {{ model.hardware_details.chassis | default("C9300-48T") }} ({{ model.cpu_type | default("ARM") }}) processor with {{ model.hardware_details.memory_mb | default(8192) }}K/{{ model.memory_free | default(6234) }}K bytes of memory.
Processor board ID {{ device.serial_number }}
{{ interfaces | length }} Virtual Ethernet interfaces
{{ interfaces | selectattr('interface_type', 'equalto', 'ethernet') | list | length }} Gigabit Ethernet interfaces
{{ model.hardware_details.flash_mb | default(16384) }}K bytes of flash-simulated non-volatile configuration memory.

Configuration register is 0x102
```

### 8.2.3 Arista EOS: `show ip interface brief`

**Template:**

```
                                                                        Address
Interface         IP Address            Status      Protocol         MTU    Owner
{% for iface in interfaces | sort(attribute='sort_order') %}
{{ iface.name | ljust(18) }}{{ (iface.ip_address | default('unassigned')) | ljust(22) }}{{ iface.admin_status | admin_status_eos | ljust(12) }}{{ iface.oper_status | oper_status_eos | ljust(17) }}{{ iface.mtu | rjust(5) }}
{% endfor %}
```

**Rendered output:**

```
                                                                        Address
Interface         IP Address            Status      Protocol         MTU    Owner
Ethernet1         10.0.1.1/30           up          up              1500
Ethernet2         10.0.2.1/30           up          up              1500
Loopback0         10.255.0.1/32         up          up             65535
Management1       192.168.1.10/24       up          up              1500
```

### 8.2.4 Cisco IOS: `show cdp neighbors`

**Template:**

```
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
{% for neighbor in neighbors %}
{{ neighbor.remote_hostname | ljust(17) }}{{ neighbor.local_interface | short_name | ljust(18) }}{{ neighbor.holdtime | default(162) | rjust(3) | ljust(11) }}{{ neighbor.capabilities | default("R S I") | ljust(12) }}{{ neighbor.remote_platform | truncate(10) | ljust(10) }}{{ neighbor.remote_interface | short_name }}
{% endfor %}
```

## 8.3 Cross-Command Consistency

The Rendering Engine enforces consistency by always reading from the same state snapshot for a given request cycle. When an SSH session runs multiple commands in sequence, each command gets the latest state independently. This means:

1. User runs `show ip interface brief` -- sees `Gi1/0/1` as `up/up`
2. Scenario engine sets `Gi1/0/1` oper_status to `down`
3. User runs `show interfaces Gi1/0/1` -- sees `line protocol is down`
4. User runs `show ip interface brief` again -- sees `Gi1/0/1` as `up/down`
5. User runs `show cdp neighbors` -- neighbor via `Gi1/0/1` is absent

All four outputs are derived from the same state model, just at different points in time. No explicit synchronization between commands is needed.

## 8.4 Rendering Pipeline

```
Command String
  |
  v
Template Resolution (Section 2.2.4 priority)
  |
  +-- CommandTemplate found? --> Load template
  |     |
  |     v
  |   State Fetch (read current device state)
  |     |
  |     v
  |   Template Render (Jinja2 execution)
  |     |
  |     v
  |   Post-Processing (trailing newline, final formatting)
  |     |
  |     v
  |   Return rendered text
  |
  +-- CLIOutputMapping found (static)? --> Return raw_output verbatim
  |
  +-- No match --> Return error template
```

---

# 9. Scenario & Fault Engine

## 9.1 Scenario Model

A **Scenario** is a named, reusable sequence of state mutations that simulates a network event or incident. Scenarios are first-class entities in the data model (see Section 3.2.11 and 3.2.12).

**Key properties:**
- Scenarios are composed of ordered **events** (ScenarioEvent)
- Each event has a **trigger** (when to fire) and an **action** (what to change)
- Scenarios can be in states: `draft`, `ready`, `running`, `paused`, `completed`
- Repeatable scenarios can be reset (via rollback actions) and run again
- Multiple scenarios can run concurrently on different devices
- Scenarios affecting the same device are serialized to prevent conflicts

## 9.2 Event Triggers

### 9.2.1 Immediate

Fires as soon as the previous event in the scenario completes (or immediately if it's the first event).

```yaml
trigger_type: "immediate"
trigger_config: {}
```

### 9.2.2 Delay

Fires after a specified wall-clock delay from the previous event's completion.

```yaml
trigger_type: "delay"
trigger_config:
  delay_seconds: 30
```

### 9.2.3 Manual

Waits for explicit user action (UI button click or API call).

```yaml
trigger_type: "manual"
trigger_config:
  prompt: "Click to simulate fiber restoration"
```

### 9.2.4 Conditional

Polls a state condition at intervals and fires when the condition is met.

```yaml
trigger_type: "conditional"
trigger_config:
  field: "interface_counter.in_errors"
  interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
  operator: "gt"      # gt, lt, eq, ne, gte, lte
  value: 1000
  check_interval_seconds: 5
  timeout_seconds: 300   # give up after 5 minutes
```

## 9.3 Event Actions

### 9.3.1 interface_state_change

Changes an interface's operational status.

```yaml
action_type: "interface_state_change"
action_config:
  interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
  oper_status: "down"
```

**Side effects (automatically applied by Inventory & State Service):**
- Counter rates set to 0 (if going down)
- Counter rates restored to previous values (if coming up)
- `last_state_change` updated
- Links with this interface become non-visible in neighbor outputs

### 9.3.2 interface_admin_change

Changes an interface's administrative status.

```yaml
action_type: "interface_admin_change"
action_config:
  interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
  admin_status: "down"
```

**Side effects:**
- If admin goes down, oper_status also goes down
- CLI output shows "administratively down" prefix

### 9.3.3 counter_set

Sets a counter to a specific value.

```yaml
action_type: "counter_set"
action_config:
  interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
  counter_name: "in_errors"
  value: 15847
```

### 9.3.4 counter_rate_change

Changes the progression rate of byte/packet counters.

```yaml
action_type: "counter_rate_change"
action_config:
  interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
  rate_in_bps: 950000000     # spike to 95% utilization
  rate_out_bps: 800000000
```

### 9.3.5 link_state_change

Brings a link up or down (affects both endpoints).

```yaml
action_type: "link_state_change"
action_config:
  link_id: "f6a7b8c9-0006-0006-0006-000000000001"
  admin_state: "down"
```

**Side effects:**
- Both interfaces' `oper_status` set to `down`
- Neighbor visibility removed for both sides
- Counter rates frozen on both interfaces

### 9.3.6 device_state_change

Changes a device's administrative state.

```yaml
action_type: "device_state_change"
action_config:
  device_id: "c3d4e5f6-0003-0003-0003-000000000001"
  admin_state: "maintenance"
```

**Side effects:**
- `maintenance`: SSH connections show maintenance banner, SNMP still responds
- `decommissioned`: SSH connections refused, SNMP silent drop

### 9.3.7 log_event

Generates a syslog-style message stored in the device's log buffer.

```yaml
action_type: "log_event"
action_config:
  device_id: "c3d4e5f6-0003-0003-0003-000000000001"
  severity: "critical"     # emergency, alert, critical, error, warning, notification, informational, debugging
  message: "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down"
```

**Log buffer:** Each device maintains an in-memory circular log buffer (default: 1000 entries). Logs are visible via `show logging` (static or structured).

### 9.3.8 bulk_update

Applies multiple actions atomically in a single transaction.

```yaml
action_type: "bulk_update"
action_config:
  updates:
    - action_type: "interface_state_change"
      action_config:
        interface_id: "..."
        oper_status: "down"
    - action_type: "log_event"
      action_config:
        device_id: "..."
        severity: "critical"
        message: "..."
```

## 9.4 Scenario Execution

### 9.4.1 Lifecycle

```
draft --> ready --> running --> completed
                      |  ^
                      v  |
                    paused

completed --> ready  (if is_repeatable, via reset)
```

### 9.4.2 Execution Rules

- **Starting:** Only `ready` scenarios can be started. Starting transitions to `running`.
- **Event processing:** Events are processed in `sequence_order`. Each event waits for its trigger condition, then applies its action.
- **Pausing:** A running scenario can be paused. The current event's trigger timer is suspended. State changes already applied are NOT rolled back.
- **Resuming:** A paused scenario resumes from where it left off. Delay timers resume counting.
- **Completion:** When the last event fires, the scenario transitions to `completed`.
- **Reset:** For repeatable scenarios, reset applies all `rollback_action` entries in reverse order, then transitions back to `ready`.
- **Cancellation:** A running or paused scenario can be cancelled, which transitions to `completed` without firing remaining events. State changes already applied remain in effect unless explicitly reset.

### 9.4.3 Concurrency

- Multiple scenarios can run concurrently
- If two scenarios modify the same entity, changes are serialized (last-write-wins at the field level)
- This is acceptable because real network events are inherently concurrent and unpredictable
- The Scenario Engine logs all applied changes for audit

## 9.5 Example Scenario: Data Center Uplink Failure

```yaml
name: "dc-east-uplink-failure"
description: "Simulates fiber cut on DC-East core uplink, causing cascading effects"
is_repeatable: true
events:
  # T+0: Physical layer goes down
  - sequence_order: 1
    trigger_type: "immediate"
    action_type: "link_state_change"
    action_config:
      link_id: "f6a7b8c9-0006-0006-0006-000000000001"
      admin_state: "down"

  # T+0: Log messages on both devices
  - sequence_order: 2
    trigger_type: "immediate"
    action_type: "bulk_update"
    action_config:
      updates:
        - action_type: "log_event"
          action_config:
            device_id: "c3d4e5f6-0003-0003-0003-000000000001"
            severity: "critical"
            message: "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down"
        - action_type: "log_event"
          action_config:
            device_id: "c3d4e5f6-0003-0003-0003-000000000099"
            severity: "critical"
            message: "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/49, changed state to down"

  # T+5s: CRC errors spike just before link went fully down
  - sequence_order: 3
    trigger_type: "delay"
    trigger_config:
      delay_seconds: 5
    action_type: "counter_set"
    action_config:
      interface_id: "d4e5f6a7-0004-0004-0004-000000000001"
      counter_name: "crc_errors"
      value: 4271

  # T+60s: Manual trigger to restore link
  - sequence_order: 4
    trigger_type: "manual"
    trigger_config:
      prompt: "Simulate fiber splice completion - click to restore link"
    action_type: "link_state_change"
    action_config:
      link_id: "f6a7b8c9-0006-0006-0006-000000000001"
      admin_state: "up"

  # T+60s: Restoration log
  - sequence_order: 5
    trigger_type: "immediate"
    action_type: "log_event"
    action_config:
      device_id: "c3d4e5f6-0003-0003-0003-000000000001"
      severity: "notification"
      message: "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to up"
```

---

# 10. API Specification

## 10.1 API Design Principles

- **REST-first** with JSON payloads (GraphQL is a Phase 3 consideration)
- **OpenAPI 3.1** schema as the contract
- **Versioned**: `/api/v1/...`
- **Consistent naming**: plural nouns, kebab-case for multi-word paths
- **Standard HTTP methods**: GET (read), POST (create), PUT (full update), PATCH (partial update), DELETE (remove)
- **Pagination**: cursor-based for list endpoints
- **Filtering**: query parameter syntax `?filter[field]=value`
- **Sorting**: `?sort=field` (ascending) or `?sort=-field` (descending)

## 10.2 Authentication

- **API key** authentication via `Authorization: Bearer <api_key>` header
- API keys are scoped to a tenant (multi-tenant mode) or installation (local mode)
- In local/development mode, authentication can be disabled via configuration
- API keys support read-only or read-write permissions

## 10.3 Endpoint Catalog

### 10.3.1 Platforms

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/platforms` | List all platforms |
| GET | `/api/v1/platforms/{id}` | Get a platform |
| POST | `/api/v1/platforms` | Create a platform |
| PUT | `/api/v1/platforms/{id}` | Update a platform |
| DELETE | `/api/v1/platforms/{id}` | Delete a platform |

**GET /api/v1/platforms response:**

```yaml
status: 200
body:
  data:
    - id: "a1b2c3d4-0001-0001-0001-000000000001"
      name: "cisco_ios"
      display_name: "Cisco IOS"
      vendor: "Cisco"
      device_model_count: 5
      device_count: 47
  pagination:
    cursor: "eyJpZCI6..."
    has_more: false
```

### 10.3.2 Device Models

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/device-models` | List all device models |
| GET | `/api/v1/device-models/{id}` | Get a device model |
| POST | `/api/v1/device-models` | Create a device model |
| PUT | `/api/v1/device-models/{id}` | Update a device model |
| DELETE | `/api/v1/device-models/{id}` | Delete a device model |

**Query parameters:**
- `?filter[platform_id]=<uuid>` -- filter by platform

### 10.3.3 Devices

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/devices` | List devices (paginated) |
| GET | `/api/v1/devices/{id}` | Get a device with full detail |
| POST | `/api/v1/devices` | Create a device |
| PUT | `/api/v1/devices/{id}` | Update a device |
| PATCH | `/api/v1/devices/{id}` | Partial update |
| DELETE | `/api/v1/devices/{id}` | Delete a device and all children |
| POST | `/api/v1/devices/bulk` | Bulk create devices |
| GET | `/api/v1/devices/{id}/interfaces` | List interfaces for a device |
| GET | `/api/v1/devices/{id}/neighbors` | List neighbors for a device |
| GET | `/api/v1/devices/{id}/cli-mappings` | List CLI output mappings |
| GET | `/api/v1/devices/{id}/connection-info` | Get SSH/SNMP connection details |

**GET /api/v1/devices/{id} response:**

```yaml
status: 200
body:
  data:
    id: "c3d4e5f6-0003-0003-0003-000000000001"
    hostname: "core-rtr-01"
    management_ip: "10.1.1.1"
    serial_number: "FCW2145L0RN"
    software_version: "17.06.05"
    admin_state: "active"
    current_uptime_seconds: 7776342
    tags:
      site: "dc-east"
      role: "core"
    device_model:
      id: "b2c3d4e5-0002-0002-0002-000000000001"
      name: "catalyst_9300_48t"
      display_name: "Cisco Catalyst 9300-48T"
    platform:
      id: "a1b2c3d4-0001-0001-0001-000000000001"
      name: "cisco_ios"
    interface_count: 52
    link_count: 3
    connection_info:
      ssh:
        host: "127.0.0.1"
        port: 10022
      snmp:
        host: "127.0.0.1"
        port: 20161
```

**POST /api/v1/devices request:**

```yaml
body:
  device_model_id: "b2c3d4e5-0002-0002-0002-000000000001"
  hostname: "access-sw-42"
  management_ip: "10.1.42.1"
  tags:
    site: "dc-east"
    role: "access"
  auto_create_interfaces: true    # create default interfaces from device model
  auto_create_snmp_profile: true  # create default SNMP profile
```

### 10.3.4 Interfaces

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/interfaces` | List all interfaces (filterable) |
| GET | `/api/v1/interfaces/{id}` | Get interface with counters |
| POST | `/api/v1/interfaces` | Create an interface |
| PUT | `/api/v1/interfaces/{id}` | Update an interface |
| PATCH | `/api/v1/interfaces/{id}` | Partial update (e.g., toggle status) |
| DELETE | `/api/v1/interfaces/{id}` | Delete an interface |

**Query parameters:**
- `?filter[device_id]=<uuid>`
- `?filter[oper_status]=up|down`
- `?filter[admin_status]=up|down`
- `?filter[interface_type]=ethernet|loopback|...`

**GET /api/v1/interfaces/{id} response:**

```yaml
status: 200
body:
  data:
    id: "d4e5f6a7-0004-0004-0004-000000000001"
    device_id: "c3d4e5f6-0003-0003-0003-000000000001"
    name: "GigabitEthernet1/0/1"
    short_name: "Gi1/0/1"
    if_index: 1
    interface_type: "ethernet"
    admin_status: "up"
    oper_status: "up"
    speed_mbps: 1000
    mtu: 1500
    mac_address: "aabb.cc01.0001"
    ip_address: "10.0.1.1/30"
    description: "Uplink to dist-sw-01 Gi1/0/49"
    counters:
      in_octets: 584792031847
      out_octets: 291034958271
      in_unicast_pkts: 4839201748
      out_unicast_pkts: 2419384751
      in_errors: 0
      out_errors: 0
      rate_in_bps: 450000000
      rate_out_bps: 225000000
```

### 10.3.5 Links

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/links` | List all links |
| GET | `/api/v1/links/{id}` | Get a link |
| POST | `/api/v1/links` | Create a link between two interfaces |
| PUT | `/api/v1/links/{id}` | Update a link |
| DELETE | `/api/v1/links/{id}` | Delete a link |

**POST /api/v1/links request:**

```yaml
body:
  interface_a_id: "d4e5f6a7-0004-0004-0004-000000000001"
  interface_b_id: "d4e5f6a7-0004-0004-0004-000000000099"
  link_type: "physical"
  discovery_protocol: "cdp"
```

### 10.3.6 Topology

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/topology` | Get full topology graph |
| GET | `/api/v1/topology/subgraph?devices=id1,id2,...` | Get topology subgraph |

**GET /api/v1/topology response:**

```yaml
status: 200
body:
  nodes:
    - id: "c3d4e5f6-0003-0003-0003-000000000001"
      hostname: "core-rtr-01"
      platform: "cisco_ios"
      model: "Cisco Catalyst 9300-48T"
      admin_state: "active"
      interface_count: 52
      tags:
        site: "dc-east"
        role: "core"

    - id: "c3d4e5f6-0003-0003-0003-000000000099"
      hostname: "dist-sw-01"
      platform: "cisco_ios"
      model: "Cisco Catalyst 9300-24T"
      admin_state: "active"
      interface_count: 28
      tags:
        site: "dc-east"
        role: "distribution"

  edges:
    - id: "f6a7b8c9-0006-0006-0006-000000000001"
      source_device_id: "c3d4e5f6-0003-0003-0003-000000000001"
      source_interface: "GigabitEthernet1/0/1"
      target_device_id: "c3d4e5f6-0003-0003-0003-000000000099"
      target_interface: "GigabitEthernet1/0/49"
      link_type: "physical"
      admin_state: "up"
      oper_state: "up"          # both interfaces must be up
```

### 10.3.7 CLI Output Mappings

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cli-mappings` | List all mappings |
| GET | `/api/v1/cli-mappings/{id}` | Get a mapping |
| POST | `/api/v1/cli-mappings` | Create a mapping (paste output) |
| PUT | `/api/v1/cli-mappings/{id}` | Update mapping/annotations |
| DELETE | `/api/v1/cli-mappings/{id}` | Delete a mapping |
| POST | `/api/v1/cli-mappings/{id}/convert` | Convert annotated mapping to template |
| POST | `/api/v1/cli-mappings/bulk-import` | Bulk import from file/directory |

### 10.3.8 Scenarios

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/scenarios` | List all scenarios |
| GET | `/api/v1/scenarios/{id}` | Get scenario with events |
| POST | `/api/v1/scenarios` | Create a scenario |
| PUT | `/api/v1/scenarios/{id}` | Update a scenario |
| DELETE | `/api/v1/scenarios/{id}` | Delete a scenario |
| POST | `/api/v1/scenarios/{id}/start` | Start execution |
| POST | `/api/v1/scenarios/{id}/pause` | Pause execution |
| POST | `/api/v1/scenarios/{id}/resume` | Resume execution |
| POST | `/api/v1/scenarios/{id}/reset` | Reset to ready state |
| POST | `/api/v1/scenarios/{id}/cancel` | Cancel execution |
| GET | `/api/v1/scenarios/{id}/status` | Get execution status |
| POST | `/api/v1/scenarios/{id}/events/{event_id}/trigger` | Manually trigger a waiting event |

### 10.3.9 Command Execution (Preview)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/devices/{id}/execute` | Execute a CLI command and return output |

**POST /api/v1/devices/{id}/execute request:**

```yaml
body:
  command: "show ip interface brief"
```

**Response:**

```yaml
status: 200
body:
  command: "show ip interface brief"
  output: "Interface                  IP-Address      OK? Method Status                Protocol\nGigabitEthernet1/0/1       10.0.1.1        YES manual up                    up\n..."
  rendering_mode: "structured"   # or "static"
  template_id: "a7b8c9d0-0007-0007-0007-000000000001"   # if structured
```

### 10.3.10 Inventory Export

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/export/nornir` | Export Nornir-compatible inventory |
| GET | `/api/v1/export/ansible` | Export Ansible-compatible inventory |
| GET | `/api/v1/export/csv` | Export device list as CSV |

**GET /api/v1/export/nornir response:**

```yaml
status: 200
body:
  hosts:
    core-rtr-01:
      hostname: "127.0.0.1"
      port: 10022
      username: "admin"
      password: "cisco123"
      platform: "cisco_ios"
      data:
        site: "dc-east"
        role: "core"
        snmp_community: "public"
        snmp_port: 20161
    dist-sw-01:
      hostname: "127.0.0.1"
      port: 10023
      username: "admin"
      password: "cisco123"
      platform: "cisco_ios"
  groups: {}
  defaults:
    username: "admin"
    password: "cisco123"
```

## 10.4 Error Response Format

All errors follow a consistent format:

```yaml
status: 422
body:
  error:
    code: "VALIDATION_ERROR"
    message: "Validation failed"
    details:
      - field: "hostname"
        message: "Hostname 'core-rtr-01' is already in use"
        code: "UNIQUE_CONSTRAINT"
```

**Standard error codes:**

| HTTP Status | Code | Description |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request |
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Entity not found |
| 409 | `CONFLICT` | State conflict (e.g., scenario already running) |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

## 10.5 WebSocket Events (Real-Time Updates)

For the UI to receive real-time state updates:

**Endpoint:** `ws://host/api/v1/ws`

**Event types:**

| Event | Payload | Description |
|---|---|---|
| `state.changed` | `{ entity_type, entity_id, changes }` | Any state field changed |
| `scenario.status` | `{ scenario_id, status, current_event }` | Scenario execution update |
| `session.connected` | `{ device_id, source_ip }` | SSH session opened |
| `session.disconnected` | `{ device_id, session_id }` | SSH session closed |
| `log.entry` | `{ device_id, severity, message }` | New log entry |

---

# 11. UI/UX Specification

## 11.1 Design Principles

- **Operational dashboard feel** -- inspired by network management tools, not generic admin panels
- **State visibility** -- always show the current state of the system prominently
- **Direct manipulation** -- click on a device to see/edit it, click on an interface to toggle state
- **Non-blocking** -- long operations (scenario execution, bulk import) run in the background with progress indicators
- **Responsive** -- functional on tablets for demo/presentation use; optimized for desktop

## 11.2 Key Screens

### 11.2.1 Topology View (Dashboard / Home)

**Purpose:** Primary landing page showing the network topology as an interactive graph.

**Elements:**
- **Graph canvas** -- force-directed or hierarchical layout of devices as nodes and links as edges
- **Device nodes** -- icons colored by status (green=active, yellow=maintenance, gray=decommissioned)
- **Link edges** -- solid green (up), dashed red (down), thickness proportional to speed
- **Sidebar** -- quick-view panel showing details of selected device/link
- **Controls:**
  - Layout toggle (force-directed, hierarchical, manual)
  - Filter by tags (site, role, platform)
  - Search devices by hostname
  - Zoom/pan
  - "Fit all" button
- **Status bar** -- total devices, total interfaces, active scenarios, active SSH sessions

**Interactions:**
- Click device node -> opens Device Detail in sidebar
- Double-click device node -> navigates to Device Editor
- Click link edge -> shows link details (both endpoints, state)
- Right-click device -> context menu (SSH to device, view CLI, start scenario, toggle state)

### 11.2.2 Device Editor

**Purpose:** Full detail view and editor for a single device.

**Sections:**

**Header:**
- Device hostname (editable), platform badge, model badge, admin state toggle
- SSH connection string (copyable: `ssh admin@127.0.0.1 -p 10022`)
- SNMP connection info (copyable)

**Tabs:**

**Interfaces tab:**
- Table of all interfaces with columns: Name, Status (admin/oper), IP, Speed, Description, Counters (live)
- Click interface row to expand inline editor
- Toggle admin/oper status with switches
- Add/remove interfaces

**Neighbors tab:**
- Table of CDP/LLDP neighbors derived from links
- Columns: Local Interface, Remote Device, Remote Interface, Remote Platform
- Click to navigate to remote device

**CLI Mappings tab:**
- List of commands with their rendering mode (static/structured)
- "Paste output" button to add new static mapping
- "Preview" button to see what the command would render right now
- Status indicator showing which commands have templates vs static mappings

**SNMP Profile tab:**
- SNMPv2 community string (editable)
- SNMPv3 credentials (editable)
- System MIB values (editable)
- "Test SNMP" button that runs a quick GET against sysName.0

**Logs tab:**
- Scrollable log buffer for this device
- Severity filtering
- Auto-scroll toggle

**Connection Info tab:**
- SSH host/port
- SNMP host/port
- Nornir host entry (copyable YAML)

### 11.2.3 CLI Modeling Interface

**Purpose:** Annotate pasted CLI output to create structured mappings.

**Layout:**
- **Left pane:** Raw CLI output text displayed in a monospaced font with line numbers
- **Right pane:** Annotation panel showing tagged fields, their mapped state paths, and data types

**Workflow:**

1. User selects "New CLI Mapping" for a device
2. User enters the command string (e.g., `show interfaces GigabitEthernet1/0/1`)
3. User pastes the raw output into the left pane
4. System detects platform from device and suggests auto-annotations for known patterns
5. User can manually highlight text in the left pane and assign a field mapping from a dropdown
6. Right pane updates in real time showing all annotations
7. Validation indicators show if all required fields for template generation are covered
8. User clicks "Save as Static" (replay only) or "Convert to Template" (if fully annotated)

**Auto-detection features:**
- Recognize interface names (GigabitEthernet, Ethernet, Loopback, etc.)
- Recognize IP addresses
- Recognize MAC addresses
- Recognize counter values (large integers)
- Recognize status keywords (up, down, administratively down)

### 11.2.4 Scenario Builder

**Purpose:** Create and manage fault scenarios visually.

**Layout:**
- **Timeline view** -- horizontal timeline showing events as cards, connected by trigger indicators (arrows for immediate, clock icons for delays, hand icons for manual)
- **Event editor** -- slide-out panel for editing a single event's trigger and action
- **Device/interface picker** -- searchable selector for choosing targets

**Workflow:**

1. User creates a new scenario (name + description)
2. User adds events to the timeline
3. For each event, user selects:
   - Trigger type and parameters
   - Action type
   - Target entity (device, interface, link)
   - Action parameters
4. User optionally defines rollback actions
5. User saves scenario (status: `draft`)
6. User clicks "Ready" to validate (checks all referenced entities exist)
7. User clicks "Start" to begin execution
8. During execution, the timeline highlights the current event and shows progress

### 11.2.5 Inventory Management

**Purpose:** Bulk operations for devices.

**Features:**
- Import devices from CSV/YAML/JSON
- Bulk create devices from a device model (e.g., "create 100 access switches")
- Export inventory in Nornir/Ansible format
- Tag management (bulk add/remove tags)
- Bulk delete with confirmation

### 11.2.6 Live Terminal

**Purpose:** Browser-based SSH terminal for testing.

**Features:**
- WebSocket-based terminal emulator (xterm.js or similar)
- Connects to the SSH Emulation Service via a server-side SSH proxy
- User selects a device from a dropdown
- Terminal opens with authentic login prompt
- Full terminal behavior (paging, cursor, etc.)
- Session recording (optional, for demos)

## 11.3 User Workflows

### Workflow 1: Set Up a New Environment

1. **Create platforms** (or use built-in Cisco IOS / Arista EOS)
2. **Create device models** (or use built-in models)
3. **Bulk create devices:**
   - Select model
   - Enter count (e.g., 100)
   - Configure hostname pattern (e.g., `access-sw-{n:03d}`)
   - System auto-creates interfaces from model defaults
   - System auto-assigns connection mappings
4. **Create links** between devices (manually or from a topology CSV)
5. **Export Nornir inventory** and verify connectivity

### Workflow 2: Import Real Device Outputs

1. Navigate to a device
2. Open "CLI Mappings" tab
3. Click "Paste Output"
4. Enter command and paste raw output
5. Save as static replay
6. Test: open Live Terminal, run the command, verify output matches

### Workflow 3: Run a Fault Scenario

1. Open Scenario Builder
2. Create scenario: "Access switch failure"
3. Add events:
   - Event 1: Set device `access-sw-042` to maintenance (immediate)
   - Event 2: All interfaces on that device go down (immediate)
   - Event 3: Wait 60 seconds, then restore (delay)
4. Save and mark as Ready
5. Start scenario
6. Observe topology view updating in real time
7. Run Nornir script against the environment to test automation response

---

# 12. Storage Strategy

## 12.1 Primary Database: PostgreSQL

PostgreSQL is the primary and only required database. It stores all persistent state.

**Why PostgreSQL:**
- JSONB support for flexible schemas (cli_modes, hardware_details, tags, etc.)
- Strong ACID guarantees for state consistency
- Excellent query performance with proper indexing
- Native INET/CIDR types for IP addresses
- Mature tooling for backup, replication, monitoring
- Widely available as managed services (RDS, Cloud SQL, etc.)
- UUID primary key support

### 12.1.1 Schema Organization

```
Tables:
  platforms
  device_models
  devices
  interfaces
  interface_counters
  links
  command_templates
  snmp_profiles
  device_credentials
  cli_output_mappings
  scenarios
  scenario_events
  connection_mappings
  api_keys

Indexes:
  devices(hostname)                      -- unique, lookups by name
  devices(device_model_id)               -- FK join
  devices(admin_state)                   -- filter active devices
  devices(tags) USING GIN               -- tag-based queries
  interfaces(device_id, sort_order)      -- ordered interface listing
  interfaces(device_id, name)            -- unique, lookups by name
  interfaces(device_id, if_index)        -- unique, SNMP lookups
  links(interface_a_id)                  -- neighbor lookups
  links(interface_b_id)                  -- neighbor lookups
  command_templates(platform_id, command_canonical) -- template resolution
  connection_mappings(protocol, listen_address, listen_port) -- unique, connection routing
  cli_output_mappings(device_id, command, is_active) -- output resolution
```

### 12.1.2 What Is Stored Where

| Data | Storage | Rationale |
|---|---|---|
| Device/interface/link state | PostgreSQL | Source of truth, needs ACID |
| Counter base values | PostgreSQL | Persistent, infrequently written |
| Counter current values | Computed at read time | Derived from base + rate * elapsed time |
| Command templates | PostgreSQL | Versioned, shared across devices |
| CLI output mappings | PostgreSQL | Including raw_output (TEXT column) |
| Scenarios and events | PostgreSQL | Persistent definitions |
| Scenario execution state | In-memory (with Redis backup in cloud) | Transient, needs low latency |
| SSH session state | In-memory | Transient, dies with process |
| Device log buffers | In-memory (circular buffer) | Transient, bounded size |
| Connection mappings | PostgreSQL + in-memory cache | Read frequently, written rarely |
| SNMP OID tree (per device) | In-memory cache | Built from state, rebuilt on change |

### 12.1.3 Migration Strategy

- Use a standard migration tool (e.g., Alembic for Python, or golang-migrate)
- All schema changes go through versioned migrations
- Migrations must be reversible (up/down)
- Seed data migrations for built-in platforms and device models

## 12.2 In-Memory Caching Layer

**Purpose:** Reduce database load for hot-path operations (SSH commands, SNMP requests).

**What is cached:**
- Device state (refreshed on state-change events)
- Interface state (refreshed on state-change events)
- Counter base values (refreshed on mutation)
- Connection mappings (refreshed on creation/deletion)
- Resolved SNMP OID trees (invalidated on interface add/remove)

**Cache invalidation:** Event-driven. When the Inventory & State Service publishes a state-change event, cache entries for the affected entity are invalidated.

**Local mode:** In-process dictionary cache (no external dependency).
**Cloud mode:** Redis as shared cache between service instances.

## 12.3 Optional: Graph Projection Layer (Post-MVP)

For advanced topology queries (shortest path, connected components, impact analysis), a graph projection can be maintained:

- **Source:** PostgreSQL remains the source of truth
- **Projection:** On state change, update an in-memory graph structure (e.g., using NetworkX in Python or a similar library)
- **Use cases:**
  - "Show all devices affected if this link goes down"
  - "What is the shortest path between device A and device B?"
  - "Show all devices 2 hops from this core router"

**Why NOT graph DB as primary:**
1. **Operational complexity** -- adding Neo4j or similar doubles the infrastructure
2. **Data is primarily relational** -- devices, interfaces, and counters are naturally tabular
3. **Graph queries are secondary** -- most operations are CRUD on individual entities
4. **JSONB in PostgreSQL** handles semi-structured data well
5. **In-memory graph projection** provides graph query performance without a separate database
6. A graph DB may be worthwhile at Phase 3 scale if graph queries become a primary access pattern; at that point, the PostgreSQL data model provides a clean migration path

---

# 13. Performance & Scalability

## 13.1 Scale Targets

| Metric | MVP Target | Phase 2 Target | Phase 3 Target |
|---|---|---|---|
| Total devices | 100 | 1,000 | 10,000 |
| Interfaces per device | 48 | 48 | 96 |
| Total interfaces | 4,800 | 48,000 | 960,000 |
| Concurrent SSH sessions | 20 | 200 | 2,000 |
| SSH commands/sec (aggregate) | 50 | 500 | 5,000 |
| SNMP requests/sec (aggregate) | 100 | 1,000 | 10,000 |
| Active scenarios | 1 | 10 | 100 |
| API requests/sec | 50 | 200 | 1,000 |

## 13.2 Memory Model

**Per-device memory footprint (estimated):**

| Component | Size | Notes |
|---|---|---|
| Device state | ~2 KB | Core fields |
| Interface state (48 interfaces) | ~48 KB | ~1 KB per interface including counters |
| SNMP OID tree cache | ~20 KB | Pre-built OID lookup structure |
| Connection mappings | ~0.5 KB | Two entries (SSH + SNMP) |
| Log buffer | ~100 KB | 1000 entries * ~100 bytes |
| **Total per device** | **~170 KB** | |

**Scale projections:**

| Devices | Memory for state cache | Notes |
|---|---|---|
| 100 | ~17 MB | MVP -- trivial |
| 1,000 | ~170 MB | Phase 2 -- comfortable on a single machine |
| 10,000 | ~1.7 GB | Phase 3 -- single machine with 8+ GB, or distributed |

**SSH session memory:**

| Component | Size per session |
|---|---|
| SSH session state | ~5 KB |
| Session buffer | ~10 KB |
| Coroutine overhead | ~2 KB |
| **Total per session** | **~17 KB** |

2,000 concurrent sessions = ~34 MB. Negligible.

## 13.3 Async Architecture

All network-facing services use async I/O:

**SSH service:**
- Single event loop process
- Each SSH connection is an async coroutine
- Command processing is non-blocking: state reads from in-memory cache, template rendering is CPU-bound but fast (~1ms per render)
- If rendering becomes a bottleneck, use a small thread pool for template execution

**SNMP service:**
- Single event loop process
- UDP packet handling is inherently async
- Each SNMP request is processed in a coroutine
- OID resolution from cache is O(log n) via binary search on sorted OID list

**State service:**
- Database reads are async (async PostgreSQL driver)
- Cache reads are in-memory (O(1) hash lookup)
- State change events are published asynchronously

## 13.4 Connection Handling

**SSH connection limits:**
- Per-process file descriptor limit: configurable (recommend 65,536)
- Connection accept rate: bounded by event loop, typically 1,000+ connections/sec
- Idle timeout: 300 seconds (configurable) -- close idle SSH sessions to reclaim resources

**SNMP UDP handling:**
- Single UDP socket per listen address (or one per device if using loopback aliases)
- Kernel UDP buffer: 8 MB (configurable via sysctl)
- Packet processing target: <1ms per request

## 13.5 Database Performance

**Indexing strategy:** See Section 12.1.1.

**Query patterns and expected performance:**

| Query | Expected Latency | Frequency |
|---|---|---|
| Get device by ID | <1ms (cached) | Every SSH command |
| Get interfaces for device | <2ms (cached) | Every SSH command |
| Get counter values | <1ms (computed) | Every SNMP request |
| Resolve connection mapping | <1ms (cached) | Every new connection |
| List all devices (paginated) | <10ms | API/UI |
| Get topology graph | <50ms (1000 devices) | UI refresh |
| Bulk create 100 devices | <500ms | Import |

## 13.6 Horizontal Scaling (Cloud Mode)

**SSH service scaling:**
- Each SSH service instance handles a subset of devices (based on connection mapping)
- New devices can be assigned to the least-loaded instance
- Session state is local to the instance (SSH sessions are not migrated)

**SNMP service scaling:**
- Stateless -- any instance can handle any request
- Load balanced via DNS or UDP load balancer
- Device state is read from shared cache (Redis)

**State service scaling:**
- Read replicas for database
- Cache layer (Redis) absorbs read load
- Write path is always through primary database

---

# 14. Security Model

## 14.1 SSH Authentication Security

**Emulated device SSH (what automation tools connect to):**
- Password authentication only (MVP)
- Credentials stored in DeviceCredential table
- Passwords stored encrypted at rest using application-level encryption (AES-256-GCM)
- Encryption key from environment variable, not in database
- Brute force protection: 3 failed attempts per source IP = 60-second lockout
- SSH host key: RSA 2048-bit, generated per installation

**Important security note:** The emulated SSH service is NOT a production-grade SSH server. It is designed for lab/testing use. It should NOT be exposed to the public internet without additional network-level controls (firewall, VPN).

## 14.2 SNMPv3 Security

**Supported security levels:**

| Level | Authentication | Privacy | Use Case |
|---|---|---|---|
| noAuthNoPriv | Username only | None | Quick testing |
| authNoPriv | HMAC-SHA-256 | None | Authenticated polling |
| authPriv | HMAC-SHA-256 | AES-128 | Full security |

- SNMPv3 passwords stored encrypted at rest (same as SSH passwords)
- Engine ID derived per-device (prevents cross-device credential reuse attacks)
- SNMPv2 community strings are inherently insecure (sent in cleartext) -- this is true of real SNMP and is emulated faithfully

## 14.3 API Authentication

**API key model:**
- API keys are 256-bit random tokens, base62 encoded (44 characters)
- Format: `snep_<base62_token>` (e.g., `snep_a1B2c3D4e5F6...`)
- Stored as SHA-256 hash in database (raw key never stored)
- Transmitted via `Authorization: Bearer <key>` header
- Keys have permissions: `read`, `write`, `admin`

**Permission levels:**

| Permission | Can do |
|---|---|
| `read` | GET on all endpoints |
| `write` | `read` + POST/PUT/PATCH/DELETE on devices, interfaces, links, scenarios, CLI mappings |
| `admin` | `write` + manage API keys, platforms, system config |

**Local/development mode:** API authentication can be disabled via configuration flag. A warning banner appears in the UI when authentication is disabled.

## 14.4 Web UI Authentication

- Session-based authentication
- Login with username/password (stored in a users table, bcrypt hashed)
- Session token in HttpOnly cookie
- CSRF protection via double-submit cookie pattern
- Local mode: optional single-user mode with no login required

## 14.5 Network Security Recommendations

| Component | Recommendation |
|---|---|
| SSH emulation ports | Bind to localhost or private network only |
| SNMP emulation ports | Bind to localhost or private network only |
| API server | TLS termination at load balancer (cloud) or reverse proxy (local) |
| Database | Private network only, no public access |
| Redis (cloud) | Private network, AUTH enabled |

## 14.6 Secrets Management

- No secrets in code or configuration files
- All secrets via environment variables or secrets manager
- Database encryption key: `SNEP_DB_ENCRYPTION_KEY`
- API key signing: derived from encryption key
- Docker Compose: use `.env` file (gitignored) for local development

---

# 15. MVP Definition

## 15.1 MVP Scope: Included

### Core Data Model
- [x] Platform entity (Cisco IOS built-in)
- [x] DeviceModel entity (one Cisco model built-in)
- [x] Device CRUD
- [x] Interface CRUD (auto-created from model defaults)
- [x] InterfaceCounter with rate-based progression
- [x] Link/Neighbor CRUD
- [x] ConnectionMapping (port-multiplexing model)
- [x] DeviceCredential (password auth)
- [x] SNMPProfile (v2c + v3)

### SSH CLI Emulation
- [x] SSH server accepting connections
- [x] Password authentication
- [x] Connection-to-device mapping (port-multiplexed)
- [x] Cisco IOS prompt behavior (user exec, privileged exec, global config)
- [x] Command parsing with abbreviation support
- [x] Commands: `show version`, `show interfaces`, `show ip interface brief`, `show cdp neighbors`
- [x] `terminal length 0` support
- [x] Paging (`--More--`)
- [x] Unknown command error handling
- [x] `enable` / `disable` / `configure terminal` / `exit` / `end` mode transitions

### SNMP Emulation
- [x] SNMPv2c (community string auth)
- [x] SNMPv3 (USM with authPriv)
- [x] GET operation
- [x] GETNEXT operation (WALK support)
- [x] GETBULK operation
- [x] system MIB (sysDescr, sysUpTime, sysName, sysContact, sysLocation)
- [x] IF-MIB (ifTable, ifXTable)
- [x] Counter progression (time-based)

### Rendering
- [x] Jinja2-compatible template engine
- [x] Built-in templates for MVP commands on Cisco IOS
- [x] Static replay mode (CLIOutputMapping)
- [x] Template resolution priority chain

### CLI Output Modeling
- [x] Paste and store raw CLI output
- [x] Static replay mode
- [x] Per-device, per-command mappings

### API
- [x] REST API for all CRUD operations
- [x] Device, interface, link, scenario endpoints
- [x] Nornir inventory export
- [x] Command execution preview endpoint
- [x] API key authentication

### UI
- [x] Device list view
- [x] Device detail/editor
- [x] Interface table with status toggles
- [x] CLI output paste interface (static mode only)
- [x] Basic topology view (nodes + edges, no fancy layout)
- [x] Live terminal (browser-based SSH)

### Infrastructure
- [x] Docker Compose deployment
- [x] PostgreSQL database
- [x] Port-multiplexing networking model
- [x] Database migrations
- [x] Seed data (one platform, one model, example devices)

## 15.2 MVP Scope: Excluded

### Deferred to Phase 2
- [ ] Field annotation UI (structured mapping)
- [ ] Auto-conversion of annotated output to templates
- [ ] Scenario engine (scenarios exist in schema but execution engine is Phase 2)
- [ ] Arista EOS platform and templates
- [ ] Loopback alias networking model
- [ ] Multiple device models per platform
- [ ] Bulk device import (CSV/YAML)
- [ ] WebSocket real-time events
- [ ] Config mode commands that modify state

### Deferred to Phase 3
- [ ] Juniper Junos platform
- [ ] Proxy routing networking model
- [ ] Graph projection layer
- [ ] Multi-tenant support
- [ ] SNMP traps
- [ ] Syslog emission (UDP syslog)
- [ ] Custom OID plugins
- [ ] Scenario conditional triggers
- [ ] Ansible inventory export
- [ ] GraphQL API
- [ ] Session recording/playback
- [ ] Advanced topology layouts (hierarchical, geographic)

---

# 16. Phased Roadmap

## Phase 1: MVP

**Goal:** A working emulator that can fool Nornir into thinking it's talking to real Cisco IOS devices.

**Capabilities:**
- Create and manage Cisco IOS devices with interfaces, counters, and neighbors
- SSH into any emulated device and run core show commands
- SNMP poll any device and walk IF-MIB
- Paste real CLI output for static replay
- Export Nornir inventory and run automation scripts
- Basic web UI for device management and live SSH terminal

**Technical foundation:**
- PostgreSQL schema with all entities
- Async SSH server (e.g., asyncssh for Python)
- Async SNMP server (e.g., pysnmp or custom UDP handler)
- Jinja2 template rendering
- REST API with OpenAPI spec
- React/Vue frontend with basic routing
- Docker Compose deployment

**Validation criteria:**
- Nornir script can SSH to 10 devices, run `show ip interface brief`, and parse output with TextFSM
- SNMP walk of IF-MIB returns correct data for all interfaces
- Counter values advance between polls
- Interface down state reflected in both CLI and SNMP

## Phase 2: Structured Rendering & Scenarios

**Goal:** Move beyond static replay to dynamic, state-driven output generation. Enable fault injection.

**New capabilities:**
- Field annotation UI for CLI output modeling
- Auto-template generation from annotated output
- Scenario engine with immediate, delay, and manual triggers
- Arista EOS platform support with templates
- Loopback alias networking model
- Bulk device import/export
- Real-time WebSocket events
- Config mode commands that modify device state (shutdown, no shutdown, description)
- Multiple device models per platform

**Technical additions:**
- Scenario executor (async scheduler with timer support)
- WebSocket server for real-time events
- Loopback alias setup automation script
- Expanded template library (20+ commands per platform)
- State mutation pipeline with event publishing
- Redis for event bus (cloud mode)

**Validation criteria:**
- User can paste `show interfaces` output, annotate all fields, and generate a working template
- Scenario can toggle an interface, and the change is visible in SSH and SNMP within 1 second
- 1,000 devices with loopback aliases, all accessible via SSH/SNMP
- Config mode `shutdown` command changes oper_status and is reflected in subsequent show commands

## Phase 3: Scale, Multi-Platform & Cloud

**Goal:** Production-grade platform supporting thousands of devices, multiple vendors, and SaaS deployment.

**New capabilities:**
- Juniper Junos platform support
- Proxy routing networking model for cloud deployment
- Multi-tenant isolation
- SNMP trap generation
- Syslog emission (UDP)
- Custom OID plugin system
- Conditional scenario triggers
- Graph projection for topology analysis
- Advanced topology layouts
- Ansible inventory export
- GraphQL API (alongside REST)
- Session recording and playback
- Performance optimization for 10,000-device scale

**Technical additions:**
- Kubernetes deployment manifests
- Tenant isolation (schema-per-tenant or RLS)
- UDP syslog emission service
- SNMP trap sender
- NetworkX graph projection (in-memory)
- GraphQL server
- CDN for static assets
- Monitoring/observability (Prometheus metrics, structured logging)

**Validation criteria:**
- 10,000 devices, 2,000 concurrent SSH sessions, 10,000 SNMP req/sec
- Multi-vendor environment (IOS + EOS + Junos) with cross-platform neighbor discovery
- Tenant A cannot see or access Tenant B's devices
- Scenario with conditional trigger fires when polled counter exceeds threshold

---

# 17. Risks & Tradeoffs

## 17.1 Realism Challenges

| Risk | Impact | Mitigation |
|---|---|---|
| CLI output doesn't match real devices closely enough | Parsers fail, defeating the purpose | Use real device output as template source material; validate against NTC-Templates test data |
| SNMP OID coverage gaps | Monitoring tools get incomplete data | Prioritize IF-MIB and system MIB; extensible OID plugin system in Phase 3 |
| Command abbreviation behavior differs from real IOS | Automation scripts fail on abbreviation mismatch | Build abbreviation engine against Cisco documentation; test against common scripts |
| Config mode commands don't behave realistically | Cannot test config-push workflows | Phase 2: limited state mutation commands; not a full config engine |
| Timing/ordering of show command output differs | Subtle parsing failures | Use real device output as reference for column widths, spacing, ordering |

## 17.2 SNMP Complexity

| Risk | Impact | Mitigation |
|---|---|---|
| SNMPv3 implementation is complex (USM, engine discovery, key derivation) | Delayed MVP or buggy implementation | Use established SNMP library for protocol handling; focus on OID mapping logic |
| GETNEXT ordering must be lexicographically correct | SNMP walks return wrong/missing data | Pre-build sorted OID tree per device; extensive walk validation testing |
| Counter wrapping and type correctness | SNMP monitoring tools miscalculate rates | Explicit Counter32/Counter64 wrapping logic; test with real SNMP pollers (Zabbix, LibreNMS) |
| MIB coverage expectations vary by tool | "Partial" SNMP support frustrates users | Document exactly which OIDs are supported; return noSuchObject for unsupported OIDs |

## 17.3 Scale Bottlenecks

| Risk | Impact | Mitigation |
|---|---|---|
| Port exhaustion with port-multiplexing model | Cannot exceed ~55k devices per IP | Loopback alias model for Phase 2; proxy model for Phase 3 |
| Database becomes bottleneck at 10k devices | Slow API, slow rendering | In-memory cache for hot path; read replicas; connection pooling |
| SSH session memory at high concurrency | OOM or performance degradation | Lightweight coroutine model; session idle timeout; memory monitoring |
| SNMP UDP packet loss under load | Missing poll data | Kernel UDP buffer tuning; dedicated SNMP service instances |
| Loopback alias setup requires root/sudo | Deployment friction | Document setup clearly; provide helper scripts; port-multiplex as no-privilege fallback |

## 17.4 UX Complexity

| Risk | Impact | Mitigation |
|---|---|---|
| CLI annotation UI is difficult to design well | Users don't adopt structured mode | Start with static replay (easy); annotation UI in Phase 2 with user testing |
| Topology view performance with 1000+ nodes | UI becomes unusable | Server-side layout computation; viewport culling; level-of-detail rendering |
| Scenario builder complexity | Users can't create scenarios | Pre-built scenario templates; simple wizard for common patterns |
| Users expect full device simulation | "Show running-config should work!" | Clear documentation: this is an emulator, not a simulator; static replay as bridge |

## 17.5 Architectural Tradeoffs

| Decision | Tradeoff | Rationale |
|---|---|---|
| State-driven (not output-driven) | More complex initial setup; must model state before getting output | Enables consistency, scenarios, and multi-protocol derivation. Output-only is a dead end. |
| PostgreSQL over graph DB | Topology queries are less natural | 95% of operations are CRUD; graph projection in-memory serves the 5%. Avoids operational complexity of running two databases. |
| Single-process async over multi-process | CPU-bound rendering can block event loop | Keep templates simple and fast (<1ms). Thread pool fallback if needed. Simplifies deployment. |
| Port multiplexing as MVP default | Non-standard ports require tool configuration | Lowest barrier to entry; works everywhere; no root required. Loopback aliases in Phase 2. |
| Jinja2 templates over custom DSL | Less control over rendering, possible Jinja2 limitations | Jinja2 is widely known, well-tested, and powerful enough. Custom DSL is a maintenance burden. |
| Static replay as first-class feature | Two rendering paths to maintain | Critical for adoption -- users can get value immediately by pasting real output. Bridges the gap to structured rendering. |

---

# 18. Testing Strategy

## 18.1 Testing Layers

```
+--------------------------+
|  Integration Tests       |  Nornir, real SSH/SNMP clients
+--------------------------+
|  Protocol Tests          |  SSH session behavior, SNMP responses
+--------------------------+
|  Rendering Tests         |  Template output validation
+--------------------------+
|  State Logic Tests       |  State mutations, counter progression
+--------------------------+
|  Data Model Tests        |  CRUD, constraints, relationships
+--------------------------+
|  Unit Tests              |  Pure functions, utilities
+--------------------------+
```

## 18.2 Unit Tests

**Scope:** Pure functions with no I/O.

**Key areas:**
- Counter progression calculation (base + rate * time)
- Counter wrapping (32-bit and 64-bit boundaries)
- MAC address formatting (Cisco, colon, dash)
- Uptime formatting (IOS, EOS, Junos)
- Command abbreviation matching
- OID sorting and comparison
- IP address validation and formatting
- Template filter functions

**Coverage target:** 95% for utility modules.

## 18.3 Data Model Tests

**Scope:** Database schema validation against a test database.

**Key areas:**
- All entity CRUD operations
- Constraint enforcement (unique hostnames, valid enums, FK integrity)
- Cascade deletion (device -> interfaces -> counters)
- JSONB field querying (tags, cli_modes)
- Migration up/down reversibility

**Approach:** Each test uses a transaction that is rolled back after the test (fast, no test pollution).

## 18.4 State Logic Tests

**Scope:** State mutations and their side effects.

**Key tests:**

| Test | Verifies |
|---|---|
| Interface admin down cascades to oper down | Admin change side effect |
| Link down cascades to both interface oper_status | Link change side effect |
| Counter rates freeze when oper_status goes down | Counter progression logic |
| Counter rates resume when oper_status comes back up | Counter restoration logic |
| Device decommissioned prevents new connections | Device state gate |
| Counter wrapping at 2^32 boundary | Overflow behavior |
| sysUpTime advances in real time | Time-based computation |

## 18.5 Rendering Tests

**Scope:** Template rendering produces correct output.

**Approach:** Golden file testing.

1. Define a known device state (fixed hostname, interfaces, counters, neighbors)
2. Render each command template
3. Compare output against a stored "golden" file (expected output)
4. If output changes, test fails -- developer must review and update golden file

**Key test commands (Cisco IOS):**

| Command | Golden File | Key Validations |
|---|---|---|
| `show version` | `golden/ios/show_version.txt` | Uptime format, serial number, interface counts |
| `show interfaces` | `golden/ios/show_interfaces.txt` | Counter values, status text, formatting |
| `show ip interface brief` | `golden/ios/show_ip_int_brief.txt` | Column alignment, status values |
| `show cdp neighbors` | `golden/ios/show_cdp_neighbors.txt` | Neighbor rows, platform, port ID |

**Parser validation:** For each golden file, also validate that the output parses correctly with:
- NTC-Templates (TextFSM) for the corresponding platform + command
- Genie parsers (where available)

This creates a powerful validation loop: **our output must parse the same as real device output.**

## 18.6 Protocol Tests

### SSH Protocol Tests

| Test | Method | Verifies |
|---|---|---|
| SSH connection and auth | Connect with paramiko/asyncssh | Handshake, auth, session open |
| Auth failure | Connect with wrong password | 3 retries, then disconnect |
| Prompt correctness | Read initial prompt after auth | Correct hostname + mode char |
| Command execution | Send `show version\n`, read response | Command routing, rendering |
| Mode transitions | Send `enable`, check prompt change | Mode state machine |
| Paging behavior | Send command with long output | `--More--` appears at terminal length |
| `terminal length 0` | Send `terminal length 0`, then long command | No paging |
| Unknown command | Send `show foobar` | Error template response |
| Idle timeout | Connect, wait, check disconnection | Session cleanup |
| Concurrent sessions | Open 100 sessions simultaneously | All respond correctly |

### SNMP Protocol Tests

| Test | Method | Verifies |
|---|---|---|
| SNMPv2 GET sysName | snmpget with community string | Correct device hostname |
| SNMPv2 wrong community | snmpget with wrong community | No response (timeout) |
| SNMPv3 authPriv GET | snmpget with v3 credentials | Authentication + encryption |
| SNMP WALK ifTable | snmpwalk 1.3.6.1.2.1.2.2 | All interfaces returned in order |
| SNMP WALK ifXTable | snmpwalk 1.3.6.1.2.1.31.1.1 | HC counters, ifAlias |
| SNMP GETBULK | snmpbulkget with max-reps=20 | Correct number of results |
| Counter consistency | GET ifInOctets twice, 10s apart | Second value > first (rate > 0) |
| Counter wrapping | Set counter near 2^32, wait, read | Value wraps correctly |
| Interface down | Set oper_status=down, GET ifOperStatus | Returns 2 (down) |
| noSuchObject | GET unsupported OID | Correct error response |

## 18.7 Integration Tests (Automation Framework)

**Goal:** Prove that real automation tools work against SNEP without modification.

### Nornir Integration Tests

```
Test setup:
  - 10 devices (Cisco IOS) with interfaces, links, counters
  - Nornir inventory exported from SNEP API
  - Port-multiplexed networking

Test 1: Basic connectivity
  - Nornir connects to all 10 devices via Netmiko
  - Runs `show version` on all devices
  - Asserts: all tasks succeed, output is non-empty

Test 2: Parser validation
  - Runs `show ip interface brief` on all devices
  - Parses with TextFSM (ntc-templates)
  - Asserts: parsed data matches device state (interface names, IPs, statuses)

Test 3: SNMP polling
  - Uses pysnmp to walk IF-MIB on all devices
  - Asserts: ifDescr matches interface names, ifOperStatus matches state

Test 4: State change visibility
  - Set interface oper_status to down via API
  - Run `show ip interface brief` via Nornir
  - Assert: interface shows as down in parsed output
  - SNMP GET ifOperStatus: returns 2

Test 5: Counter progression
  - SNMP GET ifHCInOctets at T=0
  - Wait 10 seconds
  - SNMP GET ifHCInOctets at T=10
  - Assert: T10 value > T0 value
  - Assert: delta is approximately rate_in_bps * 10 / 8
```

### CLI Parser Compatibility Matrix

Maintain a test matrix of command + platform + parser combinations:

| Platform | Command | TextFSM (NTC) | Genie | TTP |
|---|---|---|---|---|
| cisco_ios | show version | PASS | PASS | -- |
| cisco_ios | show interfaces | PASS | PASS | -- |
| cisco_ios | show ip interface brief | PASS | PASS | -- |
| cisco_ios | show cdp neighbors | PASS | PASS | -- |
| arista_eos | show version | PASS | PASS | -- |
| arista_eos | show interfaces | PASS | PASS | -- |
| arista_eos | show ip interface brief | PASS | PASS | -- |

This matrix is run in CI. Any parser failure is a blocking issue.

## 18.8 Performance Tests

| Test | Target | Method |
|---|---|---|
| SSH connection rate | 100 connections/sec | Open connections as fast as possible, measure time to first prompt |
| SSH command throughput | 500 commands/sec (aggregate) | 100 concurrent sessions, each running commands in a loop |
| SNMP request throughput | 1,000 requests/sec | Concurrent SNMP GET requests from multiple threads |
| SNMP walk latency | <100ms per device (48 interfaces) | Full IF-MIB walk, measure total time |
| API response time | <50ms (p99) for single-entity GET | Load test with wrk or similar |
| Scenario execution overhead | <10ms per event | Measure time from trigger to state mutation |

## 18.9 CI Pipeline

```
On every commit:
  1. Lint + type check
  2. Unit tests
  3. Data model tests (against PostgreSQL in Docker)
  4. Rendering tests (golden file comparison)
  5. Protocol tests (against running SNEP instance in Docker)
  6. Parser compatibility matrix

On merge to main (additional):
  7. Nornir integration tests (10-device environment)
  8. Performance benchmarks (compare against baseline)
  9. Docker image build and push
```

---

# Appendix A: Glossary

| Term | Definition |
|---|---|
| **SNEP** | Synthetic Network Emulator Platform (this project) |
| **Emulator** | Software that mimics the external behavior of a system without implementing its internals |
| **Simulator** | Software that replicates the internal workings of a system (not what we're building) |
| **State** | The canonical representation of a device's current condition (interfaces, counters, neighbors) |
| **Rendering** | The process of converting state into protocol-specific output (CLI text, SNMP values) |
| **Static replay** | Returning verbatim, pre-recorded CLI output |
| **Structured rendering** | Generating CLI output dynamically from state via templates |
| **Connection mapping** | The association between a network endpoint (IP:port) and a device identity |
| **Golden file** | A stored reference output used for comparison in rendering tests |
| **OID** | Object Identifier -- the numeric path used to identify variables in SNMP |
| **MIB** | Management Information Base -- the schema for SNMP variables |
| **IF-MIB** | The standard MIB for network interface data (RFC 2863) |
| **ifIndex** | The numeric identifier for an interface within SNMP |
| **Counter32/Counter64** | SNMP integer types that monotonically increase and wrap at their maximum |
| **USM** | User-based Security Model -- the authentication framework for SNMPv3 |
| **Nornir** | A Python automation framework for network devices |
| **Netmiko** | A Python SSH library for network device interaction |
| **TextFSM** | A template-based parser for semi-structured CLI output |
| **NTC-Templates** | A community library of TextFSM templates for network devices |
| **Genie** | Cisco's parser library for network device output |

---

# Appendix B: Reference OID Tree (IF-MIB)

```
1.3.6.1.2.1 (mib-2)
├── 1 (system)
│   ├── 1.0  sysDescr
│   ├── 2.0  sysObjectID
│   ├── 3.0  sysUpTime
│   ├── 4.0  sysContact
│   ├── 5.0  sysName
│   ├── 6.0  sysLocation
│   └── 7.0  sysServices
├── 2 (interfaces)
│   ├── 1.0  ifNumber
│   └── 2 (ifTable)
│       └── 1 (ifEntry)
│           ├── 1.{ifIndex}   ifIndex
│           ├── 2.{ifIndex}   ifDescr
│           ├── 3.{ifIndex}   ifType
│           ├── 4.{ifIndex}   ifMtu
│           ├── 5.{ifIndex}   ifSpeed
│           ├── 6.{ifIndex}   ifPhysAddress
│           ├── 7.{ifIndex}   ifAdminStatus
│           ├── 8.{ifIndex}   ifOperStatus
│           ├── 9.{ifIndex}   ifLastChange
│           ├── 10.{ifIndex}  ifInOctets
│           ├── 11.{ifIndex}  ifInUcastPkts
│           ├── 12.{ifIndex}  ifInNUcastPkts (deprecated)
│           ├── 13.{ifIndex}  ifInDiscards
│           ├── 14.{ifIndex}  ifInErrors
│           ├── 15.{ifIndex}  ifInUnknownProtos
│           ├── 16.{ifIndex}  ifOutOctets
│           ├── 17.{ifIndex}  ifOutUcastPkts
│           ├── 18.{ifIndex}  ifOutNUcastPkts (deprecated)
│           ├── 19.{ifIndex}  ifOutDiscards
│           ├── 20.{ifIndex}  ifOutErrors
│           └── 21.{ifIndex}  ifOutQLen (deprecated)
└── 31 (ifMIB)
    └── 1 (ifMIBObjects)
        └── 1 (ifXTable)
            └── 1 (ifXEntry)
                ├── 1.{ifIndex}   ifName
                ├── 2.{ifIndex}   ifInMulticastPkts
                ├── 3.{ifIndex}   ifInBroadcastPkts
                ├── 4.{ifIndex}   ifOutMulticastPkts
                ├── 5.{ifIndex}   ifOutBroadcastPkts
                ├── 6.{ifIndex}   ifHCInOctets
                ├── 7.{ifIndex}   ifHCInUcastPkts
                ├── 8.{ifIndex}   ifHCInMulticastPkts
                ├── 9.{ifIndex}   ifHCInBroadcastPkts
                ├── 10.{ifIndex}  ifHCOutOctets
                ├── 11.{ifIndex}  ifHCOutUcastPkts
                ├── 12.{ifIndex}  ifHCOutMulticastPkts
                ├── 13.{ifIndex}  ifHCOutBroadcastPkts
                ├── 14.{ifIndex}  ifLinkUpDownTrapEnable
                ├── 15.{ifIndex}  ifHighSpeed
                ├── 16.{ifIndex}  ifPromiscuousMode
                ├── 17.{ifIndex}  ifConnectorPresent
                └── 18.{ifIndex}  ifAlias
```

---

*End of Core Specification*

---

# Addendum A: Flexible IP/Port Networking Model (Revision 1.1)

The networking model defined in Section 6 is extended with a unified **hybrid auto-configuration** system.

## Configuration

```yaml
networking:
  mode: "auto" | "port_multiplex" | "loopback" | "hybrid"
  bind_address: "0.0.0.0"
  loopback_range: "127.0.0.0/8"
  ssh_base_port: 10000
  snmp_base_port: 20000
  prefer_standard_ports: true
```

## Auto Mode Logic

1. If total device count <= 254: assign loopback IPs (127.0.0.2-255) with standard ports 22/161
2. If device count <= 65,000: assign loopback IPs from configured /16 range with standard ports
3. Overflow: fall back to port-multiplex on bind_address

## Hybrid Mode

- Allocate loopback aliases with standard ports first
- When loopback range is exhausted, allocate via port-multiplex
- Each device's actual mapping stored in ConnectionMapping table
- SSH and SNMP servers read ConnectionMapping at startup and bind accordingly

## Per-Device Override

`Device.emulation_config` can force a specific IP:port combination, overriding the auto-allocator. This supports tools that require specific addresses.

## Rationale

Some SNMP tools (e.g., net-snmp's `snmpwalk`) do not support non-standard ports easily. The hybrid model ensures these tools work by defaulting to standard ports on loopback IPs, while still scaling to thousands of devices via port-multiplex when loopback IPs are exhausted.

---

# Addendum B: External Inventory Import (Revision 1.1)

## B.1 NetBox Import (GraphQL)

Users provide a NetBox URL and API token. The importer queries the GraphQL endpoint:

**GraphQL Query:**
```graphql
{
  device_list(filters: { site: "...", role: "..." }) {
    name, serial, status,
    primary_ip4 { address },
    platform { slug, name },
    device_type { model, slug, manufacturer { name } },
    interfaces {
      name, type, enabled, mac_address, mtu, speed, description,
      ip_addresses { address },
      connected_endpoints { ... on InterfaceType { name, device { name } } }
    }
  }
}
```

**Mapping:**
- `platform.slug` -> SNEP Platform (cisco_ios, arista_eos, etc.)
- `device_type` -> DeviceModel (created if not existing)
- `interfaces` -> Interface + InterfaceCounter
- `connected_endpoints` -> Link records

## B.2 Nautobot Import (GraphQL)

Same pattern as NetBox with minor GraphQL schema differences (`devices` instead of `device_list`, `connected_endpoint` singular instead of `connected_endpoints` plural).

## B.3 NetGraphy Import (Neo4j Direct)

Users provide Neo4j Bolt connection details. The importer executes Cypher queries:

```cypher
-- Devices with interfaces
MATCH (d:Device)-[:HAS_INTERFACE]->(i:Interface)
OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
OPTIONAL MATCH (d)-[:HAS_MODEL]->(hm:HardwareModel)
RETURN d, collect(i), p, hm

-- Cable connections
MATCH (i1:Interface)-[:CONNECTED_TO]->(i2:Interface)
MATCH (d1:Device)-[:HAS_INTERFACE]->(i1)
MATCH (d2:Device)-[:HAS_INTERFACE]->(i2)
RETURN d1.hostname, i1.name, d2.hostname, i2.name
```

**Mapping (NetGraphy -> SNEP):**
- `Device.hostname` -> Device.hostname
- `Device.management_ip` -> Device.management_ip
- `Interface.name` -> Interface.name
- `Interface.interface_type` -> mapped via: physical->ethernet, virtual->vlan, lag->port_channel, loopback->loopback
- `RUNS_PLATFORM.name` -> Platform (Cisco IOS->cisco_ios, Arista EOS->arista_eos)
- `CONNECTED_TO` -> Link records
- All imported devices auto-receive ConnectionMappings and default SNMPProfiles

---

# Addendum C: CLI Command Modeling UX (Revision 1.1)

Section 7 (CLI Output Modeling System) and Section 11 (UI/UX Specification) are extended with detailed UX workflows.

## C.1 Workflow A: Paste & Replay

1. User selects a device and command from dropdowns
2. Pastes raw output from a real device into a monospace text area
3. Clicks "Save as Static Replay"
4. Output is stored as CLIOutputMapping with mode=static
5. Subsequent SSH sessions replay this output verbatim

## C.2 Workflow B: Paste & Annotate

1. Same as A, but user clicks "Annotate Fields"
2. Split-pane interface: left=raw output, right=annotation panel
3. Auto-detection highlights recognized patterns (IPs, MACs, interface names, counters, status keywords)
4. User can click-and-drag to select text and map to state fields (device.hostname, interface.oper_status, counter.in_octets, etc.)
5. Validation panel shows field coverage progress
6. When all required fields are mapped, "Convert to Template" generates a CommandTemplate

## C.3 Workflow C: Neighbor Command Mapping (CDP/LLDP)

This is the most critical sub-workflow for topology building.

1. User pastes `show cdp neighbors` or `show lldp neighbors` output
2. System parses the tabular output into structured neighbor entries
3. For each entry, system displays a card showing:
   - **Device ID** from the output
   - **Local Interface** and **Remote Interface**
   - **Match Status**: automatic hostname lookup against existing devices
     - Green: exact match found
     - Yellow: partial match (substring)
     - Red: no match in inventory
4. For matched neighbors:
   - System checks if a Link already exists between the two interfaces
   - If not, offers a "Create Link" button
5. **Bulk action**: "Create All Matched Links" button processes all resolved neighbors
6. After link creation, the topology view updates immediately

This workflow enables users to build topology from real device output without manual link creation.

---

*End of Specification Document*

# CLAUDE.md

## 🧠 Project: Synthetic Network Emulator Platform

This repository implements a **Synthetic Network Emulator Platform** that emulates enterprise network devices via:

- SSH (CLI)
- SNMPv2 / SNMPv3

The system is designed to support:

- Network automation testing (e.g. Nornir)
- Parser validation (TextFSM, Genie, etc.)
- MIM / incident workflow simulation
- AI/agent-based network operations testing

---

## ⚠️ Core Rules (MANDATORY)

### 1. SPEC-FIRST DEVELOPMENT
- NEVER start coding without referencing the spec
- All features MUST map to a defined section in the spec
- If the spec is unclear → STOP and ask for clarification
- If implementation deviates → UPDATE THE SPEC FIRST

---

### 2. STATE-DRIVEN SYSTEM (CRITICAL)
- The system is **state-first**, not output-first
- CLI and SNMP outputs MUST be derived from structured state
- DO NOT hardcode command outputs unless explicitly in "static replay mode"

---

### 3. THIS IS AN EMULATOR — NOT A SIMULATOR
DO NOT implement:
- Packet forwarding
- Routing protocols (OSPF, BGP, etc.)
- Real configuration application engines

ONLY implement:
- Behavior emulation
- CLI output rendering
- SNMP response emulation
- State transitions

---

### 4. SINGLE SOURCE OF TRUTH
All of the following MUST derive from the same state model:

- CLI output
- SNMP OIDs
- Topology relationships
- Counters
- Logs/events

No duplication of logic.

---

### 5. NO PER-DEVICE PROCESSES
- DO NOT spawn one process/container per device
- The system must support **thousands of logical devices**
- Use shared services with lightweight session handling

---

### 6. ASYNC-FIRST ARCHITECTURE
- All network services (SSH, SNMP) must be async
- Must support high concurrency
- Avoid blocking operations

---

### 7. CONTAINERIZED DEVELOPMENT ONLY
- All components must run via Docker / docker-compose
- No reliance on host environment dependencies
- Rebuild containers on changes

---

## 🏗️ System Architecture (Conceptual)

### Core Services

1. **Inventory & State Service**
   - Devices
   - Interfaces
   - Links
   - Counters
   - Scenarios

2. **SSH Emulation Service**
   - CLI sessions
   - Command handling
   - Prompt rendering

3. **SNMP Emulation Service**
   - SNMPv2 + SNMPv3
   - OID mapping
   - Counter exposure

4. **Rendering Engine**
   - Converts state → CLI output
   - Converts state → SNMP responses

5. **Scenario Engine**
   - Fault injection
   - State transitions
   - Event simulation

6. **API + UI Layer**
   - User interaction
   - CLI modeling
   - Topology visualization

---

## 🧩 Core Data Model (High-Level)

Entities:

- Platform
- Device Model
- Device
- Interface
- Link / Neighbor
- SNMP Profile
- Command Template
- Scenario
- Event

Relationships must be:
- Explicit
- Normalized
- Consistent

---

## 🌐 Networking Model (CRITICAL)

The system must support large-scale emulation WITHOUT real IP allocation.

Supported strategies:

### 1. Loopback Alias IPs (Preferred)
- Many local IPs (e.g. 127.x.x.x or 10.x.x.x loopback)
- Standard ports (22, 161)

### 2. Port Multiplexing
- One IP
- Many ports per device

### 3. Proxy Routing Layer
- Map incoming connections → device identity

The system must:
- Map SSH/SNMP requests → correct device
- Work with tools like Nornir without modification

---

## 💻 CLI Emulation Rules

- Must support:
  - show version
  - show interfaces
  - show ip interface brief
  - show cdp neighbors

- Must emulate:
  - prompts
  - login flow
  - error handling
  - terminal length behavior

- CLI must feel **realistic enough for parsers**

---

## 📡 SNMP Emulation Rules

- Must support:
  - SNMPv2
  - SNMPv3 (auth + priv)

- Required MIBs:
  - system
  - IF-MIB

- Must map:
  - interfaces → ifTable
  - counters → OIDs

---

## 🧪 CLI Modeling System (Key Feature)

Users must be able to:

1. Paste real CLI output
2. Highlight and tag fields:
   - interfaces
   - counters
   - neighbors
3. Convert to structured data

System must support:

### Static Mode
- Exact replay of pasted output

### Structured Mode
- Generated output from state

---

## 🔄 Scenario Engine

Must support:

- Interface up/down
- Counter spikes
- Neighbor changes
- Log generation

Scenarios must affect:
- CLI output
- SNMP data
- topology state

---

## 🧱 Storage Strategy

Primary DB:
- PostgreSQL

Stores:
- structured state
- device inventory
- scenarios

Optional:
- graph projection layer (NOT primary)

---

## 🚫 Anti-Patterns (DO NOT DO)

- ❌ Hardcoding CLI outputs across multiple places
- ❌ Duplicating state between services
- ❌ Building per-device containers
- ❌ Implementing real networking protocols
- ❌ Using graph DB as primary store initially
- ❌ Blocking I/O in network services

---

## 🧪 Testing Requirements

Must include:

- Unit tests for state logic
- CLI output validation tests
- SNMP response validation
- Integration tests with:
  - Nornir
  - SSH clients
  - SNMP walk tools

---

## 🚀 Development Phases

### Phase 1 (MVP)
- Inventory model
- SSH CLI emulator
- Static command replay
- Basic SNMPv2/v3
- Minimal UI

### Phase 2
- Structured rendering engine
- CLI annotation system
- Topology consistency
- Scenario engine

### Phase 3
- Logs/traps
- dynamic counters
- large-scale simulation
- agent testing integrations

---

## 🧭 Engineering Expectations

- Prefer clarity over cleverness
- Prefer explicit models over magic
- Prefer composition over inheritance
- Everything should be observable and testable

---

## 🧠 Decision Heuristics

When unsure:

1. Does this improve realism?
2. Does this maintain a single source of truth?
3. Will this scale to thousands of devices?
4. Does this align with spec-first design?

If not → do not implement.

---

## 🛑 STOP CONDITIONS

STOP and ask for clarification if:

- Spec is ambiguous
- Multiple valid architectures exist
- Tradeoffs are unclear
- Implementation would violate core rules

---

## 🎯 End Goal

Build a system where:

- Automation tools believe they are talking to real devices
- Outputs are consistent across CLI and SNMP
- Thousands of devices can be emulated on a single machine
- Engineers can simulate real-world incidents without hardware

---
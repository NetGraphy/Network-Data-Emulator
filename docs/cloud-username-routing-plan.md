# Cloud Username Routing Plan for SSH and SNMP

Status: draft for review
Last reviewed: 2026-05-02

Implementation checkpoint, 2026-05-03:

- Phase 1 SSH gateway groundwork has started.
- Added shared SSH gateway parsing and client connection helpers.
- Updated SSH auth flow so gateway and per-device sessions require password authentication.
- Added gateway-aware device connection info and Nornir/Ansible export support.
- Added focused backend tests for gateway parsing, route resolution, and Railway TCP proxy endpoint rendering.
- Next implementation slice remains Phase 2: SNMPv2c gateway routing.

## 1. Executive Summary

SNEP already supports local device routing by allocating a unique SSH and SNMP port per inventory device. That model works well on a laptop or a Docker host where we can publish many ports, but it breaks down on Railway and similar cloud platforms where exposing a large dynamic port range is impractical.

The cloud-ready direction is to route inbound protocol sessions by an inventory selector carried inside the protocol credential fields:

- SSH: `admin%core-rtr-01` selects device `core-rtr-01` and authenticates as `admin`.
- SNMPv2c: `public@core-rtr-01` selects device `core-rtr-01` and authenticates with community `public`.
- SNMPv3: context name `core-rtr-01` is preferred, with `admin%core-rtr-01` security name as an optional fallback.

This creates a single shared gateway endpoint per protocol instead of a port pair per device. For Railway specifically, SSH can be exposed publicly through Railway TCP Proxy. Public UDP SNMP is the harder constraint: Railway public networking supports HTTP/HTTPS and TCP Proxy, but not public UDP ingress. That means SNEP can implement SNMP gateway routing internally, but public Railway SNMP needs either an SNMP-over-TCP compatibility path, an edge relay, or a second deployment target that supports UDP.

## 2. Current State

### Existing Behavior

SNEP currently has three related networking models:

- `port_multiplex`: each device receives a unique SSH port and SNMP UDP port.
- `loopback`: each device receives a loopback IP and standard ports.
- SSH gateway mode: `backend/snep/ssh/server.py` already starts a single gateway port and parses `username%hostname`.

The current code paths are:

- Connection allocation: `backend/snep/services/networking.py`
- Connection model: `backend/snep/models/connection.py`
- SSH gateway: `backend/snep/ssh/server.py`
- SNMP UDP listeners: `backend/snep/snmp/server.py`
- SNMP v1/v2c handler: `backend/snep/snmp/handler.py`
- Connection info UI/API: `backend/snep/api/devices.py`, `backend/snep/api/settings.py`, `frontend/src/pages/DeviceDetail.tsx`, `frontend/src/pages/Settings.tsx`
- Inventory export: `backend/snep/api/export.py`

### Important Gap

SSH is already partly cloud-gateway aware. SNMP is still bound to the older per-device UDP socket model and selects a device by local port. The cloud routing plan should formalize both protocols around a shared "credential carries target device" contract.

## 3. Railway Constraints

Railway can expose HTTP/HTTPS services through public domains and can expose non-HTTP TCP services through TCP Proxy. Railway's TCP Proxy generates a proxy domain and proxy port, and traffic to that pair is forwarded to one configured internal service port.

Relevant Railway docs:

- TCP Proxy: https://docs.railway.com/reference/tcp-proxy
- Public Networking: https://docs.railway.com/public-networking
- Public Networking specs and limits: https://docs.railway.com/networking/public-networking/specs-and-limits
- Private Networking: https://docs.railway.com/networking/private-networking/how-it-works

Implications for SNEP:

- SSH is TCP, so a single SSH gateway port is compatible with Railway TCP Proxy.
- SNMP is normally UDP, so standard public SNMP polling cannot be exposed directly by Railway TCP Proxy.
- Railway private networking can carry UDP between services inside the Railway project, but that does not solve public SNMP polling from external tools.
- A single Railway service can expose HTTP and TCP, but keeping API and SSH as separate services may be easier operationally because each has different health checks, scaling behavior, and start commands.

## 4. Target Architecture

### Cloud Gateway Mode

Add an explicit cloud mode:

```text
SNEP_NETWORK_MODE=cloud_gateway
```

In this mode, connection allocation no longer needs unique public ports per device. Every device gets connection metadata that points at the shared gateway endpoint plus the route token required by the client.

Example logical connection info:

```yaml
ssh:
  mode: gateway
  host: snep-ssh.proxy.rlwy.net
  port: 15140
  username: admin%core-rtr-01
  route_key: core-rtr-01

snmp:
  mode: gateway
  route_key: core-rtr-01
  v2c_community: public@core-rtr-01
  v3_context: core-rtr-01
  public_transport: unavailable_on_railway_udp
```

### Routing Key

Use the device hostname as the default route key because it is already unique in the database.

Rules:

- Match exact hostname first.
- Match case-insensitive hostname second for operator convenience.
- Reserve future support for aliases, such as device UUID, management IP, or imported source-of-truth names.
- Reject route keys containing delimiter characters used by gateway credentials.

Recommended delimiter policy:

```text
SSH username:      <credential_username>%<device_hostname>
SNMPv2c community: <actual_community>@<device_hostname>
SNMPv3 context:    <device_hostname>
SNMPv3 username:   <security_username>%<device_hostname> optional fallback
```

## 5. Protocol Design

### SSH Gateway

Current command shape:

```bash
ssh admin%core-rtr-01@snep-ssh.example.com -p 2222
```

The SSH server should:

1. Parse the presented username into `credential_username` and `route_key`.
2. Resolve `route_key` to an active `Device`.
3. Validate `credential_username` and password against that device's credentials.
4. Start `CLISession` with the resolved device info.
5. Reject unknown, inactive, or unauthorized devices without revealing sensitive credential details.

Implementation notes:

- Extract parsing into a small pure function, for example `parse_gateway_username(username: str) -> GatewayPrincipal`.
- Add unit tests for missing delimiter, empty credential username, empty route key, unknown route key, and route keys with delimiter characters.
- Verify `asyncssh.SSHServer.begin_auth()` semantics while touching this code. The current implementation should be checked carefully to ensure password auth is actually required in all gateway and per-device flows.
- Keep per-device port listeners available outside cloud mode for local compatibility.
- Add a map refresh strategy. At minimum, reload on startup. Better: reload every N seconds or after inventory mutations.

### SNMPv2c Gateway

Recommended command shape for UDP-capable environments:

```bash
snmpwalk -v2c -c public@core-rtr-01 snep-snmp.example.com:161 1.3.6.1.2.1.1
```

The SNMP service should:

1. Decode the SNMP message far enough to read the community string before selecting a device.
2. Parse `public@core-rtr-01` into `actual_community=public` and `route_key=core-rtr-01`.
3. Resolve `route_key` to an active `Device`.
4. Validate `actual_community` against that device's `SNMPProfile.v2_community`.
5. Build the OID tree for the resolved device.
6. Respond using the original community string from the request, not only the stripped community. Some clients expect response metadata to match the request.
7. Silently drop unknown route keys and invalid communities, matching common SNMP behavior.

Compatibility notes:

- `public@hostname` is non-standard but works with standard SNMPv2c clients because the community is an opaque string.
- This is appropriate for testing and internal labs, but SNMPv2c remains cleartext and should not be treated as a secure public credential.
- If a device's real community contains `@`, either reject it in gateway mode or support escaping. The simpler first implementation should reject it with a validation error.

### SNMPv3 Gateway

Preferred command shape:

```bash
snmpwalk -v3 -l authPriv -u admin -a SHA -A authpass -x AES -X privpass -n core-rtr-01 snep-snmp.example.com 1.3.6.1.2.1.1
```

Fallback command shape:

```bash
snmpwalk -v3 -l authPriv -u admin%core-rtr-01 -a SHA -A authpass -x AES -X privpass snep-snmp.example.com 1.3.6.1.2.1.1
```

Recommendation:

- Prefer SNMPv3 context name as the route key because context is designed to identify a logical management context.
- Support username suffix routing only if a target tool cannot set context names cleanly.
- Use an established SNMP library for full v3 USM handling. SNEP's current handler only implements basic v1/v2c packet handling.

## 6. Railway Deployment Shape

### Minimum Cloud Deployment

Services:

- `api`: FastAPI HTTP service, exposed through Railway public HTTP domain.
- `ssh-gateway`: Python SSH gateway process, exposed through one Railway TCP Proxy.
- `postgres`: Railway Postgres.
- `frontend`: Vite/static frontend, or combined behind the API depending on final deployment packaging.

Environment variables:

```text
SNEP_DATABASE_URL=${{Postgres.DATABASE_URL}}
SNEP_NETWORK_MODE=cloud_gateway
SNEP_BIND_ADDRESS=0.0.0.0
SNEP_SSH_GATEWAY_PORT=2222
SNEP_CONNECT_HOSTNAME=<railway tcp proxy domain or custom domain>
SNEP_SECRET_KEY=<generated secret>
SNEP_SSH_HOST_KEY_PATH=/app/data/host_key
```

Operational requirements:

- Persist the SSH host key with a Railway volume or load it from a sealed variable. Without this, clients will see host key changes after redeploys.
- Start with one `ssh-gateway` replica. Multi-replica TCP proxy can work later, but the first version should avoid debugging host key, cache refresh, and connection distribution at the same time.
- Keep API and SSH start commands separate. The existing `backend/start.sh` is API-oriented and should not become responsible for SSH.

### SNMP Deployment Options

Railway cannot be the whole public SNMP answer if the requirement is standard external UDP polling.

Recommended product path:

1. Implement SNMP gateway routing in the server because it is needed for cloud and SaaS architecture.
2. Mark public SNMP on Railway as "not directly available over UDP".
3. Offer one of the following deployment options for public SNMP:

| Option | Description | Pros | Cons |
|---|---|---|---|
| UDP-capable host | Run `snep.snmp.server` on a VM or provider that exposes UDP, connected to the same database or API | Standard SNMP tools work | More infrastructure |
| Edge relay | User runs a small local UDP listener near their poller; it forwards requests to Railway over HTTPS/WebSocket/TCP | Keeps Railway as source of truth and preserves local UDP for tools | New component to build and distribute |
| SNMP over TCP | Add a TCP transport listener and document clients that support it | Fits Railway TCP Proxy | Not universally supported by SNMP pollers |
| API-only SNMP | Use `/snmp-walk` and `/snmp-get` API routes for cloud demos | Simple and already close to current UI behavior | Not real external SNMP polling |

Recommended first milestone: ship SSH gateway on Railway and document SNMP as API-only or edge-relay pending. Recommended second milestone: implement the SNMPv2c gateway parser and test it locally over UDP. Recommended third milestone: choose between edge relay and SNMP-over-TCP based on the target early adopter tools.

## 7. Data Model and Configuration Changes

### Configuration

Add these settings:

```text
SNEP_NETWORK_MODE=auto|port_multiplex|loopback|hybrid|cloud_gateway
SNEP_SSH_GATEWAY_ENABLED=true
SNEP_SSH_GATEWAY_PORT=2222
SNEP_SNMP_GATEWAY_ENABLED=true
SNEP_SNMP_GATEWAY_PORT=161
SNEP_SNMP_GATEWAY_TRANSPORT=udp|tcp|disabled
SNEP_GATEWAY_ROUTE_DELIMITER_SSH=%
SNEP_GATEWAY_ROUTE_DELIMITER_SNMP_V2=@
```

### Connection Mapping

Two possible approaches:

- Minimal change: keep `ConnectionMapping` for local modes and compute cloud gateway connection info dynamically.
- More explicit change: extend `ConnectionMapping` with `routing_mode`, `route_key`, `credential_template`, and `transport`.

Recommended first implementation: minimal change. The connection mapping table is already endpoint-oriented, and cloud gateway mode is better represented as service-level endpoint plus per-device route metadata. This avoids trying to pretend every device owns a unique listen endpoint when it does not.

### Future Alias Table

If imported inventories have multiple valid names for a device, add:

```text
device_aliases
  id
  device_id
  alias
  source
  is_primary
```

Lookup order would become hostname, alias, UUID. This is not required for the first implementation because hostname is unique today.

## 8. API and UI Changes

### Device Connection Info

Update device detail response to include mode-aware examples:

```yaml
connection_info:
  mode: cloud_gateway
  ssh:
    host: snep-ssh.proxy.rlwy.net
    port: 15140
    username: admin%core-rtr-01
    command: ssh admin%core-rtr-01@snep-ssh.proxy.rlwy.net -p 15140
  snmp:
    public_udp_available: false
    v2c_community: public@core-rtr-01
    v3_context: core-rtr-01
    note: Railway TCP Proxy does not expose standard UDP SNMP.
```

### Settings Page

Add a cloud gateway card with:

- Detected environment: Railway, Docker, native, configured.
- SSH gateway status and example command.
- SNMP public availability status.
- A warning when SNMP requires UDP but the detected platform only exposes TCP.
- Export mode selector: local per-port, local gateway, cloud gateway.

### Device Detail Page

Show:

- SSH gateway command in cloud mode.
- SNMPv2c gateway community example only when UDP gateway is available.
- SNMPv3 context example when v3 is implemented.
- Railway-specific SNMP limitation text when detected environment is Railway.

### Inventory Export

Add export variants:

```text
GET /api/v1/export/nornir?connection_mode=local
GET /api/v1/export/nornir?connection_mode=gateway
GET /api/v1/export/nornir?connection_mode=cloud_gateway
GET /api/v1/export/ansible?connection_mode=cloud_gateway
```

Nornir cloud gateway example:

```yaml
core-rtr-01:
  hostname: snep-ssh.proxy.rlwy.net
  port: 15140
  username: admin%core-rtr-01
  password: cisco123
  platform: cisco_ios
  data:
    snep_route_key: core-rtr-01
    snmp_public_udp_available: false
    snmp_v2_community_gateway: public@core-rtr-01
```

Ansible cloud gateway example:

```yaml
all:
  hosts:
    core-rtr-01:
      ansible_host: snep-ssh.proxy.rlwy.net
      ansible_port: 15140
      ansible_user: admin%core-rtr-01
      ansible_password: cisco123
      ansible_network_os: cisco.ios.ios
      ansible_connection: ansible.netcommon.network_cli
```

## 9. Implementation Plan

### Phase 1: Formalize SSH Gateway

Deliverables:

- Add pure parser and resolver helpers for SSH gateway usernames.
- Add unit tests for parser edge cases.
- Verify password auth is required in both gateway and per-device modes.
- Add config flags for gateway enablement and port.
- Update connection info and exports to generate gateway SSH commands.
- Keep local per-port mode unchanged.

Acceptance criteria:

- `ssh admin%core-rtr-01@<gateway-host> -p <gateway-port>` reaches `core-rtr-01`.
- Wrong password fails.
- Unknown hostname fails.
- `ssh admin@<gateway-host> -p <gateway-port>` returns a concise gateway usage message only after an acceptable unauthenticated path is confirmed safe, or rejects cleanly.
- Existing `ssh admin@127.0.0.1 -p 10000` still works in local mode.

### Phase 2: Add SNMPv2c Gateway Routing

Deliverables:

- Build a device map keyed by hostname for SNMP, similar to SSH.
- Add a shared UDP gateway listener in addition to per-device listeners when enabled.
- Parse `actual_community@route_key`.
- Validate stripped community against `SNMPProfile.v2_community`.
- Echo original community in the response.
- Add packet-level tests for GET, GETNEXT, GETBULK, invalid community, unknown route key, and inactive device.

Acceptance criteria:

- `snmpwalk -v2c -c public@core-rtr-01 <udp-host>:<port> 1.3.6.1.2.1.1` returns `core-rtr-01` OID values.
- `public@core-rtr-02` on the same listener returns `core-rtr-02` values.
- Invalid community or hostname returns no response.
- Existing per-device SNMP ports continue to work in local mode.

### Phase 3: Decide Public SNMP Strategy for Railway

Decision needed:

- Is standard public SNMP polling from third-party tools a hard requirement for the Railway-hosted product?

If yes, choose one:

- Build an edge relay that exposes local UDP to the user's poller and tunnels to Railway.
- Run the SNMP gateway on a UDP-capable host outside Railway.
- Implement SNMP-over-TCP and validate support in the target pollers.

If no, document:

- Railway cloud supports SSH gateway and API SNMP walk/get.
- Full external UDP SNMP requires local Docker, a UDP-capable deployment target, or the future edge relay.

### Phase 4: SNMPv3 Gateway

Deliverables:

- Replace or supplement the current v1/v2c handler with a library-backed v3 implementation.
- Use SNMP context name as the primary route key.
- Support security name suffix routing only where needed.
- Store and validate v3 auth/priv credentials securely.
- Add integration tests using `snmpwalk -v3`.

Acceptance criteria:

- `snmpwalk -v3 -u admin -n core-rtr-01 ...` resolves the correct device.
- `snmpwalk -v3 -u admin -n core-rtr-02 ...` resolves a different device on the same endpoint.
- Invalid v3 auth fails without response.

### Phase 5: Railway Packaging

Deliverables:

- Add Railway service docs or config for API and SSH gateway services.
- Document TCP Proxy setup for the SSH service's internal gateway port.
- Persist SSH host key across deploys.
- Add health checks appropriate to API and SSH.
- Add deployment smoke tests.

Acceptance criteria:

- API is reachable over Railway HTTP domain.
- SSH gateway is reachable over Railway TCP proxy domain and port.
- Host key remains stable across redeploy.
- Inventory export produces usable cloud gateway connection details.

## 10. Testing Matrix

| Area | Test Type | Cases |
|---|---|---|
| SSH parser | Unit | delimiter present, delimiter missing, empty username, empty hostname, delimiter in hostname |
| SSH auth | Integration | valid credential, wrong password, unknown route key, inactive device |
| SSH CLI | Integration | `show version`, `show interfaces`, unknown command through gateway |
| SNMP v2 parser | Unit | `public@host`, missing route key, bad delimiter, community delimiter rejection |
| SNMP v2 packets | Integration | GET, GETNEXT, GETBULK, invalid community, unknown route key |
| Connection info | API | local mode, gateway mode, Railway mode |
| Exports | Snapshot/API | Nornir local, Nornir gateway, Ansible gateway |
| Railway deployment | Manual smoke | TCP proxy reaches SSH, API health, host key persistence |

## 11. Security and Operations

Security:

- Treat SNMPv2c gateway mode as lab/test only when exposed publicly.
- Prefer SNMPv3 for any public or shared environment.
- Do not log full credentials or full community strings.
- Rate-limit failed SSH attempts per source IP and route key.
- Avoid listing all device hostnames to unauthenticated public clients unless an explicit demo mode is enabled.
- Validate route keys to avoid injection into logs, shell commands, templates, or paths.

Operations:

- Persist SSH host key.
- Use one SSH gateway replica for the first Railway release.
- Add structured logs: protocol, route_key, device_id, outcome, latency.
- Add metrics: active SSH sessions, SNMP request rate, auth failures, unknown route keys.
- Refresh gateway device maps periodically or after inventory changes.

## 12. Open Questions

1. Does the first Railway cloud solution need standard public SNMP from external pollers, or is SSH plus API-backed SNMP enough for the first demo?
2. Which early adopter tools must work with cloud SNMP: LibreNMS, Zabbix, Datadog, custom Nornir scripts, or something else?
3. Are SNMPv3 context names acceptable in those tools, or do we need community-string routing for v2c compatibility?
4. Should unauthenticated SSH gateway connections show available device examples, or should public cloud mode reject without inventory disclosure?
5. Should cloud gateway be the default whenever Railway is detected, or should it require explicit `SNEP_NETWORK_MODE=cloud_gateway`?

## 13. Recommended Next Step

Implement Phase 1 first because it converts an already-started SSH gateway into a production-worthy cloud path and unlocks Railway TCP Proxy deployments. In parallel, decide whether public UDP SNMP is a hard requirement for Railway. That decision determines whether Phase 3 should become an edge relay, SNMP-over-TCP, or a documented limitation with API-based SNMP for cloud demos.

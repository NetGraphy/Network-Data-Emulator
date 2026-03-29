# Real CLI Output Reference Samples

This file contains real CLI outputs collected from actual network devices, documentation,
and test fixtures (primarily from the ntc-templates project). These serve as ground-truth
references for building accurate Jinja2 templates in SNEP.

Sources:
- ntc-templates test fixtures (https://github.com/networktocode/ntc-templates)
- Arista official documentation (https://www.arista.com/en/um-eos/)
- Cisco NX-OS DevNet documentation (https://developer.cisco.com/docs/cisco-nexus-9000-series-nx-api-cli-reference/)
- Juniper Junos documentation (https://www.juniper.net/documentation/)
- Network engineering blogs (https://yetiops.net/, https://cmdref.net/)
- Dell ECS support documentation (https://www.dell.com/support/kbdoc/en-us/000180092/)
- GitHub: arista-northwest/shakedown, aristanetworks/arcomm, napalm-automation/napalm

---

## 1. Arista EOS - show version

### 1a. vEOS - EOS 4.14.7M (ntc-templates fixture)

```
Arista vEOS
Hardware version:
Serial number:
System MAC address:  2803.829a.1347

Software image version: 4.14.7M
Architecture:           i386
Internal build version: 4.14.7M-2384414.4147M
Internal build ID:      92a53fad-f853-42a5-9f57-c3c4ea3c26b3

Uptime:                 1 hour and 5 minutes
Total memory:           2028860 kB
Free memory:            301240 kB
```

### 1b. vEOS - EOS 4.15.2F (arcomm GitHub)

```
Arista vEOS
Hardware version:
Serial number:
System MAC address:  0800.2776.48c5

Software image version: 4.15.2F
Architecture:           i386
Internal build version: 4.15.2F-2663444.4152F
Internal build ID:      0ebbad93-563f-4920-8ecb-731057802b9c

Uptime:                 13 hours and 38 minutes
Total memory:           1897596 kB
Free memory:            158892 kB
```

### 1c. vEOS - EOS 4.16.6M (napalm issue #484)

```
Arista vEOS
Hardware version:
Serial number:
System MAC address: 5254.00dc.d547

Software image version: 4.16.6M
Architecture: i386
Internal build version: 4.16.6M-3205780.4166M
Internal build ID: e796e94c-ba3b-4355-afcf-ef0abfbfaee3

Uptime: 30 weeks, 3 days, 0 hours and 13 minutes
Total memory: 3893820 kB
Free memory: 143996 kB
```

### 1d. CCS-720XP-24ZY4-F - EOS 4.27.6M (ntc-templates fixture)

```
Arista CCS-720XP-24ZY4-F
Hardware version: 11.00
Serial number: JPE11400249
Hardware MAC address: fcbd.67c7.ffe7
System MAC address: fcbd.67c7.ffe7

Software image version: 4.27.6M
Architecture: i686
Internal build version: 4.27.6M-28481162.4276M
Internal build ID: f62c8154-2e05-4650-be1e-c30774deec7e
Image format version: 2.0
Image optimization: DEFAULT

Uptime: 134 weeks, 5 days, 23 hours and 44 minutes
Total memory: 3982820 kB
Free memory: 1807180 kB
```

### 1e. DCS-7010T-48-R - EOS 4.28.9M (ntc-templates fixture)

```
Arista DCS-7010T-48-R
Hardware version: 12.03
Serial number: JPE18523609
Hardware MAC address: 985d.82b8.faf5
System MAC address: 985d.82b8.faf5

Software image version: 4.28.9M
Architecture: i686
Internal build version: 4.28.9M-33818481.4289M
Internal build ID: ecbeee98-6249-4e05-84e6-60b46a08f83e
Image format version: 3.0
Image optimization: Strata-4GB

Uptime: 3 weeks, 0 days, 20 hours and 45 minutes
Total memory: 3982456 kB
Free memory: 2076700 kB
```

### 1f. DCS-7050SX-72-F - EOS 4.22.4M (linuxpowered boot log)

```
Arista DCS-7050SX-72-F
Hardware version: 01.00
Deviations:
Serial number: JPE14292091
System MAC address: 001c.738d.2e4b

Software image version: 4.22.4M
Architecture: i686
Internal build version: 4.22.4M-15583082.4224M
Internal build ID: 523a3357-484c-4110-9019-39750ffa8af5

Uptime: 0 weeks, 0 days, 0 hours and 3 minutes
Total memory: 3991020 kB
Free memory: 3106672 kB
```

### 1g. DCS-7280CR-48-F - EOS 4.16.6FX-7500R (shakedown GitHub)

```
Arista DCS-7280CR-48-F
Hardware version:    01.00
Serial number:       JPE16123175
System MAC address:  444c.a896.ca19

Software image version: 4.16.6FX-7500R
Architecture:           i386
Internal build version: 4.16.6FX-7500R-3217494.4166FX7500R
Internal build ID:      7b5b44e2-3f61-44d8-b386-67dabb3b2ed0

Uptime:                 26 minutes
Total memory:           16035752 kB
Free memory:            11410748 kB
```

### 1h. DCS-7280CR-48-F (second unit) - EOS 4.16.6FX-7500R (shakedown GitHub)

```
Arista DCS-7280CR-48-F
Hardware version:    01.00
Serial number:       JPE16151910
System MAC address:  444c.a896.e9e1

Software image version: 4.16.6FX-7500R
Architecture:           i386
Internal build version: 4.16.6FX-7500R-3217494.4166FX7500R
Internal build ID:      7b5b44e2-3f61-44d8-b386-67dabb3b2ed0

Uptime:                 2 weeks, 3 days, 4 hours and 17 minutes
Total memory:           16035752 kB
Free memory:            11219016 kB
```

### 1i. DCS-7280SR-48C6-M-F - EOS 4.19.5M (Arista Warrior / O'Reilly)

```
Arista DCS-7280SR-48C6-M-F
Hardware version: 21.05
Serial number: SSJ17290598
System MAC address: 2899.3abe.9f92

Software image version: 4.19.5M
Architecture: i386
Internal build version: 4.19.5M-7506183.4195M
Internal build ID: ef83948c-6c45-4097-9d8b-a78a4722d49a

Uptime: 3 minutes
Total memory: 32463792 kB
Free memory: 30178840 kB
```

### 1j. cEOSLab - EOS 4.31.6M (ntc-templates fixture)

```
Arista cEOSLab
Hardware version:
Serial number: 35BA12C16E793CAD48DE0EEC072CFD74
Hardware MAC address: 001c.73cd.2352
System MAC address: 001c.73cd.2352

Software image version: 4.31.6M-39953990.4316M (engineering build)
Architecture: x86_64
Internal build version: 4.31.6M-39953990.4316M
Internal build ID: 27a18095-d8a6-4dcf-a74c-c9ad0f655faf
Image format version: 1.0
Image optimization: None

cEOS tools version: (unknown)
Kernel version: 6.8.0-60-generic

Uptime: 2 days, 15 hours and 56 minutes
Total memory: 43138472 kB
Free memory: 27548760 kB
```

### 1k. cEOSLab - EOS 4.32.1F (ntc-templates fixture)

```
Arista cEOSLab
Hardware version:
Serial number:
Hardware MAC address: 001c.7312.b056
System MAC address: 001c.7312.b056

Software image version: 4.32.1F-37265360.4321F (engineering build)
Architecture: x86_64
Internal build version: 4.32.1F-37265360.4321F
Internal build ID: 5cc97ff0-08f5-438e-9b7c-c94dea3f44a6
Image format version: 1.0
Image optimization: None

Kernel version: 6.6.87.2-microsoft-standard-WSL2

Uptime: 1 hour and 16 minutes
Total memory: 16378596 kB
Free memory: 8609248 kB
```

### Key observations for show version templates:

- Memory is ALWAYS reported in kB (not MB)
- Hardware version field is present even when empty (vEOS)
- Newer EOS (4.27+) adds "Hardware MAC address" field separate from "System MAC address"
- Newer EOS (4.27+) adds "Image format version" and "Image optimization" fields
- cEOS adds "cEOS tools version" and "Kernel version" fields
- MAC format is always xxxx.xxxx.xxxx (dotted notation)
- Serial number format for physical: JPExxxxxxxx or SSJxxxxxxxx
- Architecture: i386 (older/32-bit), i686 (mid-gen), x86_64 (modern/cEOS)
- Internal build version format: VERSION-BUILDNUM.VERSIONCOMPACT
- Uptime formats: "X hours and Y minutes", "X weeks, Y days, Z hours and W minutes", "X days, Y hours and Z minutes"
- Physical hardware total memory: ~4GB (7010/7050), ~16GB (7280CR), ~32GB (7280SR)
- "Deviations:" field sometimes appears (can be empty)

---

## 2. Arista EOS - show ip interface brief

### 2a. ntc-templates fixture

```
Interface              IP Address         Status     Protocol         MTU
Loopback0              1.1.1.1/32         up         up             65535
Management1            unassigned         down       down            1500
Vlan10                 unassigned         down       lowerlayerdown  1500
Ethernet5              10.0.0.1/24        up         up              1500
Port-Channel1          11.11.11.11/24     down       lowerlayerdown  1500
```

### 2b. YetiOps blog (arista-01)

```
                                                                        Address
Interface         IP Address              Status       Protocol            MTU    Owner
----------------- ----------------------- ------------ -------------- ----------- -------
Ethernet1         10.100.103.253/24       up           up                 1500
Ethernet2         10.100.203.254/24       up           up                 1500
Ethernet3         192.168.122.72/24       up           up                 1500
Loopback0         192.0.2.103/32          up           up                65535
Management1       10.15.30.43/24          up           up                 1500
```

### 2c. YetiOps blog (arista-02)

```
                                                                        Address
Interface         IP Address              Status       Protocol            MTU    Owner
----------------- ----------------------- ------------ -------------- ----------- -------
Ethernet1         10.100.203.253/24       up           up                 1500
Loopback0         192.0.2.203/32          up           up                65535
Management1       10.15.30.44/24          up           up                 1500
```

### Key observations for show ip interface brief:

- TWO different header formats exist in Arista EOS:
  - Compact (older): "Interface / IP Address / Status / Protocol / MTU"
  - Extended (newer): "Interface / IP Address / Status / Protocol / MTU / Owner"
    - The extended format has an "Address" header line above
- IP addresses include CIDR notation (/24, /32)
- "unassigned" used when no IP is configured
- Protocol states: "up", "down", "lowerlayerdown"
- Loopback MTU is 65535
- Ethernet/Management MTU typically 1500

---

## 3. Arista EOS - show lldp neighbors

### 3a. ntc-templates fixture (basic)

```
Last table change time   : 0:00:02 ago
Number of table inserts  : 2
Number of table deletes  : 0
Number of table drops    : 0
Number of table age-outs : 0

Port       Neighbor Device ID             Neighbor Port ID           TTL
Et1        localhost                      Ethernet1                  120
Et2        localhost                      Ethernet2                  120
Et3/1      tg104.sjc.aristanetworks.com   Ethernet3/2                120
Ma1/1      dc1-rack11-tor1.sjc            1/1                        120
```

### 3b. ntc-templates fixture (multi-neighbor)

```
Last table change time   : 5 days, 8:24:38 ago
Number of table inserts  : 9
Number of table deletes  : 3
Number of table drops    : 0
Number of table age-outs : 3
Port          Neighbor Device ID       Neighbor Port ID    TTL
---------- ------------------------ ---------------------- ---
Et2           arista2                  Ethernet2           120
Et3           arista2                  Ethernet3           120
Et4           arista2                  Ethernet4           120
Et5           arista2                  Ethernet5           120
Et6           arista2                  Ethernet6           120
Et7           arista2                  Ethernet7           120
```

### 3c. Arista official documentation

```
switch(config)# show lldp neighbors
Last table change time   : 0:12:33 ago
Number of table inserts  : 33
Number of table deletes  : 0
Number of table drops    : 0
Number of table age-outs : 0

Port      Neighbor Device ID             Neighbor Port ID           TTL
Et3/1     tg104.sjc.aristanetworks.com   Ethernet3/2                120

Ma1/1     dc1-rack11-tor1.sjc            1/1                        120
```

### 3d. Arista official documentation - show lldp neighbors detail

```
switch# show lldp neighbors 3/1 detail

Interface Ethernet 3/1 detected 1 LLDP neighbors:

  Neighbor 001c.7300.1506/Ethernet6/25, age 8 seconds
  Discovered 5 days, 3:58:58 ago; Last changed 5 days, 3:56:57 ago
    - Chassis ID type: MAC address (4)
      Chassis ID     : 001c.7300.1506
    - Port ID type: Interface name (5)
      Port ID     : "Ethernet6/25"
    - Time To Live: 120 seconds
     - Port Description: "Ethernet6/25"
     - IEEE802.3 Power Via MDI
        Port Class               : PD
        PSE MDI Power Support    : Not Supported
        PSE MDI Power State      : Disabled
        - System Name: "Leaf-Switch1.aristanetworks.com"
        - System Description: "Arista Networks EOS version 4.10.1-SSO running on an Arista Networks DCS-7504"
        - System Capabilities : Bridge, Router
          Enabled Capabilities: Bridge
        - Management Address Subtype: IPv4 (1)
          Management Address        : 172.22.30.116
          Interface Number Subtype  : ifIndex (2)
          Interface Number          : 999999
          OID String                :
        - IEEE802.1 Port VLAN ID: 1
        - IEEE802.1/IEEE802.3 Link Aggregation
          Link Aggregation Status: Capable, Disabled (0x01)
          Port ID                : 0
        - IEEE802.3 Maximum Frame Size: 9236 bytes
```

### Key observations for show lldp neighbors:

- Port names use abbreviated form: Et1, Et3/1, Ma1/1
- Header includes metadata: table change time, inserts, deletes, drops, age-outs
- TTL is typically 120
- "Last table change time" uses format "H:MM:SS ago" or "X days, H:MM:SS ago"
- Two column header styles observed (with and without dashes separator line)
- Detail output includes Chassis ID, Port ID, System Name, System Description, Capabilities

---

## 4. Arista EOS - show interfaces

### 4a. ntc-templates fixture - Ethernet (up, with IP)

```
Ethernet1 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 0800.27dc.5443
  Internet address is 172.16.1.1/24
  Broadcast address is 255.255.255.255
  Address determined by manual configuration
  IP MTU 1500 bytes , BW 10000000 kbit
  Full-duplex, 10Gb/s, auto negotiation: off, uni-link: unknown
  Up 14 minutes, 2 seconds
  1 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 0 bps (0.0% with framing overhead), 0 packets/sec
  5 minutes output rate 0 bps (0.0% with framing overhead), 0 packets/sec
     292 packets input, 31440 bytes
     Received 3 broadcasts, 0 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     0 PAUSE input
     203 packets output, 33221 bytes
     Sent 0 broadcasts, 32 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 0 output discards
     0 PAUSE output
```

### 4b. ntc-templates fixture - Ethernet (up, with description)

```
Ethernet2 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 0800.27dc.5443
  Description: Connects to Ethernet1 on localhost
  Internet address is 172.16.2.1/24
  Broadcast address is 255.255.255.255
  Address determined by manual configuration
  IP MTU 1500 bytes , BW 10000000 kbit
  Full-duplex, 10Gb/s, auto negotiation: off, uni-link: unknown
  Up 14 minutes, 2 seconds
  1 link status changes since last clear
  Last clearing of "show interface" counters 0:15:31 ago
  5 minutes input rate 0 bps (0.0% with framing overhead), 0 packets/sec
  5 minutes output rate 0 bps (0.0% with framing overhead), 0 packets/sec
     0 packets input, 0 bytes
     Received 0 broadcasts, 0 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     0 PAUSE input
     32 packets output, 6446 bytes
     Sent 0 broadcasts, 32 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 0 output discards
     0 PAUSE output
```

### 4c. ntc-templates fixture - Ethernet (admin down)

```
Ethernet49/1 is administratively down, line protocol is notpresent (disabled)
  Hardware is Ethernet, address is fcbd.67e2.b922 (bia fcbd.67e2.b922)
  Ethernet MTU 9214 bytes , BW 100000000 kbit
  Full-duplex, 100Gb/s, auto negotiation: off, uni-link: n/a
  Down 6 days, 11 hours, 16 minutes, 54 seconds
  Loopback Mode : None
  1 link status changes since last clear
  Last clearing of "show interface" counters 6 days, 11:19:37 ago
  5 minutes input rate 0 bps (0.0% with framing overhead), 0 packets/sec
  5 minutes output rate 0 bps (0.0% with framing overhead), 0 packets/sec
     0 packets input, 0 bytes
     Received 0 broadcasts, 0 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     0 PAUSE input
     0 packets output, 0 bytes
     Sent 0 broadcasts, 0 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 0 output discards
     0 PAUSE output
```

### 4d. ntc-templates fixture - Loopback

```
Loopback0 is up, line protocol is up (connected)
  Hardware is Loopback
  Internet address is 1.1.1.1/32
  Broadcast address is 255.255.255.255
  Address determined by manual configuration
  IP MTU 65535 bytes
  Up 7 seconds
```

### 4e. ntc-templates fixture - Port-Channel (down)

```
Port-Channel1 is down, line protocol is lowerlayerdown (notconnect)
  Hardware is Port-Channel, address is 0000.0000.0000
  Ethernet MTU 9214 bytes
  Full-duplex, Unconfigured
  Active members in this channel: 0
  Fallback mode is: off
  Down 10 minutes, 21 seconds
  1 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 0 bps (- with framing overhead), 0 packets/sec
  5 minutes output rate 0 bps (- with framing overhead), 0 packets/sec
     0 packets input, 0 bytes
     Received 0 broadcasts, 0 multicast
     0 input errors, 0 input discards
     0 packets output, 0 bytes
     Sent 0 broadcasts, 0 multicast
     0 output errors, 0 output discards
```

### 4f. ntc-templates fixture - Management1

```
Management1 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 0800.27a5.02b7 (bia 0800.27a5.02b7)
  IP MTU 1500 bytes , BW 1000000 kbit
  Full-duplex, 1Gb/s, auto negotiation: on, uni-link: unknown
  Up 14 minutes, 4 seconds
  3 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 12 bps (0.0% with framing overhead), 0 packets/sec
  5 minutes output rate 46 bps (0.0% with framing overhead), 0 packets/sec
     11 packets input, 1933 bytes
     Received 11 broadcasts, 0 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     0 PAUSE input
     30 packets output, 5192 bytes
     Sent 0 broadcasts, 0 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 0 output discards
     0 PAUSE output
```

### 4g. ntc-templates fixture - Vlan (down)

```
Vlan10 is down, line protocol is lowerlayerdown (notconnect)
  Hardware is Vlan, address is 0800.27dc.5443 (bia 0800.27dc.5443)
  Internet address is 10.0.0.1/24
  Broadcast address is 255.255.255.255
  Address determined by manual configuration
  IP MTU 1500 bytes
  Down 35 seconds
```

### 4h. Dell ECS / real production switch - Ethernet with high traffic

```
Ethernet9 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 2899.3af4.e099 (bia 2899.3af4.e099)
  Description: MLAG group 1
  Member of Port-Channel1
  Ethernet MTU 9214 bytes , BW 10000000 kbit
  Full-duplex, 10Gb/s, auto negotiation: off, uni-link: n/a
  Up 16 days, 11 hours, 11 minutes, 33 seconds
  Loopback Mode : None
  143 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 4.39 Mbps (0.0% with framing overhead), 900 packets/sec
  5 minutes output rate 3.93 Mbps (0.0% with framing overhead), 837 packets/sec
     14816317766 packets input, 10767089176347 bytes
     Received 195138 broadcasts, 791536 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     121 PAUSE input
     15450395319 packets output, 12027987949137 bytes
     Sent 591418 broadcasts, 7471144 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 111784 output discards
     0 PAUSE output
```

### 4i. Dell ECS / real production - long uptime variant

```
Ethernet9 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 2xxx.xxxxx.xxxx (bia 2xxx.3xxx.0xxx)
  Description: MLAG group 1
  Member of Port-Channel1
  Ethernet MTU 9214 bytes , BW 10000000 kbit
  Full-duplex, 10Gb/s, auto negotiation: off, uni-link: n/a
  Up 176 days, 15 hours, 50 minutes, 16 seconds
  Loopback Mode : None
  64 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 83.1 Mbps (0.8% with framing overhead), 10914 packets/sec
  5 minutes output rate 44.4 Mbps (0.5% with framing overhead), 7915 packets/sec
     2089446721845 packets input, 2396162845580046 bytes
     Received 299922 broadcasts, 6615343 multicast
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol, 0 input discards
     9258523 PAUSE input
     2234539463655 packets output, 2622737809302178 bytes
     Sent 2368209 broadcasts, 59767250 multicast
     0 output errors, 0 collisions
     0 late collision, 0 deferred, 96470619 output discards
     0 PAUSE output
```

### Key observations for show interfaces:

- First line format: "InterfaceName is {up|administratively down}, line protocol is {up|lowerlayerdown|notpresent} ({connected|disabled|notconnect})"
- MAC address shown with optional "(bia xxxx.xxxx.xxxx)" for hardware address
- When interface has L3 config: "Internet address is x.x.x.x/y" and "Address determined by manual configuration"
- When interface has no L3: "Ethernet MTU" instead of "IP MTU"; no "Internet address" line
- BW values: 1000000 kbit (1G), 10000000 kbit (10G), 100000000 kbit (100G)
- Speed strings: "1Gb/s", "10Gb/s", "100Gb/s"
- "Loopback Mode : None" only shown for physical interfaces
- Counters include: runts, giants, CRC, alignment, symbol, input discards, PAUSE
- Uptime format: "X days, Y hours, Z minutes, W seconds" or "X minutes, Y seconds"
- Port-Channel uses "Active members in this channel: N" and "Fallback mode is: off"
- Loopback interfaces have minimal output: Hardware is Loopback, IP MTU 65535, no counters
- Vlan interfaces show "Hardware is Vlan"

---

## 5. Arista EOS - show inventory

### 5a. ntc-templates fixture - DCS-7150S-52-CL (compact format)

```
System information
 DCS-7150S-52-CL 52-port SFP+ 10GigE 1RU + Clock
 02.00 JPE13120702 2013-03-27
System has 2 power supply slots
 Slot Model Serial Number
 ---- ---------------- ----------------
 1 PWR-460AC-F K192KU00241CZ
 2 PWR-460AC-F K192L200751CZ
System has 4 fan modules
 Module Number of Fans Model Serial Number
 ------- --------------- ---------------- ----------------
 1 1 FAN-7000-F N/A
 2 1 FAN-7000-F N/A
 3 1 FAN-7000-F N/A
 4 1 FAN-7000-F N/A
System has 53 ports
 Type Count
 ---------------- ----
 Management 1
 Switched 52
System has 52 transceiver slots
 Port Manufacturer Model Serial Number Rev
 ---- ---------------- ---------------- ---------------- ----
 1 Arista Networks SFP-10G-SR XCW1225FD753 0002
 2 Arista Networks SFP-10G-SR XCW1225FD753 0002
 51 Arista Networks SFP-10G-SR XCW1225FD753 0002
 52 Arista Networks SFP-10G-SR XCW1225FD753 0002
```

### 5b. ntc-templates fixture - DCS-7150S-52-CL (extended format with column headers)

```
System information
 Model                    Description
 ------------------------ ----------------------------------------------------
 DCS-7150S-52-CL 52-port SFP+ 10GigE 1RU + Clock
 HW Version  Serial Number  Mfg Date   Epoch
 ----------- -------------- ---------- -----
 02.00 JPE13120702 2013-03-27 01.00
System has 2 power supply slots
 Slot Model Serial Number
 ---- ---------------- ----------------
 1 PWR-460AC-F K192KU00241CZ
 2 PWR-460AC-F K192L200751CZ
System has 4 fan modules
 Module Number of Fans Model Serial Number
 ------- --------------- ---------------- ----------------
 1 1 FAN-7000-F N/A
 2 1 FAN-7000-F N/A
 3 1 FAN-7000-F N/A
 4 1 FAN-7000-F N/A
System has 53 ports
 Type Count
 ---------------- ----
 Management 1
 Switched 52
System has 52 transceiver slots
 Port Manufacturer Model Serial Number Rev
 ---- ---------------- ---------------- ---------------- ----
 1 Arista Networks SFP-10G-SR XCW1225FD753 0002
 2 Arista Networks SFP-10G-SR XCW1225FD753 0002
 51 Arista Networks SFP-10G-SR XCW1225FD753 0002
 52 Arista Networks SFP-10G-SR XCW1225FD753 0002
```

### Key observations for show inventory:

- Sections: System information, Power supply slots, Fan modules, Ports, Transceiver slots
- Power supply models: PWR-460AC-F, PWR-750AC-F, PWR-1100AC-F (varies by chassis)
- Fan module models: FAN-7000-F (front-to-back), FAN-7000-R (rear-to-front)
- Transceiver manufacturers: "Arista Networks" for Arista-branded optics
- Common SFP models: SFP-10G-SR, SFP-10G-LR, SFP-1G-T
- Common QSFP models: QSFP-100G-SR4, QSFP-40G-SR4
- Port types: Management, Switched, Routed
- Serial numbers for PSU start with K (e.g., K192KU00241CZ)
- Two format variants exist (with and without Model/Description column headers)

---

## 6. Arista EOS - show interfaces status

### 6a. Dell ECS / real production switch

```
Port       Name                              Status       Vlan     Duplex Speed  Type         Flags
Et1        MLAG group 100                    connected    in Po100 full   10G    10GBASE-SRL
Et2        MLAG group 100                    connected    in Po100 full   10G    10GBASE-SRL
Et3        MLAG group 100                    notconnect   in Po100 full   10G    10GBASE-SRL
Et4        MLAG group 100                    notconnect   in Po100 full   10G    Not Present
Et8        MLAG group 100                    notconnect   in Po100 auto   auto   1000BASE-T
Et9        MLAG group 1                      connected    in Po1   full   10G    10GBASE-CRA
Et45       mlag peer connection              connected    in Po25  full   10G    10GBASE-CRA
Et49/1                                       notconnect   1        full   10G    Not Present
Ma1                                          connected    routed   a-full a-1G   10/100/1000
Po1        Nile Node01 (Data) MLAG 1         connected    2769     full   20G    N/A
Po25       mlag peer connection              connected    trunk    full   40G    N/A
Po100      Customer Uplink (MLAG group 100)  connected    2769     full   40G    N/A
```

### 6b. YetiOps blog - show interfaces description

```
Interface                      Status         Protocol           Description
Et1                            up             up                 To netsvr
Et2                            up             up                 To arista-02
Et3                            up             up                 To the Internet
Lo0                            up             up                 Loopback
Ma1                            up             up                 Management
```

---

## 7. Cisco NX-OS - show version

### 7a. Nexus 9396PX - NX-OS 6.1(2)I3(1) (ntc-templates fixture)

```
Cisco Nexus Operating System (NX-OS) Software
TAC support: http://www.cisco.com/tac
Copyright (C) 2002-2014, Cisco and/or its affiliates.
All rights reserved.
The copyrights to certain works contained in this software are
owned by other third parties and used and distributed under their own
licenses, such as open source.  This software is provided "as is," and unless
otherwise stated, there is no warranty, express or implied, including but not
limited to warranties of merchantability and fitness for a particular purpose.
Certain components of this software are licensed under
the GNU General Public License (GPL) version 2.0 or
GNU General Public License (GPL) version 3.0  or the GNU
Lesser General Public License (LGPL) Version 2.1 or
Lesser General Public License (LGPL) Version 2.0.
A copy of each such license is available at
http://www.opensource.org/licenses/gpl-2.0.php and
http://opensource.org/licenses/gpl-3.0.html and
http://www.opensource.org/licenses/lgpl-2.1.php and
http://www.gnu.org/licenses/old-licenses/library.txt.

Software
  BIOS: version 07.15
  NXOS: version 6.1(2)I3(1)
  BIOS compile time:  06/29/2014
  NXOS image file is: bootflash:///n9000-dk9.6.1.2.I3.1.bin
  NXOS compile time:  9/27/2014 23:00:00 [09/28/2014 06:23:37]


Hardware
  cisco Nexus9000 C9396PX Chassis
  Intel(R) Core(TM) i3-3227U C with 16402544 kB of memory.
  Processor Board ID SAL1819S6LU

  Device name: N9K1
  bootflash:   21693714 kB
Kernel uptime is 123 day(s), 5 hour(s), 15 minute(s), 19 second(s)

Last reset
  Reason: Unknown
  System version: 6.1(2)I3(1)
  Service:

plugin
  Core Plugin, Ethernet Plugin

Active Packages:
```

### 7b. Nexus 9396PX - NX-OS 9.2(2) (Cisco DevNet documentation)

```
Switch# show version
Cisco Nexus Operating System (NX-OS) Software
TAC support: http://www.cisco.com/tac
Copyright (C) 2002-2018, Cisco and/or its affiliates. All rights reserved.
The copyrights to certain works contained in this software are owned by other third parties and used and distributed under their own licenses, such as open source.  This software is provided "as is," and unless otherwise stated, there is no warranty, express or implied, including but not limited to warranties of merchantability and fitness for a particular purpose.
Certain components of this software are licensed under
the GNU General Public License (GPL) version 2.0 or
GNU General Public License (GPL) version 3.0  or the GNU
Lesser General Public License (LGPL) Version 2.1 or
Lesser General Public License (LGPL) Version 2.0.
A copy of each such license is available at http://www.opensource.org/licenses/gpl-2.0.php and http://opensource.org/licenses/gpl-3.0.html and http://www.opensource.org/licenses/lgpl-2.1.php and http://www.gnu.org/licenses/old-licenses/library.txt.
Software
BIOS: version 07.64
NXOS: version 9.2(2) [build 9.2(1.47)]
BIOS compile time:  05/16/2018
NXOS image file is: bootflash:///nxos.9.2.1.47.bin
NXOS compile time:  8/4/2018 19:00:00 [08/05/2018 03:07:21]
Hardware
cisco Nexus9000 C9396PX Chassis
Intel(R) Core(TM) i3- CPU @ 2.50GHz with 16400292 kB of memory.
Processor Board ID SAL1932LNKJ
Device name: 9396px
bootflash:   51496280 kB
Kernel uptime is 0 day(s), 20 hour(s), 36 minute(s), 18 second(s)
Last reset at 897986 usecs after Wed Aug  8 00:10:51 2018
Reason: Reset Requested by CLI command reload
System version: 9.2(1)
Service:  plugin
Core Plugin, Ethernet Plugin
Active Package(s):
```

### 7c. Nexus 9396PX (ACI mode) - NX-OS 14.0(1h) (ntc-templates fixture)

```
Cisco Nexus Operating System (NX-OS) Software
TAC support: http://www.cisco.com/tac
Documents: http://www.cisco.com/en/US/products/ps9372/tsd_products_support_series_home.html
Copyright (c) 2002-2014, Cisco Systems, Inc. All rights reserved.
The copyrights to certain works contained in this software are
owned by other third parties and used and distributed under
license. Certain components of this software are licensed under
the GNU General Public License (GPL) version 2.0 or the GNU
Lesser General Public License (LGPL) Version 2.1. A copy of each
such license is available at
http://www.opensource.org/licenses/gpl-2.0.php and
http://www.opensource.org/licenses/lgpl-2.1.php

Software
  BIOS:      version 07.64
  kickstart: version 14.0(1h) [build 14.0(1h)]
  system:    version 14.0(1h) [build 14.0(1h)]
  PE:        version 4.0(1h)
  BIOS compile time:       05/16/2018
  kickstart image file is: /bootflash/aci-n9000-dk9.14.0.1h.bin
  kickstart compile time:  10/24/2018 03:13:58 [10/24/2018 03:13:58]
  system image file is:    /bootflash/auto-s
  system compile time:     10/24/2018 03:13:58 [10/24/2018 03:13:58]


Hardware
  cisco N9K-C9396PX ("supervisor")

   Intel(R) Core(TM) i3- CPU @ 2.50GHz with 16267264 kB of memory.
  Processor Board ID SAL1909A8CT

  Device name: Leaf-101
  bootflash:    62522368 kB

Kernel uptime is 11 day(s), 01 hour(s), 57 minute(s), 02 second(s)

Last reset at 20000 usecs after Mon Mar 25 11:44:47 2019 EDT
  Reason: unknown
  System version: 14.0(1h)
  Service: module reloaded

plugin
  Core Plugin, Ethernet Plugin
```

### 7d. Nexus 9372PX - NX-OS 7.0(3)I4(3) (ntc-templates fixture)

```
Cisco Nexus Operating System (NX-OS) Software
TAC support: http://www.cisco.com/tac
Copyright (C) 2002-2016, Cisco and/or its affiliates.
All rights reserved.
The copyrights to certain works contained in this software are
owned by other third parties and used and distributed under their own
licenses, such as open source.  This software is provided "as is," and unless
otherwise stated, there is no warranty, express or implied, including but not
limited to warranties of merchantability and fitness for a particular purpose.
Certain components of this software are licensed under
the GNU General Public License (GPL) version 2.0 or
GNU General Public License (GPL) version 3.0  or the GNU
Lesser General Public License (LGPL) Version 2.1 or
Lesser General Public License (LGPL) Version 2.0.
A copy of each such license is available at
http://www.opensource.org/licenses/gpl-2.0.php and
http://opensource.org/licenses/gpl-3.0.html and
http://www.opensource.org/licenses/lgpl-2.1.php and
http://www.gnu.org/licenses/old-licenses/library.txt.

Software
  BIOS: version 07.51
  NXOS: version 7.0(3)I4(3)
  BIOS compile time:  02/15/2016
  NXOS image file is: bootflash:///nxos.7.0.3.I4.3.bin
  NXOS compile time:  9/2/2016 3:00:00 [09/02/2016 23:19:13]


Hardware
  cisco Nexus9000 C9372PX chassis
  Intel(R) Core(TM) i3- CPU @ 2.50GHz with 16401548 kB of memory.
  Processor Board ID SAL2211QQWS

  Device name: obttestw02
  bootflash:   21693714 kB
Kernel uptime is 670 day(s), 6 hour(s), 34 minute(s), 1 second(s)

Last reset
  Reason: Unknown
  System version: 7.0(3)I4(3)
  Service:

plugin
  Core Plugin, Ethernet Plugin

Active Package(s):
```

### 7e. Nexus 93180YC-FX3 - NX-OS 10.4(5) (ntc-templates fixture, modern)

```
Cisco Nexus Operating System (NX-OS) Software
TAC support: http://www.cisco.com/tac
Copyright (C) 2002-2025, Cisco and/or its affiliates.
All rights reserved.
The copyrights to certain works contained in this software are
owned by other third parties and used and distributed under their own
licenses, such as open source.  This software is provided "as is," and unless
otherwise stated, there is no warranty, express or implied, including but not
limited to warranties of merchantability and fitness for a particular purpose.
Certain components of this software are licensed under
the GNU General Public License (GPL) version 2.0 or
GNU General Public License (GPL) version 3.0  or the GNU
Lesser General Public License (LGPL) Version 2.1 or
Lesser General Public License (LGPL) Version 2.0.
A copy of each such license is available at
http://www.opensource.org/licenses/gpl-2.0.php and
http://opensource.org/licenses/gpl-3.0.html and
http://www.opensource.org/licenses/lgpl-2.1.php and
http://www.gnu.org/licenses/old-licenses/library.txt.

Software
  BIOS: version 01.11
  NXOS: version 10.4(5) [Maintenance Release]
  Host NXOS: version 10.4(5)
  BIOS compile time:  12/04/2024
  NXOS image file is: bootflash:///nxos64-cs.10.4.5.M.bin
  NXOS compile time:  3/5/2025 31:00:00 [03/01/2025 05:48:31]
  NXOS boot mode: LXC

Hardware
  cisco Nexus9000 C93180YC-FX3 Chassis
  Intel(R) Xeon(R) CPU D-1526 @ 1.80GHz with 32802700 kB of memory.
  Processor Board ID FLM27400B3D
  Device name: N9K-LAB-15
  bootflash:  115805708 kB

Kernel uptime is 60 day(s), 17 hour(s), 26 minute(s), 51 second(s)

Last reset at 769579 usecs after Wed May 28 16:37:32 2025
  Reason: Power Down/UP epld upgrade process
  System version: 9.3(15)
  Service: Power Down/UP epld upgrade process

plugin
  Core Plugin, Ethernet Plugin

Active Package(s):
```

### 7f. Nexus 5596 - NX-OS 7.1(4)N1(1) (ntc-templates fixture, kickstart/system format)

```
Documents: http://www.cisco.com/en/US/products/ps9372/tsd_products_support_series_home.html
Copyright (c) 2002-2016, Cisco Systems, Inc. All rights reserved.
The copyrights to certain works contained herein are owned by
other third parties and are used and distributed under license.
Some parts of this software are covered under the GNU Public
License. A copy of the license is available at
http://www.gnu.org/licenses/gpl.html.

Software
  BIOS:      version 3.6.0
  Power Sequencer Firmware:
             Module 1: v7.0
             Module 1: v1.0
             Module 2: v1.0
             Module 3: v1.0
  Microcontroller Firmware:        version v1.0.0.2
  QSFP Microcontroller Firmware:
             Module not detected
  CXP Microcontroller Firmware:
             Module not detected
  kickstart: version 7.1(4)N1(1)
  system:    version 7.1(4)N1(1)
  BIOS compile time:       05/09/2012
  kickstart image file is: bootflash:///n5000-uk9-kickstart.7.1.4.N1.1.bin
  kickstart compile time:  9/2/2016 10:00:00 [09/02/2016 19:37:35]
  system image file is:    bootflash:///n5000-uk9.7.1.4.N1.1.bin
  system compile time:     9/2/2016 10:00:00 [09/02/2016 21:16:21]


Hardware
  cisco Nexus 5596 Chassis ("O2 48X10GE/Modular Supervisor")
  Intel(R) Xeon(R) CPU         with 8253848 kB of memory.
  Processor Board ID FOC17153X08

  Device name: IEDP02-N5K-SW01
  bootflash:    2007040 kB

Kernel uptime is 749 day(s), 15 hour(s), 17 minute(s), 48 second(s)

Last reset at 958444 usecs after  Wed Nov  1 21:20:35 2017

  Reason: Disruptive upgrade
  System version: 7.0(7)N1(1)
  Service:

plugin
  Core Plugin, Ethernet Plugin, Fc Plugin
```

### Key observations for NX-OS show version:

- Always starts with "Cisco Nexus Operating System (NX-OS) Software" and TAC/copyright block
- Copyright year range changes with NX-OS version (2002-2014, 2002-2018, 2002-2025)
- Two software version formats:
  - Modern (Nexus 9000): "BIOS" + "NXOS" fields
  - Legacy (Nexus 5000/7000): "BIOS" + "kickstart" + "system" fields
- NX-OS 10.x adds "Host NXOS" and "NXOS boot mode: LXC" fields
- Hardware section: "cisco NexusXXXX CYYYYY Chassis" or "cisco NexusXXXX CYYYYY chassis"
- Processor Board ID format: SALxxxxxxxxx (San Jose) or FOCxxxxxxxxx (Foxconn) or FLMxxxxxxxxx
- Kernel uptime format: "N day(s), N hour(s), N minute(s), N second(s)"
- Last reset includes Reason, System version, Service
- Plugins typically: "Core Plugin, Ethernet Plugin" (+ "Fc Plugin" for Nexus 5000 with FC)

---

## 8. Juniper JunOS - show version

### 8a. M20 Router - Junos 7.2R1.7

```
user@host> show version

Hostname: router1
Model: m20
JUNOS Base OS boot [7.2-20050312.0]
JUNOS Base OS Software Suite [7.2-20050312.0]
JUNOS Kernel Software Suite [7.2R1.7]
JUNOS Packet Forwarding Engine Support (M20/M40) [7.2R1.7]
JUNOS Routing Software Suite [7.2R1.7]
JUNOS Online Documentation [7.2R1.7]
JUNOS Crypto Software Suite [7.2R1.7]
```

### 8b. MX80 Router - Junos 11.3

```
user@host5> show version

Hostname: host5
Model: mx80
JUNOS Base OS boot [11.3-20110717.0]
JUNOS Base OS Software Suite [11.3-20110717.0]
JUNOS Kernel Software Suite [11.3-20110717.0]
JUNOS Crypto Software Suite [11.3-20110717.0]
JUNOS Packet Forwarding Engine Support (MX80) [11.3-20110717.0]
JUNOS Online Documentation [11.3-20110717.0]
JUNOS Routing Software Suite [11.3-20110717.0]
```

### 8c. MX480 Router - Junos 24.4R1.9 (modern)

```
user@mx480-a> show version
Hostname: mx480-a
Model: mx480
Family: junos
Junos: 24.4R1.9
JUNOS OS Kernel 64-bit [20241104.1ed86e6_builder_bsd15_244]
JUNOS modules [20241219.060016_builder_junos_244_r1]
JUNOS OS vmguest [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS libs [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS libs compat32 [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS 32-bit compatibility [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS runtime [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS boot-ve files [20241104.1ed86e6_builder_bsd15_244]
JUNOS OS time zone information [20241104.1ed86e6_builder_bsd15_244]
```

### 8d. QFX3500 Switch - Junos 11.1R1

```
user@switch> show version

Hostname: switch
Model: qfx_s3500
JUNOS Base OS boot [11.1R1]
JUNOS Base OS Software Suite [11.1R1]
JUNOS Kernel Software Suite [11.1R1]
JUNOS Crypto Software Suite [11.1R1]
JUNOS Online Documentation [11.1R1]
JUNOS Enterprise Software Suite [11.1R1]
JUNOS Packet Forwarding Engine Support (QFX) [11.1R1]
JUNOS Routing Software Suite [11.1R1]
```

### 8e. TX Matrix Plus (multi-chassis) - Junos 12.3

```
user@host> show version

sfc0-re0:
--------------------------------------------------------------------------
Hostname: host
Model: txp
JUNOS Base OS boot [12.3-20121019.0]
JUNOS Base OS Software Suite [12.3-20121019.0]
JUNOS Kernel Software Suite [12.3-20121019.0]
JUNOS Crypto Software Suite [12.3-20121019.0]
JUNOS Packet Forwarding Engine Support (M/T Common) [12.3-20121019.0]
JUNOS Packet Forwarding Engine Support (T-Series) [12.3-20121019.0]
JUNOS Online Documentation [12.3-20121019.0]
JUNOS Services AACL Container package [12.3-20121019.0]
JUNOS Services Application Level Gateways [12.3-20121019.0]
JUNOS AppId Services [12.3-20121019.0]
JUNOS Border Gateway Function package [12.3-20121019.0]
JUNOS Services Captive Portal and Content Delivery Container package [12.3-20121019.0]
JUNOS Services HTTP Content Management package [12.3-20121019.0]
JUNOS IDP Services [12.3-20121019.0]
JUNOS Services LL-PDF Container package [12.3-20121019.0]
JUNOS Services NAT [12.3-20121019.0]
JUNOS Services PTSP Container package [12.3-20121019.0]
JUNOS Services RPM [12.3-20121019.0]
JUNOS Services Stateful Firewall [12.3-20121019.0]
JUNOS Voice Services Container package [12.3-20121019.0]
JUNOS Services Example Container package [12.3-20121019.0]
JUNOS Services Crypto [12.3-20121019.0]
JUNOS Services SSL [12.3-20121019.0]
JUNOS Services IPSec [12.3-20121019.0]
JUNOS Runtime Software Suite [12.3-20121019.0]
JUNOS Routing Software Suite [12.3-20121019.0]
```

### Key observations for JunOS show version:

- Always starts with "Hostname:" and "Model:" fields
- Junos 24.4R1+ adds "Family:" field
- Package names always in brackets: [version]
- Older versions list traditional package names: "JUNOS Base OS boot", "JUNOS Routing Software Suite"
- Modern versions (24.x) list new-style: "JUNOS OS Kernel 64-bit", "JUNOS modules", "JUNOS OS libs"
- PFE support line varies by platform: "(MX80)", "(M20/M40)", "(QFX)", "(M/T Common)", "(T-Series)"
- Model names: m20, mx80, mx240, mx480, mx960, qfx_s3500, txp, t640, t1600, t4000
- Multi-chassis systems show per-RE sections with separator lines
- No uptime or memory information in show version (use "show system uptime" and "show chassis routing-engine" for those)

---

## 9. Arista EOS - Additional Command Outputs

### 9a. show ipv6 interface brief (YetiOps blog)

```
   Interface       Status         MTU       IPv6 Address                     Addr State    Addr Source
--------------- ------------ ----------- -------------------------------- ---------------- -----------
   Et1             up            1500       fe80::5054:ff:fec5:df3c/64       up            link local
                                            2001:db8:103::f/64               up            config
   Et2             up            1500       fe80::5054:ff:fec5:df3c/64       up            link local
                                            2001:db8:203::a/64               up            config
   Lo0             up           65535       fe80::ff:fe00:0/64               up            link local
                                            2001:db8:903:beef::1/128         up            config
```

### 9b. show ip bgp summary (YetiOps blog)

```
BGP summary information for VRF default
Router identifier 192.0.2.103, local AS number 65103
Neighbor Status Codes: m - Under maintenance
  Neighbor         V  AS           MsgRcvd   MsgSent  InQ OutQ  Up/Down State   PfxRcd PfxAcc
  10.100.103.254   4  65430            403       403    0    0 06:36:38 Estab   1      1
  192.0.2.203      4  65103            399       404    0    0 06:35:11 Estab   0      0
```

### 9c. show ip ospf interface brief (YetiOps blog)

```
   Interface    Instance VRF        Area            IP Address         Cost  State      Nbrs
   Et2          1        default    0.0.0.0         10.100.203.254/24  10    Backup DR  1
   Lo0          1        default    0.0.0.0         192.0.2.103/32     10    DR         0
   Et1          1        default    0.0.0.0         10.100.103.253/24  10    DR         0
```

### 9d. show ip ospf neighbor (YetiOps blog)

```
Neighbor ID     Instance VRF      Pri State                  Dead Time   Address         Interface
192.0.2.203     1        default  1   FULL/DR                00:00:29    10.100.203.253  Ethernet2
```

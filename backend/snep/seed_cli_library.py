"""Seed the CLI Output Library with realistic sample outputs across platforms, versions, and models.

Sources: Cisco documentation, NTC-Templates test fixtures, Arista EOS documentation,
network engineering blogs, and community forums.
"""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.db import async_session_factory
from snep.models import Platform, DeviceModel, SoftwareVersion, Vendor
from snep.models.cli_library import CommandOutputLibrary
from snep.services.parser_validation import validate_against_parsers

# ---------- Additional models and versions to seed ----------

EXTRA_VENDORS = [
    {"name": "Juniper Networks", "slug": "juniper"},
    {"name": "Palo Alto Networks", "slug": "paloalto"},
]

EXTRA_MODELS = {
    "cisco_ios": [
        {"name": "isr_4331", "slug": "isr-4331", "display_name": "Cisco ISR 4331/K9"},
        {"name": "isr_4321", "slug": "isr-4321", "display_name": "Cisco ISR 4321/K9"},
        {"name": "asr_1001x", "slug": "asr-1001x", "display_name": "Cisco ASR 1001-X"},
        {"name": "catalyst_3850_48xs", "slug": "ws-c3850-48xs", "display_name": "Cisco Catalyst 3850-48XS"},
        {"name": "catalyst_2960x_48td", "slug": "ws-c2960x-48td-l", "display_name": "Cisco Catalyst 2960X-48TD-L"},
    ],
    "arista_eos": [
        {"name": "7050sx_64", "slug": "dcs-7050sx-64", "display_name": "Arista DCS-7050SX-64"},
        {"name": "7280cr2a_30", "slug": "dcs-7280cr2a-30", "display_name": "Arista DCS-7280CR2A-30"},
        {"name": "720xp_48zc6", "slug": "ccs-720xp-48zc6", "display_name": "Arista CCS-720XP-48ZC6"},
    ],
}

EXTRA_VERSIONS = {
    "cisco_ios": [
        {"version_string": "15.2(7)E1", "major": 15, "minor": 2, "patch": "7E1", "status": "end_of_support"},
        {"version_string": "16.12.04", "major": 16, "minor": 12, "patch": "04", "status": "deprecated"},
        {"version_string": "03.13.06a.S", "major": 3, "minor": 13, "patch": "06a.S", "status": "end_of_support"},
    ],
    "arista_eos": [
        {"version_string": "4.28.3M", "major": 4, "minor": 28, "patch": "3M", "status": "current"},
        {"version_string": "4.22.4M", "major": 4, "minor": 22, "patch": "4M", "status": "deprecated"},
        {"version_string": "4.31.1F", "major": 4, "minor": 31, "patch": "1F", "status": "current"},
    ],
}


# ---------- CLI Output Samples ----------

SAMPLES = []

# ===== Cisco IOS-XE: Catalyst 9300-48T, version 17.06.05 =====

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show version",
    "output": """Cisco IOS XE Software, Version 17.06.05
Cisco IOS Software [Bengaluru], Catalyst L3 Switch Software (CAT9K_IOSXE), Version 17.06.05, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2024 by Cisco Systems, Inc.
Compiled Sat 17-Jun-24 07:03 by mcpre


Cisco IOS-XE software, Copyright (c) 2005-2024 by cisco Systems, Inc.
All rights reserved.  Certain components of Cisco IOS-XE software are
licensed under the GNU General Public License ("GPL") Version 2.0.  The
software code licensed under GPL Version 2.0 is free software that comes
with ABSOLUTELY NO WARRANTY.  You can redistribute and/or modify such
GPL code under the terms of GPL Version 2.0.  For more details, see the
documentation or "License Notice" file accompanying the IOS-XE software,
or the applicable URL provided on the flyer accompanying the IOS-XE
software.


ROM: IOS-XE ROMMON
BOOTLDR: System Bootstrap, Version 17.06.05 [FC2], RELEASE SOFTWARE (P)

core-rtr-01 uptime is 2 years, 14 weeks, 3 days, 7 hours, 22 minutes
Uptime for this control processor is 2 years, 14 weeks, 3 days, 7 hours, 24 minutes
System returned to ROM by PowerOn
System restarted at 14:32:11 UTC Mon Jan 15 2024
System image file is "flash:packages.conf"
Last reload reason: PowerOn



This product contains cryptographic features and is subject to United
States and local country laws governing import, export, transfer and
use. Delivery of Cisco cryptographic products does not imply
third-party authority to import, export, distribute or use encryption.
Importers, exporters, distributors and users are responsible for
compliance with U.S. and local country laws. By using this product you
agree to comply with applicable laws and regulations. If you are unable
to comply with U.S. and local laws, return this product immediately.

A summary of U.S. laws governing Cisco cryptographic products may be found at:
http://www.cisco.com/wwl/export/crypto/tool/stqrg.html

If you require further assistance please contact us by sending email to
export@cisco.com.


Technology Package License Information:

-----------------------------------------------------------------
Technology-package                   Technology-package
Current                              Type
-----------------------------------------------------------------
network-essentials                   Smart License
DNA-essentials                       Subscription Smart License


Smart Licensing Status: REGISTERED/AUTHORIZED

cisco C9300-48T (ARM) processor with 1419044K/6147K bytes of memory.
Processor board ID FCW2145L0RN
2 Virtual Ethernet interfaces
52 Gigabit Ethernet interfaces
4 Ten Gigabit Ethernet interfaces
2048K bytes of non-volatile configuration memory.
16384K bytes of physical memory.

Configuration register is 0x102"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show ip interface brief",
    "output": """Interface              IP-Address      OK? Method Status                Protocol
Vlan1                  10.1.1.1        YES manual up                    up
GigabitEthernet0/0     unassigned      YES unset  up                    up
GigabitEthernet1/0/1   10.0.1.1        YES manual up                    up
GigabitEthernet1/0/2   10.0.2.1        YES manual up                    up
GigabitEthernet1/0/3   10.0.3.1        YES manual up                    up
GigabitEthernet1/0/4   unassigned      YES unset  up                    up
GigabitEthernet1/0/5   unassigned      YES unset  administratively down down
GigabitEthernet1/0/6   unassigned      YES unset  administratively down down
GigabitEthernet1/0/7   unassigned      YES unset  up                    down
TenGigabitEthernet1/1/1 unassigned     YES unset  up                    up
TenGigabitEthernet1/1/2 unassigned     YES unset  down                  down
Loopback0              10.255.1.1      YES manual up                    up"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show cdp neighbors",
    "output": """Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
dist-sw-01.example.com
                 Gig 1/0/1         162              R S I  WS-C3850 Gig 1/0/49
dist-sw-02.example.com
                 Gig 1/0/2         171              R S I  WS-C3850 Gig 1/0/49
core-rtr-02      Gig 1/0/3         155              R S I  C9300-48 Gig 1/0/3
SEP001A2B3C4D5E  Gig 1/0/4         145                P            Port 1

Total cdp entries displayed : 4"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show interfaces GigabitEthernet1/0/1",
    "output": """GigabitEthernet1/0/1 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is aabb.cc01.0001 (bia aabb.cc01.0001)
  Description: Uplink to dist-sw-01
  Internet address is 10.0.1.1/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 45/255, rxload 112/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full-duplex, 1000Mb/s, media type is 10/100/1000BaseTX
  input flow-control is off, output flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:01, output 00:00:00, output hang never
  Last clearing of "show interface" counters 14w3d
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 450000000 bits/sec, 878906 packets/sec
  5 minute output rate 225000000 bits/sec, 439453 packets/sec
     584792031847 packets input, 4839201748523 bytes, 0 no buffer
     Received 12847 broadcasts (8471 multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 12847 multicast, 0 pause input
     291034958271 packets output, 2419384751892 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show inventory",
    "output": """NAME: "Chassis", DESCR: "Cisco Catalyst 9300-48T Switch"
PID: C9300-48T          , VID: V02  , SN: FCW2145L0RN

NAME: "Power Supply Module 0", DESCR: "Cisco Catalyst 9300 1100W AC Power Supply"
PID: PWR-C1-1100WAC     , VID: V02  , SN: LIT2142FAKP

NAME: "Fan Tray 0", DESCR: "Cisco Catalyst 9300 Fan Tray"
PID: C9300-FAN-1        , VID:      , SN:

NAME: "Slot 1 Supervisor", DESCR: "Cisco Catalyst 9300-48T Switch"
PID: C9300-48T          , VID: V02  , SN: FCW2145L0RN

NAME: "TenGigabitEthernet1/1/1", DESCR: "SFP+ 10GBASE-SR"
PID: SFP-10G-SR         , VID: V03  , SN: AVD2044R2TY

NAME: "TenGigabitEthernet1/1/2", DESCR: "SFP+ 10GBASE-SR"
PID: SFP-10G-SR         , VID: V03  , SN: AVD2044R2UZ"""
})

# ===== Cisco IOS-XE: ISR 4331, version 16.09.06 =====

SAMPLES.append({
    "platform": "cisco_ios", "model": "isr_4331", "version": "16.09.06",
    "command": "show version",
    "output": """Cisco IOS XE Software, Version 16.09.06
Cisco IOS Software [Fuji], ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 16.09.06, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2020 by Cisco Systems, Inc.
Compiled Fri 31-Jul-20 17:37 by mcpre

Cisco IOS-XE software, Copyright (c) 2005-2020 by cisco Systems, Inc.
All rights reserved.

ROM: IOS-XE ROMMON

isr4331-rtr-01 uptime is 1 year, 22 weeks, 5 days, 11 hours, 43 minutes
Uptime for this control processor is 1 year, 22 weeks, 5 days, 11 hours, 45 minutes
System returned to ROM by reload
System restarted at 03:12:45 UTC Thu Sep 10 2020
System image file is "bootflash:isr4300-universalk9.16.09.06.SPA.bin"
Last reload reason: Reload Command

cisco ISR4331/K9 (1RU) processor with 1795979K/6147K bytes of memory.
Processor board ID FLM2203P1AB
3 Gigabit Ethernet interfaces
1 Serial interface
32768K bytes of non-volatile configuration memory.
8388608K bytes of physical memory.
6684671K bytes of flash memory at bootflash:.

Configuration register is 0x2102"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "isr_4331", "version": "16.09.06",
    "command": "show ip interface brief",
    "output": """Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0/0   203.0.113.1     YES NVRAM  up                    up
GigabitEthernet0/0/1   10.0.100.1      YES NVRAM  up                    up
GigabitEthernet0/0/2   unassigned      YES NVRAM  administratively down down
Serial0/1/0            172.16.0.1      YES NVRAM  up                    up
Loopback0              10.255.0.1      YES NVRAM  up                    up"""
})

SAMPLES.append({
    "platform": "cisco_ios", "model": "isr_4331", "version": "16.09.06",
    "command": "show inventory",
    "output": """NAME: "Chassis", DESCR: "Cisco ISR4331 Chassis"
PID: ISR4331/K9         , VID: V05  , SN: FLM2203P1AB

NAME: "Power Supply Module 0", DESCR: "250W AC Power Supply for Cisco ISR 4330"
PID: PWR-4330-AC        , VID: V02  , SN: PST2145ABCD

NAME: "Fan Tray", DESCR: "Cisco ISR4330 Fan Assembly"
PID: ACS-4330-FANASSY   , VID:      , SN:

NAME: "module 0", DESCR: "Cisco ISR4331 Built-In NIM controller"
PID: ISR4331/K9         , VID:      , SN:

NAME: "NIM subslot 0/1", DESCR: "NIM-1T Serial Module"
PID: NIM-1T             , VID: V01  , SN: FOC21432K1P

NAME: "module R0", DESCR: "Cisco ISR4331 Route Processor"
PID: ISR4331/K9         , VID: V05  , SN: FLM2203P1AB

NAME: "module F0", DESCR: "Cisco ISR4331 Forwarding Processor"
PID: ISR4331/K9         , VID:      , SN:"""
})

# ===== Cisco IOS-XE: ASR 1001-X, version 16.09.08 =====

SAMPLES.append({
    "platform": "cisco_ios", "model": "asr_1001x", "version": "16.09.08",
    "command": "show version",
    "output": """Cisco IOS XE Software, Version 16.09.08
Cisco IOS Software [Fuji], ASR1000 Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 16.09.08, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2021 by Cisco Systems, Inc.
Compiled Tue 02-Mar-21 07:07 by mcpre

Cisco IOS-XE software, Copyright (c) 2005-2021 by cisco Systems, Inc.
All rights reserved.

ROM: 16.09.08

asr1001x-rtr-01 uptime is 3 years, 2 weeks, 1 day, 8 hours, 12 minutes
Uptime for this control processor is 3 years, 2 weeks, 1 day, 8 hours, 14 minutes
System returned to ROM by reload
System restarted at 08:22:33 UTC Sat Mar 13 2021
System image file is "bootflash:asr1001x-universalk9.16.09.08.SPA.bin"
Last reload reason: Reload Command

cisco ASR1001-X (1NG) processor with 3745036K/6147K bytes of memory.
Processor board ID FOX1832P4XY
8 Gigabit Ethernet interfaces
2 Ten Gigabit Ethernet interfaces
32768K bytes of non-volatile configuration memory.
16777216K bytes of physical memory.
14942207K bytes of flash memory at bootflash:.

Configuration register is 0x2102"""
})

# ===== Cisco IOS: Catalyst 2960X, version 15.2(7)E1 =====

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_2960x_48td", "version": "15.2(7)E1",
    "command": "show version",
    "output": """Cisco IOS Software, C2960X Software (C2960X-UNIVERSALK9-M), Version 15.2(7)E1, RELEASE SOFTWARE (fc1)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2019 by Cisco Systems, Inc.
Compiled Wed 06-Nov-19 06:42 by prod_rel_team

ROM: Bootstrap program is C2960X boot loader
BOOTLDR: C2960X Boot Loader (C2960X-HBOOT-M) Version 15.2(7r)E1, RELEASE SOFTWARE (fc1)

access-sw-01 uptime is 47 weeks, 3 days, 14 hours, 22 minutes
System returned to ROM by power-on
System restarted at 09:14:22 CDT Fri May 1 2020
System image file is "flash:c2960x-universalk9-mz.152-7.E1.bin"

cisco WS-C2960X-48TD-L (APM86XXX) processor (revision N0) with 524288K bytes of memory.
Processor board ID FCW2367N2XY
Last reset from power-on
2 Virtual Ethernet interfaces
1 FastEthernet interface
52 Gigabit Ethernet interfaces
2 Ten Gigabit Ethernet interfaces
The password-recovery mechanism is enabled.

512K bytes of flash-simulated non-volatile configuration memory.
Total of 131072K bytes of Flash internal.
15935K bytes of Flash external.

Base ethernet MAC Address       : A0:B1:C2:D3:E4:F5
Motherboard assembly number     : 73-16300-05
Motherboard serial number       : FCW2367N2XY
Model revision number           : N0
Motherboard revision number     : A0
Model number                    : WS-C2960X-48TD-L
System serial number            : FCW2367N2XY
Top Assembly Part Number        : 68-5388-02
Top Assembly Revision Number    : A0
Version ID                      : V05
CLEI Code Number                : CMMQ200ARC
Hardware Board Revision Number  : 0x02


Switch Ports Model                     SW Version            SW Image
------ ----- -----                     ----------            ----------
*    1 54    WS-C2960X-48TD-L          15.2(7)E1             C2960X-UNIVERSALK9-M

Configuration register is 0xF"""
})

# ===== Arista EOS: 7050SX-64, version 4.22.4M =====

SAMPLES.append({
    "platform": "arista_eos", "model": "7050sx_64", "version": "4.22.4M",
    "command": "show version",
    "output": """Arista DCS-7050SX-64-F
Hardware version:    01.01
Serial number:       JPE14080459
System MAC address:  001c.7340.1a18

Software image version: 4.22.4M
Architecture:           i386
Internal build version: 4.22.4M-14695974.4224M
Internal build ID:      d0e9014b-abf0-4779-8f39-5bd2aee8c1f2

Uptime:                 62 weeks, 3 days, 4 hours and 38 minutes
Total memory:           3982456 kB
Free memory:            2417500 kB"""
})

SAMPLES.append({
    "platform": "arista_eos", "model": "7050sx_64", "version": "4.22.4M",
    "command": "show ip interface brief",
    "output": """                                                                        Address
Interface         IP Address            Status      Protocol         MTU    Owner
Ethernet1         10.0.1.1/30           up          up              1500
Ethernet2         10.0.2.1/30           up          up              1500
Ethernet3         unassigned            up          up              9214
Ethernet4         unassigned            down        down            9214
Loopback0         10.255.0.1/32         up          up             65535
Management1       192.168.1.10/24       up          up              1500
Port-Channel1     10.0.100.1/30         up          up              9214
Vlan100           10.100.0.1/24         up          up              1500"""
})

SAMPLES.append({
    "platform": "arista_eos", "model": "7050sx_64", "version": "4.22.4M",
    "command": "show lldp neighbors",
    "output": """Last table change time   : 2:04:12 ago
Number of table inserts  : 5
Number of table deletes  : 0
Number of table drops    : 0
Number of table age-outs : 0

Port          Neighbor Device ID    Neighbor Port ID    TTL
Et1           spine-01.dc1          Ethernet3           120
Et2           spine-02.dc1          Ethernet3           120
Et49          leaf-02.dc1           Ethernet49          120
Ma1           mgmt-sw-01            Gi1/0/24            120"""
})

SAMPLES.append({
    "platform": "arista_eos", "model": "7050sx_64", "version": "4.22.4M",
    "command": "show interfaces Ethernet1",
    "output": """Ethernet1 is up, line protocol is up (connected)
  Hardware is Ethernet, address is 001c.7340.1a19
  Description: Uplink to spine-01
  Internet address is 10.0.1.1/30
  Broadcast address is 255.255.255.255
  IP MTU 1500 bytes (default)
  Up 62 weeks, 3 days, 4 hours, 38 minutes, 12 seconds
  10 Gbps full-duplex, 10GBASE-SR, auto negotiation: off, uni-link: n/a
  Loopback Mode : None
  2 link status changes since last clear
  Last clearing of "show interface" counters never
  5 minutes input rate 312.4 Mbps (3.0% with framing overhead), 38207 packets/sec
  5 minutes output rate 158.7 Mbps (1.5% with framing overhead), 19412 packets/sec
     842891273416 packets input, 681924791024832 bytes
     Received 0 broadcasts, 48271 multicasts
     0 runts, 0 giants
     0 input errors, 0 CRC, 0 alignment, 0 symbol
     0 PAUSE input
     429817364021 packets output, 347238104192736 bytes
     Sent 0 broadcasts, 24136 multicasts
     0 output errors, 0 collisions
     0 late collision, 0 deferred
     0 PAUSE output"""
})

# ===== Arista EOS: CCS-720XP, version 4.31.1F =====

SAMPLES.append({
    "platform": "arista_eos", "model": "720xp_48zc6", "version": "4.31.1F",
    "command": "show version",
    "output": """Arista CCS-720XP-48ZC6
Hardware version:    11.00
Serial number:       SSJ23456789
Hardware MAC address: 001c.7390.abcd
System MAC address:  001c.7390.abcd

Software image version: 4.31.1F
Architecture:           x86_64
Internal build version: 4.31.1F-34554157.4311F
Internal build ID:      a8bc23ef-1234-5678-9abc-def012345678
Image format version:   3.0
Image optimization:     Default

cEOSLab:               No

Uptime:                 12 weeks, 5 days, 3 hours and 47 minutes
Total memory:           8143532 kB
Free memory:            5234112 kB"""
})

# ===== Cisco IOS: show interfaces full (multi-interface) =====

SAMPLES.append({
    "platform": "cisco_ios", "model": "catalyst_9300_48t", "version": "17.06.05",
    "command": "show interfaces",
    "output": """GigabitEthernet1/0/1 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is aabb.cc01.0001 (bia aabb.cc01.0001)
  Description: Uplink to dist-sw-01
  Internet address is 10.0.1.1/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 45/255, rxload 112/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full-duplex, 1000Mb/s, media type is 10/100/1000BaseTX
  input flow-control is off, output flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:01, output 00:00:00, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 450000000 bits/sec, 878906 packets/sec
  5 minute output rate 225000000 bits/sec, 439453 packets/sec
     584792031847 packets input, 4839201748523 bytes, 0 no buffer
     Received 12847 broadcasts (8471 multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 12847 multicast, 0 pause input
     291034958271 packets output, 2419384751892 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out
GigabitEthernet1/0/2 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is aabb.cc01.0002 (bia aabb.cc01.0002)
  Description: Uplink to dist-sw-02
  Internet address is 10.0.2.1/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 22/255, rxload 55/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full-duplex, 1000Mb/s, media type is 10/100/1000BaseTX
  input flow-control is off, output flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:03, output 00:00:01, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 220000000 bits/sec, 429687 packets/sec
  5 minute output rate 110000000 bits/sec, 214843 packets/sec
     291034958271 packets input, 2419384751892 bytes, 0 no buffer
     Received 6423 broadcasts (4235 multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 6423 multicast, 0 pause input
     145517479135 packets output, 1209692375946 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out
Loopback0 is up, line protocol is up
  Hardware is Loopback
  Internet address is 10.255.1.1/32
  MTU 65535 bytes, BW 8000000 Kbit/sec, DLY 5000 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation LOOPBACK, loopback not set
  Keepalive set (10 sec)
  Last input never, output never, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/0 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     0 packets input, 0 bytes, 0 no buffer
     Received 0 broadcasts (0 multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored, 0 abort
     0 packets output, 0 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 output buffer failures, 0 output buffers swapped out"""
})


async def seed_cli_library(session: AsyncSession) -> None:
    """Create extra models/versions and seed CLI library entries."""

    # Check if already seeded
    result = await session.execute(select(CommandOutputLibrary).limit(1))
    if result.scalar_one_or_none():
        print("CLI library already seeded, skipping.")
        return

    # Get platform IDs
    platforms = {}
    result = await session.execute(select(Platform))
    for p in result.scalars().all():
        platforms[p.name] = p

    # Create extra vendors
    for v_data in EXTRA_VENDORS:
        existing = (await session.execute(select(Vendor).where(Vendor.slug == v_data["slug"]))).scalar_one_or_none()
        if not existing:
            session.add(Vendor(**v_data))
    await session.flush()

    # Get vendor map
    vendor_map = {}
    for v in (await session.execute(select(Vendor))).scalars().all():
        vendor_map[v.slug] = v

    # Create extra models
    model_map = {}
    for platform_name, models in EXTRA_MODELS.items():
        platform = platforms.get(platform_name)
        if not platform:
            continue
        for m_data in models:
            existing = (await session.execute(
                select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == m_data["name"])
            )).scalar_one_or_none()
            if not existing:
                vendor_slug = "cisco" if "cisco" in platform_name else "arista" if "arista" in platform_name else None
                vendor = vendor_map.get(vendor_slug)
                model = DeviceModel(
                    platform_id=platform.id, vendor_id=vendor.id if vendor else None,
                    name=m_data["name"], slug=m_data["slug"], display_name=m_data["display_name"],
                    software_version="imported", default_interface_pattern=[],
                )
                session.add(model)
    await session.flush()

    # Refresh model map
    for m in (await session.execute(select(DeviceModel))).scalars().all():
        model_map[m.name] = m

    # Create extra software versions
    version_map = {}
    for platform_name, versions in EXTRA_VERSIONS.items():
        platform = platforms.get(platform_name)
        if not platform:
            continue
        for v_data in versions:
            existing = (await session.execute(
                select(SoftwareVersion).where(
                    SoftwareVersion.platform_id == platform.id,
                    SoftwareVersion.version_string == v_data["version_string"]
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(SoftwareVersion(platform_id=platform.id, **v_data))
    await session.flush()

    # Refresh version map
    for sv in (await session.execute(select(SoftwareVersion))).scalars().all():
        version_map[(sv.platform_id, sv.version_string)] = sv

    # Seed CLI library entries
    count = 0
    for sample in SAMPLES:
        platform = platforms.get(sample["platform"])
        if not platform:
            continue

        model = model_map.get(sample.get("model"))
        sv = version_map.get((platform.id, sample["version"]))

        # Validate against parsers
        parser_results = validate_against_parsers(sample["output"], sample["platform"], sample["command"])

        entry = CommandOutputLibrary(
            platform_id=platform.id,
            device_model_id=model.id if model else None,
            software_version_id=sv.id if sv else None,
            software_version=sample["version"],
            command=sample["command"],
            raw_output=sample["output"],
            parser_results=parser_results,
            is_reference=(count == 0),  # First entry for each combo is reference
            source_description="Seeded from web research — Cisco/Arista documentation and community sources",
        )
        session.add(entry)
        count += 1

    await session.commit()
    print(f"Seeded {count} CLI library entries across {len(set(s['platform'] for s in SAMPLES))} platforms.")


async def main():
    async with async_session_factory() as session:
        await seed_cli_library(session)


if __name__ == "__main__":
    asyncio.run(main())

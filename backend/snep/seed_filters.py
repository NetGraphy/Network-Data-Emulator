"""Seed built-in custom Jinja2 filters — useful examples ready to use."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.db import async_session_factory
from snep.models.custom_filter import CustomFilter

BUILTIN_FILTERS = [
    {
        "name": "bits_to_human",
        "description": "Convert bits/sec to human-readable format (e.g., 450000000 → '450.0 Mbps')",
        "code": "value = int(value)\nfor unit in ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps']:\n    if abs(value) < 1000:\n        return f'{value:.1f} {unit}'\n    value /= 1000\nreturn f'{value:.1f} Pbps'",
        "signature": "value",
        "test_input": "[450000000]",
        "test_expected": "450.0 Mbps",
        "category": "formatting",
    },
    {
        "name": "bytes_to_human",
        "description": "Convert bytes to human-readable format (e.g., 584792031847 → '544.6 GB')",
        "code": "value = int(value)\nfor unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:\n    if abs(value) < 1024:\n        return f'{value:.1f} {unit}'\n    value /= 1024\nreturn f'{value:.1f} EB'",
        "signature": "value",
        "test_input": "[584792031847]",
        "test_expected": "544.6 GB",
        "category": "formatting",
    },
    {
        "name": "utilization",
        "description": "Calculate interface utilization percentage from rate (bps) and speed (Mbps)",
        "code": "if int(speed_mbps) <= 0:\n    return '0.0%'\npct = (int(rate_bps) / (int(speed_mbps) * 1_000_000)) * 100\nreturn f'{pct:.1f}%'",
        "signature": "rate_bps, speed_mbps",
        "test_input": "[450000000, 1000]",
        "test_expected": "45.0%",
        "category": "calculation",
    },
    {
        "name": "subnet_mask",
        "description": "Convert CIDR prefix length to dotted subnet mask (e.g., 24 → '255.255.255.0')",
        "code": "net = ipaddress.ip_network(f'0.0.0.0/{int(cidr)}', strict=False)\nreturn str(net.netmask)",
        "signature": "cidr",
        "test_input": "[24]",
        "test_expected": "255.255.255.0",
        "category": "network",
    },
    {
        "name": "wildcard_mask",
        "description": "Convert CIDR prefix length to Cisco wildcard mask (e.g., 24 → '0.0.0.255')",
        "code": "net = ipaddress.ip_network(f'0.0.0.0/{int(cidr)}', strict=False)\nreturn str(net.hostmask)",
        "signature": "cidr",
        "test_input": "[24]",
        "test_expected": "0.0.0.255",
        "category": "network",
    },
    {
        "name": "network_address",
        "description": "Extract network address from CIDR notation (e.g., '10.0.1.5/24' → '10.0.1.0')",
        "code": "net = ipaddress.ip_network(value, strict=False)\nreturn str(net.network_address)",
        "signature": "value",
        "test_input": "[\"10.0.1.5/24\"]",
        "test_expected": "10.0.1.0",
        "category": "network",
    },
    {
        "name": "cisco_time_ago",
        "description": "Format seconds as Cisco time format (e.g., 3661 → '01:01:01')",
        "code": "if value is None:\n    return 'never'\nseconds = int(value)\nh, r = divmod(seconds, 3600)\nm, s = divmod(r, 60)\nreturn f'{h:02d}:{m:02d}:{s:02d}'",
        "signature": "value",
        "test_input": "[3661]",
        "test_expected": "01:01:01",
        "category": "formatting",
    },
    {
        "name": "mac_vendor",
        "description": "Extract the vendor OUI from a MAC address (first 6 hex chars)",
        "code": "clean = str(value).replace(':', '').replace('-', '').replace('.', '').upper()\nreturn clean[:6] if len(clean) >= 6 else value",
        "signature": "value",
        "test_input": "[\"aabb.cc01.0001\"]",
        "test_expected": "AABBCC",
        "category": "network",
    },
    {
        "name": "pct",
        "description": "Format a number as a percentage with configurable precision",
        "code": "return f'{float(value):.{int(precision)}f}%'",
        "signature": "value, precision=1",
        "test_input": "[45.6789, 2]",
        "test_expected": "45.68%",
        "category": "formatting",
    },
    {
        "name": "counter_delta",
        "description": "Calculate the delta between two counter values, handling 32-bit wrap",
        "code": "old = int(old_val)\nnew = int(new_val)\nif new >= old:\n    return str(new - old)\nreturn str((2**32 - old) + new)",
        "signature": "new_val, old_val",
        "test_input": "[100, 4294967290]",
        "test_expected": "106",
        "category": "calculation",
    },
]


async def seed_filters(session: AsyncSession) -> None:
    result = await session.execute(select(CustomFilter).where(CustomFilter.is_builtin == True).limit(1))
    if result.scalar_one_or_none():
        print("Custom filters already seeded, skipping.")
        return

    for fd in BUILTIN_FILTERS:
        f = CustomFilter(**fd, is_active=True, is_builtin=True)
        session.add(f)

    await session.commit()
    print(f"Seeded {len(BUILTIN_FILTERS)} built-in custom Jinja2 filters.")


async def main():
    async with async_session_factory() as session:
        await seed_filters(session)


if __name__ == "__main__":
    asyncio.run(main())

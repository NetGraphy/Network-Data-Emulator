"""Counter progression computation."""

from datetime import datetime, timezone

COUNTER32_MAX = 2**32
COUNTER64_MAX = 2**64
DEFAULT_AVG_PACKET_SIZE = 512  # bytes


def compute_current_counter(base_value: int, rate_bps: int, rate_reference: datetime, now: datetime | None = None) -> int:
    """Compute current counter value based on base + rate * elapsed time."""
    if now is None:
        now = datetime.now(timezone.utc)
    elapsed = max(0, (now - rate_reference).total_seconds())
    bytes_added = int(elapsed * rate_bps / 8)
    return base_value + bytes_added


def compute_current_packets(base_octets: int, rate_bps: int, rate_reference: datetime, base_pkts: int, now: datetime | None = None) -> int:
    """Derive packet count from byte counter progression."""
    if now is None:
        now = datetime.now(timezone.utc)
    elapsed = max(0, (now - rate_reference).total_seconds())
    bytes_added = int(elapsed * rate_bps / 8)
    pkts_added = bytes_added // DEFAULT_AVG_PACKET_SIZE
    return base_pkts + pkts_added


def wrap_counter32(value: int) -> int:
    return value % COUNTER32_MAX


def wrap_counter64(value: int) -> int:
    return value % COUNTER64_MAX


def compute_txload(rate_bps: int, speed_mbps: int) -> int:
    """Compute txload/rxload as fraction of 255."""
    if speed_mbps <= 0:
        return 0
    speed_bps = speed_mbps * 1_000_000
    return min(255, int(rate_bps / speed_bps * 255))


def uptime_to_ios_string(total_seconds: int) -> str:
    """Format uptime as Cisco IOS style: '2 years, 14 weeks, 3 days, 7 hours, 22 minutes'."""
    years, rem = divmod(total_seconds, 365 * 24 * 3600)
    weeks, rem = divmod(rem, 7 * 24 * 3600)
    days, rem = divmod(rem, 24 * 3600)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if weeks > 0:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts)

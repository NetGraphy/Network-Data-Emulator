"""Tests for counter progression computation."""

from datetime import datetime, timezone, timedelta

from snep.services.counter import (
    compute_current_counter,
    compute_txload,
    uptime_to_ios_string,
    wrap_counter32,
    wrap_counter64,
)


def test_counter_progression():
    base = 1000
    rate_bps = 8_000_000  # 8 Mbps = 1 MBps
    ref = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = ref + timedelta(seconds=10)

    result = compute_current_counter(base, rate_bps, ref, now)
    # 10 seconds * 8_000_000 / 8 = 10_000_000 bytes added
    assert result == 1000 + 10_000_000


def test_counter_zero_rate():
    result = compute_current_counter(5000, 0, datetime.now(timezone.utc))
    assert result == 5000


def test_wrap_counter32():
    assert wrap_counter32(2**32 + 100) == 100
    assert wrap_counter32(100) == 100


def test_wrap_counter64():
    assert wrap_counter64(2**64 + 42) == 42


def test_txload():
    # 500 Mbps on a 1G interface = ~127/255
    load = compute_txload(500_000_000, 1000)
    assert 126 <= load <= 128

    # 0 bps = 0 load
    assert compute_txload(0, 1000) == 0

    # 0 speed = 0 load (avoid division by zero)
    assert compute_txload(100, 0) == 0


def test_uptime_ios_string():
    # 90 days
    assert "12 weeks" in uptime_to_ios_string(90 * 86400)

    # 1 year, 2 weeks, 3 days
    seconds = 365 * 86400 + 14 * 86400 + 3 * 86400
    result = uptime_to_ios_string(seconds)
    assert "1 year" in result
    assert "2 weeks" in result
    assert "3 days" in result

    # 0 seconds
    assert "0 minutes" in uptime_to_ios_string(0)

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from nsealgo.entry_policy import EntryPolicy, IST

UTC = ZoneInfo("UTC")


def ist_time(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=IST)


def test_blocks_before_ten_and_allows_at_ten():
    policy = EntryPolicy()
    assert not policy.reserve_entry(ist_time(5, 9, 55)).allowed
    assert policy.reserve_entry(ist_time(5, 10, 0)).allowed


def test_only_one_entry_per_bar():
    policy = EntryPolicy()
    assert policy.reserve_entry(ist_time(5, 10, 0)).allowed
    decision = policy.reserve_entry(ist_time(5, 10, 0))
    assert not decision.allowed
    assert "per 5-minute bar" in decision.reason
    assert policy.reserve_entry(ist_time(5, 10, 5)).allowed


def test_two_entries_maximum_in_each_window():
    policy = EntryPolicy()
    assert policy.reserve_entry(ist_time(5, 10, 0)).allowed
    assert policy.reserve_entry(ist_time(5, 10, 5)).allowed
    assert not policy.reserve_entry(ist_time(5, 10, 10)).allowed

    assert policy.reserve_entry(ist_time(5, 13, 0)).allowed
    assert policy.reserve_entry(ist_time(5, 13, 5)).allowed
    assert not policy.reserve_entry(ist_time(5, 13, 10)).allowed


def test_afternoon_entry_is_allowed_even_when_morning_quota_used():
    policy = EntryPolicy()
    assert policy.reserve_entry(ist_time(5, 10, 0)).allowed
    assert policy.reserve_entry(ist_time(5, 10, 5)).allowed
    assert policy.reserve_entry(ist_time(5, 13, 0)).allowed


def test_rejects_close_and_after_close():
    policy = EntryPolicy()
    assert not policy.reserve_entry(ist_time(5, 15, 30)).allowed


def test_rejects_non_bar_aligned_timestamp():
    policy = EntryPolicy()
    assert not policy.reserve_entry(ist_time(5, 10, 3)).allowed


def test_resets_counts_on_new_local_date():
    policy = EntryPolicy()
    assert policy.reserve_entry(ist_time(5, 10, 0)).allowed
    assert policy.reserve_entry(ist_time(5, 10, 5)).allowed
    assert not policy.reserve_entry(ist_time(5, 10, 10)).allowed
    assert policy.reserve_entry(ist_time(6, 10, 0)).allowed


def test_timezone_aware_utc_time_converts_to_ist():
    policy = EntryPolicy()
    # 04:30 UTC is 10:00 IST.
    assert policy.reserve_entry(datetime(2026, 1, 5, 4, 30, tzinfo=UTC)).allowed


def test_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        EntryPolicy().reserve_entry(datetime(2026, 1, 5, 10, 0))


def test_session_bars_must_be_aligned_from_0915():
    policy = EntryPolicy()
    # 10:02 is not a valid five-minute close from 09:15 session alignment.
    assert not policy.reserve_entry(ist_time(5, 10, 2)).allowed

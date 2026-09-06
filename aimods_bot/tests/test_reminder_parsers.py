import pytest

from datetime import datetime, time

from aimods_bot.src.helpers.utils.time_utils import (
    parse_absolute_datetime,
    parse_clock_time,
    is_nonexistent_local_time,
)


@pytest.mark.parametrize("raw", [
    "05/03/2026 14:30",
    "5-3-2026 14.30",
    "5.3.2026 14:30",
    "05/03/2026, 14:30",
    "05/03/2026 alle 14:30",
    "  05/03/2026  14:30  ",
])
def test_absolute_datetime_accepted_forms(raw):
    assert parse_absolute_datetime(raw) == datetime(2026, 3, 5, 14, 30)


def test_absolute_datetime_is_naive():
    assert parse_absolute_datetime("05/03/2026 14:30").tzinfo is None


@pytest.mark.parametrize("raw", [
    "", "ciao", "05/03/2026",
    "31/02/2026 10:00",     # giorno inesistente
    "05/03/2026 25:00",     # ora fuori range
    "5/3/26 14:30",         # anno a 2 cifre
    "05/03/2026 14:5",      # minuti a 1 cifra
])
def test_absolute_datetime_rejected_forms(raw):
    assert parse_absolute_datetime(raw) is None


def test_clock_time():
    assert parse_clock_time("09:00") == time(9, 0)
    assert parse_clock_time("9.05") == time(9, 5)
    assert parse_clock_time("24:00") is None
    assert parse_clock_time("9:5") is None
    assert parse_clock_time("") is None


def test_nonexistent_local_time_spring_gap():
    # 29 marzo 2026: le 02:00 diventano le 03:00
    assert is_nonexistent_local_time(datetime(2026, 3, 29, 2, 30)) is True
    assert is_nonexistent_local_time(datetime(2026, 3, 29, 1, 30)) is False
    assert is_nonexistent_local_time(datetime(2026, 3, 29, 4, 30)) is False


def test_ambiguous_autumn_time_is_not_flagged():
    # 25 ottobre 2026: le 02:30 esistono due volte, fold=0 va bene
    assert is_nonexistent_local_time(datetime(2026, 10, 25, 2, 30)) is False


def test_aware_datetime_raises():
    from datetime import timezone
    with pytest.raises(ValueError):
        is_nonexistent_local_time(datetime(2026, 3, 29, 2, 30, tzinfo=timezone.utc))

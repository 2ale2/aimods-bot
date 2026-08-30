import pytest

from datetime import datetime, time, timezone

from aimods_bot.src.helpers.models.reminders import LAST_DAY_OF_MONTH, Recurrence, Reminder
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ
from aimods_bot.src.helpers.utils.reminder_time_utils import (
    advance_past,
    clamp_day,
    compute_first_fire,
    compute_next_fire,
)

NINE = time(hour=9, minute=0)


def rome(y, m, d, hh=9, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def make(recurrence, next_fire, **kwargs) -> Reminder:
    return Reminder(
        title="VPS",
        body="Pagamento VPS",
        chat_id=-100123,
        recurrence=recurrence,
        fire_time=NINE,
        next_fire=next_fire,
        created_by=1,
        **kwargs,
    )


# ---------- clamp_day ----------

@pytest.mark.parametrize("year,month,day,expected", [
    (2026, 2, 31, 28),   # febbraio non bisestile
    (2028, 2, 31, 29),   # febbraio bisestile
    (2026, 2, 29, 28),   # il caso che ci interessa
    (2028, 2, 29, 29),
    (2026, 4, 31, 30),   # aprile
    (2026, 3, 31, 31),   # nessun clamp
    (2026, 2, LAST_DAY_OF_MONTH, 28),
    (2026, 12, LAST_DAY_OF_MONTH, 31),
])
def test_clamp_day(year, month, day, expected):
    assert clamp_day(year, month, day) == expected


def test_monthly_clamp_is_not_sticky():
    """Il 31 ridotto a febbraio deve tornare 31 a marzo."""
    r = make(Recurrence.MONTHLY, rome(2026, 1, 31), day_of_month=31)

    feb = compute_next_fire(r)
    assert feb.astimezone(LOCAL_TZ).day == 28

    r.next_fire = feb
    mar = compute_next_fire(r)
    assert mar.astimezone(LOCAL_TZ).day == 31

    r.next_fire = mar
    apr = compute_next_fire(r)
    assert apr.astimezone(LOCAL_TZ).day == 30


def test_monthly_day_29_survives():
    """Il 29 deve essere selezionabile e rispettato in 11 mesi su 12."""
    r = make(Recurrence.MONTHLY, rome(2026, 1, 29), day_of_month=29)
    for month, expected_day in [(2, 28), (3, 29), (4, 29)]:
        r.next_fire = compute_next_fire(r)
        local = r.next_fire.astimezone(LOCAL_TZ)
        assert (local.month, local.day) == (month, expected_day)


# ---------- interval ----------

def test_interval_anchors_on_schedule_not_now():
    r = make(Recurrence.INTERVAL, rome(2026, 3, 1), interval_days=3)
    assert compute_next_fire(r) == rome(2026, 3, 4)


def test_daily_is_interval_one():
    r = make(Recurrence.INTERVAL, rome(2026, 6, 10), interval_days=1)
    assert compute_next_fire(r) == rome(2026, 6, 11)


def test_interval_keeps_local_time_across_dst_spring():
    """29 marzo 2026: ora legale. Le 9:00 restano le 9:00."""
    r = make(Recurrence.INTERVAL, rome(2026, 3, 27), interval_days=3)
    nxt = compute_next_fire(r)
    assert nxt.astimezone(LOCAL_TZ).hour == 9
    assert nxt == rome(2026, 3, 30)


def test_interval_keeps_local_time_across_dst_autumn():
    """25 ottobre 2026: ritorno all'ora solare."""
    r = make(Recurrence.INTERVAL, rome(2026, 10, 24), interval_days=2)
    nxt = compute_next_fire(r)
    assert nxt.astimezone(LOCAL_TZ).hour == 9
    assert nxt == rome(2026, 10, 26)


# ---------- weekly ----------

def test_weekly_advances_a_full_week_on_same_day():
    r = make(Recurrence.WEEKLY, rome(2026, 3, 2), day_of_week=0)  # lunedi
    assert compute_next_fire(r) == rome(2026, 3, 9)


def test_weekly_jumps_to_target_weekday():
    r = make(Recurrence.WEEKLY, rome(2026, 3, 2), day_of_week=4)  # venerdi
    nxt = compute_next_fire(r)
    assert nxt.astimezone(LOCAL_TZ).weekday() == 4
    assert nxt == rome(2026, 3, 6)


# ---------- once ----------

def test_once_has_no_next():
    r = make(Recurrence.ONCE, rome(2026, 5, 1))
    assert compute_next_fire(r) is None


# ---------- first fire ----------

def test_first_fire_today_if_still_ahead():
    now = rome(2026, 6, 10, 7, 0)
    got = compute_first_fire(Recurrence.INTERVAL, NINE, now=now)
    assert got == rome(2026, 6, 10)


def test_first_fire_tomorrow_if_passed():
    now = rome(2026, 6, 10, 11, 0)
    got = compute_first_fire(Recurrence.INTERVAL, NINE, now=now)
    assert got == rome(2026, 6, 11)


def test_first_fire_monthly_rolls_to_next_month():
    now = rome(2026, 1, 31, 12, 0)
    got = compute_first_fire(Recurrence.MONTHLY, NINE, now=now, day_of_month=31)
    assert got == rome(2026, 2, 28)


# ---------- catch-up ----------

def test_advance_past_collapses_missed_occurrences():
    """Bot giu' 10 giorni, intervallo 3: 4 occorrenze mancate, 1 solo invio."""
    r = make(Recurrence.INTERVAL, rome(2026, 6, 1), interval_days=3)
    now = rome(2026, 6, 11, 12, 0)
    next_fire, missed = advance_past(r, now=now)

    assert missed == 4
    assert next_fire > now
    assert next_fire == rome(2026, 6, 13)


def test_advance_past_noop_when_future():
    r = make(Recurrence.INTERVAL, rome(2026, 6, 20), interval_days=3)
    next_fire, missed = advance_past(r, now=rome(2026, 6, 10))
    assert missed == 0
    assert next_fire == r.next_fire


def test_advance_past_once_returns_none():
    r = make(Recurrence.ONCE, rome(2026, 6, 1))
    next_fire, missed = advance_past(r, now=rome(2026, 6, 10))
    assert missed == 1
    assert next_fire is None


# ---------- validation ----------

def test_recurrence_requires_its_field():
    with pytest.raises(ValueError):
        make(Recurrence.MONTHLY, rome(2026, 1, 1))


def test_recurrence_rejects_foreign_fields():
    with pytest.raises(ValueError):
        make(Recurrence.WEEKLY, rome(2026, 1, 1), day_of_week=1, interval_days=3)


def test_monthly_rejects_out_of_range_day():
    with pytest.raises(ValueError):
        make(Recurrence.MONTHLY, rome(2026, 1, 1), day_of_month=32)

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from aimods_bot.src.helpers.constants.constants import LOCAL_TZ
from aimods_bot.src.helpers.models.reminders import (
    LAST_DAY_OF_MONTH,
    Recurrence,
    Reminder,
)


def clamp_day(year: int, month: int, day: int) -> int:
    """Riporta `day` dentro i limiti del mese indicato. LAST_DAY_OF_MONTH è l'"ultimo giorno"."""
    last = calendar.monthrange(year, month)[1]
    if day == LAST_DAY_OF_MONTH:
        return last
    return min(day, last)


def _at_local_time(local_day: datetime, fire_time: time) -> datetime:
    """Fissa l'orario locale e riporta in UTC."""
    local = local_day.replace(
        hour=fire_time.hour,
        minute=fire_time.minute,
        second=0,
        microsecond=0,
    )
    return local.astimezone(timezone.utc)


def _add_months(year: int, month: int, count: int = 1) -> tuple[int, int]:
    zero_based = (month - 1) + count
    return year + zero_based // 12, zero_based % 12 + 1


def compute_next_fire(reminder: Reminder, anchor: datetime | None = None) -> datetime | None:
    """
    Calcola l'occorrenza successiva a partire da `anchor`.

    Attenzione: usare anchor = `now` farebbe accumulare il ritardo di esecuzione a ogni ciclo.

    Ritorna None per i promemoria one-shot.
    """
    if reminder.recurrence is Recurrence.ONCE:
        return None

    base = (anchor or reminder.next_fire).astimezone(LOCAL_TZ)
    fire_time = reminder.fire_time

    match reminder.recurrence:
        case Recurrence.INTERVAL:
            return _at_local_time(base + timedelta(days=reminder.interval_days), fire_time)

        case Recurrence.WEEKLY:
            delta = (reminder.day_of_week - base.weekday()) % 7
            return _at_local_time(base + timedelta(days=delta or 7), fire_time)

        case Recurrence.MONTHLY:
            year, month = _add_months(base.year, base.month)
            day = clamp_day(year, month, reminder.day_of_month)
            return _at_local_time(base.replace(year=year, month=month, day=day), fire_time)

    return None


def compute_first_fire(
        recurrence: Recurrence,
        fire_time: time,
        now: datetime | None = None,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
) -> datetime:
    """Prima occorrenza di un promemoria ricorrente appena creato."""
    now = (now or datetime.now(timezone.utc)).astimezone(LOCAL_TZ)
    today = _at_local_time(now, fire_time)

    match recurrence:
        case Recurrence.INTERVAL:
            if today > now:
                return today
            return _at_local_time(now + timedelta(days=1), fire_time)

        case Recurrence.WEEKLY:
            delta = (day_of_week - now.weekday()) % 7
            if delta == 0 and today > now:
                return today
            return _at_local_time(now + timedelta(days=delta or 7), fire_time)

        case Recurrence.MONTHLY:
            day = clamp_day(now.year, now.month, day_of_month)
            candidate = _at_local_time(now.replace(day=day), fire_time)
            if candidate > now:
                return candidate
            year, month = _add_months(now.year, now.month)
            day = clamp_day(year, month, day_of_month)
            return _at_local_time(now.replace(year=year, month=month, day=day), fire_time)

    raise ValueError(f"compute_first_fire non supporta {recurrence}")


def advance_past(reminder: Reminder, now: datetime | None = None) -> tuple[Optional[datetime], int]:
    """
    Fa avanzare `next_fire` finchè non è nel futuro. Evita che al boot vengano mandati più reminders.

    Ritorna anche le occorrenze balzate.
    """
    now = now or datetime.now(timezone.utc)
    next_fire = reminder.next_fire
    missed = 0

    while next_fire is not None and next_fire <= now:
        missed += 1
        next_fire = compute_next_fire(reminder, anchor=next_fire)

    return next_fire, missed

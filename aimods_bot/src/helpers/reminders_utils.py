from __future__ import annotations

import asyncpg

from datetime import datetime

from aimods_bot.src.helpers.constants.constants import REMINDERS_TABLE
from aimods_bot.src.helpers.database import execute_query, fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.reminders import Reminder

log = logger.getChild(__name__)

_COLUMNS = ", ".join(Reminder.model_fields)
_PAGE_SIZE = 8


def reminder_from_record(record: asyncpg.Record) -> Reminder:
    return Reminder(**dict(record))


async def create_reminder(reminder: Reminder) -> int | None:
    """Inserisce un promemoria e ritorna il suo id."""
    rows = await fetch_query(
        f"""
        INSERT INTO {REMINDERS_TABLE}
            (title, body, chat_id, thread_id, recurrence, fire_time, next_fire,
             interval_days, day_of_week, day_of_month, enabled, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """,
        [
            reminder.title,
            reminder.body,
            reminder.chat_id,
            reminder.thread_id,
            reminder.recurrence.value,
            reminder.fire_time,
            reminder.next_fire,
            reminder.interval_days,
            reminder.day_of_week,
            reminder.day_of_month,
            reminder.enabled,
            reminder.created_by,
        ],
    )

    if not rows:
        log.error("Reminder creation failed (no id returned)")
        return None

    reminder_id = rows[0]["id"]
    log.info(f"Reminder {reminder_id} created by {reminder.created_by}")
    return reminder_id


async def update_reminder(reminder: Reminder) -> bool:
    """Riscrive un promemoria esistente."""
    if reminder.id is None:
        log.error("update_reminder called without an id")
        return False

    updated = await execute_query(
        f"""
        UPDATE {REMINDERS_TABLE}
        SET title = $2, body = $3, chat_id = $4, thread_id = $5, recurrence = $6,
            fire_time = $7, next_fire = $8, interval_days = $9, day_of_week = $10,
            day_of_month = $11, enabled = $12
        WHERE id = $1
        """,
        [
            reminder.id,
            reminder.title,
            reminder.body,
            reminder.chat_id,
            reminder.thread_id,
            reminder.recurrence.value,
            reminder.fire_time,
            reminder.next_fire,
            reminder.interval_days,
            reminder.day_of_week,
            reminder.day_of_month,
            reminder.enabled,
        ],
    )

    if updated:
        log.info(f"Reminder {reminder.id} updated")
    return updated


async def get_reminder(reminder_id: int) -> Reminder | None:
    rows = await fetch_query(
        f"SELECT {_COLUMNS} FROM {REMINDERS_TABLE} WHERE id = $1", [reminder_id]
    )
    return reminder_from_record(rows[0]) if rows else None


async def list_reminders(only_enabled: bool = False) -> list[Reminder]:
    """Elenco ordinato per prossima esecuzione."""
    where = "WHERE enabled" if only_enabled else ""
    rows = await fetch_query(
        f"SELECT {_COLUMNS} FROM {REMINDERS_TABLE} {where} ORDER BY next_fire"
    )
    return [reminder_from_record(r) for r in rows] if rows else []


async def register_execution(
        reminder_id: int,
        next_fire: datetime | None,
        last_fired_at: datetime | None = None,
) -> bool:
    """Registra l'esecuzione e avanza la prossima. `next_fire=None` significa one-shot esaurito."""
    if next_fire is None:
        return await execute_query(
            f"UPDATE {REMINDERS_TABLE} SET enabled = FALSE, last_fired_at = $2 WHERE id = $1",
            [reminder_id, last_fired_at],
        )

    return await execute_query(
        f"UPDATE {REMINDERS_TABLE} SET next_fire = $2, last_fired_at = $3 WHERE id = $1",
        [reminder_id, next_fire, last_fired_at],
    )


async def reschedule_reminder(reminder_id: int, next_fire: datetime) -> bool:
    """Riprogramma un promemoria."""
    return await execute_query(
        f"UPDATE {REMINDERS_TABLE} SET next_fire = $2 WHERE id = $1",
        [reminder_id, next_fire],
    )


async def toggle_reminder(reminder_id: int, enabled: bool) -> bool:
    return await execute_query(
        f"UPDATE {REMINDERS_TABLE} SET enabled = $2 WHERE id = $1",
        [reminder_id, enabled],
    )


async def delete_reminder(reminder_id: int) -> bool:
    return await execute_query(
        f"DELETE FROM {REMINDERS_TABLE} WHERE id = $1", [reminder_id]
    )


def paginate_reminders(
        reminders: list[Reminder],
        page: int
) -> tuple[list[Reminder], int, int]:
    """
    Ritaglia la pagina richiesta. Ritorna (elementi, pagina effettiva, pagine totali).

    `page` viene riportato dentro i limiti invece di sollevare: arriva da un
    `callback_data`, cioè da un bottone che può essere rimasto in un messaggio di
    quando le pagine erano di più.
    """
    pages = max(1, -(-len(reminders) // _PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    start = page * _PAGE_SIZE
    return reminders[start:start + _PAGE_SIZE], page, pages

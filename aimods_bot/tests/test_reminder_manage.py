"""
Pezzi puri della gestione promemoria: paginazione, descrizione della ricorrenza,
troncamento dei testi.

I pannelli non si testano qui — parlano con Telegram. Si testa quello che decide
*cosa* mostrano, che è dove sbagliare costa: una pagina fuori intervallo che
nasconde un promemoria, una ricorrenza descritta male su cui un admin decide.
"""
import pytest

from datetime import datetime, time, timezone

from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import _describe_recurrence
from aimods_bot.src.helpers.reminders_utils import paginate_reminders
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ, Recurrence
from aimods_bot.src.infra.scheduling.job_names import ReminderJobName, parse_job_name
from aimods_bot.src.helpers.models.reminders import LAST_DAY_OF_MONTH, Reminder
from aimods_bot.src.helpers.utils.text_utils import shorten

NINE = time(hour=9, minute=0)


def make(recurrence=Recurrence.INTERVAL, title="VPS", **kwargs) -> Reminder:
    if recurrence is Recurrence.INTERVAL and "interval_days" not in kwargs:
        kwargs["interval_days"] = 3
    return Reminder(
        title=title,
        body="Pagamento VPS",
        chat_id=-100123,
        recurrence=recurrence,
        fire_time=NINE,
        next_fire=datetime(2026, 10, 1, 9, 0, tzinfo=LOCAL_TZ).astimezone(timezone.utc),
        created_by=1,
        **kwargs,
    )


# ---------- paginate_reminders ----------

def test_paginate_empty_is_one_page():
    items, page, pages = paginate_reminders([], page=0)
    assert (items, page, pages) == ([], 0, 1)


def test_paginate_single_page_keeps_everything():
    reminders = [make(title=str(i)) for i in range(5)]
    items, page, pages = paginate_reminders(reminders, page=0)
    assert len(items) == 5
    assert (page, pages) == (0, 1)


@pytest.mark.parametrize("requested", [-5, -1, 99])
def test_paginate_clamps_out_of_range_page(requested):
    """La pagina arriva da un callback_data: un bottone vecchio non deve far saltare nulla."""
    reminders = [make(title=str(i)) for i in range(20)]
    items, page, pages = paginate_reminders(reminders, page=requested)
    assert 0 <= page < pages
    assert items


def test_paginate_covers_every_reminder():
    """Nessun promemoria deve restare irraggiungibile: uno fuori lista non si spegne più."""
    reminders = [make(title=str(i)) for i in range(23)]
    _, _, pages = paginate_reminders(reminders, page=0)

    seen = []
    for p in range(pages):
        items, page, _ = paginate_reminders(reminders, page=p)
        assert page == p
        seen.extend(items)

    assert [r.title for r in seen] == [r.title for r in reminders]


# ---------- _describe_recurrence ----------

@pytest.mark.parametrize("reminder,expected", [
    (make(Recurrence.ONCE, interval_days=None), "Una Sola Volta"),
    (make(Recurrence.INTERVAL, interval_days=1), "Ogni Giorno alle 09:00"),
    (make(Recurrence.INTERVAL, interval_days=3), "Ogni 3 Giorni alle 09:00"),
    (make(Recurrence.WEEKLY, interval_days=None, day_of_week=0), "Ogni Lunedì alle 09:00"),
    (make(Recurrence.WEEKLY, interval_days=None, day_of_week=6), "Ogni Domenica alle 09:00"),
    (make(Recurrence.MONTHLY, interval_days=None, day_of_month=15), "Il 15 del Mese alle 09:00"),
    (make(Recurrence.MONTHLY, interval_days=None, day_of_month=LAST_DAY_OF_MONTH),
     "L'Ultimo Giorno del Mese alle 09:00"),
])
def test_describe_recurrence(reminder, expected):
    assert _describe_recurrence(reminder) == expected


def test_describe_weekly_uses_python_weekday_convention():
    """0 = lunedì, non domenica. La convenzione di `run_daily` nel recap è l'opposta."""
    assert "Lunedì" in _describe_recurrence(make(Recurrence.WEEKLY, interval_days=None, day_of_week=0))


# ---------- shorten ----------

def test_shorten_leaves_short_text_untouched():
    assert shorten("breve", 120) == "breve"


def test_shorten_truncates_and_marks():
    out = shorten("a" * 300, 120)
    assert len(out) == 121
    assert out.endswith("…")


def test_shorten_does_not_escape():
    """L'escaping tocca al chiamante: troncare prima evita di tagliare a metà un'entità."""
    assert shorten("a & b", 120) == "a & b"


# ---------- ReminderJobName ----------

def test_reminder_job_name_roundtrip():
    original = ReminderJobName(reminder_id=42)
    assert parse_job_name(original.to_string()) == original


@pytest.mark.parametrize("malformed", ["reminder", "reminder:abc", "reminder:1:2"])
def test_reminder_malformed_returns_none(malformed):
    assert parse_job_name(malformed) is None
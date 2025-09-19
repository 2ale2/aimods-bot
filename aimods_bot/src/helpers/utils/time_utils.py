import re
from typing import Optional

import pytz
from zoneinfo import ZoneInfo
from datetime import timedelta, datetime, timezone, time


def pluralize(value: int, singular: str, plural: str) -> str:
    return f"{value} {singular if value == 1 else plural}"


async def get_duration_text(seconds: Optional[int]) -> str:
    if not seconds:
        return ""

    time_timedelta = timedelta(seconds=seconds)
    days = time_timedelta.days
    hours = time_timedelta.seconds // 3600
    minutes = (time_timedelta.seconds % 3600) // 60
    seconds = time_timedelta.seconds % 60

    parts = []
    if days > 0:
        parts.append(pluralize(days, "giorno", "giorni"))
    if hours > 0:
        parts.append(pluralize(hours, "ora", "ore"))
    if minutes > 0:
        parts.append(pluralize(minutes, "minuto", "minuti"))
    parts.append(pluralize(seconds, "secondo", "secondi"))

    parts = [el for el in parts if not el.startswith("0")]

    return "🕔 " + ", ".join(parts)


def parse_duration(duration_string: str) -> timedelta | None:
    mapping = {
        "giorno": "days", "giorni": "days",
        "ora": "hours", "ore": "hours",
        "minuto": "minutes", "minuti": "minutes",
        "secondo": "seconds", "secondi": "seconds"
    }

    kwargs = {key: 0 for key in mapping.values()}
    for num, unit in re.findall(r"(\d+)\s*(giorni|giorno|ore|ora|minuti|minuto|secondi|secondo)", duration_string):
        kwargs[mapping[unit]] += int(num)

    return timedelta(**kwargs) if any(kwargs.values()) else None


async def get_time_until_next_recap():
    # in futuro potrebbe implementare adattamento a giorno e ora personalizzabili
    # ora default domenica a mezzanotte
    tz_rome = ZoneInfo("Europe/Rome")
    now_utc = datetime.now(timezone.utc)
    now_rome = now_utc.astimezone(tz_rome)

    days_until_sunday = (6 - now_rome.weekday()) or 7
    next_sunday_date_rome = (now_rome.date() + timedelta(days=days_until_sunday))
    target_rome = datetime.combine(next_sunday_date_rome, time(0, 0), tzinfo=tz_rome)
    target_utc = target_rome.astimezone(timezone.utc)
    return target_utc - now_utc


def zero_datetime() -> datetime:
    """
    Restituisce un datetime "zero" (1 gennaio 1970 UTC), usato come valore predefinito per "tempo indeterminato".
    """
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def timedelta_to_seconds(t: timedelta) -> int:
    return int(t.total_seconds())


def get_until_date(duration) -> datetime:
    """Ritorna la scadenza di un'azione se la durata viene specificata, zero_datetime() altrimenti."""
    if not duration:
        return zero_datetime()
    now_utc = datetime.now(timezone.utc)
    return now_utc + duration


def format_time_as_rome(until: datetime) -> Optional[str]:
    """Formatta il testo nel fuso orario italiano se diverso da zero_datetime(), altrimenti a tempo indeterminato."""
    if until is None:
        raise Exception("Devi fornire il parametro 'until'")
    if until == zero_datetime():
        return None
    rome_time = until.astimezone(pytz.timezone('Europe/Rome'))
    return (f"<b>{rome_time.strftime('%d %B %Y')}</b> "
            f"alle {rome_time.strftime('%H:%M')}")


def sec_value_limited(sec: int):
    # Se sec non appartiene a questo intervallo, Telegram non lo considera.
    return 30 <= sec <= 60*60*24*365


def get_allow_after_text(allow_after: int) -> str:
    if allow_after == 0:
        allow_after_text = "🆓 Nessun Limite"
    elif allow_after <= 1800:
        allow_after_text = f"{int(allow_after / 60)} {'Minuti' if allow_after > 60 else 'Minuto'}"
    elif allow_after <= 43200:
        allow_after_text = f"{int(allow_after / 3600)} {'Ore' if allow_after > 3600 else 'Ora'}"
    elif allow_after <= 432000:
        allow_after_text = f"{int(allow_after / 86400)} {'Giorni' if allow_after > 86400 else 'Giorno'}"
    else:
        allow_after_text = "Una settimana"

    return allow_after_text


def get_rate_limit_text(time_limit: int) -> str:
    if time_limit == 1:
        return "1 Secondo"
    if time_limit < 60:
        return f"{time_limit} Secondi"
    if time_limit == 60:
        return "1 Minuto"
    # time_limit < 3600
    return f"{int(time_limit / 60)} Minuti"

import re
import pytz
from datetime import timedelta, datetime, timezone


def pluralize(value: int, singular: str, plural: str) -> str:
    return f"{value} {singular if value == 1 else plural}"


async def get_time_text(seconds: int) -> str:
    time_timedelta = timedelta(seconds=seconds)
    days = time_timedelta.days
    hours = time_timedelta.seconds // 3600
    minutes = (time_timedelta.seconds % 3600) // 60
    seconds = time_timedelta.seconds % 60

    parts = []
    if days > 0:
        parts.append(pluralize(days, "giorno", "giorni"))
    if hours > 0 or days > 0:
        parts.append(pluralize(hours, "ora", "ore"))
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(pluralize(minutes, "minuto", "minuti"))
    parts.append(pluralize(seconds, "secondo", "secondi"))

    return "🕔 " + ", ".join(parts)


async def parse_duration(duration_string: str) -> timedelta | None:
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
    now = datetime.now()
    days_until_sunday = (6 - now.weekday()) or 7
    next_recap_time = datetime.combine(
        now.date() + timedelta(days=days_until_sunday),
        datetime.min.time()
    )
    return next_recap_time - now


def zero_datetime() -> datetime:
    """
    Restituisce un datetime "zero" (1 gennaio 1970 UTC), usato come valore predefinito per "tempo indeterminato".
    """
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def get_until_date(duration) -> datetime:
    """Ritorna la scadenza di un'azione se la durata viene specificata, zero_datetime() altrimenti."""
    if not duration:
        return zero_datetime()
    now_utc = datetime.now(timezone.utc)
    return now_utc + duration


def format_time_as_rome(until: datetime) -> str:
    """Formatta il testo nel fuso orario italiano se diverso da zero_datetime(), altrimenti a tempo indeterminato."""
    if until == zero_datetime():
        return "a <b>tempo indeterminato</b>."
    rome_time = until.astimezone(pytz.timezone('Europe/Rome'))
    return (f"fino al <b>{rome_time.strftime('%d %B %Y')}</b> "
            f"alle {rome_time.strftime('%H:%M')}.")

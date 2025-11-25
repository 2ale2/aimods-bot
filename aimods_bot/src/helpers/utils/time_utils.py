import re
from typing import Optional
from datetime import timedelta, datetime, timezone, time

from aimods_bot.src.helpers.constants.constants import LOCAL_TZ

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800

_ZERO_DATETIME = datetime(1970, 1, 1, tzinfo=timezone.utc)
_DURATION_PATTERN = re.compile(
    r"(\d+)\s*(giorni|giorno|ore|ora|minuti|minuto|secondi|secondo)"
)


def pluralize(value: int, singular: str, plural: str) -> str:
    """Restituisce il testo al singolare o plurale in base al valore."""
    return f"{value} {singular if value == 1 else plural}"


def _format_time_unit(value: int, singular: str, plural: str) -> Optional[str]:
    """Formatta un'unità di tempo, restituendo None se il valore è 0."""
    if value == 0:
        return None
    return pluralize(value, singular, plural)


def get_duration_text(seconds: Optional[int], with_emoji: bool = True) -> str:
    """Converte i secondi in una stringa testuale leggibile."""
    if not seconds or seconds < 0:
        return ""

    time_timedelta = timedelta(seconds=seconds)
    days = time_timedelta.days
    hours = time_timedelta.seconds // SECONDS_PER_HOUR
    minutes = (time_timedelta.seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
    secs = time_timedelta.seconds % SECONDS_PER_MINUTE

    parts = [
        _format_time_unit(days, "giorno", "giorni"),
        _format_time_unit(hours, "ora", "ore"),
        _format_time_unit(minutes, "minuto", "minuti"),
        _format_time_unit(secs, "secondo", "secondi")
    ]

    parts = [el for el in parts if el is not None]

    return f"{'🕐 ' if with_emoji else ''}" + ", ".join(parts)


def parse_duration(duration_string: str) -> Optional[timedelta]:
    """Parse una stringa di durata in italiano e restituisce un timedelta."""
    if not duration_string:
        return None

    mapping = {
        "giorno": "days", "giorni": "days",
        "ora": "hours", "ore": "hours",
        "minuto": "minutes", "minuti": "minutes",
        "secondo": "seconds", "secondi": "seconds"
    }

    kwargs = {key: 0 for key in set(mapping.values())}
    for num, unit in _DURATION_PATTERN.findall(duration_string):
        kwargs[mapping[unit]] += int(num)

    return timedelta(**kwargs) if any(kwargs.values()) else None


def get_time_until_next_recap() -> timedelta:
    """
    Calcola il tempo rimanente fino alla prossima domenica a mezzanotte (ora italiana).
    In futuro potrebbe implementare adattamento a giorno e ora personalizzabili.
    """
    now_utc = datetime.now(timezone.utc)
    now_rome = now_utc.astimezone(LOCAL_TZ)

    days_until_sunday = (6 - now_rome.weekday()) or 7
    next_sunday_date_rome = (now_rome.date() + timedelta(days=days_until_sunday))
    target_rome = datetime.combine(next_sunday_date_rome, time(0, 0), tzinfo=LOCAL_TZ)
    target_utc = target_rome.astimezone(timezone.utc)
    return target_utc - now_utc


def get_last_monday_midnight() -> datetime:
    """Restituisce la mezzanotte del lunedì più recente (o corrente) in UTC."""
    now_utc = datetime.now(timezone.utc)
    days_since_monday = now_utc.weekday()
    last_monday = now_utc - timedelta(days=days_since_monday)
    last_monday_midnight = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return last_monday_midnight


def zero_datetime() -> datetime:
    """
    Restituisce un datetime "zero" (1 gennaio 1970 UTC), usato come valore predefinito per "tempo indeterminato".
    """
    return _ZERO_DATETIME


def timedelta_to_seconds(t: timedelta) -> int:
    """Converte un timedelta in secondi interi."""
    return int(t.total_seconds())


def get_until_date(duration: Optional[timedelta]) -> datetime:
    """Ritorna la scadenza di un'azione se la durata viene specificata, zero_datetime() altrimenti."""
    if not duration:
        return zero_datetime()
    now_utc = datetime.now(timezone.utc)
    return now_utc + duration


def format_time_as_rome(until: datetime) -> Optional[str]:
    """Formatta il datetime nel fuso orario italiano se diverso da zero_datetime(), altrimenti None."""
    if until is None:
        raise ValueError("Devi fornire il parametro 'until'")
    if until == zero_datetime():
        return None
    rome_time = until.astimezone(LOCAL_TZ)
    return (f"<b>{rome_time.strftime('%d %B %Y')}</b> "
            f"alle {rome_time.strftime('%H:%M')}")


def sec_value_limited(sec: int) -> bool:
    """
    Verifica se il valore dei secondi rientra nell'intervallo valido per Telegram.
    Se sec non appartiene a questo intervallo, Telegram non lo considera.
    """
    return 30 <= sec <= SECONDS_PER_DAY * 365


def get_allow_after_text(allow_after: int) -> str:
    """Formatta il testo del limite temporale per un'azione."""
    if allow_after == 0:
        return "🆓 Nessun Limite"
    elif allow_after <= 1800:
        minutes = int(allow_after / SECONDS_PER_MINUTE)
        return f"{minutes} {'Minuti' if minutes > 1 else 'Minuto'}"
    elif allow_after <= 43200:
        hours = int(allow_after / SECONDS_PER_HOUR)
        return f"{hours} {'Ore' if hours > 1 else 'Ora'}"
    elif allow_after <= 432000:
        days = int(allow_after / SECONDS_PER_DAY)
        return f"{days} {'Giorni' if days > 1 else 'Giorno'}"
    else:
        return "Una settimana"


def get_rate_limit_text(time_limit: int) -> str:
    """Formatta il testo del rate limit."""
    if time_limit == 1:
        return "1 Secondo"
    if time_limit < SECONDS_PER_MINUTE:
        return f"{time_limit} Secondi"
    if time_limit == SECONDS_PER_MINUTE:
        return "1 Minuto"
    # time_limit < SECONDS_PER_HOUR
    minutes = int(time_limit / SECONDS_PER_MINUTE)
    return f"{minutes} Minuti"


def ensure_utc(dt: datetime) -> datetime:
    """
    Normalizza la data in UTC.
    Se è naive (senza timezone), assume che sia UTC.
    Se è aware, la converte.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

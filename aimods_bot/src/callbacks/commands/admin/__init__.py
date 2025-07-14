import pytz
from datetime import datetime, timezone
from aimods_bot.src.helpers.utils.time_utils import zero_datetime


def format_user_mention(user_id: str | int, username: str | None, first_name: str) -> str:
    if username:
        return f"{'@' + username.removeprefix('@')} (<code>{user_id}</code>)"
    return f'<a href="tg://user?id={user_id}">{first_name}</a> (<code>{user_id}</code>)'


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

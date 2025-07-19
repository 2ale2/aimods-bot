import re
from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.utils.time_utils import parse_duration
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, is_username, normalize_user, is_user_id
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import MissingConfigurationException

log = logger.getChild("command_parser")


async def parse_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        full_command: str
) -> dict | None:
    """
    Analizza un comando testuale in base al pattern configurato.

    Args:
        update: Oggetto Update.
        context: ContextTypes.
        command: Comando (senza slash).
        full_command: Comando completo con argomenti.

    Returns:
        Dizionario con i campi estratti, oppure None se il parsing fallisce.
    """
    try:
        cmd_conf = context.bot_data["commands"][command]
        pattern = cmd_conf["pattern"]
        parameters = cmd_conf["parameters"]
    except KeyError:
        raise MissingConfigurationException(what=command)

    match = re.match(pattern, full_command)
    if not match:
        log.warning(f"⚠️ Comando non valido: {full_command}")
        return None

    replied = update.effective_message.reply_to_message
    replied = replied if replied and not replied.forum_topic_created else None

    extracted = {"action": match.group(1), "username_not_participant": False}
    gidx = 2

    for param in parameters:
        if param == "mention":
            extracted["user"] = _extract_user_mention(match, gidx)
            gidx += 3
        elif param == "permissions":
            extracted["permissions"] = _extract_permissions(match.group(gidx))
            gidx += 1
        else:
            extracted[param] = match.group(gidx) or ""
            gidx += 1

    if not extracted["user"]:
        if replied:
            extracted["user"] = replied.from_user.username or replied.from_user.id

    if "duration" in extracted:
        extracted["duration"] = await parse_duration(extracted["duration"])

    response = await resolve_chat_member(context=context, user_identifier=extracted["user"])

    if response["status"] == "success":
        extracted["member"] = normalize_user(response["member"])
    elif response["error"] == "username_404":
        extracted["member"] = {
            "id": None,
            "username": extracted["user"],
            "first_name": "",
            "chat_member_instance": None,
            "user_instance": None,
            "source": "unknown"
        }
    else:
        i = is_user_id(extracted["user"]) or None
        extracted["member"] = {
            "id": extracted["user"] if i is True else None,
            "username": extracted["user"] if i is False else None,
            "first_name": "",
            "chat_member_instance": None,
            "user_instance": None,
            "source": "unknown"
        }
        if i is False:
            extracted["username_not_participant"] = True

    return {
        "action": extracted.get("action"),
        "user": extracted.get("user"),
        "member": extracted.get("member"),
        "username_not_participant": extracted.get("username_not_participant"),
        "duration": extracted.get("duration", ""),
        "message": extracted.get("message", "").strip() if extracted.get("message") else None,
        "permissions": extracted.get("permissions")
    }


def _extract_user_mention(match: re.Match, gidx: int) -> str | None:
    """
    Estrae l'utente da una menzione (username o ID o HTML mention).
    """
    username = match.group(gidx)
    id1 = match.group(gidx + 1)
    id2 = match.group(gidx + 2)
    return id1 or id2 or username


def _extract_permissions(raw: str) -> list[int]:
    """
    Converte una stringa di permessi separati da virgole in lista di interi filtrati.
    """
    try:
        return [p for p in map(int, raw.split(",")) if 0 <= p <= 11]
    except Exception:
        return []

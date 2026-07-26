import re
from typing import Optional, Dict, Any, List
from telegram import Update, Message

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingConfigurationException
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, normalize_user, is_user_id
from aimods_bot.src.helpers.utils.time_utils import parse_duration

log = logger.getChild("command_parser")

MIN_PERMISSION = 0
MAX_PERMISSION = 11
MENTION_GROUP_SIZE = 3


async def parse_command(
        update: Update,
        context: CustomContext,
        command: str,
        full_command: str
) -> Optional[Dict[str, Any]]:
    """
    Analizza un comando testuale in base al pattern configurato.

    Args:
        update: Oggetto Update di Telegram.
        context: Contesto personalizzato con configurazione.
        command: Nome del comando (senza slash).
        full_command: Comando completo con tutti gli argomenti.

    Returns:
        Dizionario con i campi estratti, oppure None se il parsing fallisce.
    """
    cmd_conf = _get_command_config(context, command)

    match = re.match(cmd_conf.pattern, full_command)
    if not match:
        log.warning(f"⚠️ Comando non valido: {full_command}")
        return None

    replied_message = _get_replied_message(update)
    extracted = _extract_command_data(match, cmd_conf.parameters, replied_message)

    member_data = await _resolve_member_info(context, extracted)

    return _format_result(extracted, member_data)


def _get_command_config(context: CustomContext, command: str):
    """Recupera la configurazione del comando."""
    try:
        return context.pydb.commands[command]
    except KeyError:
        raise MissingConfigurationException(what=command)


def _get_replied_message(update: Update) -> Optional[Message]:
    """
    Estrae il messaggio a cui si risponde, se presente e valido.

    Returns:
        Messaggio di risposta o None se non presente o è un topic forum.
    """
    replied = update.effective_message.reply_to_message
    if replied and not replied.forum_topic_created:
        return replied
    return None


def _extract_command_data(
        match: re.Match,
        parameters: List[str],
        replied_message: Optional[Message]
) -> Dict[str, Any]:
    """
    Estrae i dati dal match regex in base ai parametri configurati.

    Args:
        match: Risultato del match regex.
        parameters: Lista dei parametri da estrarre.
        replied_message: Messaggio a cui si risponde (opzionale).

    Returns:
        Dizionario con i dati estratti.
    """
    extracted = {
        "action": match.group(1),
        "username_not_participant": False,
        "user": None
    }

    group_index = 2

    for param in parameters:
        if param == "mention":
            extracted["user"] = _extract_user_mention(match, group_index)
            group_index += MENTION_GROUP_SIZE
        elif param == "permissions":
            extracted["permissions"] = _extract_permissions(match.group(group_index))
            group_index += 1
        elif param == "duration":
            raw_duration = match.group(group_index) or ""
            extracted["duration"] = parse_duration(raw_duration)
            group_index += 1
        else:
            extracted[param] = match.group(group_index) or ""
            group_index += 1

    if not extracted["user"] and replied_message:
        extracted["user"] = replied_message.from_user.username or replied_message.from_user.id

    return extracted


def _extract_user_mention(match: re.Match, group_index: int) -> Optional[str]:
    """
    Estrae l'identificatore utente da una menzione.

    Può essere:
    - Username (@username)
    - ID numerico
    - HTML mention con ID

    Args:
        match: Risultato del match regex.
        group_index: Indice del primo gruppo relativo alla menzione.

    Returns:
        Identificatore utente o None.
    """
    username = match.group(group_index)
    id_from_mention = match.group(group_index + 1)
    id_from_html = match.group(group_index + 2)

    return id_from_mention or id_from_html or username


def _extract_permissions(raw: str) -> List[int]:
    """
    Converte una stringa di permessi separati da virgole in lista di interi validi.

    Args:
        raw: Stringa con permessi separati da virgole (es: "1,2,5").

    Returns:
        Lista di interi nell'intervallo [MIN_PERMISSION, MAX_PERMISSION].
    """
    if not raw or not raw.strip():
        return []

    try:
        permissions = [int(p.strip()) for p in raw.split(",") if p.strip()]
        return [p for p in permissions if MIN_PERMISSION <= p <= MAX_PERMISSION]
    except (ValueError, AttributeError) as e:
        log.warning(f"Errore nel parsing dei permessi '{raw}': {e}")
        return []


async def _resolve_member_info(
        context: CustomContext,
        extracted: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Risolve le informazioni complete del membro dalla chat.

    Args:
        context: Contesto personalizzato.
        extracted: Dati estratti dal comando.

    Returns:
        Dizionario con informazioni sul membro e flag di stato.
    """
    user_identifier = extracted.get("user")

    if not user_identifier:
        return {
            "member": _create_member_dict(),
            "username_not_participant": False
        }

    response = await resolve_chat_member(context=context, user_identifier=user_identifier)

    if response["status"] == "success":
        return {
            "member": normalize_user(response["member"]),
            "username_not_participant": False
        }

    if response["error"] == "username_404":
        return {
            "member": _create_member_dict(username=user_identifier),
            "username_not_participant": False
        }

    return _handle_unresolved_user(user_identifier)


def _handle_unresolved_user(user_identifier: str) -> Dict[str, Any]:
    """
    Gestisce il caso di utente non risolto dalla chat.

    Args:
        user_identifier: Identificatore dell'utente (username o ID).

    Returns:
        Dizionario con dati parziali e flag appropriato.
    """
    user_id_check = is_user_id(user_identifier)

    return {
        "member": _create_member_dict(user_id=user_identifier),
        "username_not_participant": not user_id_check
    }


def _create_member_dict(
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        source: str = "unknown"
) -> Dict[str, Any]:
    """
    Crea un dizionario standardizzato per le informazioni del membro.

    Args:
        user_id: ID numerico dell'utente.
        username: Username dell'utente.
        source: Fonte delle informazioni.

    Returns:
        Dizionario con struttura standardizzata.
    """
    return {
        "id": user_id,
        "username": username,
        "first_name": "",
        "chat_member_instance": None,
        "user_instance": None,
        "source": source
    }


def _format_result(extracted: Dict[str, Any], member_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatta il risultato finale con tutti i campi necessari.

    Args:
        extracted: Dati estratti dal comando.
        member_data: Informazioni sul membro risolto.

    Returns:
        Dizionario formattato con tutti i campi richiesti.
    """
    message = extracted.get("message", "").strip() if extracted.get("message") else None

    return {
        "action": extracted.get("action"),
        "user": extracted.get("user"),
        "member": member_data["member"],
        "username_not_participant": member_data["username_not_participant"],
        "duration": extracted.get("duration", ""),
        "message": message,
        "permissions": extracted.get("permissions")
    }

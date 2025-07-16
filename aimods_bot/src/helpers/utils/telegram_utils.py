import pyrogram.types
import telegram

import aimods_bot.src.helpers.constants.constants as constants
from typing import Optional, Any
from pyrogram.errors import UserNotParticipant, UserKicked
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import CallbackDataException, UserMentionException
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("telegram_utils")


def get_valid_thread_id(update: Update) -> Optional[int]:
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


async def safe_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message: telegram.Message = None):
    """
    Tenta di eliminare un messaggio Telegram in modo sicuro.
    Se viene fornito 'message', tenta di eliminare quello.
    Altrimenti, tenta di eliminare update.effective_message.
    Ignora errori di tipo BadRequest (es. messaggio già eliminato o non trovato).
    """
    message_to_delete = message if message is not None else update.effective_message

    if message_to_delete is None:
        log.warning("Nessun messaggio valido da eliminare è stato fornito o trovato.")
        return

    try:
        await message_to_delete.delete()
    except telegram.error.BadRequest as e:
        log.warning(f"Impossibile eliminare il messaggio (ID: {message_to_delete.message_id if hasattr(message_to_delete, 'message_id') else 'N/A'}): {e}")
    except AttributeError:
        log.error(f"L'oggetto fornito non è un telegram.Message valido e non ha il metodo delete.")
    except Exception as e:
        log.error(f"Errore inatteso durante l'eliminazione del messaggio: {e}", exc_info=True)


def validate_callback_structure(
    callback_data: str,
    expected_fields: list[dict],
    separator: str = "_",
    should_be: str = None
) -> list[Any]:
    """
        Valida la struttura del callback_data e ne converte i valori secondo specifiche.

        Args:
            callback_data: la stringa di callback ricevuta.
            expected_fields: lista di dict, ognuno con:
                - "type": type o "literal"
                - "value": se type == "literal"
                Tutti gli elementi sono obbligatori: la loro assenza produce eccezioni.
            separator: separatore tra i campi.
            should_be: stringa per messaggio d’errore.

        Returns:
            Lista di valori convertiti (o None se opzionali mancanti).

        Raises:
            CallbackDataException
        """

    parts = callback_data.split(separator)

    if len(parts) != len(expected_fields):
        raise CallbackDataException(callback_data, should_be=should_be)

    result = []

    for i, spec in enumerate(expected_fields):
        raw_value = parts[i]
        field_type = spec["type"]  # Se non c'è, genero eccezione

        # Caso 1: valore letterale (fisso)
        if field_type == "literal":
            expected_value = spec.get("value")
            if raw_value != expected_value:
                raise CallbackDataException(callback_data, should_be)
            result.append(raw_value)

        # Caso 2: tipo singolo (int, str)
        elif isinstance(field_type, type):
            try:
                result.append(field_type(raw_value))
            except Exception:
                raise CallbackDataException(callback_data, should_be)

        # Caso 3: lista di tipi alternativi [int, str]
        elif isinstance(field_type, list):
            converted = None
            # Ordine sequenziale
            # Se il tipo è preferibile che sia int (str), int (str) dovrebbe essere il primo della lista
            for t in field_type:
                try:
                    converted = t(raw_value)
                    break
                except Exception:
                    continue
            if converted is None:
                raise CallbackDataException(callback_data, should_be)
            result.append(converted)

        else:
            raise ValueError(f"Tipo di campo non gestito: {field_type}")

    return result


async def resolve_chat_member(context: ContextTypes.DEFAULT_TYPE, user_identifier: int | str):
    try:
        member = await constants.pyro_instance.get_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=user_identifier
        )
    except UserNotParticipant or UserKicked as e:
        if user_identifier.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    chat_id=context.bot_data["group_chat_id"],
                    user_id=user_identifier
                )
            except TelegramError as e:
                log.warning(f"Non è stato possibile ottenere ChatMember per {user_identifier}: {e}")
                return {"status": "failed", "error": "cannot_resolve", "member": None}
            return {"status": "success", "error": "", "member": member}
        else:
            log.debug(f"{user_identifier} non è membro del gruppo")
        return {"status": "failed", "error": "user_not_participant", "member": None}
    except Exception as e:
        log.warning(f"Non è stato possibile ottenere ChatMember per {user_identifier}: {e}")
        return {"status": "failed", "error": "cannot_resolve", "member": None}
    return {"status": "success", "error": "", "member": member}


def is_username(string) -> bool:
    """Se string è una stringa alfanumerica, ritorna True."""
    return not (not string or string.isdigit())


def is_user_id(string) -> bool:
    """Se è una stringa numerica o un intero, ritorna True."""
    return string and (isinstance(string, int) or string.isdigit())


def normalize_user(user) -> dict:
    """Funzione utility per normalizzare il tipo ritornata da classi di ritorno diverse."""
    if isinstance(user, telegram.ChatMember) or isinstance(user, pyrogram.types.ChatMember):
        user = user.user
    return {
        "id": user.id,
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", ""),
        "source": user.__class__.__name__
    }


def format_user_mention(user_id: str | int | None, username: str | None, first_name: str | None) -> str:
    if username:
        if user_id:
            return f"{'@' + username.removeprefix('@')} (<code>{user_id}</code>)"
        return f"{'@' + username.removeprefix('@')}"
    if user_id:
        if first_name:
            f'<a href="tg://user?id={user_id}">{first_name}</a> (<code>{user_id}</code>)'
        return f"<code>{user_id}</code>"
    raise UserMentionException

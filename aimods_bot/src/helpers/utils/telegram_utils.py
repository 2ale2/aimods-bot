from typing import Optional, Any, Union, Dict

import telegram
from pyrogram.errors import UserNotParticipant, UserKicked, UsernameNotOccupied
from pyrogram.types import ChatMember as PyroChatMember, User as PyroUser, ChatPermissions as PyroChatPermissions
from telegram import Update, ChatMember as PTBChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.exceptions import CallbackDataException, UserMentionException
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("telegram_utils")


def get_valid_thread_id(update: Update) -> Optional[int]:
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


async def safe_delete_wrapper(update: Update, context: CallbackContext):
    await safe_delete(update, context, update.effective_message)


async def safe_delete(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: telegram.Message = None,
        message_id: int = None
):
    """
    Tenta di eliminare un messaggio Telegram in modo sicuro.
    Se viene fornito 'message' o 'message_id' tenta di eliminare quello.
    Altrimenti, tenta di eliminare update.effective_message.
    Ignora errori di tipo BadRequest (es. messaggio già eliminato o non trovato).
    """

    if message:
        message_id_to_delete = message.message_id
    elif message_id:
        message_id_to_delete = message_id
    else:
        message_id_to_delete = update.effective_message.message_id

    if message_id_to_delete is None:
        log.warning("Nessun messaggio valido da eliminare è stato fornito o trovato.")
        return

    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=message_id_to_delete
        )
    except telegram.error.BadRequest as e:
        log.warning(f"Impossibile eliminare il messaggio (ID: {message_id_to_delete.message_id if hasattr(message_id_to_delete, 'message_id') else 'N/A'}): {e}")
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


async def resolve_chat_member(context: ContextTypes.DEFAULT_TYPE, user_identifier: Union[int, str]) -> Dict[str, Any]:
    """Risolve un ChatMember usando prima pyrogram, poi telegram bot come fallback."""

    if not user_identifier:
        log.warning("user_identifier vuoto fornito a resolve_chat_member")
        return _create_error_response("invalid_identifier")

    chat_id = context.bot_data["group_chat_id"]
    user_id_str = str(user_identifier)

    pyro_result = await _try_pyrogram_chat_member_resolve(chat_id, user_identifier)

    if pyro_result["status"] == "success" or pyro_result["error"] == "username_404":
        return pyro_result

    if is_user_id(user_id_str):
        resolved_id = user_id_str
    else:
        user_obj = await _try_pyrogram_user_resolve(user_identifier)
        resolved_id = user_obj.id if user_obj else None

    if resolved_id:
        ptb_result = await _try_ptb_resolve(context, chat_id, resolved_id)
        if ptb_result["status"] == "success":
            return ptb_result

    log.debug(f"Impossibile risolvere ChatMember per {user_identifier}")
    return pyro_result


async def _try_pyrogram_chat_member_resolve(chat_id: Union[int, str], user_identifier: Union[int, str]) -> Dict[str, Any]:
    """Tenta di risolvere un ChatMember usando pyrogram."""

    try:
        member = await constants.pyro_instance.get_chat_member(
            chat_id=chat_id,
            user_id=user_identifier
        )
        log.debug(f"ChatMember risolto con successo per {user_identifier} (pyrogram)")
        return _create_success_response(member)

    except (UserNotParticipant, UserKicked) as e:
        log.debug(f"Utente {user_identifier} non è partecipante del gruppo: {e}")
        return _create_error_response("user_not_participant")
    except UsernameNotOccupied:
        log.debug(f"Utente {user_identifier} non esiste.")
        return _create_error_response("username_404")
    except Exception as e:
        log.warning(f"Errore pyrogram durante risoluzione ChatMember per {user_identifier}: {e}")
        return _create_error_response("cannot_resolve")


async def _try_pyrogram_user_resolve(user_identifier: Union[int, str]) -> Optional[PyroUser]:
    try:
        return await constants.pyro_instance.get_users(user_ids=user_identifier)
    except Exception as e:
        log.warning(f"Errore pyrogram durante risoluzione ChatMember per {user_identifier}: {e}")
        return None


async def _try_ptb_resolve(context: ContextTypes.DEFAULT_TYPE, chat_id: Union[int, str],
                           user_identifier: Union[int, str]) -> Dict[str, Any]:
    """Tenta di risolvere un ChatMember usando PTB."""
    try:
        member = await context.bot.get_chat_member(
            chat_id=chat_id,
            user_id=int(user_identifier)
        )
        log.debug(f"ChatMember risolto con successo per {user_identifier} (telegram bot fallback)")
        return _create_success_response(member)

    except Exception as e:
        log.warning(f"Errore PTB durante risoluzione ChatMember per {user_identifier}: {e}")
        return _create_error_response("cannot_resolve")


def _create_success_response(member) -> Dict[str, Any]:
    return {
        "status": "success",
        "error": "",
        "member": member
    }


def _create_error_response(error_code: str) -> Dict[str, Any]:
    return {
        "status": "failed",
        "error": error_code,
        "member": None
    }


def is_username(string) -> bool:
    """Se string è una stringa alfanumerica, ritorna True."""
    return not (not string or string.isdigit())


def is_user_id(string) -> bool:
    """Se è una stringa numerica o un intero, ritorna True."""
    return string and (isinstance(string, int) or string.isdigit())


def normalize_user(user) -> dict:
    """Funzione utility per normalizzare il tipo ritornata da classi di ritorno diverse."""
    chat_member = isinstance(user, (PTBChatMember, PyroChatMember))
    chat_member_obj = user.user if chat_member else user

    return {
        "id": chat_member_obj.id,
        "username": chat_member_obj.username,
        "first_name": chat_member_obj.first_name,
        "chat_member_instance": user if chat_member else None,
        "user_instance": chat_member_obj,
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


def add_fucking_at(s: str) -> str:
    return '@' + s.removeprefix("@")


def permission_instance_to_dict(permissions: Union[PyroChatPermissions, PyroChatPermissions]):
    if isinstance(permissions, PyroChatPermissions):
        return {
            attr: getattr(permissions, attr)
            for attr in permissions.__dict__
            if isinstance(getattr(permissions, attr), bool)
        }
    return permissions.to_dict()


async def not_implemented_yet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠ Funzionalità non ancora implementata.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🚮 Chiude", callback_data="close")]]
        )
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    del context.chat_data['setting_duration']

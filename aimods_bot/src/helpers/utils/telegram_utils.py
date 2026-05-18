import re
from typing import Optional, Any, Union, Dict, List, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta

import telegram
from telegram.constants import ParseMode
from pyrogram.errors import UserNotParticipant, UserKicked, UsernameNotOccupied
from pyrogram.types import ChatMember as PyroChatMember, User as PyroUser, ChatPermissions as PyroChatPermissions
from telegram import (Update, ChatMember as PTBChatMember, InlineKeyboardMarkup, InlineKeyboardButton,
                      LinkPreviewOptions, ChatPermissions as PTBChatPermissions, User as PTBUser)

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import CallbackDataException, UserMentionException
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction
from aimods_bot.src.helpers.models.ui import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories

log = logger.getChild(__name__)


# ============================================================================
# CONFIGURAZIONE E COSTANTI
# ============================================================================

class TelegramConfig:
    """Configurazione centralizzata per il modulo telegram_utils"""
    USERNAME_MIN_LENGTH = 5
    USERNAME_MAX_LENGTH = 32
    CACHE_TTL_MINUTES = 5


# Regex compilate per performance
USERNAME_PATTERN = re.compile(
    rf"[a-z0-9_]{{{TelegramConfig.USERNAME_MIN_LENGTH},{TelegramConfig.USERNAME_MAX_LENGTH}}}",
    re.IGNORECASE
)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

@dataclass
class ResolveResult:
    """Risultato strutturato della risoluzione di un utente/membro"""
    status: Literal["success", "failed"]
    error: str
    user: Optional[Union[PyroUser, PTBUser]]
    member: Optional[Union[PyroChatMember, PTBChatMember]]


# ============================================================================
# CACHING SYSTEM
# ============================================================================

_user_cache: Dict[str, tuple[Union[Dict[str, Any], PyroUser, PTBUser], datetime]] = {}
CACHE_TTL = timedelta(minutes=TelegramConfig.CACHE_TTL_MINUTES)


def _get_cache_key(chat_id: Optional[Union[int, str]], user_identifier: Union[int, str]) -> str:
    """Genera una chiave di cache univoca"""
    return f"{chat_id}:{user_identifier}"


def _get_from_cache(cache_key: str) -> Optional[Union[Dict[str, Any], PyroUser, PTBUser]]:
    """Recupera un valore dalla cache se valido"""
    if cache_key in _user_cache:
        result, timestamp = _user_cache[cache_key]
        if datetime.now() - timestamp < CACHE_TTL:
            log.debug(f"Cache hit per chiave: {cache_key}")
            return result
        else:
            # Rimuove entry scaduta
            del _user_cache[cache_key]
    return None


def _set_in_cache(cache_key: str, result: Union[Dict[str, Any], PyroUser, PTBUser]) -> None:
    """Salva un valore nella cache"""
    _user_cache[cache_key] = (result, datetime.now())


def clear_user_cache() -> None:
    """Pulisce la cache degli utenti (utile per testing o reset)"""
    _user_cache.clear()
    log.info("Cache utenti pulita")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_valid_thread_id(update: Update) -> Optional[int]:
    """Restituisce un thread_id valido se presente"""
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


async def safe_delete_wrapper(update: Update, context: CustomContext):
    """Wrapper per safe_delete usando il messaggio corrente"""
    await safe_delete(update, context, update.effective_message)


async def safe_delete(
        update: Update,
        context: CustomContext,
        message: telegram.Message = None,
        message_id: int = None
) -> bool:
    """
    Tenta di eliminare un messaggio Telegram in modo sicuro.

    Args:
        update: Update object di Telegram
        context: CustomContext
        message: Messaggio da eliminare (opzionale)
        message_id: ID del messaggio da eliminare (opzionale)

    Returns:
        bool: True se eliminato con successo, False altrimenti
    """
    # Determina l'ID del messaggio da eliminare
    msg_id = message.message_id if message else message_id or update.effective_message.message_id

    if msg_id is None:
        log.warning("Nessun messaggio valido da eliminare è stato fornito o trovato")
        return False

    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=msg_id
        )
        log.debug(f"Messaggio {msg_id} eliminato con successo")
        return True
    except telegram.error.BadRequest as e:
        log.warning(f"Impossibile eliminare il messaggio (ID: {msg_id}): {e}")
        return False
    except Exception as e:
        log.error(f"Errore inatteso durante l'eliminazione del messaggio {msg_id}: {e}", exc_info=True)
        return False


def is_username(string: str) -> bool:
    """
    Restituisce True se la stringa è un possibile username Telegram.

    Regole:
    - Solo lettere (a-z), numeri (0-9), underscore (_)
    - Lunghezza: 5-32 caratteri
    - Può iniziare con @

    NOTA: In casi limite (es.: first_name "mario1") non posso sapere
    se la stringa è uno username se non ha la @
    """
    if not string:
        return False
    return string.startswith("@") or bool(USERNAME_PATTERN.fullmatch(string))


def is_user_id(string: Union[str, int]) -> bool:
    """Verifica se la stringa/int rappresenta un ID utente numerico"""
    if not string:
        return False
    return isinstance(string, int) or (isinstance(string, str) and string.isdigit() and len(string) >= 6)


def add_fucking_at(s: str) -> str:
    """Aggiunge la c*zzo di chiocciola, se mancante"""
    if not s:
        return s
    return '@' + s.removeprefix("@")


def normalize_user(user: Union[PTBChatMember, PyroChatMember, PyroUser, PTBUser]) -> Dict[str, Any]:
    """
    Funzione utility per normalizzare il tipo ritornato da classi diverse.

    Args:
        user: Oggetto utente o ChatMember da normalizzare

    Returns:
        Dict con campi standardizzati
    """
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


def format_user_mention(
        user_id: Optional[Union[str, int]] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None
) -> str:
    """
    Formatta una menzione utente in HTML per Telegram.

    Args:
        user_id: ID dell'utente
        username: Username dell'utente (con o senza @)
        first_name: Nome dell'utente

    Returns:
        str: Stringa HTML formattata

    Raises:
        UserMentionException: Se nessun parametro è fornito
    """
    if not any([user_id, username, first_name]):
        raise UserMentionException("Almeno uno tra user_id, username o first_name deve essere fornito")

    parts = []

    if username:
        parts.append(add_fucking_at(username))
    elif first_name and user_id:
        parts.append(f'<a href="tg://user?id={user_id}">{first_name}</a>')

    if user_id and (username or not first_name):
        parts.append(f"(<code>{user_id}</code>)")

    return " ".join(parts) if parts else (f"<code>{user_id}</code>" if user_id else f"{first_name}")


def get_toggle_text(b: bool) -> str:
    """Restituisce emoji/testo per stato on/off"""
    return '☂️ <i>On</i>' if b else '🌂 <i>Off</i>'


def chunk_buttons(buttons: list[ButtonItem], size: int = 2) -> list[list[ButtonItem]]:
    """Divide una lista piatta di bottoni in righe della dimensione specificata."""
    return [buttons[i:i + size] for i in range(0, len(buttons), size)]


def permission_instance_to_dict(permissions: Union[PTBChatPermissions, PyroChatPermissions]) -> Dict[str, bool]:
    """
    Converte un oggetto permissions in dizionario.

    Args:
        permissions: Oggetto permissions (PTB o Pyrogram)

    Returns:
        Dict con permessi booleani

    Raises:
        TypeError: Se il tipo non è supportato
    """
    if isinstance(permissions, PyroChatPermissions):
        return {
            attr: getattr(permissions, attr)
            for attr in permissions.__dict__
            if isinstance(getattr(permissions, attr), bool)
        }
    elif isinstance(permissions, PTBChatPermissions):
        return permissions.to_dict()
    else:
        raise TypeError(f"Tipo non supportato: {type(permissions)}")


# ============================================================================
# CALLBACK DATA VALIDATION
# ============================================================================

def validate_callback_structure(
        callback_data: str,
        expected_fields: List[Dict[str, Any]],
        separator: str = "_",
        should_be: Optional[str] = None
) -> List[Any]:
    """
    Valida la struttura del callback_data e ne converte i valori secondo specifiche.

    Args:
        callback_data: la stringa di callback ricevuta
        expected_fields: lista di dict, ognuno con:
            - "type": type, "literal", o lista di type
            - "value": se type == "literal"
        separator: separatore tra i campi
        should_be: stringa per messaggio d'errore

    Returns:
        Lista di valori convertiti

    Raises:
        CallbackDataException: Se la validazione fallisce
    """
    parts = callback_data.split(separator)

    if len(parts) != len(expected_fields):
        raise CallbackDataException(callback_data, should_be=should_be)

    return [
        _parse_callback_field(raw, spec, callback_data, should_be)
        for raw, spec in zip(parts, expected_fields)
    ]


def _parse_callback_field(
        raw_value: str,
        spec: Dict[str, Any],
        callback_data: str,
        should_be: Optional[str]
) -> Any:
    """
    Parsa e converte un singolo campo del callback.

    Args:
        raw_value: Valore grezzo da convertire
        spec: Specifica del campo
        callback_data: Callback completo (per errori)
        should_be: Descrizione attesa (per errori)

    Returns:
        Valore convertito

    Raises:
        CallbackDataException: Se la conversione fallisce
    """
    field_type = spec.get("type")

    if field_type is None:
        raise ValueError("Campo 'type' mancante nella specifica")

    # Caso 1: valore letterale (fisso)
    if field_type == "literal":
        expected_value = spec.get("value")
        if raw_value != expected_value:
            raise CallbackDataException(callback_data, should_be)
        return raw_value

    # Caso 2: tipo singolo (int, str)
    if isinstance(field_type, type):
        return _convert_to_type(raw_value, field_type, callback_data, should_be)

    # Caso 3: lista di tipi alternativi [int, str]
    if isinstance(field_type, list):
        for t in field_type:
            try:
                return t(raw_value)
            except (ValueError, TypeError):
                continue
        raise CallbackDataException(callback_data, should_be)

    raise ValueError(f"Tipo di campo non gestito: {field_type}")


def _convert_to_type(
        value: str,
        target_type: type,
        callback_data: str,
        should_be: Optional[str]
) -> Any:
    """
    Converte un valore a un tipo specifico.

    Args:
        value: Valore da convertire
        target_type: Tipo target
        callback_data: Callback completo (per errori)
        should_be: Descrizione attesa (per errori)

    Returns:
        Valore convertito

    Raises:
        CallbackDataException: Se la conversione fallisce
    """
    try:
        return target_type(value)
    except (ValueError, TypeError):
        raise CallbackDataException(callback_data, should_be)


# ============================================================================
# USER RESOLUTION
# ============================================================================

async def resolve_chat_member(
        context: CustomContext,
        user_identifier: Union[int, str],
        chat_id: Optional[int] = None
) -> Union[Dict[str, Any], PyroUser, PTBUser]:
    """
    Risolve un ChatMember usando prima pyrogram, poi telegram bot come fallback.
    Utilizza caching per migliorare le performance.

    Args:
        context: CustomContext
        user_identifier: ID utente o username
        chat_id: ID della chat (opzionale, usa pydb.group_chat_id se non specificato)

    Returns:
        Dict con status/error/user/member oppure oggetto User
    """
    if not user_identifier:
        log.warning("user_identifier vuoto fornito a resolve_chat_member")
        return _create_error_response("invalid_identifier")

    me = await context.bot.get_me()
    if user_identifier == me.id:
        return me

    chat_id = chat_id or context.pydb.group_chat_id

    cache_key = _get_cache_key(chat_id, user_identifier)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result

    pyro_result = await _try_pyrogram_chat_member_resolve(chat_id, user_identifier)

    if pyro_result["status"] == "success" or pyro_result["error"] == "username_404":
        _set_in_cache(cache_key, pyro_result)
        return pyro_result

    user_id_str = str(user_identifier)
    if is_user_id(user_id_str):
        resolved_id = user_id_str
    else:
        user_obj = await _try_pyrogram_user_resolve(user_identifier)
        resolved_id = user_obj.id if user_obj else None

    if resolved_id:
        ptb_result = await _try_ptb_resolve(context, chat_id, resolved_id)
        if ptb_result["status"] == "success":
            _set_in_cache(cache_key, ptb_result)
            return ptb_result

    log.debug(f"Impossibile risolvere ChatMember per {user_identifier}")
    return pyro_result


async def username_to_id(username: Union[int, str]) -> Optional[int]:
    """
    Converte un username in user ID.

    Args:
        username: Username o ID da convertire

    Returns:
        User ID se trovato, None altrimenti
    """
    if isinstance(username, int) or (isinstance(username, str) and username.isnumeric()):
        return int(username)

    try:
        user_response = await resolve_user(identifier=username)
        user = user_response.get("user")
    except Exception as e:
        log.warning(f"Impossibile risolvere username {username}: {e}")
        return None

    if user is None:
        log.warning(f"Username {username} non trovato: assicurati che esista")
        return None

    return user.id


async def resolve_user(identifier: Union[int, str]) -> Dict[str, Any]:
    """
    Risolve un utente (senza riferimento a chat specifica).

    Args:
        identifier: ID o username dell'utente

    Returns:
        Dict con status/error/user/member
    """
    user = await _try_pyrogram_user_resolve(user_identifier=identifier)
    if user:
        return _create_success_response(member=user)
    return _create_error_response("unable_to_identify")


async def _try_pyrogram_chat_member_resolve(
        chat_id: Union[int, str],
        user_identifier: Union[int, str]
) -> Dict[str, Any]:
    """Tenta di risolvere un ChatMember usando pyrogram"""
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
        log.debug(f"Username {user_identifier} non esiste")
        return _create_error_response("username_404")
    except Exception as e:
        log.warning(f"Errore pyrogram durante risoluzione ChatMember per {user_identifier}: {e}")
        return _create_error_response("cannot_resolve")


async def _try_pyrogram_user_resolve(user_identifier: Union[int, str]) -> Optional[PyroUser]:
    """Tenta di risolvere un User usando pyrogram"""
    try:
        return await constants.pyro_instance.get_users(user_ids=user_identifier)
    except Exception as e:
        log.warning(f"Errore pyrogram durante risoluzione User per {user_identifier}: {e}")
        return None


async def _try_ptb_resolve(
        context: CustomContext,
        chat_id: Union[int, str],
        user_identifier: Union[int, str]
) -> Dict[str, Any]:
    """Tenta di risolvere un ChatMember usando PTB (fallback)"""
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


def _create_success_response(member: Union[PyroChatMember, PTBChatMember, PyroUser, PTBUser]) -> Dict[str, Any]:
    """Crea una risposta di successo standardizzata"""
    if isinstance(member, (PTBChatMember, PyroChatMember)):
        return {
            "status": "success",
            "error": "",
            "user": member.user,
            "member": member
        }
    else:
        return {
            "status": "success",
            "error": "",
            "user": member,
            "member": None
        }


def _create_error_response(error_code: str) -> Dict[str, Any]:
    """Crea una risposta di errore standardizzata"""
    return {
        "status": "failed",
        "error": error_code,
        "user": None,
        "member": None
    }


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

async def edit_message_safely(
        context: CustomContext,
        message_id: int,
        chat_id: int,
        text: str,
        keyboard: InlineKeyboardMarkup
) -> Optional[int]:
    """
    Wrapper per edit_message_text con gestione errori.
    Tenta prima di modificare, poi invia nuovo messaggio se fallisce.

    Returns:
        ID del messaggio (modificato o nuovo), None in caso di errore
    """
    try:
        await context.bot.edit_message_text(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return message_id
    except Exception as edit_error:
        log.debug(f"Impossibile modificare messaggio {message_id}, tento invio nuovo: {edit_error}")
        try:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return message.id
        except Exception as send_error:
            log.error(f"Impossibile modificare o inviare un nuovo messaggio: {send_error}")
            return None


async def handle_if_not_file(
        update: Update,
        context: CustomContext,
        filename: Optional[str],
        callback_data: str
) -> bool:
    """
    Gestisce il caso in cui un file non sia stato creato correttamente.

    Returns:
        bool: True se c'è stato un errore (file mancante), False altrimenti
    """
    if not filename:
        text = "❌ Errore durante la creazione del file di testo. Contatta l'admin."
        keyboard = [[InlineKeyboardButton(
            text="🔙 Indietro",
            callback_data=callback_data)
        ]]

        await context.bot.edit_message_text(
            message_id=update.effective_message.message_id,
            chat_id=update.effective_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return True
    return False


async def wrong_input_message(
        update: Update,
        context: CustomContext,
        correct_message: str,
        reply_to_message_id: int | None = None
) -> None:
    """Invia un messaggio di errore per input non valido"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"⚠️ {correct_message}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🗑️ Chiudi", callback_data=GlobalAction.CLOSE)]]
        ),
        reply_to_message_id=reply_to_message_id,
        parse_mode=ParseMode.HTML
    )


async def not_implemented_yet(update: Update, context: CustomContext) -> None:
    """Messaggio per funzionalità non ancora implementate"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ Funzionalità non ancora implementata.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🗑️ Chiudi", callback_data="close_menu")]]
        )
    )


# ============================================================================
# PANEL & SETTINGS
# ============================================================================

async def create_and_render_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        text: str,
        keyboard: List[List[ButtonItem]],
        message_id: Optional[int] = None,
        user_id: Optional[int] = None,
        send: bool = False
) -> None:
    """
    Crea e renderizza un pannello con configurazione specifica.

    Args:
        update: Update object
        context: CustomContext
        base_path: Path base per il pannello
        text: Testo del pannello
        keyboard: Layout tastiera
        message_id: ID messaggio da modificare (opzionale)
        user_id: ID utente target (opzionale)
        send: Se True, invia nuovo messaggio invece di modificare
    """
    panel = Panel(
        PanelConfig(base_path=base_path, text=text, keyboard=keyboard)
    )

    await panel.render(
        update=update,
        context=context,
        message_id=message_id,
        user_id=user_id,
        send=send
    )


async def set_moderation_bool_setting(
        update: Update,
        context: CustomContext,
        setting: str,
        sub_setting: str,
        value: bool,
        category: Optional[str] = None
) -> None:
    """
    Imposta un valore booleano per un setting di moderazione e logga l'azione.

    Args:
        update: Update object
        context: CustomContext
        setting: Nome del setting (può contenere '/')
        sub_setting: Nome del sub-setting
        value: Valore booleano da impostare
        category: Categoria opzionale
    """
    log_name = "_".join(setting.split("/")) + ("_category" if category else "")
    log_c = logger.getChild(log_name)

    path = f"moderation.{'.'.join(setting.split('/'))}{f'.{category}' if category else ''}.{sub_setting}"
    set_value(context=context, path=path, value=value)

    log_c.info(
        f"Modifica setting: {path} impostato a '{value}' "
        f"da utente {update.effective_user.id} "
        f"({update.effective_user.username or update.effective_user.first_name})"
    )


def get_banned_panel() -> Panel:
    """Restituisce il pannello per utenti bannati"""
    return Panel(
        PanelConfig(
            base_path="banned",
            text="❌ Sei stato bannato/a. Non potrai usare il bot.",
            keyboard=[[ButtonItem(text="🗑️ Chiudi", callback_key="close_menu")]]
        ),
        send=True
    )


async def render_action_not_permitted_panel(update: Update, context: CustomContext, base_path: PathBuilder) -> None:
    text = ("⛔ <b>Azione Vietata</b>\n\n"
            "🔐 Non hai i permessi per eseguire questa azione.")

    keyabord = [
        [
            ButtonItem(text="🔙 Indietro", callback_key=base_path.back()),
            ButtonItem(text="🏠 Home", callback_key=PathBuilder(base_path.segments[0]))
        ]
    ]


def get_config(context: CustomContext, platform: Platform, category: Category) -> CategorySetting:
    """Helper per recuperare la configurazione in modo sicuro e tipizzato."""
    return getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)


def resolve_pl_cat(pl_str: str, cat_str: str):
    """Risolve le enum Platform e Category dalle stringhe."""
    platform = Platform(pl_str)
    # get_platform_categories restituisce la classe Enum (es. Category), che chiamiamo con la stringa
    category = get_platform_categories(platform)(cat_str)
    return platform, category

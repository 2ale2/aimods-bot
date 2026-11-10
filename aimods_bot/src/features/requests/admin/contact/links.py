"""
Link alla chat privata di un utente, da mettere su un tasto url.

Le strade sono due:

- `https://t.me/<username>`: funziona sempre, ma solo se l'utente ha uno username pubblico.
- `tg://user?id=<id>`: funziona anche senza username, ma Telegram rifiuta **l'intero
  messaggio** (`BUTTON_USER_PRIVACY_RESTRICTED`) se la privacy «Messaggi inoltrati →
  Collegamento al mio account» dell'utente non lo permette. Il bot non è mai un contatto,
  quindi «I miei contatti» vale quanto «Nessuno».

La Bot API non dice in anticipo come è impostata la privacy: si prova a mandare il tasto
e si guarda l'errore. L'esito negativo resta in cache per `LINK_FAILURE_TTL`, così il
pannello non riprova (e non fallisce) a ogni apertura.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from telegram import Bot
from telegram.error import BadRequest, TelegramError

from aimods_bot.src.infra.log import logger

log = logger.getChild(__name__)

LINK_FAILURE_TTL = 6 * 60 * 60

# Magic string, come `_is_not_modified` in ui/panel.py: la Bot API non dà altro modo di
# distinguere questi errori.
_PRIVACY_ERRORS = ("button_user_privacy_restricted",)
_INVALID_USER_ERRORS = ("button_user_invalid", "user_id_invalid", "peer_id_invalid")


class LinkFailure(StrEnum):
    PRIVACY = "privacy"   # la privacy dell'utente non consente il link al suo account
    INVALID = "invalid"   # Telegram non riconosce l'utente (es. account eliminato)


@dataclass(frozen=True)
class PrivateChatLink:
    url: str
    # Con lo username il link non passa dal controllo privacy: non può far fallire il messaggio.
    via_username: bool


# user_id → (motivo, istante del fallimento). Volutamente non persistito.
_failures: dict[int, tuple[LinkFailure, float]] = {}


def classify_link_error(error: BadRequest) -> LinkFailure | None:
    """Ritorna il motivo se l'errore riguarda un tasto `tg://user`, altrimenti None."""
    message = str(error).lower()
    if any(marker in message for marker in _PRIVACY_ERRORS):
        return LinkFailure.PRIVACY
    if any(marker in message for marker in _INVALID_USER_ERRORS):
        return LinkFailure.INVALID
    return None


def remember_link_failure(user_id: int, failure: LinkFailure) -> None:
    _failures[user_id] = (failure, time.monotonic())


def known_link_failure(user_id: int) -> LinkFailure | None:
    entry = _failures.get(user_id)
    if entry is None:
        return None
    failure, at = entry
    if time.monotonic() - at > LINK_FAILURE_TTL:
        _failures.pop(user_id, None)
        return None
    return failure


def forget_link_failures() -> None:
    _failures.clear()


async def fetch_username(bot: Bot, user_id: int) -> str | None:
    """
    Username attuale dell'utente. Le richieste salvano solo lo user_id e lo username
    può cambiare, quindi va letto ogni volta. `getChat` funziona per chi ha avviato il bot.
    """
    try:
        chat = await bot.get_chat(chat_id=user_id)
    except TelegramError as e:
        log.debug(f"Cannot read chat of {user_id}: {e}")
        return None
    return chat.username or None


async def resolve_private_chat_link(bot: Bot, user_id: int, use_cache: bool = True) -> PrivateChatLink | None:
    """
    Link migliore per aprire la chat con l'utente. None se già si sa che `tg://user`
    verrebbe rifiutato (solo con `use_cache`).
    """
    username = await fetch_username(bot=bot, user_id=user_id)
    if username:
        return PrivateChatLink(url=f"https://t.me/{username}", via_username=True)
    if use_cache and known_link_failure(user_id) is not None:
        return None
    return PrivateChatLink(url=f"tg://user?id={user_id}", via_username=False)

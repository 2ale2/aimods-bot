"""
Ponte verso i metodi Bot API 10.1 non ancora coperti da PTB.

PERCHÉ ESISTE
    PTB 22.8 copre nativamente fino al Bot API 10.0. I metodi delle join
    request queries (Bot API 10.1, 11/06/2026) non hanno un wrapper: issue
    PTB #5261, aperta. La via documentata dalla wiki PTB ("Bot API Forward
    Compatibility") è `Bot.do_api_request`, con endpoint in snake_case.

QUANDO VA RIMOSSO
    Quando PTB espone `Bot.send_chat_join_request_web_app` e
    `Bot.answer_chat_join_request_query`. A quel punto:
      - sostituire le due chiamate ai metodi nativi,
      - togliere `extract_query_id` (il campo diventerà un attributo di
        `ChatJoinRequest`, non più `api_kwargs`),
      - cancellare il file.
    `assert_bridge_still_needed()` fa scattare un warning al boot appena la
    versione supportata arriva a 10.1, così non resta qui per anni.

NON METTERE QUI
    Logica di dominio (blacklist, DB, Pyrogram, decisioni su chi approvare).
    Questo modulo deve restare cancellabile senza perdere niente.
"""

from typing import Any, Literal

import telegram
from telegram import Bot, Update

from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)

#: Versione a partire dalla quale questo ponte è superfluo.
_SUPERSEDED_AT = (10, 1)

#: Endpoint in snake_case, come richiesto da `do_api_request`.
_SEND_ENDPOINT = "send_chat_join_request_web_app"
_ANSWER_ENDPOINT = "answer_chat_join_request_query"

JoinRequestResult = Literal["approve", "decline", "queue"]

# Timeout stretti: queste chiamate vivono dentro la finestra di 10 secondi.
# I default di PTB (5s read + pool) sommati ai retry possono superarla senza
# che nessuno se ne accorga: meglio fallire presto e finire nel fallback.
_TIMEOUTS: dict[str, float] = {
    "connect_timeout": 3.0,
    "read_timeout": 5.0,
    "write_timeout": 5.0,
    "pool_timeout": 1.0,
}


def assert_bridge_still_needed() -> None:
    """
    Da chiamare una volta al boot (post_init_hook). Non solleva: logga.
    """
    supported = telegram.__bot_api_version_info__
    if tuple(supported[:2]) >= _SUPERSEDED_AT:
        log.warning(
            "botapi_10_1.py è superato: PTB supporta il Bot API %s.%s. "
            "Sostituire le chiamate raw con i metodi nativi e cancellare il modulo.",
            supported[0],
            supported[1],
        )
    else:
        log.info(
            "botapi_10_1.py attivo: PTB copre il Bot API %s.%s, servono i metodi 10.1.",
            supported[0],
            supported[1],
        )


def extract_query_id(update: Update) -> str | None:
    """
    Legge il query_id da un ChatJoinRequest.

    ATTENZIONE all'asimmetria dei nomi, che sembra un errore e non lo è:
      - nell'UPDATE il campo si chiama `query_id`
      - nei METODI il parametro si chiama `chat_join_request_query_id`
    Uniformare i due lati "per pulizia" rompe tutto silenziosamente.

    Restituisce None se la richiesta non passa dal guard bot (link diretto,
    utente aggiunto a mano): è un caso normale, non un errore.
    """
    jr = update.chat_join_request
    if jr is None:
        return None
    return (jr.api_kwargs or {}).get("query_id")


async def send_join_request_web_app(bot: Bot, query_id: str, web_app_url: str) -> Any:
    """
    sendChatJoinRequestWebApp — apre la Mini App all'utente che ha chiesto di entrare.

    `web_app_url` è una STRINGA, non un `WebAppInfo`. Ritorna True.
    Non cattura eccezioni: la scelta del fallback spetta al chiamante.
    """
    return await bot.do_api_request(
        endpoint=_SEND_ENDPOINT,
        api_kwargs={
            "chat_join_request_query_id": query_id,
            "web_app_url": web_app_url,
        },
        **_TIMEOUTS,
    )


async def answer_join_request(bot: Bot, query_id: str, result: JoinRequestResult) -> Any:
    """
    answerChatJoinRequestQuery — risposta finale.

    `queue` restituisce la richiesta agli admin: è il default sensato in ogni
    `except` e per lo sweeper (dopo un `decline` Telegram limita la
    ripresentazione, e il gruppo ha già l'anti-spam aggressivo).

    Il query_id è MONOUSO: usare solo quello firmato che arriva nell'initData,
    mai riciclarne uno memorizzato.
    """
    return await bot.do_api_request(
        endpoint=_ANSWER_ENDPOINT,
        api_kwargs={
            "chat_join_request_query_id": query_id,
            "result": result,
        },
        **_TIMEOUTS,
    )


async def answer_queue_or_log(bot: Bot, query_id: str) -> bool:
    """
    Fallback che non solleva mai. Da usare negli `except` del percorso sincrono,
    dove un'eccezione in più significa join request persa senza segnale.
    """
    try:
        await answer_join_request(bot, query_id, "queue")
        return True
    except Exception:
        log.exception(
            "fallback 'queue' fallito per query_id=%s — richiesta persa, "
            "va recuperata a mano dal pannello admin",
            query_id,
        )
        return False
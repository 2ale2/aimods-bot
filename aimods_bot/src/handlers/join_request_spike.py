"""
SPIKE TEMPORANEO — Bot API 10.1 join request queries.

Scopo: mettere in sicurezza il cancello (Guard Mode è attivo, il gruppo ha
join_by_request=True e guard_bot=@aimodsbot) e osservare cosa arriva davvero.

Da rimuovere quando il flusso reale è pronto. Non tocca DB, non tocca Pyrogram,
non tocca context.pydb: deve stare largamente dentro i 10 secondi.
"""

import os

from telegram import Update
from telegram.ext import ChatJoinRequestHandler

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)

MINIAPP_URL = os.getenv("MINIAPP_URL", "https://app.aimodsitalia.store/")

# I nomi dei parametri di sendChatJoinRequestWebApp non sono confermati sulla doc.
# Per answerChatJoinRequestQuery è certo che sia 'chat_join_request_query_id'.
# Provo i candidati in ordine: il primo che non solleva vince, e il log dice quale.
_SEND_PARAM_CANDIDATES = (
    ("chat_join_request_query_id", "web_app_url"),
    ("query_id", "web_app_url"),
)


async def _answer_queue(context: CustomContext, qid: str) -> None:
    """Fallback difendibile: restituisce la richiesta agli admin."""
    try:
        await context.bot.do_api_request(
            endpoint="answer_chat_join_request_query",
            api_kwargs={"chat_join_request_query_id": qid, "result": "queue"},
        )
        log.info("JR SPIKE: fallback queue OK")
    except Exception:
        log.exception("JR SPIKE: anche il fallback queue è fallito — richiesta persa")


async def join_request_spike(update: Update, context: CustomContext) -> None:
    jr = update.chat_join_request
    extra = dict(jr.api_kwargs or {})

    # Il log più importante di tutto il file.
    log.info(
        "JR SPIKE user=%s chat=%s invite_link=%s api_kwargs=%r",
        jr.from_user.id,
        jr.chat.id,
        getattr(jr.invite_link, "invite_link", None),
        extra,
    )

    qid = extra.get("query_id")
    if qid is None:
        log.warning(
            "JR SPIKE: nessun query_id. O PTB 22.8 lo scarta, o la richiesta "
            "arriva da un percorso non presidiato. Non rispondo: gestione agli admin."
        )
        return

    for id_key, url_key in _SEND_PARAM_CANDIDATES:
        try:
            res = await context.bot.do_api_request(
                endpoint="send_chat_join_request_web_app",
                api_kwargs={id_key: qid, url_key: MINIAPP_URL},
            )
            log.info("JR SPIKE: send OK con (%s, %s) -> %r", id_key, url_key, res)
            return
        except Exception as e:
            log.warning("JR SPIKE: send fallito con (%s, %s): %s", id_key, url_key, e)

    log.error("JR SPIKE: nessun set di parametri ha funzionato")
    await _answer_queue(context, qid)


# block=False: la callback gira in un task suo, non accoda altri update.
chat_join_request_spike_handler = ChatJoinRequestHandler(
    callback=join_request_spike,
    block=False,
)

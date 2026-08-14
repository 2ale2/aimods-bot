"""
Handler delle join request (Guard Mode, Bot API 10.1).

Sostituisce `join_request_spike.py`, che va cancellato.

FINESTRA DI 10 SECONDI
    Vale per la PRIMA chiamata (`send…` oppure `answer…`). La risposta finale
    arriva dopo, dall'endpoint della Mini App. Quindi qui dentro NON deve
    esserci niente che tocchi il DB o Pyrogram: solo una chiamata di rete.

    `block=False` sull'handler: la callback gira in un task suo e non accoda
    gli altri update.
"""

from telegram import Update
from telegram.ext import ChatJoinRequestHandler

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.botapi_10_1 import (
    answer_queue_or_log,
    extract_query_id,
    send_join_request_web_app,
)
from aimods_bot.src.helpers.utils.join_request_sweeper import track_pending

log = logger.getChild(__name__)


def build_join_request_handler(miniapp_url: str) -> ChatJoinRequestHandler:
    """
    L'URL arriva da init.py e non da os.getenv: così il valore loggato al boot
    è per costruzione quello davvero in uso, invece di combaciare per
    coincidenza con un secondo default scritto altrove.
    """

    async def on_join_request(update: Update, context: CustomContext) -> None:
        jr = update.chat_join_request
        user_id = jr.from_user.id
        chat_id = jr.chat.id

        query_id = extract_query_id(update)

        if query_id is None:
            # Richiesta arrivata da un percorso non presidiato dal guard bot.
            # Non c'è niente a cui rispondere: resta in coda per gli admin,
            # che è il comportamento di prima di Guard Mode.
            log.warning(
                "Join request senza query_id: user=%s chat=%s invite_link=%s. "
                "Gestione agli admin.",
                user_id,
                chat_id,
                getattr(jr.invite_link, "invite_link", None),
            )
            return

        # PUNTO DI INNESTO — lookup blacklist.
        # Va qui, prima del send, e deve essere SOLO un lookup in memoria su
        # context.pydb.ban_list: niente Pyrogram, niente add_to_table, niente
        # send_chat_action. Il ban vero si accoda con job_queue.run_once(0).
        # Rimandato con la riscrittura della moderazione.

        try:
            await send_join_request_web_app(context.bot, query_id, miniapp_url)
        except Exception:
            log.exception(
                "sendChatJoinRequestWebApp fallita: user=%s chat=%s", user_id, chat_id
            )
            # La richiesta torna agli admin invece di restare pendente.
            await answer_queue_or_log(context.bot, query_id)
            return

        log.info("Mini App aperta per user=%s chat=%s", user_id, chat_id)
        track_pending(context.bot_data, query_id)

        # Da qui in poi la palla è dell'utente: la risposta finale arriva
        # dall'endpoint (`/api/join`), non da questo handler.
        # Chi non preme niente resta pendente: serve lo sweeper periodico.

    return ChatJoinRequestHandler(callback=on_join_request, block=False)

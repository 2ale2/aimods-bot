"""
Sweeper delle join request senza risposta.

PERCHÉ SERVE
    Se l'utente apre la Mini App e fa swipe, al backend non arriva NIENTE: è
    indistinguibile da "sta ancora leggendo". Quella join request resta pendente per sempre.

    Il Bot API non ha un metodo per elencare le richieste pendenti, quindi lo
    sweeper non può andare a cercarle: deve ricordarsi da solo chi ha aperto
    la Mini App e non ha risposto. Da qui la mappa in bot_data.

PERCHÉ `decline`
    L'accettazione del regolamento deve essere esplicita: chi non conferma non
    entra. Restituire la richiesta agli admin (`queue`) significherebbe
    rimettere a mano proprio il lavoro che questo meccanismo automatizza.
"""

import time

from telegram.ext import Application, ContextTypes

from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import JoinRequestSweeperJobName
from aimods_bot.src.helpers.utils.botapi_10_1 import answer_join_request

JOB_NAME = JoinRequestSweeperJobName()

log = logger.getChild(__name__)

# Quanto tempo l'utente ha per rispondere prima che la richiesta venga declinata.
# Deve essere >= INITDATA_MAX_AGE del listener (1800s)
PENDING_TTL_SECONDS = 1800

SWEEP_INTERVAL_SECONDS = 5 * 60


def track_pending(bot_data, query_id: str) -> None:
    """Da chiamare quando la Mini App viene aperta."""
    bot_data.pending_join_requests[query_id] = time.time()


def untrack_pending(bot_data, query_id: str) -> None:
    """
    Da chiamare quando l'utente ha risposto (approve o decline).
    Non solleva se la chiave non c'è: può essere già stata tolta dallo sweeper.
    """
    bot_data.pending_join_requests.pop(query_id, None)


async def sweep_pending_join_requests(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Job periodico. Declina le richieste rimaste senza risposta oltre il TTL.
    """
    pending = context.bot_data.pending_join_requests
    if not pending:
        return

    now = time.time()
    scaduti = [qid for qid, ts in pending.items() if now - ts > PENDING_TTL_SECONDS]

    if not scaduti:
        return

    log.info("Sweeper: %s richieste scadute su %s tracciate", len(scaduti), len(pending))

    for qid in scaduti:
        # Rimossa PRIMA della chiamata: se questa fallisce, riprovare a ogni
        # passata per sempre non aiuta nessuno e continua a chiamare l'API.
        # Il caso peggiore è una richiesta che resta pendente, cioè lo stato
        # in cui era comunque.
        pending.pop(qid, None)
        try:
            await answer_join_request(context.bot, qid, "decline")
            log.info("Sweeper: richiesta %s declinata (nessuna risposta)", qid)
        except Exception as e:
            # Hide_requester_missing = l'utente ha già risposto per altra via,
            # o un admin ha già gestito la richiesta a mano. Non è un errore.
            log.info("Sweeper: %s non più pendente (%s)", qid, e)


def schedule_sweeper(app: Application) -> None:
    """Da chiamare in post_init_hook."""
    app.job_queue.run_repeating(
        sweep_pending_join_requests,
        interval=SWEEP_INTERVAL_SECONDS,
        first=SWEEP_INTERVAL_SECONDS,
        name=JOB_NAME.to_string(),
    )
    log.info(
        "Sweeper join request programmato: ogni %ss, TTL %ss",
        SWEEP_INTERVAL_SECONDS,
        PENDING_TTL_SECONDS,
    )

"""
Listener HTTP della Mini App (join request).

Vive nello STESSO processo dell'Application: `run_webhook` è bloccante, quindi
il runner va avviato in `post_init_hook` e fermato in `post_shutdown_hook`.
Porta separata (8081, `expose` nel compose, non `ports`): il tornado del
webhook non va toccato — invariante del path, §3.2 del v8.

Serve statico e API dallo stesso origin: la Same-Origin Restriction su
BotFather è attiva e non va disattivata.

SICUREZZA
    L'endpoint è raggiungibile da internet via nginx. L'unica credenziale è la
    firma HMAC dell'initData: nessun ramo deve toccare bot o DB prima che
    `parse_init_data` sia passata. Il replay è limitato da due cose messe
    insieme — `auth_date` (max_age) e il fatto che il query_id sia monouso.
"""

import asyncio
import json
import os
from typing import Any

from aiohttp import web
from telegram.error import BadRequest
from telegram.ext import Application

from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.constants.paths import MINIAPP_STATIC_DIR
from aimods_bot.src.helpers.utils.botapi_10_1 import answer_join_request
from aimods_bot.src.helpers.utils.initdata import InitDataError, parse_init_data
from aimods_bot.src.helpers.utils.join_request_sweeper import untrack_pending

log = logger.getChild(__name__)

# L'auth_date è fissato all'APERTURA della Mini App, non al POST: l'utente sta
# leggendo un regolamento, non compilando un form. 300s (default di
# initdata.py) rifiuterebbe chi legge con calma. Il replay qui è già limitato
# dal query_id monouso, quindi la finestra può essere larga.
INITDATA_MAX_AGE = int(os.getenv("MINIAPP_INITDATA_MAX_AGE", "1800"))

# Difesa banale contro body assurdi: un initData sta in pochi KB.
MAX_BODY_BYTES = 8 * 1024

# Il runner sta qui e non in `bot_data` perché `bot_data` è un modello pydantic
# (`BotData`) serializzato con `model_dump(mode="json")` a ogni flush: non è un
# dict, e comunque non ha un campo `ephemeral` come ChatData/UserData.
# Nemmeno `Application` va bene: usa __slots__.
# Il processo è uno solo, quindi una variabile di modulo è sufficiente.
_runner: web.AppRunner | None = None


def _json(payload: dict[str, Any], status: int = 200) -> web.Response:
    return web.json_response(payload, status=status)


async def _handle_health(request: web.Request) -> web.Response:
    """Per il check dall'interno della rete docker. Non espone nulla."""
    return _json({"ok": True})


async def _handle_accept(request: web.Request) -> web.Response:
    """
    POST /api/join — body JSON: {"init_data": "...", "action": "accept"|"decline"}
    """
    tg_app: Application = request.app["tg_app"]
    bot_token: str = request.app["bot_token"]

    # Letto a ogni richiesta e non catturato al boot: `group_chat_id` è un campo
    # di BotData, quindi modificabile a runtime. Catturarlo significherebbe
    # rifiutare ogni initData valido dopo un cambio di gruppo.
    group_chat_id: int | None = tg_app.bot_data.group_chat_id
    if group_chat_id is None:
        log.error("group_chat_id non configurato in bot_data: impossibile validare")
        return _json({"ok": False, "error": "bot non configurato"}, 503)

    if request.content_length and request.content_length > MAX_BODY_BYTES:
        return _json({"ok": False, "error": "payload troppo grande"}, 413)

    try:
        body = json.loads(await request.text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json({"ok": False, "error": "body non JSON"}, 400)

    raw_init_data = body.get("init_data")
    action = body.get("action")
    if action not in ("accept", "decline"):
        return _json({"ok": False, "error": "action non valida"}, 400)

    # --- da qui in poi niente è fidato finché la firma non torna ---
    try:
        data = parse_init_data(raw_init_data or "", bot_token, max_age=INITDATA_MAX_AGE)
    except InitDataError as e:
        # Volutamente generico verso il client: non aiutiamo chi sta provando.
        log.warning("initData rifiutato: %s", e)
        return _json({"ok": False, "error": "sessione non valida"}, 403)

    query_id = data.get("chat_join_request_query_id")
    if not query_id:
        # Caso LEGITTIMO: la stessa URL è registrata come Main Mini App, quindi
        # si può arrivare qui aprendo l'app dal profilo del bot, senza nessuna
        # join request in corso. Non è un attacco.
        log.info("initData valido ma senza query_id (apertura fuori dal flusso join)")
        return _json({"ok": False, "reason": "no_join_request"}, 409)

    chat = data.get("chat") or {}
    if chat.get("id") != group_chat_id:
        log.warning(
            "initData valido ma per il gruppo sbagliato: chat.id=%r atteso=%r",
            chat.get("id"),
            group_chat_id,
        )
        return _json({"ok": False, "error": "gruppo non riconosciuto"}, 403)

    user_id = (data.get("user") or {}).get("id")
    result = "approve" if action == "accept" else "decline"

    try:
        await answer_join_request(tg_app.bot, query_id, result)
    except BadRequest as e:
        # Quasi sempre: query_id già consumato (doppio tap, o retry del client).
        # NON è un errore per l'utente — l'esito è già quello giusto.
        # TODO: quando il messaggio esatto sarà noto dai log, distinguere
        # "già risposto" da un BadRequest vero e restituire 500 sul secondo.
        log.info("answer %s su query_id già consumato? user=%s: %s", result, user_id, e)
        untrack_pending(tg_app.bot_data, query_id)
        return _json({"ok": True, "result": result, "repeated": True})
    except Exception:
        log.exception("answer %s fallita per user=%s query_id=%s", result, user_id, query_id)
        return _json({"ok": False, "error": "errore interno"}, 500)

    log.info("join %s: user=%s chat=%s", result, user_id, group_chat_id)
    untrack_pending(tg_app.bot_data, query_id)

    # Il post-approvazione (DB, log_ban, messaggio di benvenuto in privato —
    # `allows_write_to_pm` è true) NON va qui: si accoda alla job_queue, così
    # la risposta HTTP non aspetta il DB.
    # tg_app.job_queue.run_once(...)

    return _json({"ok": True, "result": result})


async def _handle_rules(request: web.Request) -> web.Response:
    """POST /api/rules — body: {"init_data": "..."}"""
    tg_app: Application = request.app["tg_app"]
    bot_token: str = request.app["bot_token"]

    try:
        body = json.loads(await request.text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json({"ok": False, "error": "body non JSON"}, 400)

    try:
        data = parse_init_data(body.get("init_data") or "", bot_token, max_age=INITDATA_MAX_AGE)
    except InitDataError as e:
        log.warning("initData rifiutato su /api/rules: %s", e)
        return _json({"ok": False, "error": "sessione non valida"}, 403)

    if not data.get("chat_join_request_query_id"):
        return _json({"ok": False, "reason": "no_join_request"}, 409)

    text = tg_app.bot_data.user_joined_message_text or ""
    if not text:
        log.error("user_joined_message_text vuoto: la Mini App mostrerebbe una pagina bianca")
        return _json({"ok": False, "error": "regolamento non configurato"}, 503)

    return _json({"ok": True, "title": "Regolamento", "text": text})


async def _handle_index(request: web.Request) -> web.Response:
    """GET / — l'URL che apre Telegram. add_static non fa fallback su index.html."""
    index = MINIAPP_STATIC_DIR / "index.html"
    if not os.path.isfile(index):
        log.error("index.html mancante in %s", MINIAPP_STATIC_DIR)
        return web.Response(status=503, text="Mini App non disponibile")
    return web.FileResponse(index)


@web.middleware
async def _error_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """
    Rete di sicurezza del listener.

    L'error handler di PTB (§8.6) non vede queste eccezioni: sono in un runner
    aiohttp separato. Senza questo middleware una eccezione non prevista
    diventa una pagina HTML 500 generata da aiohttp, che il client prova a
    leggere come JSON e fallisce una seconda volta — con il risultato che
    l'utente vede un errore muto e il traceback finisce sul logger di aiohttp
    invece che sul nostro.
    """
    try:
        return await handler(request)
    except asyncio.CancelledError:
        # Client che chiude la connessione, o shutdown: non è un errore nostro
        # e non va trasformato in una risposta.
        raise
    except web.HTTPException as exc:
        # 404/405 generati da aiohttp. Sullo statico l'HTML va bene; sotto /api
        # il client si aspetta JSON.
        if request.path.startswith("/api/"):
            return _json({"ok": False, "error": exc.reason}, exc.status)
        raise
    except Exception:
        log.exception("Eccezione non gestita su %s %s", request.method, request.path)
        # Volutamente generico: il dettaglio sta nei log, non nella risposta.
        return _json({"ok": False, "error": "errore interno"}, 500)


def build_miniapp(tg_app: Application, bot_token: str) -> web.Application:
    aio_app = web.Application(
        client_max_size=MAX_BODY_BYTES,
        middlewares=[_error_middleware],
    )
    aio_app["tg_app"] = tg_app
    aio_app["bot_token"] = bot_token

    aio_app.router.add_post("/api/join", _handle_accept)
    aio_app.router.add_get("/healthz", _handle_health)
    aio_app.router.add_post("/api/rules", _handle_rules)
    aio_app.router.add_get("/", _handle_index)
    # Statico per ultimo: la rotta catch-all non deve mangiarsi /api.
    aio_app.router.add_static("/", MINIAPP_STATIC_DIR, show_index=False, follow_symlinks=False)
    return aio_app


async def start_miniapp_server(tg_app: Application, bot_token: str) -> None:
    """Da chiamare in post_init_hook. Non blocca."""
    global _runner

    if _runner is not None:
        # Succede solo se post_init_hook gira due volte nello stesso processo.
        # Senza questa guardia il secondo bind fallisce con EADDRINUSE e il
        # primo runner resta orfano, non fermabile.
        log.warning("start_miniapp_server: runner già attivo, non ne avvio un altro")
        return

    port = int(os.getenv("MINIAPP_PORT", "8081"))
    runner = web.AppRunner(build_miniapp(tg_app, bot_token))
    await runner.setup()
    # 0.0.0.0 dentro il container: l'unico accesso è nginx sulla proxy_network,
    # perché nel compose la porta è `expose`, non `ports`.
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    _runner = runner
    log.info("Mini App in ascolto sulla porta %s", port)


async def stop_miniapp_server() -> None:
    """Da chiamare in post_shutdown_hook."""
    global _runner

    if _runner is None:
        log.warning("stop_miniapp_server: nessun runner da fermare")
        return
    runner, _runner = _runner, None
    await runner.cleanup()
    log.info("Mini App fermata")

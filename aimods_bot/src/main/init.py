import os
import locale
import sys
from urllib.parse import urlparse
from telegram.ext import ApplicationBuilder, ContextTypes
from aimods_bot.src.core.async_persistence import AsyncPostgresPersistence
from aimods_bot.src.core.customcontext import CustomContext, BotData, ChatData, UserData
from aimods_bot.src.core.setup import set_application_data
from aimods_bot.src.core.shutdown import post_shutdown
from aimods_bot.src.handlers.conversation_handlers import main_private_conversation_handler, close_menu_handler
from aimods_bot.src.handlers.join_request import build_join_request_handler
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import ConfigError

from aimods_bot.src.helpers.miniapp_server import start_miniapp_server, stop_miniapp_server
from aimods_bot.src.helpers.utils.botapi_10_1 import assert_bridge_still_needed
from aimods_bot.src.helpers.utils.join_request_sweeper import schedule_sweeper

locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

log = logger.getChild(__name__)


def main():
    log.info(f"Codice in esecuzione: GIT_SHA={os.getenv('GIT_SHA', 'unknown')}")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        log.error("BOT_TOKEN not set. Exiting...")
        sys.exit(1)

    miniapp_url = os.getenv("MINIAPP_URL", "https://app.aimodsitalia.store/")
    log.info(f"Mini App URL: {miniapp_url}")

    persistence = AsyncPostgresPersistence(
        url=os.getenv("POSTGRES_CONNECTION_URL"),
        on_flush=False,
        coalesce_delay=0.1
    )

    context_types = ContextTypes(context=CustomContext, bot_data=BotData, chat_data=ChatData, user_data=UserData)

    async def post_init_hook(app):
        await persistence.initialize()  # crea pool + carica dati nel loop PTB
        await set_application_data(app)
        assert_bridge_still_needed()
        schedule_sweeper(app)
        # Per ultimo: non accettare traffico prima che bot_data sia caricato.
        await start_miniapp_server(app, bot_token)

    async def post_shutdown_hook(app):
        # Prima cosa: smettere di accettare richieste HTTP, poi chiudere il resto.
        try:
            await stop_miniapp_server()
        except Exception:
            log.exception("Errore fermando il listener Mini App, proseguo")
        await post_shutdown(app)
        await persistence.aclose()

    application = (
        ApplicationBuilder()
        .token(bot_token)
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .context_types(context_types=context_types)
        .post_init(post_init_hook)
        .post_shutdown(post_shutdown_hook)
        .build()
    )

    handlers = [main_private_conversation_handler, close_menu_handler]
    application.add_handlers(handlers)
    application.add_handler(build_join_request_handler(miniapp_url), group=-1)

    run_mode = os.getenv("RUN_MODE", "webhook")
    drop_pending = os.getenv("DROP_PENDING_UPDATES", "false").lower() == "true"

    log.info(f"Booting in {run_mode} mode (drop_pending_updates={drop_pending})...")

    try:
        if run_mode == "polling":
            application.run_polling(drop_pending_updates=drop_pending)
        else:
            webhook_url = os.getenv("WEBHOOK_URL")
            if not webhook_url:
                log.error("WEBHOOK_URL not set or not found. Exiting...")
                sys.exit(1)

            webhook_secret = os.getenv("WEBHOOK_SECRET_TOKEN")
            if run_mode != "polling" and not webhook_secret:
                log.error("WEBHOOK_SECRET_TOKEN not set or not found. Add it in the .env file. Exiting...")
                sys.exit(1)

            url_path = urlparse(webhook_url).path.strip("/")
            log.info(f"Webhook: {webhook_url} (url_path={url_path!r})")

            application.run_webhook(
                listen="0.0.0.0",
                port=int(os.getenv("PORT", "8080")),
                url_path=url_path,
                webhook_url=webhook_url,
                drop_pending_updates=drop_pending,
                secret_token=webhook_secret
            )
        r = application.bot_data.restart
        if r and r.toggle:
            application.bot_data.restart.toggle = False
            os.execl(sys.executable, sys.executable, *sys.argv)
    except ConfigError as e:
        log.error(f"Config validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

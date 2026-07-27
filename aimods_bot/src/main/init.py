import os
import locale
import sys
from telegram.ext import ApplicationBuilder, ContextTypes
from aimods_bot.src.core.async_persistence import AsyncPostgresPersistence
from aimods_bot.src.core.customcontext import CustomContext, BotData, ChatData, UserData
from aimods_bot.src.core.setup import set_application_data
from aimods_bot.src.core.shutdown import post_shutdown
from aimods_bot.src.handlers.conversation_handlers import main_private_conversation_handler, close_menu_handler
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import ConfigError

locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

log = logger.getChild(__name__)


def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        log.error("BOT_TOKEN non impostato")
        sys.exit(1)

    persistence = AsyncPostgresPersistence(
        url=os.getenv("POSTGRES_CONNECTION_URL"),
        on_flush=False,
        coalesce_delay=0.1
    )

    context_types = ContextTypes(context=CustomContext, bot_data=BotData, chat_data=ChatData, user_data=UserData)

    async def post_init_hook(app):
        await persistence.initialize()  # crea pool + carica dati nel loop PTB
        await set_application_data(app)

    async def post_shutdown_hook(app):
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

    run_mode = os.getenv("RUN_MODE", "webhook")
    drop_pending = os.getenv("DROP_PENDING_UPDATES", "false").lower() == "true"

    log.info(f"Avvio in modalità {run_mode} (drop_pending_updates={drop_pending})")

    try:
        if run_mode == "polling":
            application.run_polling(drop_pending_updates=drop_pending)
        else:
            application.run_webhook(
                listen="0.0.0.0",
                port=int(os.getenv("PORT", "8080")),
                url_path="bot",
                webhook_url=os.getenv("WEBHOOK_URL", "https://bot.aimodsitalia.store/bot"),
                drop_pending_updates=drop_pending
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

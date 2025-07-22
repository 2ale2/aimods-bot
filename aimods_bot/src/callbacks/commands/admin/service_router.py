from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.commands.admin.echo import echo, handle_media_group
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.user_utils import is_admin

log = logger.getChild("service_router")

action_map = {
    "annuncio": echo,
    "echo": echo
}


async def service_command_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.media_group_id:
        return await handle_media_group(update=update, context=context)

    text = update.effective_message.text or update.effective_message.caption

    await safe_delete(update, context)
    cmd = text.split()[0][1:].lower()

    # ⛔ Solo admin/moderatori
    if not await is_admin(update.effective_user.id, context):
        return await send_temporary_message(update, context, "⛔ Solo gli admin possono usare questo comando.")

    if cmd not in action_map:
        return await send_private_alert(update, context, "❌ Comando non riconosciuto.")

    await action_map[cmd](update, context, text)

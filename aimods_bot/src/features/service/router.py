from telegram import Update

from aimods_bot.src.features.service.echo import echo, handle_media_group
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.infra.scheduling.job_queue import send_temporary_message
from aimods_bot.src.infra.log import logger
from aimods_bot.src.ui.alerts import send_private_alert
from aimods_bot.src.infra.telegram.utils import safe_delete
from aimods_bot.src.infra.telegram.auth import is_admin

log = logger.getChild("service_router")

action_map = {
    "annuncio": echo,
    "echo": echo
}


async def service_command_router(update: Update, context: CustomContext):
    if update.message.media_group_id:
        return await handle_media_group(update=update, context=context)

    text = update.effective_message.text or update.effective_message.caption

    await safe_delete(update, context)
    cmd = text.split()[0][1:].lower()

    # ⛔ Solo admin/moderatori
    if not is_admin(update.effective_user.id, context):
        return await send_temporary_message(
            update=update,
            context=context,
            recipient_id=None,
            text="⛔ Solo gli admin possono usare questo comando."
        )

    if cmd not in action_map:
        return await send_private_alert(update, context, "❌ Comando non riconosciuto.")

    await action_map[cmd](update, context, text)

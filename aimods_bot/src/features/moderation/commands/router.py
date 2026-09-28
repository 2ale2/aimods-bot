from telegram import Update
from aimods_bot.src.features.moderation.commands.ban import ban_user, unban_user
from aimods_bot.src.features.moderation.commands.kick import kick_user
from aimods_bot.src.features.moderation.commands.limit import limit_user
from aimods_bot.src.callbacks.commands.admin.warn import warn_user, unwarn_user
from aimods_bot.src.features.moderation.commands.mute import mute_user, unmute_user
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.ui.alerts import send_private_alert
from aimods_bot.src.infra.telegram.utils import safe_delete
from aimods_bot.src.infra.telegram.auth import is_admin
from aimods_bot.src.infra.scheduling.job_queue import send_temporary_message

action_map = {
    "ban": ban_user,
    "unban": unban_user,
    "kick": kick_user,
    "warn": warn_user,
    "unwarn": unwarn_user,
    "limit": limit_user,
    "unlimit": limit_user,
    "mute": mute_user,
    "unmute": unmute_user
}


async def moderation_command_router(update: Update, context: CustomContext):
    await safe_delete(update, context)
    cmd_raw = update.effective_message.text.split()[0][1:].lower()

    delete_flag = False
    if cmd_raw.startswith("del"):
        delete_flag = True
        cmd = cmd_raw.removeprefix("del")
        command = update.effective_message.text.replace(cmd_raw, cmd)
    else:
        cmd = cmd_raw
        command = update.effective_message.text

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

    await action_map[cmd](update, context, command, delete_flag=delete_flag)

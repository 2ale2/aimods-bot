from telegram import Update
from telegram.ext import ContextTypes
from aimods_bot.src.callbacks.commands.admin.ban import ban_user, unban_user
from aimods_bot.src.callbacks.commands.admin.kick import kick_user
from aimods_bot.src.callbacks.commands.admin.warn import warn_user
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.user_utils import is_admin
from aimods_bot.src.helpers.job_queue import send_temporary_message

action_map = {
    "ban": ban_user,
    "unban": unban_user,
    "kick": kick_user,
    "warn": warn_user
}


async def moderation_command_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_delete(update, context)
    cmd_raw = update.effective_message.text.split()[0][1:].lower()

    delete_flag = False
    if cmd_raw.startswith("del"):
        delete_flag = True
        cmd = cmd_raw.removeprefix("del")
    else:
        cmd = cmd_raw

    # ⛔ Solo admin/moderatori
    if not await is_admin(update.effective_user.id, context):
        return await send_temporary_message(update, context, "⛔ Solo gli admin possono usare questo comando.")

    if cmd not in action_map:
        return await send_private_alert(update, context, "❌ Comando non riconosciuto.")

    await action_map[cmd](update, context, update.message.text, delete_flag=delete_flag)

from telegram import Update
from telegram.ext import CallbackContext
from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("antispam_handler")


async def toggle_antispam(update: Update, context: CallbackContext):
    bool_value = update.callback_query.data.split("_")[-1] == "on"
    log.info(f"Antispam {'acceso' if bool_value else 'spento'} "
             f"da {update.message.from_user.first_name} ({update.message.from_user.id})")
    set_value(context=context, path="moderation.antispam.toggle", value=bool_value)

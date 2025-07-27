from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("antispam_mention_per_message")

async def set_per_message(update: Update, context: CallbackContext, value: int):
    set_value(context=context, path="moderation.antispam.mention.per_message", value=value)
    log.info(f"Menzioni per Messaggio Settato a {value} menzioni da {update.message.from_user.id}")

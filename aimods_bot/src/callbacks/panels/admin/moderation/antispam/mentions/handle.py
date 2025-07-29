from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.loggers import logger

map_to_word = {
    "user": "Utenti",
    "group": "Gruppi",
    "channel": "Canali",
    "bot": "Bot"
}


async def set_per_message(update: Update, context: CallbackContext, value: int):
    log = logger.getChild("antispam_mention_per_message")
    set_value(context=context, path="moderation.antispam.mention.per_message", value=value)
    log.info(f"Menzioni per Messaggio Settato a {value} menzioni da {update.effective_user.id}")


async def set_category_toggle(update: Update, context: CallbackContext, category: str, value: bool):
    log = logger.getChild("antispam_mention_category")
    set_value(context=context, path=f"moderation.antispam.mention.{category}", value=value)
    log.info(f"Antispam: controllo menzioni categoria {category} modificato in '{value}' da {update.effective_user.id}")

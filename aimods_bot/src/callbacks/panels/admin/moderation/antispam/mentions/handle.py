from telegram import Update

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger

map_to_word = {
    "user": "Utenti",
    "group": "Gruppi",
    "channel": "Canali",
    "bot": "Bot"
}


async def set_per_message(update: Update, context: CustomContext, value: int):
    log = logger.getChild("antispam_mention_per_message")
    set_value(context=context, path="moderation.antispam.mention.per_message", value=value)
    log.info(f"Menzioni per Messaggio Settato a {value} menzioni da {update.effective_user.id}")

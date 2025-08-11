from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.loggers import logger


async def set_if_not_member(update: Update, context: CallbackContext, category: str, value: bool):
    log = logger.getChild("antispam_forward_category_if_not_member")
    set_value(context=context, path=f"moderation.antispam.forward.{category}.if", value=value)
    log.info(f"Antispam: controllo menzioni inoltro {category} modificato in '{value}' da {update.effective_user.id}")

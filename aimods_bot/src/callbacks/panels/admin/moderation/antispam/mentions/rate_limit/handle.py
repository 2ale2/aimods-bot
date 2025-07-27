from typing import Literal, Union
from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("antispam_mention_rate_limit")


async def set_antispam_mention_rate_limit(
        update: Update,
        context: CallbackContext,
        setting: Literal['time', 'mention', 'toggle'],
        value: Union[int, bool]
):
    user_id = update.effective_user.id
    if setting == 'time':
        log.info(f"Tempo Antispam Mention Rate Limit impostato a {value} secondi da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.time", value=int(value))
    elif setting == 'mention':
        log.info(f"Menzioni Antispam Mention Rate Limit impostato a {value} menzioni da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.mention", value=int(value))
    else:  # setting == 'toggle'
        log.info(f"Toggle Antispam Mention Rate Limit impostato a {value} da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.toggle", value=value)

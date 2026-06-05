from telegram import Update

from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.moderation import ModerationSettingRoute
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


async def set_antispam_mention_rate_limit(
        update: Update,
        context: CustomContext,
        setting: ModerationSettingRoute,
        value: int | bool
):
    user_id = update.effective_user.id
    if setting == ModerationSettingRoute.TIME:
        log.info(f"Tempo Antispam Mention Rate Limit impostato a {value} secondi da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.time", value=int(value))
    elif setting == ModerationSettingRoute.MENTION:
        log.info(f"Menzioni Antispam Mention Rate Limit impostato a {value} menzioni da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.mention", value=int(value))
    elif setting == ModerationSettingRoute.TOGGLE:
        log.info(f"Toggle Antispam Mention Rate Limit impostato a {value} da {user_id}")
        set_value(context=context, path="moderation.antispam.mention.rate_limit.toggle", value=value)
    else:
        raise ValueError(f"Invalid setting: {setting}")

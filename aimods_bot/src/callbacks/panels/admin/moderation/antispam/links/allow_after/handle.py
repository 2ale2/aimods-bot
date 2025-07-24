from telegram.ext import CallbackContext
from aimods_bot.src.core.config_accessor import set_value


async def set_antispam_link_allow_after(context: CallbackContext, raw_value: str):
    raw_split = raw_value.split("_")
    match raw_split[-1]:
        case "off":
            value = 0
        case "min":
            value = int(raw_split[0]) * 60
        case "hour":
            value = int(raw_split[0]) * 60 * 60
        case "day":
            value = int(raw_split[0]) * 60 * 60 * 24
        case _:
            value = 60 * 60 * 24 * 7

    set_value(context=context, path="moderation.antispam.link.allow_after", value=value)

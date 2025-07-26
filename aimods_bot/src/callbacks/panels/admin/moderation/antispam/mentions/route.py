from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.render import render_antispam_mention_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_mention_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_mention_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "allow_after":
            return await antispam_link_allow_after_route(
                update=update,
                context=context,
                setting="antispam/mention",
                path=path[1:]
            )
        case "rate_limit":
            await not_implemented_yet(update=update, context=context)
        case "user":
            await not_implemented_yet(update=update, context=context)
        case "group":
            await not_implemented_yet(update=update, context=context)
        case "channel":
            await not_implemented_yet(update=update, context=context)
        case "bot":
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
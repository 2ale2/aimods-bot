from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.handle import set_per_message
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.route import \
    antispam_mentions_rate_limit_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.render import render_antispam_mention_panel, \
    render_antispam_mention_per_message_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_mention_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_mention_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "allow_after":
            if len(path) == 1:
                return await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/mention",
                    path=path[1:]
                )
            else:
                await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/mention",
                    path=path[1:]
                )
                await render_antispam_mention_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION
        case "rate_limit":
            return await antispam_mentions_rate_limit_route(update=update, context=context, path=path[1:])
        case "user":
            await not_implemented_yet(update=update, context=context)
        case "per_message":
            if len(path) > 1:
                await set_per_message(update=update, context=context, value=int(path[1]))
            await render_antispam_mention_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "group":
            await not_implemented_yet(update=update, context=context)
        case "channel":
            await not_implemented_yet(update=update, context=context)
        case "bot":
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
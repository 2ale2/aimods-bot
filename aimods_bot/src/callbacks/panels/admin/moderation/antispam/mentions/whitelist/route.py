from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.render import \
    render_antispam_mention_whitelist_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.whitelist.handle import edit_whitelist_pre_step, \
    view_mention_whitelist, remove_from_category_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.whitelist.render import \
    render_antispam_mention_whitelist_view_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def antispam_mention_whitelist_backer(update: Update, context: CallbackContext):
    message_id = context.chat_data["editing_mention_whitelist"]["message_id"]
    await safe_delete(update=update, context=context, message_id=message_id)
    del context.chat_data["editing_mention_whitelist"]
    await safe_delete(update=update, context=context)
    return await antispam_mention_whitelist_route(update=update, context=context, path=[], send=True)


async def antispam_mention_whitelist_route(update: Update, context: CallbackContext, path: list[str], send: bool = False):
    if len(path) == 0:
        await render_antispam_mention_whitelist_panel(update=update, context=context, send=send)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "view":
            if len(path) > 1:
                return await view_mention_whitelist(update=update, context=context, category=path[1])
            await render_antispam_mention_whitelist_view_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "add":
            return await edit_whitelist_pre_step(update=update, context=context, action="add")
        case "remove":
            if len(path) > 1:
                return await remove_from_category_whitelist(update=update, context=context, category=path[1])
            return await edit_whitelist_pre_step(update=update, context=context, action="remove")

from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import view_whitelist, \
    edit_whitelist_pre_step, remove_from_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.render import render_antispam_whitelist_panel, \
    render_antispam_whitelist_view_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_whitelist_route(update: Update, context: CallbackContext, path: list[str], send: bool = False):
    if len(path) == 0:
        await render_antispam_whitelist_panel(update=update, context=context, send=send)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "view":
            if len(path) > 1:
                return await view_whitelist(update=update, context=context, category=path[1])
            await render_antispam_whitelist_view_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "add":
            return await edit_whitelist_pre_step(update=update, context=context, action="add")
        case "remove":
            if len(path) > 1:
                return await remove_from_whitelist(update=update, context=context, category=path[1])
            return await edit_whitelist_pre_step(update=update, context=context, action="remove")

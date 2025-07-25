from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import view_list, edit_list
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.render import render_antispam_links_list_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_links_list_route(update: Update, context: CallbackContext, l: str, path: list[str]):
    if len(path) == 0:
        await render_antispam_links_list_panel(update=update, context=context, l=l)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "view":
            return await view_list(update=update, context=context, l=l)
        case "add":
            return await edit_list(update=update, context=context, l=l, action="add")
        case "remove":
            return await edit_list(update=update, context=context, l=l, action="remove")

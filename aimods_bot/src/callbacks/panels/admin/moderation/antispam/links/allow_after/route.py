from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.allow_after.handle import \
    set_antispam_link_allow_after
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.allow_after.render import \
    render_antispam_links_allow_after_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_antispam_links_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_link_allow_after_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_links_allow_after_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    await set_antispam_link_allow_after(context=context, raw_value=path[-1])
    await render_antispam_links_panel(update=update, context=context)
    return PCS.ADMIN_CONVERSATION

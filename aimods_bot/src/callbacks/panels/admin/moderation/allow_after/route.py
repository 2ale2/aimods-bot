from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.handle import set_antispam_link_allow_after
from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.render import render_allow_after_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder


async def antispam_link_allow_after_route(
        update: Update,
        context: CustomContext,
        setting: str,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_allow_after_panel(update=update, context=context, setting=setting)
        case [raw_value]:
            await set_antispam_link_allow_after(context=context, setting=setting, raw_value=raw_value)

    return PCS.ADMIN_CONVERSATION

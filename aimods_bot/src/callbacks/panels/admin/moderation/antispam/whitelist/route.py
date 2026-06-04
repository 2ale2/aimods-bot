from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import view_whitelist, \
    edit_whitelist_pre_step, remove_from_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.render import render_antispam_whitelist_panel, \
    render_antispam_whitelist_view_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.path_navigation import ModerationListsRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def antispam_whitelist_backer(update: Update, context: CustomContext):
    message_id = context.chat_data["editing_antispam_whitelist"]["message_id"]
    await safe_delete(update=update, context=context, message_id=message_id)
    del context.chat_data["editing_antispam_whitelist"]
    await safe_delete(update=update, context=context)
    return await antispam_whitelist_route(update=update, context=context, root=[], send=True)


async def antispam_whitelist_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        send: bool = False
):
    match relative_path.segments:
        case []:
            await render_antispam_whitelist_panel(update=update, context=context, send=send)
        case [ModerationListsRoute.VIEW, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    await render_antispam_whitelist_view_panel(update=update, context=context)
                case [category, *rest] if category in ChatType:  # *rest potrebbe non servire, così come from_category
                    return await view_whitelist(update=update, context=context, category=category)

        case [ModerationListsRoute.ADD, *rest]:
            return await edit_whitelist_pre_step(update=update, context=context, action="add")

        case [ModerationListsRoute.REMOVE, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    return await edit_whitelist_pre_step(update=update, context=context, action="remove")
                case [category, *rest] if category in ChatType:
                    return await remove_from_whitelist(update=update, context=context, category=root[1])

    return PCS.ADMIN_CONVERSATION

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


async def antispam_whitelist_backer(update: Update, context: CustomContext, root: PathBuilder):
    message_id = context.chat_data["editing_antispam_whitelist"]["message_id"]
    await safe_delete(update=update, context=context, message_id=message_id)
    del context.chat_data["editing_antispam_whitelist"]
    await safe_delete(update=update, context=context)
    return await antispam_whitelist_route(
        update=update,
        context=context,
        root=root,
        relative_path=PathBuilder(),
        send=True
    )


async def antispam_whitelist_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        send: bool = False
):
    match relative_path.segments:
        case []:
            await render_antispam_whitelist_panel(update=update, context=context, base_path=root, send=send)
        case [ModerationListsRoute.VIEW, *rest]:
            root = root.add(ModerationListsRoute.VIEW)
            match PathBuilder(*rest).segments:
                case []:
                    await render_antispam_whitelist_view_panel(update=update, context=context, base_path=root)
                case [chat_type_str, *rest] if chat_type_str in ChatType:  # *rest potrebbe non servire, così come from_category
                    root = root.add(chat_type_str)
                    chat_type = ChatType(chat_type_str)
                    return await view_whitelist(
                        update=update,
                        context=context,
                        base_path=root,
                        chat_type=chat_type
                    )

        case [ModerationListsRoute.ADD, *rest]:
            root = root.add(ModerationListsRoute.ADD)
            return await edit_whitelist_pre_step(
                update=update,
                context=context,
                base_path=root,
                action=ModerationListsRoute.ADD
            )

        case [ModerationListsRoute.REMOVE, *rest]:
            root = root.add(ModerationListsRoute.REMOVE)
            match PathBuilder(*rest).segments:
                case []:
                    return await edit_whitelist_pre_step(
                        update=update,
                        context=context,
                        base_path=root,
                        action=ModerationListsRoute.REMOVE
                    )
                case [chat_type_str, *rest] if chat_type_str in ChatType:
                    root = root.add(chat_type_str)
                    chat_type = ChatType(chat_type_str)
                    return await remove_from_whitelist(
                        update=update,
                        context=context,
                        base_path=root,
                        chat_type=chat_type
                    )

    return PCS.ADMIN_CONVERSATION

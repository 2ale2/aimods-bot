from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import view_list, edit_list
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.render import render_antispam_links_list_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ModerationList
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import ModerationListsRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


async def antispam_links_list_route(
        update: Update,
        context: CustomContext,
        list_type: ModerationList,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_antispam_links_list_panel(
                update=update,
                context=context,
                base_path=root,
                list_type=list_type
            )
            return PCS.ADMIN_CONVERSATION
        case [ModerationListsRoute.VIEW]:
            root.add(ModerationListsRoute.VIEW)
            return await view_list(
                update=update,
                context=context,
                base_path=root,
                list_type=list_type
            )
        case [ModerationListsRoute.ADD]:
            root.add(ModerationListsRoute.ADD)
            return await edit_list(
                update=update,
                context=context,
                base_path=root,
                list_type=list_type,
                action=ModerationListsRoute.ADD
            )
        case [ModerationListsRoute.REMOVE]:
            root.add(ModerationListsRoute.REMOVE)
            return await edit_list(
                update=update,
                context=context,
                base_path=root,
                list_type=list_type,
                action=ModerationListsRoute.REMOVE
            )

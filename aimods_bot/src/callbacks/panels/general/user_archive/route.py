from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.render import render_user_archive_request_identifier_panel, \
    render_user_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRoute
from aimods_bot.src.helpers.models.routing import PathBuilder

from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def route_user_archive(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            if root.segments[0] == AdminRoute.ROOT:
                context.pydc.persistent.bot_message_id = update.effective_message.message_id
                await render_user_archive_request_identifier_panel(
                    update=update,
                    context=context,
                    base_path=root
                )
                return PCS.SET_USER_FOR_REQUEST_ARCHIVE
            else:  # root.segments[0] == UserRoute.ROOT
                await render_user_archive_panel(
                    update=update,
                    context=context,
                    base_path=root,
                    user_id=update.effective_user.id,
                    requested_by_admin=False
                )
                return PCS.USER_CONVERSATION

        case [identifier]:
            pass

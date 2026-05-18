from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.render import render_user_archive_request_identifier_panel, \
    render_user_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRoute
from aimods_bot.src.helpers.models.routing import PathBuilder

from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import wrong_input_message, render_action_not_permitted_panel
from aimods_bot.src.helpers.utils.user_utils import resolve_user_from_identifier, is_admin
from aimods_bot.src.helpers.loggers import logger


log = logger.getChild(__name__)


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
            if root.segments[0] != AdminRoute.ROOT:
                # lo user non è admin (non dovrebbe finire qua)
                await render_action_not_permitted_panel(
                    update=update,
                    context=context,
                    base_path=relative_path.back()
                )
                log.warning(
                    f"User {update.effective_user.id} attempted to download request archive of {identifier}. "
                    "Action was not permitted."
                )
                return PCS.USER_CONVERSATION
            resolved_user = await resolve_user_from_identifier(identifier=identifier)

            if resolved_user is None:
                # utente non trovato
                await wrong_input_message(
                    update=update,
                    context=context,
                    correct_message="Manda un <b>identificatore esistente</b> (Username o ID numerico)."
                )
                return PCS.SET_USER_FOR_REQUEST_ARCHIVE

            user_id = resolved_user if isinstance(resolved_user, int) else resolved_user.id

            # nel path sempre uno user id
            relative_path.change(identifier, str(user_id))

            await render_user_archive_panel(
                update=update,
                context=context,
                base_path=root,
                user_id=user_id,
                requested_by_admin=True
            )
            return PCS.ADMIN_CONVERSATION

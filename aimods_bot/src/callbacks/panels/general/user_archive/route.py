from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.render import render_user_archive_request_identifier_panel, \
    render_user_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import wrong_input_message, render_action_not_permitted_panel, \
    safe_delete, is_user_id
from aimods_bot.src.helpers.utils.user_utils import resolve_user_from_identifier, is_admin

log = logger.getChild(__name__)


async def route_user_archive(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            if await is_admin(user_id=update.effective_chat.id, context=context):
                context.pydc.persistent.bot_message_id = update.effective_message.message_id
                await render_user_archive_request_identifier_panel(
                    update=update,
                    context=context,
                    base_path=root
                )
                return PCS.SET_USER_FOR_REQUEST_ARCHIVE
            else:
                await render_user_archive_panel(
                    update=update,
                    context=context,
                    base_path=root,
                    user_id=update.effective_user.id,
                    requested_by_admin=False
                )
                return PCS.USER_CONVERSATION

        case [identifier]:
            if not await is_admin(user_id=update.effective_chat.id, context=context):
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

            if isinstance(resolved_user, str) and is_user_id(resolved_user):
                resolved_user = int(resolved_user)

            user_id = resolved_user if isinstance(resolved_user, int) else resolved_user.id

            await render_user_archive_panel(
                update=update,
                context=context,
                base_path=root,
                user_id=user_id,
                requested_by_admin=True
            )
            return PCS.ADMIN_CONVERSATION


async def handle_user_archive_user_input(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context, message_id=update.message.message_id)

    identifier = update.message.text
    base = PathBuilder.from_string(context.pydc.persistent.root_path)
    context.clear_saved_path(clear_relative=False)

    return await route_user_archive(
        update=update,
        context=context,
        root=base,
        relative_path=PathBuilder(identifier)
    )

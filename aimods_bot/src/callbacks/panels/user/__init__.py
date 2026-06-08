from telegram import Update
from telegram.ext import InvalidCallbackData

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.user.request.route import requests_management_route
from aimods_bot.src.callbacks.panels.user.settings_management.route import user_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import UserRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.user_utils import check_auth

log = logger.getChild(__name__)


@check_auth()
async def user_main_router(update: Update, context: CustomContext):
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    # log.info(f"{c_data} (user: {update.effective_user.id})")

    # if c_data == "reset_conversation":
    #     await update.effective_message.edit_text(
    #         text="🔄 <b>Conversation has been reset.</b>\n\n"
    #              "🔹 Chiudi questo messaggio e prova a riavviare la conversazione.",
    #         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]]),
    #         parse_mode=ParseMode.HTML
    #     )
    #     log.info(f"Conversation for user {update.effective_user.id} has been reset.")
    #     return ConversationHandler.END

    if isinstance(c_data, InvalidCallbackData):
        log.warning(f"Data from user {update.effective_user.id} was invalid! Data: {c_data}. "
                    f"I'll restart the conversation.")
        return await start(update=update, context=context)

    if c_data is None:
        raise ValueError("Callback data must not be None!")

    path = PathBuilder.from_string(c_data)

    if len(path) == 1:
        return await start(update=update, context=context)

    path.pop(0)
    try:
        match path.segments:
            case [main_route_el, *sub_path] if main_route_el in (UserRoute.ADD_REQUEST, UserRoute.VIEW_REQUESTS):
                return await requests_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(UserRoute.ROOT),
                    relative_path=PathBuilder(main_route_el, *sub_path)
                )
            case [UserRoute.MANAGE_SETTINGS, *sub_path]:
                return await user_settings_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(UserRoute.MANAGE_SETTINGS),
                    relative_path=PathBuilder(*sub_path)
                )
    finally:
        try:
            await update.callback_query.answer()
            context.drop_callback_data(update.callback_query)
        except Exception:
            pass

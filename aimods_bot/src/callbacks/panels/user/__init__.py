from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import InvalidCallbackData, ConversationHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.user.request.route import requests_management_route
from aimods_bot.src.callbacks.panels.user.settings_management.route import user_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.user_utils import check_auth
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


@check_auth()
async def user_main_router(update: Update, context: CustomContext):
    c_data = update.callback_query.data

    if c_data == "reset_conversation":
        await update.effective_message.edit_text(
            text="🔄 <b>Conversation has been reset.</b>\n\n"
                 "🔹 Chiudi questo messaggio e prova a riavviare la conversazione.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]]),
            parse_mode=ParseMode.HTML
        )
        log.info(f"Conversation for user {update.effective_user.id} has been reset.")
        return ConversationHandler.END

    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    path = c_data.split("/")

    if len(path) == 1:
        return await start(update=update, context=context)

    path.pop(0)
    try:
        if path[0] in ("add_request", "view_requests"):
            return await requests_management_route(update=update, context=context, path=path)
        if path[0] == "manage_settings":
            return await user_settings_management_route(update=update, context=context, path=path[1:])
    finally:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

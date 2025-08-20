from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.request.windows.game_request import request_game_name
from aimods_bot.src.callbacks.panels.user.request_management.request.windows.handle import RequestDataManager
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("windows_request_router")
WRCS = RCS.WindowsRequest

async def request_software_category(update: Update, context: CallbackContext) -> int:
    """Inizia il flusso della conversazione chiedendo la categoria di software"""
    await update.callback_query.answer()

    if update.callback_query.data == "back_category":
        RequestDataManager.cleanup_request(context=context)

    text = ("💻 <b>Nuova Richiesta – Windows</b>\n\n"
            "🔹 Scegli la categoria di software che vorresti richiedere.")

    keyboard = [
        [
            InlineKeyboardButton(text="🕹 Gioco", callback_data="game"),
            InlineKeyboardButton(text="🖌 Adobe", callback_data="adobe")
        ],
        [
            InlineKeyboardButton(text="🎹 DAW", callback_data="daw"),
            InlineKeyboardButton(text="⌨ Altro Software", callback_data="software")
        ],
        [InlineKeyboardButton(text="🔙 Indietro", callback_data="back_main")]
    ]

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return WRCS.SOFTWARE_CATEGORY


async def request_router(update: Update, context: CallbackContext):
    category = update.callback_query.data

    match category:
        case "game":
            RequestDataManager.initialize_request(context=context, platform="windows", game=True)
            return await request_game_name(update=update, context=context)
        case "daw":
            pass
        case "adobe":
            pass
        case "software":
            pass

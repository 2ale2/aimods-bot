from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from aimods_bot.src.callbacks.panels.user.request.handle import RequestDataManager
from aimods_bot.src.callbacks.panels.user.request.render import render_user_request_management_main_panel
from aimods_bot.src.callbacks.panels.user.request.request import request_detail, user_request_check
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS, \
    RequestConversationState as RCS
from aimods_bot.src.helpers.constants.models import Platform, AndroidCategory, WindowsCategory, IOSCategory, \
    MacOSCategory, Category


async def requests_management_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_main_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    match path[0]:
        case "view_requests":
            pass
        case "add_request":
            # Inizializzo una richiesta vuota
            return await user_request_check(update=update, context=context, path=path[1:])


async def request_category(update: Update, context: CallbackContext) -> int:
    """Inizia il flusso della conversazione chiedendo la categoria di software"""
    await update.callback_query.answer()
    if "new_request" not in context.chat_data:
        RequestDataManager.initialize_request(context=context)

    request_data = RequestDataManager.get_request_data(context=context)
    platform = request_data.get_platform()
    if not platform:
        data = update.callback_query.data.split("/")[-1]

        platform = Platform(data)
        RequestDataManager.update_field(context=context, field="platform", value=platform)

    categories = {
        "android": AndroidCategory,
        "windows": WindowsCategory,
        "ios": IOSCategory,
        "macos": MacOSCategory
    }
    category = categories[platform.value]
    category_items = CATEGORY_DETAILS[platform.value]

    if len(category_items) == 1:
        RequestDataManager.update_field(
            context=context,
            field="category",
            value=category(list(category_items.keys())[0])
        )
        return await request_router(update=update, context=context)

    name = PLATFORM_DETAILS[platform.value]['label']
    icon = PLATFORM_DETAILS[platform.value]['icon']
    item = "app" if platform in ("android", "ios") else "software"

    text = (f"{icon} <b>Nuova Richiesta – {name}</b>\n\n"
            f"🔹 Scegli la categoria di {item} che vorresti richiedere.")

    keyboard = []

    for el in category_items:
        label = category_items[el]["label"]
        icon = category_items[el]["icon"]

        if len(keyboard) == 0 or len(keyboard[-1]) == 2:
            keyboard.append([])

        keyboard[-1].append(InlineKeyboardButton(text=f"{icon} {label}", callback_data=el))

    keyboard.append([InlineKeyboardButton(text="🔙 Indietro", callback_data="back_main")])

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return RCS.REQUEST_CATEGORY


async def request_router(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    request_data = RequestDataManager.get_request_data(context=context)

    platform = request_data.get_platform()
    category = request_data.get_category()

    if not category:
        callback_data = update.callback_query.data
        categories = {
            "android": AndroidCategory,
            "windows": WindowsCategory,
            "ios": IOSCategory,
            "macos": MacOSCategory
        }

        category = categories[platform.value](callback_data)
        RequestDataManager.update_field(context=context, field="category", value=category)

    if not is_category_request_allowed(context=context, platform=platform, category=category):
        RequestDataManager.initialize_request(context=context)
        text = ("🔐 <b>Richieste Chiuse</b>\n\n"
                "▪️ Non è al momento possibile formulare nuove richieste per questa categoria.")
        keyboard = [[InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data="user/manage_requests/add_request"
        )]]
        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    return await request_detail(update=update, context=context)


def is_category_request_allowed(context: CallbackContext, platform: Platform, category: Category) -> bool:
    """Verifica se è possibile fare richieste controllando la configurazione."""
    return context.bot_data["configuration"]["settings"]["request"][platform.value][category.value]

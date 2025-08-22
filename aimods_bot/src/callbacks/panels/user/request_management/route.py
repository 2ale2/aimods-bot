from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.handle import RequestDataManager, AndroidCategory, \
    WindowsCategory, IOSCategory, MacOSCategory, Platform, Category
from aimods_bot.src.callbacks.panels.user.request_management.render import render_user_request_management_panel
from aimods_bot.src.callbacks.panels.user.request_management.request import request_detail, user_request_check
from aimods_bot.src.helpers.constants.constants import PLATFORM_ICONS, CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS, \
    RequestConversationState as RCS


async def requests_management_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    match path[0]:
        case "view_requests":
            pass
        case "add_request":
            # Inizializzo una richiesta vuota
            RequestDataManager.initialize_request(context=context)
            return await user_request_check(update=update, context=context, path=path[1:])


async def request_category(update: Update, context: CallbackContext) -> int:
    """Inizia il flusso della conversazione chiedendo la categoria di software"""
    await update.callback_query.answer()
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

    names = {
        "android": "Android",
        "ios": "iOS",
        "windows": "Windows",
        "macos": "MacOS"
    }

    name = names[platform.value]
    icon = PLATFORM_ICONS[platform.value]
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

    return await request_detail(update=update, context=context)

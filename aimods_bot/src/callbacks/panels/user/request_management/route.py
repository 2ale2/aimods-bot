from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.handle import RequestDataManager, AndroidCategory, \
    WindowsCategory, IOSCategory, MacOSCategory, Platform, can_user_request
from aimods_bot.src.callbacks.panels.user.request_management.render import render_user_request_management_panel, \
    render_user_request_panel, render_user_cant_request_panel
from aimods_bot.src.callbacks.panels.user.request_management.request import request_detail
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
            return await user_request_route(update=update, context=context, path=path[1:])


async def request_category(update: Update, context: CallbackContext) -> int:
    """Inizia il flusso della conversazione chiedendo la categoria di software"""
    await update.callback_query.answer()

    request_data = RequestDataManager.get_request_data(context=context)
    platform = request_data.get_platform()

    names = {
        "android": "Android",
        "ios": "iOS",
        "windows": "Windows",
        "macos": "MacOS"
    }

    name = names[platform]
    icon = PLATFORM_ICONS[platform]
    item = "app" if platform in ("android", "ios") else "software"

    text = (f"{icon} <b>Nuova Richiesta – {name}</b>\n\n"
            f"🔹 Scegli la categoria di {item} che vorresti richiedere.")

    keyboard = []
    categories = CATEGORY_DETAILS[platform]
    for el in categories:
        label = categories[el]["label"]
        icon = categories[el]["icon"]

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
    category = update.callback_query.data

    categories = {
        "android": AndroidCategory,
        "windows": WindowsCategory,
        "ios": IOSCategory,
        "macos": MacOSCategory
    }

    category = categories[platform](category)
    RequestDataManager.initialize_request(context=context, platform=Platform(platform), category=category)
    return request_detail(update=update, context=context)


async def user_request_route(update: Update, context: CallbackContext, path=Optional[list[str]]):
    if path is not None and len(path) == 0:
        answer = await can_user_request(update=update, context=context)
        if answer.yn:
            await render_user_request_panel(update=update, context=context)
            return PCS.NEW_REQUEST
        else:
            await render_user_cant_request_panel(update=update, context=context, reason=answer.reason)
            return PCS.USER_CONVERSATION

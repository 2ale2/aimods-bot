from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from aimods_bot.src.callbacks.panels.user.request.handle import RequestDataManager
from aimods_bot.src.callbacks.panels.user.request.management.route import user_request_management_route
from aimods_bot.src.callbacks.panels.user.request.render import (render_user_has_cooldown_panel,
                                                                 render_user_request_panel, render_cant_request_panel)
from aimods_bot.src.callbacks.panels.user.request.request import request_detail
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, Platform, Category, LOCAL_TZ
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS, \
    RequestConversationState as RCS
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


async def requests_management_route(update: Update, context: CustomContext, path: list[str]):
    RequestDataManager.cleanup_request(context=context)

    match path[0]:
        case "view_requests":
            return await user_request_management_route(update=update, context=context, path=path[1:])
        case "add_request":
            if path[-1] == "from_notification":
                return await request_from_notification(update=update, context=context)

            rc = context.user_request_cooldown()
            if rc and update.effective_user.id not in [7233636327, 6540199713]:
                # L'utente ha un cooldown
                await render_user_has_cooldown_panel(update=update, context=context, rc=rc)
                return PCS.USER_CONVERSATION
            if len(path) > 1:
                # expected: ".../add_request/<platform>
                return await request_category(update=update, context=context)

            RequestDataManager.initialize_request(context=context)
            await render_user_request_panel(update=update, context=context)
            return PCS.NEW_REQUEST


async def request_category(update: Update, context: CustomContext) -> int:
    """Inizia il flusso della conversazione chiedendo la categoria di software"""
    await update.callback_query.answer()

    request_data = RequestDataManager.get_request_data(context=context)

    RequestDataManager.update_field(context=context, field="category", value=None)
    RequestDataManager.update_field(context=context, field="requesting", value=None)

    platform = request_data.platform
    if not platform:
        data = update.callback_query.data.split("/")[-1]

        platform = Platform(data)
        RequestDataManager.update_field(context=context, field="platform", value=platform)

    category = get_platform_categories(platform=platform)
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
        log.info(f"Category Keyboard Button -> text: {label} | data: {el}")
        keyboard[-1].append(InlineKeyboardButton(text=f"{icon} {label}", callback_data=el))

    keyboard.append([InlineKeyboardButton(text="🔙 Indietro", callback_data="back_main")])

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return RCS.REQUEST_CATEGORY


async def request_from_notification(update: Update, context: CustomContext):
    rc = context.user_request_cooldown()
    if rc:
        # L'utente ha un cooldown
        await render_user_has_cooldown_panel(update=update, context=context, rc=rc)
        return ConversationHandler.END

    path = update.callback_query.data.split("/")
    pl, ca = path[-3], path[-2]
    platform = Platform(pl)

    RequestDataManager.initialize_request(context=context)
    RequestDataManager.update_field(context=context, field="platform", value=platform)
    RequestDataManager.update_field(context=context, field="category", value=get_platform_categories(platform)(ca))

    return await request_router(update=update, context=context)


async def request_router(update: Update, context: CustomContext):
    await update.callback_query.answer()
    request_data = RequestDataManager.get_request_data(context=context)

    platform = request_data.platform
    category = request_data.category

    if not category:
        callback_data = update.callback_query.data

        category = get_platform_categories(platform)(callback_data)
        RequestDataManager.update_field(context=context, field="category", value=category)

    l = context.is_user_request_limited(platform=platform, category=category)
    if l:
        if l.until:
            until = l.until.replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_TZ)
            until_str = until.strftime('fino al %d %b %Y alle %H:%M:%S')
        else:
            until_str = "a tempo indeterminato"

        if len(l.reasons) == 1:
            reasons_text = "– " + l.reasons[0]
        else:
            reasons_text = "\n"
            for r in l.reasons:
                reasons_text += f"        – {r}\n"
        text = ("⛔ <b>Richieste Bloccate</b>\n\n"
                "<blockquote>ℹ Sei stato bloccato dallo staff: non potrai formulare richieste"
                f" per questa sezione <b>{until_str}</b>.</blockquote>\n\n"
                f"<b>Motivazioni</b> {reasons_text}")
        await render_cant_request_panel(update=update, context=context, message=text)
        return ConversationHandler.END

    if not is_category_request_allowed(context=context, platform=platform, category=category):
        RequestDataManager.initialize_request(context=context)
        text = ("🔐 <b>Richieste Chiuse</b>\n\n"
                "▪️ <b>Non è al momento possibile formulare nuove richieste</b> per questa categoria, perché ha "
                "<b>raggiunto il limite</b> di richieste impostato o perché stato <b>chiuso manualmente</b> "
                "dallo staff.")
        await render_cant_request_panel(update=update, context=context, message=text)
        return ConversationHandler.END

    return await request_detail(update=update, context=context)


def is_category_request_allowed(context: CustomContext, platform: Platform, category: Category) -> bool:
    """Verifica se è possibile fare richieste controllando la configurazione."""
    platform_settings = getattr(context.pydb.configuration.settings.request, platform.value)
    category_config = getattr(platform_settings, str(category.value))
    assert isinstance(category_config, CategorySetting)
    return category_config.toggle

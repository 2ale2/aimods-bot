import os
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from aimods_bot.src.callbacks.panels.user.request.management.route import user_request_management_route
from aimods_bot.src.callbacks.panels.user.request.render import (
    render_user_has_cooldown_panel,
    render_user_request_platform_panel,
    render_cant_request_panel, render_user_request_category_panel, render_global_request_wizard_panel
)
from aimods_bot.src.callbacks.panels.user.request.request import request_detail
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import (
    PLATFORM_DETAILS, CATEGORY_DETAILS, Platform, Category, LOCAL_TZ
)
from aimods_bot.src.helpers.constants.conversation_paths.navigation import UserRoute, NotificationAction as NA
from aimods_bot.src.helpers.constants.conversation_states import (
    PrivateConversationState as PCS,
    RequestConversationState as RCS
)
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.requests import REQUESTS_LAYOUT_REGISTRY
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories

log = logger.getChild(__name__)

BYPASS_LIMITS_USERS = {7233636327, 6540199713}


async def requests_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case [UserRoute.VIEW_REQUESTS, *rest]:
            return await user_request_management_route(
                update=update,
                context=context,
                root=root.add(UserRoute.VIEW_REQUESTS),
                relative_path=PathBuilder(*rest)
            )
        case [UserRoute.ADD_REQUEST, *rest]:
            root.add(UserRoute.ADD_REQUEST)
            match PathBuilder(*rest).segments:
                case []:
                    await render_user_request_platform_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )
                case [NA.FROM_NOTIFICATION, platform, category] if platform in Platform and category in Category:
                    context.init_request_wizard_session(
                        user_id=update.effective_user.id,
                        platform=Platform(platform),
                        category=Category(category),
                        from_notification=True,
                        msg_id=update.effective_message.id
                    )
                    context.pydc.persistent.base_path = root
                    await render_global_request_wizard_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )
                    return PCS.USER_REQUEST_WIZARD_SESSION
                case [platform, *rest] if platform in Platform:
                    root.add(platform)
                    match PathBuilder(*rest).segments:
                        case []:
                            configs_cat = REQUESTS_LAYOUT_REGISTRY[platform]
                            if len(configs_cat) > 1:
                                await render_user_request_category_panel(
                                    update=update,
                                    context=context,
                                    base_path=root,
                                    platform=platform
                                )
                            else:
                                category = list(configs_cat.keys())[0].value()
                                is_bypassed = (update.effective_user.id in BYPASS_LIMITS_USERS)
                                request_cooldown = context.user_request_cooldown()

                                if request_cooldown and not is_bypassed:
                                    await render_user_has_cooldown_panel(
                                        update=update,
                                        context=context,
                                        rc=request_cooldown,
                                        base_path=root
                                    )
                                else:
                                    context.pydc.persistent.base_path = root
                                    context.init_request_wizard_session(
                                        user_id=update.effective_user.id,
                                        platform=Platform(platform),
                                        category=Category(category),
                                        from_notification=False,
                                        msg_id=update.effective_message.id
                                    )
                                    await render_global_request_wizard_panel(
                                        update=update,
                                        context=context,
                                        base_path=root
                                    )
                                    return PCS.USER_REQUEST_WIZARD_SESSION

                        case [category, *rest] if category in Category:
                            root.add(category)
                            match PathBuilder(*rest):
                                case []:
                                    cooldown = context.user_request_cooldown()
                                    is_bypassed = (update.effective_user.id in BYPASS_LIMITS_USERS)

                                    if cooldown and not is_bypassed:
                                        await render_user_has_cooldown_panel(
                                            update=update,
                                            context=context,
                                            rc=cooldown,
                                            base_path=root,
                                        )
                                    else:
                                        context.pydc.persistent.base_path = root
                                        context.init_request_wizard_session(
                                            user_id=update.effective_user.id,
                                            platform=Platform(platform),
                                            category=Category(category),
                                            from_notification=False,
                                            msg_id=update.effective_message.id
                                        )
                                        await render_global_request_wizard_panel(
                                            update=update,
                                            context=context,
                                            base_path=root
                                        )
                                        return PCS.USER_REQUEST_WIZARD_SESSION
                                case _:
                                    log.warning(f"Unhandled path in {os.path.realpath(__file__)}: "
                                                f"{relative_path.build()}")
                        case _:
                            log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")
                case _:
                    log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")
        case _:
            log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")

    return PCS.USER_CONVERSATION


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

    p_details = PLATFORM_DETAILS[platform.value]
    item_type = "app" if platform in (Platform.ANDROID, Platform.IOS) else "software"

    text = (f"{p_details['icon']} <b>Nuova Richiesta – {p_details['label']}</b>\n\n"
            f"🔹 Scegli la categoria di {item_type} che vorresti richiedere.")

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

    return RCS.REQUEST_CATEGORY if update.callback_query.data != "back_category" else RCS.CANCEL_PROCESS


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
    user_id = update.effective_user.id

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

    if not is_category_request_allowed(context=context, platform=platform, category=category) and user_id not in BYPASS_LIMITS_USERS:
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

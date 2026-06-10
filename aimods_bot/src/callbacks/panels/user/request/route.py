import os
from zoneinfo import ZoneInfo

from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.management.route import user_request_management_route
from aimods_bot.src.callbacks.panels.user.request.render import (
    render_user_has_cooldown_panel,
    render_user_request_platform_panel,
    render_user_request_category_panel, render_global_request_wizard_panel, render_cant_request_panel
)
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting, RequestSectionLimitation
from aimods_bot.src.helpers.constants.constants import Platform, LOCAL_TZ, DATETIME_FORMAT, Category
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import UserRoute, NotificationAction as NA
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.models.routing import PathBuilder

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
            root = root.add(UserRoute.ADD_REQUEST)
            match PathBuilder(*rest).segments:
                case []:
                    await render_user_request_platform_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )

                case [NA.FROM_NOTIFICATION, platform_str,
                      category_str] if platform_str in Platform and category_str in Category:
                    platform = Platform(platform_str)
                    category = Category(category_str)
                    context.init_request_wizard_session(
                        user_id=update.effective_user.id,
                        section=RequestSection(platform=platform, category=category),
                        from_notification=True,
                        msg_id=update.effective_message.id
                    )
                    context.pydc.persistent.base_path = root.build()
                    await render_global_request_wizard_panel(
                        update=update,
                        context=context,
                        base_path=root.add(platform, category)
                    )
                    return PCS.USER_REQUEST_WIZARD_SESSION

                case [platform_str, *rest] if platform_str in Platform:
                    platform = Platform(platform_str)
                    root = root.add(platform)
                    match PathBuilder(*rest).segments:
                        case []:
                            configs_cat = PLATFORM_CATEGORY_REGISTRY[platform]
                            if len(configs_cat) > 1:
                                await render_user_request_category_panel(
                                    update=update,
                                    context=context,
                                    base_path=root,
                                    platform=platform
                                )
                            else:
                                category = list(configs_cat.keys())[0]
                                root = root.add(category)
                                section = RequestSection(platform=platform, category=category)
                                return await _enter_wizard_or_explain(
                                    update=update,
                                    context=context,
                                    root=root,
                                    section=section
                                )

                        case [category_str, *rest] if category_str in Category:
                            category = Category(category_str)
                            root = root.add(category)
                            match PathBuilder(*rest).segments:
                                case []:
                                    section = RequestSection(platform=platform, category=category)
                                    return await _enter_wizard_or_explain(
                                        update=update,
                                        context=context,
                                        root=root,
                                        section=section
                                    )

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


def is_category_request_allowed(context: CustomContext, section: RequestSection) -> bool:
    """Verifica se è possibile fare richieste controllando la configurazione."""
    platform_settings = getattr(context.pydb.configuration.settings.request, section.platform.value)
    category_config = getattr(platform_settings, section.category.value)
    assert isinstance(category_config, CategorySetting)
    return category_config.toggle


_CLOSED_MSG = ("🔐 <b>Richieste Chiuse</b>\n\n"
               "▪️ <b>Non è al momento possibile formulare nuove richieste</b> "
               "per questa categoria, perché <b>ha raggiunto il limite</b> di "
               "richieste impostato o perché è stato <b>chiuso manualmente</b> "
               "dallo staff.")


def _blocked_message(limitation: RequestSectionLimitation) -> str:
    if limitation.until:
        until = limitation.until.replace(
            tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_TZ)
        until_str = until.strftime(f"fino al {DATETIME_FORMAT}")
    else:
        until_str = "a tempo indeterminato"

    if len(limitation.reasons) == 1:
        reasons_text = "– " + limitation.reasons[0]
    else:
        reasons_text = "\n"
        for r in limitation.reasons:
            reasons_text += f"        – {r}\n"
    return ("⛔ <b>Richieste Bloccate</b>\n\n"
            "<blockquote>ℹ Sei stato bloccato dallo staff: "
            f"non potrai formulare richieste per questa sezione "
            f"<b>{until_str}</b>.</blockquote>\n\n"
            f"<b>Motivazioni</b> {reasons_text}")


async def _enter_wizard_or_explain(update: Update, context: CustomContext, section: RequestSection, root: PathBuilder):
    if not is_category_request_allowed(context=context, section=section):
        await render_cant_request_panel(update, context, base_path=root, message=_CLOSED_MSG)
        return PCS.USER_CONVERSATION

    cooldown = context.user_request_cooldown()
    if cooldown and update.effective_user.id not in BYPASS_LIMITS_USERS:
        await render_user_has_cooldown_panel(update=update, context=context, rc=cooldown, base_path=root)
        return PCS.USER_CONVERSATION

    limitation = context.is_user_request_limited(section=section)
    if limitation:
        await render_cant_request_panel(
            update=update,
            context=context,
            base_path=root,
            message=_blocked_message(limitation)
        )
        return PCS.USER_CONVERSATION

    context.pydc.persistent.base_path = root.build()
    context.init_request_wizard_session(
        user_id=update.effective_user.id,
        section=section,
        from_notification=False,
        msg_id=update.effective_message.id,
    )
    await render_global_request_wizard_panel(update=update, context=context, base_path=root)
    return PCS.USER_REQUEST_WIZARD_SESSION

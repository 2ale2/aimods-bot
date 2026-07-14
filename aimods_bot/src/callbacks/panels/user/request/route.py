import os
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.management.route import user_request_management_route
from aimods_bot.src.callbacks.panels.user.request.render import (
    render_user_has_cooldown_panel,
    render_user_request_platform_panel,
    render_user_request_category_panel, render_global_request_wizard_panel, render_cant_request_panel,
    render_section_notification_activated_panel, render_user_has_an_active_request_wizard_panel
)
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting, RequestSectionLimitation
from aimods_bot.src.helpers.constants.constants import Platform, LOCAL_TZ, DATETIME_FORMAT, Category
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import UserRoute, NotificationAction as NA, \
    UserManageRequestsRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem

log = logger.getChild(__name__)

BYPASS_LIMITS_USERS = {7233636327, 6540199713}


async def user_requests_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match root.segments[0]:
        case UserRoute.VIEW_REQUESTS:
            return await user_request_management_route(
                update=update,
                context=context,
                root=root,
                relative_path=relative_path
            )

        case UserRoute.ADD_REQUEST:
            match relative_path.segments:
                case []:
                    await render_user_request_platform_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )

                case [NA.FROM_NOTIFICATION, section_str]:
                    try:
                        section = RequestSection.from_string(section_str)
                    except (ValueError, ValidationError):
                        log.warning(f"Invalid Section input: {section_str}")
                        return PCS.USER_CONVERSATION

                    root = root.add(section.platform, section.category)
                    if await _guard_existing_wizard(update=update, context=context, section=section, base_path=root):
                        return PCS.USER_CONVERSATION

                    return await _enter_wizard_or_explain(
                        update=update,
                        context=context,
                        section=section,
                        base_path=root
                    )

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
                                    base_path=root,
                                    section=section
                                )

                        case [category_str, *rest] if category_str in Category:
                            category = Category(category_str)
                            root = root.add(category)

                            section = RequestSection(platform=platform, category=category)
                            match PathBuilder(*rest).segments:
                                case []:
                                    if await _guard_existing_wizard(
                                            update=update,
                                            context=context,
                                            section=section,
                                            base_path=root
                                    ):
                                        return PCS.USER_CONVERSATION

                                    return await _enter_wizard_or_explain(
                                        update=update,
                                        context=context,
                                        section=section,
                                        base_path=root
                                    )

                                case [user_had_wizard] if user_had_wizard in (
                                    UserManageRequestsRoute.CONTINUE_REQUEST,
                                    UserManageRequestsRoute.DISMISS_REQUEST
                                ):
                                    return await _enter_wizard_or_explain(
                                        update=update,
                                        context=context,
                                        base_path=root,
                                        section=section,
                                        new_wizard=(user_had_wizard == UserManageRequestsRoute.DISMISS_REQUEST)
                                    )

                                case [UserManageRequestsRoute.ENABLE_SECTION_NOTIFICATIONS]:
                                    s_o_c = context.pydc.persistent.user_notifications.section_opening_notifications
                                    s_o_c[section.platform][section.category] = True
                                    await render_section_notification_activated_panel(
                                        update=update,
                                        context=context,
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
               "per questa sezione, perché <b>ha raggiunto il limite</b> di "
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


async def _enter_wizard_or_explain(
        update: Update,
        context: CustomContext,
        section: RequestSection,
        base_path: PathBuilder,
        new_wizard: bool = True
):
    cat_num = len(PLATFORM_CATEGORY_REGISTRY[section.platform])
    back_callback = base_path.back(2) if cat_num == 1 else base_path.back()

    if not is_category_request_allowed(context=context, section=section):
        if context.pydc.persistent.user_notifications.section_opening_notifications[section.platform][section.category]:
            text = _CLOSED_MSG + ("\n\nℹ️ <b>Hai già attivato le notifiche di apertura di questa sezione</b>. "
                                  "Riceverai un messaggio da me non appena verrà riaperta.")
            keyboard = []
        else:
            text = _CLOSED_MSG + ("\n\n💡 <b>Attiva le notifiche</b> di questa sezione per ricevere un messaggio "
                                  "<b>non appena la sezione verrà nuovamente aperta</b>.")
            keyboard = [
                [
                    ButtonItem(
                        text="🔔 Attiva Notifiche Sezione",
                        callback_key=base_path.add(UserManageRequestsRoute.ENABLE_SECTION_NOTIFICATIONS)
                    )
                ]
            ]

        keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=back_callback)])
        await render_cant_request_panel(
            update=update,
            context=context,
            back_callback=back_callback,
            message=text,
            kayboard=keyboard
        )
        return PCS.USER_CONVERSATION

    cooldown = context.user_request_cooldown()
    if cooldown and update.effective_user.id not in BYPASS_LIMITS_USERS:
        await render_user_has_cooldown_panel(update=update, context=context, rc=cooldown, back_callback=back_callback)
        return PCS.USER_CONVERSATION

    limitation = context.is_user_request_limited(section=section)
    if limitation:
        await render_cant_request_panel(
            update=update,
            context=context,
            back_callback=back_callback,
            message=_blocked_message(limitation)
        )
        return PCS.USER_CONVERSATION

    context.pydc.persistent.root_path = base_path.build()
    if new_wizard:
        context.init_request_wizard_session(
            user_id=update.effective_user.id,
            section=section,
            from_notification=False,
            msg_id=update.effective_message.id,
        )
    await render_global_request_wizard_panel(update=update, context=context)
    return PCS.USER_REQUEST_WIZARD_SESSION


async def _guard_existing_wizard(
        update: Update,
        context: CustomContext,
        section: RequestSection,
        base_path: PathBuilder,
) -> bool:
    """
    Se esiste già un wizard attivo, mostra il pannello di scelta continua/ricomincia
    e ritorna True (il chiamante deve fermarsi). Altrimenti ritorna False (procedi).
    """
    if context.pydc.persistent.active_request_wizard is not None:
        await render_user_has_an_active_request_wizard_panel(
            update=update,
            context=context,
            base_path=base_path,
            section=section,
        )
        return True
    return False

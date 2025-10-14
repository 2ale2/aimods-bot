import asyncio

from pyrogram.errors import BadRequest
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.core.pydantic import Request, CategorySetting
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, PLATFORM_DETAILS
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild(__name__)


async def send_opening_notifications(context: CustomContext, section: str):
    pl, ca = section.split(":")
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]
    pa_label = PLATFORM_DETAILS[pl]["label"]
    for user_id in context.application.chat_data:
        cd = context.application.chat_data.get(user_id)
        assert isinstance(cd, ChatData)
        pl_settings = cd.persistent.user_notifications.section_opening_notifications.get(pl, None)
        if not pl_settings:
            log.error(f"Unable to check user ChatData: platform '{pl}' does not exist. "
                      f"Skipping all to avoid exception flooding.")
            return
        ca_settings = pl_settings.get(ca, None)
        if ca_settings is None:
            log.error(f"Unable to check user ChatData: category '{ca}' does not exist in platform '{pl}'. "
                      f"Skipping all to avoid exception flooding.")
            return

        if ca_settings:
            deactivate_callback = f"user/manage_settings/notifications/section_opening/{pl}:{ca}/from_notification"
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="📭 <b>Sezione Richieste Aperta!</b>\n\n"
                         f"▫ La sezione {ca_icon} <b>{ca_label}</b> ({pa_label}) è ora aperta!\n\n"
                         "🔹 Scegli un'opzione.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text=f"{ca_icon} Formula Richiesta",
                                    callback_data=f"user/add_request/{pl}/{ca}/from_notification"
                                ),
                            ],
                            [
                                InlineKeyboardButton(
                                    text="🔕 Disattiva Richieste",
                                    callback_data=deactivate_callback
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="🚮 Chiudi",
                                    callback_data="close_menu"
                                )
                            ]
                        ]
                    ),
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(1)
            except BadRequest:
                log.warning(f"Unable to send notification to {user_id} (the user may have blocked the bot).")
            except Exception as e:
                log.error(f"Unable to send notification to {user_id}: {e}")


async def send_new_request_admin_notification(
        update: Update,
        context: CustomContext,
        admin_id: int,
        request: Request
):
    pl, ca = request.platform.value, request.category.value
    text = _get_new_request_admin_notification_text(pl=pl, ca=ca)
    request_id = request.id

    new_request_notification = Panel(
        PanelConfig(
            base_path="admin",
            text=text,
            keyboard=[
                [
                    ButtonItem(
                        text="👁 Visiona",
                        callback_key=f"admin/manage_requests/active_requests/{pl}/{ca}/{request_id}",
                        override_path_generation=True
                    ),
                    ButtonItem(
                        text="🗃 Richieste Attive",
                        callback_key=f"admin/manage_requests/active_requests/{pl}/{ca}",
                        override_path_generation=True
                    )
                ],
                [
                    ButtonItem(
                        text="🔕 Disattiva Notifiche",
                        callback_key=f"admin/manage_settings/notifications/new_requests/{pl}:{ca}/from_notification",
                        override_path_generation=True
                    )
                ],
                [ButtonItem(text="🚮 Guarda Dopo", callback_key="close_menu")]
            ]
        )
    )

    await new_request_notification.render(update=update, context=context, user_id=admin_id)


def _get_new_request_admin_notification_text(pl: str, ca: str) -> str:
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = ("🔔 <b>Nuova Richiesta Ricevuta</b>\n\n"
            "▫ È stata appena aggiunta una <b>nuova richiesta</b> per la sezione\n\n"
            f"            {ca_icon} <b>{ca_label}</b> ({pl_label})\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def send_section_closing_admin_notification(update: Update, context: CustomContext, admin_id: int, section: str):
    pl, ca = section.split(":")
    text = _get_section_closing_admin_notification_text(context=context, pl=pl, ca=ca)

    section_closing_admin_notification = Panel(
        PanelConfig(
            base_path="admin",
            text=text,
            keyboard=[
                [
                    ButtonItem(
                        text="🗃 Richieste Attive",
                        callback_key=f"admin/manage_requests/active_requests/{pl}/{ca}",
                        override_path_generation=True
                    ),
                    ButtonItem(
                        text="🔕 Disattiva Notifiche",
                        callback_key=f"admin/manage_settings/notifications/section_closing/{pl}:{ca}/from_notification",
                        override_path_generation=True
                    )
                ],
                [ButtonItem(text="🚮 Chiudi", callback_key="close_menu")]
            ]
        )
    )

    await section_closing_admin_notification.render(update=update, context=context, user_id=admin_id)


def _get_section_closing_admin_notification_text(context: CustomContext, pl: str, ca: str) -> str:
    config = getattr(getattr(context.pydb.configuration.settings.request, pl), ca)
    assert isinstance(config, CategorySetting)
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = ("🔔 <b>Sezione Chiusa</b>\n\n"
            "<blockquote>ℹ <b>Info</b> – Il <b>limite di richieste</b> per la sezione\n\n"
            f"            {ca_icon} <b>{ca_label}</b> ({pl_label})\n\n"
            f"è stato appena <b>raggiunto</b> "
            f"(<i>{pluralize(config.limit, 'richiesta', 'richieste')}</i>) e tale <b>sezione è stata "
            f"chiusa</b>.</blockquote>\n\n"
            "🔹 Scegli un'opzione.")

    return text

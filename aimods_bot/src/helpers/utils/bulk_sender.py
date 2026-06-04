import asyncio
from time import time

from pyrogram.errors import BadRequest
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, NotificationAction, UserRoute, \
    UserManageSettingsRoute, AdminRoute, AdminRequestsRoute, AdminSettingsRoute, AdminSettingsNotificationsRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import BaseRequest
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild(__name__)


MAX_MESSAGES_PER_SECOND = 20
BATCH_SIZE = 20
BATCH_DELAY = 1.0


async def _send_single_opening_notification(
        context: CustomContext,
        user_id: int,
        section: RequestSection
) -> bool:
    """
    Send opening notification to a single user.

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        cat_config = section.category_config
        await context.bot.send_message(
            chat_id=user_id,
            text="📭 <b>Sezione Richieste Aperta!</b>\n\n"
                 f"▫ La sezione {cat_config.icon} <b>{cat_config.label}</b> "
                 f"({section.platform.label}) è ora aperta!\n\n"
                 "🔹 Scegli un'opzione.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text=f"{cat_config.icon} Formula Richiesta",
                        callback_data=PathBuilder(
                            UserRoute.ROOT,
                            UserRoute.VIEW_REQUESTS,
                            NotificationAction.FROM_NOTIFICATION,
                            section.platform,
                            section.category
                        )
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔕 Disattiva Notifiche Sezione",
                        callback_data=PathBuilder(
                            UserRoute.ROOT,
                            UserRoute.MANAGE_SETTINGS,
                            UserManageSettingsRoute.NOTIFICATIONS,
                            UserManageSettingsRoute.SECTION_OPENING_NOTIFICATIONS,
                            NotificationAction.FROM_NOTIFICATION,
                            section.platform,
                            section.category
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🚮 Chiudi",
                        callback_data=GlobalAction.CLOSE_MENU
                    )
                ]
            ]),
            parse_mode=ParseMode.HTML
        )
        log.debug(f"Opening notification sent successfully to user {user_id} [{str(section)}]")
        return True

    except BadRequest as e:
        log.warning(
            f"Unable to send notification to user {user_id} [{str(section)}] "
            f"(user may have blocked the bot): {e}"
        )
        return False

    except Exception as e:
        log.error(f"Unexpected error sending notification to user {user_id} [{str(section)}]: {type(e).__name__}: {e}")
        return False


async def send_opening_notifications(context: CustomContext, section: RequestSection):
    """Send opening notifications to all subscribed users with rate limiting."""
    start_time = time()

    eligible_users = []
    for user_id in context.application.chat_data:
        cd = context.application.chat_data.get(user_id)
        if not isinstance(cd, ChatData):
            continue

        pl_settings = cd.persistent.user_notifications.section_opening_notifications.get(section.platform)
        if not pl_settings:
            continue

        ca_settings = pl_settings.get(section.category)
        if ca_settings:
            eligible_users.append(user_id)

    if not eligible_users:
        log.info(f"No eligible users for opening notification [{str(section)}]")
        return

    log.info(
        f"Starting opening notification batch for [{str(section)}] - "
        f"{len(eligible_users)} eligible users"
    )

    sent_count = 0
    error_count = 0

    for i in range(0, len(eligible_users), BATCH_SIZE):
        batch = eligible_users[i:i + BATCH_SIZE]
        batch_start = time()

        tasks = [
            _send_single_opening_notification(context=context, user_id=user_id, section=section)
            for user_id in batch
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, bool):
                if result:
                    sent_count += 1
                else:
                    error_count += 1
            else:
                error_count += 1

        batch_num = i // BATCH_SIZE + 1
        batch_sent = sum(1 for r in results if r is True)
        batch_errors = len(batch) - batch_sent
        batch_duration = time() - batch_start

        log.info(
            f"Batch {batch_num} completed: {batch_sent}/{len(batch)} sent, "
            f"{batch_errors} errors, {batch_duration:.2f}s"
        )

        if i + BATCH_SIZE < len(eligible_users):
            await asyncio.sleep(BATCH_DELAY)

    duration = time() - start_time
    msg_per_sec = round(sent_count / duration, 2) if duration > 0 else 0

    log.info(
        f"Opening notification batch completed [{str(section)}]: "
        f"{sent_count}/{len(eligible_users)} sent successfully, "
        f"{error_count} errors, {duration:.2f}s ({msg_per_sec} msg/s)"
    )


async def send_new_request_admin_notification(
        update: Update,
        context: CustomContext,
        admin_id: int,
        request: BaseRequest
):
    """Send notification to admin about new request."""
    text = _get_new_request_admin_notification_text(section=request.section)
    request_id = request.id

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=PathBuilder(AdminRoute.ROOT),
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="👁 Visiona",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_REQUESTS,
                        AdminRequestsRoute.ACTIVE,
                        request.section.platform,
                        request.section.category,
                        str(request_id)
                    )
                ),
                ButtonItem(
                    text="🗃 Richieste Attive",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_REQUESTS,
                        AdminRequestsRoute.ACTIVE,
                        request.section.platform,
                        request.section.category
                    )
                )
            ],
            [
                ButtonItem(
                    text="🔕 Disattiva Notifiche",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_SETTINGS,
                        AdminSettingsRoute.NOTIFICATIONS,
                        AdminSettingsNotificationsRoute.NEW_REQUESTS,
                        NotificationAction.FROM_NOTIFICATION,
                        request.section.platform,
                        request.section.category
                    )
                )
            ],
            [ButtonItem(text="🚮 Guarda Dopo", callback_key=GlobalAction.CLOSE_MENU)]
        ],
        user_id=admin_id
    )


def _get_new_request_admin_notification_text(section: RequestSection) -> str:
    cat_config = section.category_config
    text = ("📬 <b>Nuova Richiesta Ricevuta</b>\n\n"
            "▫ È stata appena aggiunta una <b>nuova richiesta</b> per la sezione\n\n"
            f"            {cat_config.icon} <b>{cat_config.label}</b> ({section.platform.label})\n\n"
            "🔹 Scegli un'opzione.")
    return text


async def send_section_closing_admin_notification(
        update: Update,
        context: CustomContext,
        admin_id: int,
        section: RequestSection
):
    """Send notification to admin about section closing."""
    text = _get_section_closing_admin_notification_text(context=context, section=section)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=PathBuilder(AdminRoute.ROOT),
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="🗃 Richieste Attive",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_REQUESTS,
                        AdminRequestsRoute.ACTIVE,
                        section.platform,
                        section.category
                    )
                ),
                ButtonItem(
                    text="🔕 Disattiva Notifiche",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_SETTINGS,
                        AdminSettingsRoute.NOTIFICATIONS,
                        AdminSettingsNotificationsRoute.SECTION_CLOSING,
                        NotificationAction.FROM_NOTIFICATION,
                        section.platform,
                        section.category
                    )
                )
            ],
            [ButtonItem(text="🚮 Chiudi", callback_key=GlobalAction.CLOSE_MENU)]
        ],
        user_id=admin_id
    )


def _get_section_closing_admin_notification_text(context: CustomContext, section: RequestSection) -> str:
    """Build notification text for section closing."""
    config = getattr(getattr(context.pydb.configuration.settings.request, section.platform), section.category)
    assert isinstance(config, CategorySetting)

    if config.limit is None:
        raise RuntimeError(
            f"Request section {str(section)} limit cannot be reached if None "
            "(what triggered the notification?)"
        )

    cat_config = section.category_config

    text = ("📕 <b>Sezione Chiusa</b>\n\n"
            "<blockquote>ℹ <b>Info</b> – Il <b>limite di richieste</b> per la sezione\n\n"
            f"            {cat_config.icon} <b>{cat_config.label}</b> ({section.platform.label})\n\n"
            f"è stato appena <b>raggiunto</b> "
            f"(<i>{pluralize(config.limit, 'richiesta', 'richieste')}</i>) e tale <b>sezione è stata "
            f"chiusa</b>.</blockquote>\n\n"
            "🔹 Scegli un'opzione.")

    return text

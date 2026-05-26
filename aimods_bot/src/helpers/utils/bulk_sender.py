import asyncio
from time import time
from typing import Optional, Tuple

from pyrogram.errors import BadRequest
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.requests import BaseRequest, PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild(__name__)


MAX_MESSAGES_PER_SECOND = 20
BATCH_SIZE = 20
BATCH_DELAY = 1.0


def _parse_section(section: str) -> Optional[Tuple[str, str]]:
    """
    Parse section string into platform and category.

    Args:
        section: String in format "platform:category"

    Returns:
        Tuple of (platform, category) or None if invalid format
    """
    try:
        parts = section.split(":")
        if len(parts) != 2:
            return None
        return parts[0], parts[1]
    except Exception:
        return None


async def _send_single_opening_notification(
        context: CustomContext,
        user_id: int,
        platform: Platform,
        category: Category
) -> bool:
    """
    Send opening notification to a single user.

    Returns:
        True if sent successfully, False otherwise
    """
    deactivate_callback = f"user/manage_settings/notifications/section_opening/{platform}:{category}/from_notification"

    cat_config = PLATFORM_CATEGORY_REGISTRY[platform][category]
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="📭 <b>Sezione Richieste Aperta!</b>\n\n"
                 f"▫ La sezione {cat_config.icon} <b>{cat_config.label}</b> ({platform.label}) è ora aperta!\n\n"
                 "🔹 Scegli un'opzione.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text=f"{cat_config.icon} Formula Richiesta",
                        callback_data=f"user/add_request/{platform}/{category}/from_notification"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔕 Disattiva Notifiche Sezione",
                        callback_data=deactivate_callback
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
        log.debug(f"Opening notification sent successfully to user {user_id} [{platform.value}:{category.value}]")
        return True

    except BadRequest as e:
        log.warning(
            f"Unable to send notification to user {user_id} [{platform.value}:{category.value}] "
            f"(user may have blocked the bot): {e}"
        )
        return False

    except Exception as e:
        log.error(
            f"Unexpected error sending notification to user {user_id} [{platform.value}:{category.value}]: "
            f"{type(e).__name__}: {e}"
        )
        return False


async def send_opening_notifications(context: CustomContext, platform: Platform, category: Category):
    """
    Send opening notifications to all subscribed users with rate limiting.

    Respects Telegram's flood limits by sending messages in batches with delays.
    """
    start_time = time()

    cat_config = PLATFORM_CATEGORY_REGISTRY[platform][category]

    eligible_users = []
    for user_id in context.application.chat_data:
        cd = context.application.chat_data.get(user_id)
        if not isinstance(cd, ChatData):
            continue

        pl_settings = cd.persistent.user_notifications.section_opening_notifications.get(platform)
        if not pl_settings:
            continue

        ca_settings = pl_settings.get(category)
        if ca_settings:
            eligible_users.append(user_id)

    if not eligible_users:
        log.info(f"No eligible users for opening notification [{platform.value}:{category.value}]")
        return

    log.info(
        f"Starting opening notification batch for [{platform.value}:{category.value}] - "
        f"{len(eligible_users)} eligible users"
    )

    sent_count = 0
    error_count = 0

    for i in range(0, len(eligible_users), BATCH_SIZE):
        batch = eligible_users[i:i + BATCH_SIZE]
        batch_start = time()

        tasks = [
            _send_single_opening_notification(context=context, user_id=user_id, platform=platform, category=category)
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
        f"Opening notification batch completed [{platform.value}:{category.value}]: "
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
    text = _get_new_request_admin_notification_text(platform=request.platform, category=request.category)
    request_id = request.id

    await create_and_render_panel(
        update=update,
        context=context,
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
        ],
        user_id=admin_id
    )


def _get_new_request_admin_notification_text(platform: Platform, category: Category) -> str:
    cat_config = PLATFORM_CATEGORY_REGISTRY[platform][category]
    text = ("📬 <b>Nuova Richiesta Ricevuta</b>\n\n"
            "▫ È stata appena aggiunta una <b>nuova richiesta</b> per la sezione\n\n"
            f"            {cat_config.icon} <b>{cat_config.label}</b> ({platform.label})\n\n"
            "🔹 Scegli un'opzione.")
    return text


async def send_section_closing_admin_notification(
        update: Update,
        context: CustomContext,
        admin_id: int,
        section: str
):
    """Send notification to admin about section closing."""
    parsed = _parse_section(section)
    if not parsed:
        log.error(f"Invalid section format: '{section}'. Expected 'platform:category'")
        return

    pl, ca = parsed

    if not _validate_section_data(pl, ca):
        log.error(f"Validation failed for section '{section}'. Aborting notification send.")
        return

    text = _get_section_closing_admin_notification_text(context=context, pl=pl, ca=ca)

    await create_and_render_panel(
        update=update,
        context=context,
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
        ],
        user_id=admin_id
    )


def _get_section_closing_admin_notification_text(context: CustomContext, pl: str, ca: str) -> str:
    """Build notification text for section closing."""
    config = getattr(getattr(context.pydb.configuration.settings.request, pl), ca)
    assert isinstance(config, CategorySetting)
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = ("📕 <b>Sezione Chiusa</b>\n\n"
            "<blockquote>ℹ <b>Info</b> – Il <b>limite di richieste</b> per la sezione\n\n"
            f"            {ca_icon} <b>{ca_label}</b> ({pl_label})\n\n"
            f"è stato appena <b>raggiunto</b> "
            f"(<i>{pluralize(config.limit, 'richiesta', 'richieste')}</i>) e tale <b>sezione è stata "
            f"chiusa</b>.</blockquote>\n\n"
            "🔹 Scegli un'opzione.")

    return text

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import DEFAULT_SECTION_OPENING_NOTIFICATION
from aimods_bot.src.helpers.models.request_section import RequestSection


async def handle_user_section_opening_notification_toggle(
        context: CustomContext,
        section: RequestSection
):
    settings = context.pydc.persistent.user_notifications.section_opening_notifications

    platform_settings = settings.setdefault(section.platform, {})
    current = platform_settings.get(section.category, DEFAULT_SECTION_OPENING_NOTIFICATION)
    platform_settings[section.category] = not current

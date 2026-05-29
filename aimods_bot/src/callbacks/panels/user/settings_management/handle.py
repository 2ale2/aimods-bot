from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.request_section import RequestSection


async def handle_user_section_opening_notification_toggle(
        context: CustomContext,
        section: RequestSection
):
    settings = context.pydc.persistent.user_notifications.section_opening_notifications

    settings[section.platform][section.category] = not settings[section.platform][section.category]

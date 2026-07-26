from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.request_section import RequestSection


async def handle_admin_new_requests_notification_toggle(context: CustomContext, section: RequestSection):
    settings = context.pydc.persistent.admin_notifications.new_requests_notifications

    settings[section.platform][section.category] = not settings[section.platform][section.category]


async def handle_admin_section_closing_notification_toggle(context: CustomContext, section: RequestSection):
    settings = context.pydc.persistent.admin_notifications.section_closing_notifications

    settings[section.platform][section.category] = not settings[section.platform][section.category]

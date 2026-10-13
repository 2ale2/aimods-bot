from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.features.requests.section import RequestSection


async def handle_admin_new_requests_notification_toggle(
        context: CustomContext,
        section: RequestSection,
        value: bool | None = None
):
    """Inverte la notifica, oppure la imposta a `value` se indicato (i tasti «Disattiva» delle notifiche)."""
    settings = context.pydc.persistent.admin_notifications.new_requests_notifications
    current = settings[section.platform][section.category]
    settings[section.platform][section.category] = (not current) if value is None else value


async def handle_admin_section_closing_notification_toggle(
        context: CustomContext,
        section: RequestSection,
        value: bool | None = None
):
    """Inverte la notifica, oppure la imposta a `value` se indicato (i tasti «Disattiva» delle notifiche)."""
    settings = context.pydc.persistent.admin_notifications.section_closing_notifications
    current = settings[section.platform][section.category]
    settings[section.platform][section.category] = (not current) if value is None else value

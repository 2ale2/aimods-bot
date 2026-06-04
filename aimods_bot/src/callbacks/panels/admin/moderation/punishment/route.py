from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_type, \
    set_punishment_duration, set_as_parent
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.render import render_punishment_panel, \
    render_punishment_duration_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import PunishmentRoute, SecurityFiltersRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


async def punishment_route(
        update: Update,
        context: CustomContext,
        setting: str,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_punishment_panel(update=update, context=context, setting=setting)
            return PCS.ADMIN_CONVERSATION

        case [punishment_type] if punishment_type in (
            PunishmentRoute.WARN,
            PunishmentRoute.KICK,
            PunishmentRoute.MUTE,
            PunishmentRoute.BAN
        ):
            await set_punishment_type(context=context, setting=setting, punishment=punishment_type)
            await render_punishment_panel(update=update, context=context, setting=setting)
            return PCS.ADMIN_CONVERSATION

        case [PunishmentRoute.DURATION, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    await render_punishment_duration_panel(update=update, context=context, setting=setting)
                    return PCS.SET_PUNISHMENT_DURATION
                case [PunishmentRoute.DURATION_ENDLESS]:
                    return await set_punishment_duration(update=update, context=context)

        case [security_filter] if security_filter in (
            SecurityFiltersRoute.ANTISPAM,
            SecurityFiltersRoute.ANTIFLOOD
        ):
            # L'utente ha scelto di impostare la punizione come la macro categoria
            return await set_as_parent(update=update, context=context, setting=setting)
